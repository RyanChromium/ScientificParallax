from __future__ import annotations

import json
from pathlib import Path

import pytest

from scientific_parallax.discovery import latent_final_world
from scientific_parallax.discovery.latent_final_world import (
    evaluate_latent_final_world_once,
    freeze_latent_strategy,
    provision_latent_final_world,
)
from scientific_parallax.discovery.latent_runner import (
    _confirmatory_decision,
    _wilson_bound,
)

CONFIG_PATH = Path("configs/experiments/latent-discovery-confirmatory-v1.json")


def test_wilson_bounds_support_preregistered_sample_sizes() -> None:
    assert _wilson_bound(20, 20, upper=False) > 0.80
    assert _wilson_bound(0, 30, upper=True) < 0.10


def test_confirmatory_decision_keeps_h3_and_h2_separate() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    capability = {
        "task_success_rate_one_sided_95_lower": 0.88,
        "held_out_improvement_interval": [0.50, 0.80],
        "null_false_positive_one_sided_95_upper": 0.08,
        "all_successful_structures_have_multistep_lineage": True,
    }
    comparison = {"confidence_interval": [-0.1, 0.1]}
    mechanism = {"confidence_interval": [0.2, 0.8]}
    decision = _confirmatory_decision(capability, comparison, mechanism, {"valid": True}, config)
    assert decision == {
        "h3": "go",
        "h1": "supported",
        "h2": "rejected",
        "overall": "scientifically_meaningful_mixed_result",
    }


def test_provision_and_freeze_return_no_hidden_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "sealed"
    summary = provision_latent_final_world(
        config_path=CONFIG_PATH,
        output_root=root,
        development_root=Path.cwd(),
    )
    assert summary["task_count"] == 50
    assert not summary["task_contents_returned"]
    assert not (root / "strategy-freeze.json").exists()
    assert not (root / "access-log.json").exists()
    monkeypatch.setattr(
        latent_final_world,
        "capture_environment",
        lambda _: {"git_dirty": False, "git_revision": "a" * 40},
    )
    freeze = freeze_latent_strategy(
        config_path=CONFIG_PATH,
        sealed_root=root,
        development_root=Path.cwd(),
    )
    assert freeze["code_revision"] == "a" * 40
    assert len(freeze["strategy_hash"]) == 64
    with pytest.raises(FileExistsError):
        freeze_latent_strategy(
            config_path=CONFIG_PATH,
            sealed_root=root,
            development_root=Path.cwd(),
        )


def test_small_confirmatory_world_is_one_shot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config.update(
        {
            "truth_clusters": config["truth_clusters"][:2],
            "seeds_per_truth_cluster": 1,
            "grid_size": 8,
            "steps": 8,
            "sample_every": 4,
            "world_query_budget": 4,
            "candidate_generation_budget": 64,
            "candidate_evaluation_budget": 1024,
            "maximum_candidates": 20,
            "active_candidates": 6,
            "maximum_questions": 5,
            "eig_samples": 8,
            "persistence_checkpoints": 2,
            "bootstrap_samples": 20,
        }
    )
    config_path = tmp_path / "confirmatory.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    root = tmp_path / "sealed"
    provision_latent_final_world(
        config_path=config_path, output_root=root, development_root=Path.cwd()
    )
    monkeypatch.setattr(
        latent_final_world,
        "capture_environment",
        lambda _: {"git_dirty": False, "git_revision": "b" * 40},
    )
    freeze_latent_strategy(config_path=config_path, sealed_root=root, development_root=Path.cwd())
    report = evaluate_latent_final_world_once(
        config_path=config_path, sealed_root=root, development_root=Path.cwd()
    )
    assert report["task_count"] == 32
    assert report["run_count"] == 44
    assert report["status"] == "latent_discovery_confirmatory_complete"
    assert (root / "access-log.json").is_file()
    assert (root / "result.json").is_file()
    with pytest.raises(FileExistsError):
        evaluate_latent_final_world_once(
            config_path=config_path, sealed_root=root, development_root=Path.cwd()
        )
