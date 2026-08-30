from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from scientific_parallax.discovery import mechanism_audit as audit_module
from scientific_parallax.discovery.latent_model import LatentCandidate, two_state_founders
from scientific_parallax.discovery.latent_runner import ARM_POLICIES, _build_tasks, _run_task
from scientific_parallax.discovery.mechanism_audit import (
    POLICIES,
    _interval,
    fixed_reference,
    graph_descriptor,
    load_config,
    retain_archive,
    run_audit,
    run_task,
    search,
    training_choice,
)
from scientific_parallax.worlds.latent_gray_scott import LatentGrayScottWorld, LatentLaw

CONFIG = Path("configs/experiments/mechanism-audit-development-v1.json")


@pytest.fixture
def small_config():
    audit, config = load_config(CONFIG, Path.cwd())
    audit["workers"] = 1
    config.update(
        truth_clusters=config["truth_clusters"][:2],
        seeds_per_truth_cluster=1,
        null_control_seeds=1,
        grid_size=8,
        steps=8,
        sample_every=4,
        world_query_budget=4,
        candidate_generation_budget=64,
        candidate_evaluation_budget=1024,
        maximum_candidates=24,
        active_candidates=6,
        maximum_questions=5,
        eig_samples=8,
        persistence_checkpoints=2,
        bootstrap_samples=20,
    )
    return audit, config


@pytest.mark.parametrize("arm,legacy", [("p0e0", "no_niches"), ("p1e1", "coevolution")])
def test_factorial_corners_reproduce_frozen_v2_trajectories(small_config, arm, legacy):
    audit, config = small_config
    task = _build_tasks(config)[0]
    old = _run_task(task, legacy, ARM_POLICIES[legacy], config, 0)
    new = run_task(task, arm, config, audit)
    assert new["compatibility_v2_success"] == old["success"]
    assert new["compatibility_v2_query"] == old["stable_discovery_query"]
    assert [x["question_hash"] for x in new["trace"]] == [
        x["selected_question_hash"] for x in old["rounds"]
    ]
    assert [x["prediction_commitment"] for x in new["trace"]] == [
        x["prediction_commitment"] for x in old["rounds"]
    ]
    for key in ("world_queries", "candidate_generations", "candidate_evaluations"):
        assert new["budget"][key] == old["budget"][key]


@pytest.mark.parametrize("priority", [0, 1])
def test_ensemble_only_toggle_has_no_effect_on_passive_search(small_config, priority):
    audit, config = small_config
    task = _build_tasks(config)[0]
    rows = [run_task(task, f"passive_p{priority}e{e}", config, audit) for e in range(2)]
    assert rows[0]["trace"] == rows[1]["trace"]
    assert rows[0]["validation_rmse"] == rows[1]["validation_rmse"]
    assert rows[0]["budget"] == rows[1]["budget"]


def test_graph_descriptor_is_parameter_and_label_invariant():
    founder = two_state_founders()[0]
    renamed = replace(
        founder, candidate_id="not-a-stage-label", law=replace(founder.law, reaction_scale=1.2)
    )
    assert graph_descriptor(founder) == graph_descriptor(renamed)
    assert graph_descriptor(founder)[0] == 2
    hidden = LatentCandidate("hidden", LatentLaw(True, False, False), 0, None, None)
    driven = replace(hidden, law=LatentLaw(True, True, False))
    feedback = replace(hidden, law=LatentLaw())
    assert len({graph_descriptor(x) for x in (founder, hidden, driven, feedback)}) == 4


def test_map_archive_preserves_data_best_model_per_graph_cell():
    founders = two_state_founders()
    hidden = LatentCandidate("hidden", LatentLaw(True, False, False), 0, None, None)
    candidates = {item.candidate_id: item for item in (*founders, hidden)}
    posterior = {key: 1 / len(candidates) for key in candidates}
    aliases = {key: key for key in candidates}
    kept = retain_archive(set(candidates), candidates, posterior, aliases, 4, "map_elites")
    assert len(kept) == 2
    assert hidden.candidate_id in kept
    scalar = retain_archive(set(candidates), candidates, posterior, aliases, 4, "scalar_archive")
    assert len(scalar) == 4
    assert hidden.candidate_id not in scalar


def test_training_selection_does_not_require_a_latent_variable():
    founder = two_state_founders()[0]
    hidden = LatentCandidate("hidden", LatentLaw(), 0, None, None)
    candidates = {x.candidate_id: x for x in (founder, hidden)}
    aliases = {key: key for key in candidates}
    assert (
        training_choice(candidates, {founder.candidate_id: 0.9, "hidden": 0.1}, aliases)
        == founder.candidate_id
    )


def test_search_only_accesses_requested_training_questions(small_config):
    audit, config = small_config
    task = _build_tasks(config)[0]
    heldout = {experiment.content_hash for experiment in task.validation}
    calls = []
    world = LatentGrayScottWorld(task.measurement_seed, task.law)

    def observe(experiment):
        assert experiment.content_hash not in heldout
        calls.append(experiment.content_hash)
        return world.observe(experiment)

    result = search(
        task.task_token,
        task.questions,
        observe,
        POLICIES["p1e1"],
        config,
        audit["archive_capacity"],
    )
    assert len(calls) == config["world_query_budget"]
    assert len(result["history"]) == len(calls)


def test_cluster_interval_is_reproducible_and_paired_zero_is_exact():
    values = [("a", 0.0), ("a", 0.0), ("b", 0.0)]
    first = _interval(values, 20, 14)
    assert first == _interval(values, 20, 14)
    assert first["interval_95"] == [0.0, 0.0]
    assert first["cluster_count"] == 2
    assert np.isfinite(first["mean"])


def test_fixed_reference_uses_the_same_noise_weighting_as_search(monkeypatch, small_config):
    _, config = small_config
    experiment = _build_tasks(config)[0].questions[0]

    def fake_predict(candidate, experiment, cache, budget):
        # Unweighted SSE prefers 1.0; calibrated likelihood correctly prefers 0.8.
        return (
            (0.0, 0.0, 0.030, 0.0)
            if candidate.law.reaction_scale == 0.8
            else (0.025, 0.0, 0.0, 0.0)
        )

    monkeypatch.setattr(audit_module, "_predict", fake_predict)
    chosen, _ = fixed_reference([(experiment, (0.0, 0.0, 0.0, 0.0))], [0.8, 1.0], 0.015)
    assert chosen.law.reaction_scale == 0.8


def test_frozen_validation_rejects_dirty_revision(tmp_path, small_config, monkeypatch):
    audit, config = small_config
    audit["scope"] = "frozen_validation"
    audit["overrides"] = config
    path = tmp_path / "frozen.json"
    path.write_text(json.dumps(audit))
    monkeypatch.setattr(
        audit_module, "capture_environment", lambda _: {"git_dirty": True, "git_revision": "test"}
    )
    with pytest.raises(RuntimeError, match="clean committed"):
        run_audit(path, tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_development_v2_fixed_grid_includes_every_founder():
    audit, _ = load_config(
        Path("configs/experiments/mechanism-audit-development-v2.json"), Path.cwd()
    )
    assert {item.law.reaction_scale for item in two_state_founders()} <= set(
        audit["fixed_reaction_scales"]
    )


def test_small_audit_records_every_arm_and_refuses_overwrite(tmp_path, small_config):
    audit, config = small_config
    audit["overrides"] = config
    path = tmp_path / "config.json"
    path.write_text(json.dumps(audit))
    report = run_audit(path, tmp_path / "output")
    assert report["run_count"] == 3 * len(POLICIES)
    assert report["status"] == "complete"
    assert all(report["checks"].values())
    assert (tmp_path / "output" / "registration.json").is_file()
    with pytest.raises(FileExistsError):
        run_audit(path, tmp_path / "output")


def test_v2_frozen_components_remain_byte_identical():
    record = json.loads(
        Path("artifacts/protocol-v2/confirmatory-v1/strategy-freeze.json").read_text()
    )
    for name, digest in record["component_hashes"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    assert (
        hashlib.sha256(
            Path("configs/experiments/latent-discovery-confirmatory-v1.json").read_bytes()
        ).hexdigest()
        == record["config_file_sha256"]
    )
