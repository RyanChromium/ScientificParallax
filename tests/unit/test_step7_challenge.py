from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from scientific_parallax.challenge.blind import DevelopmentBlindTask, anonymous_task_token
from scientific_parallax.challenge.runner import (
    _build_development_tasks,
    _decision,
    _QuestionDiagnostic,
    _validate_config,
    run_step7_development_challenge,
)
from scientific_parallax.challenge.scoring import score_endpoint, score_truth_rank

CONFIG_PATH = Path("configs/experiments/step7-blind-development.json")


def _config() -> dict[str, object]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_blind_view_excludes_evaluator_coordinates_and_seeds() -> None:
    tasks = _build_development_tasks(_config())
    assert len(tasks) == 30
    assert all(isinstance(item, DevelopmentBlindTask) for item in tasks)
    assert set(asdict(tasks[0].view)) == {"task_token", "capabilities", "summary_dimension"}
    assert "cluster" not in asdict(tasks[0].view)
    assert anonymous_task_token(1, 2, 3) == anonymous_task_token(1, 2, 3)


def test_selection_diagnostic_cannot_carry_experiment_or_seed() -> None:
    assert set(_QuestionDiagnostic.__dataclass_fields__) == {
        "experiment_hash",
        "expected_information_gain",
        "disagreement",
        "weighted_cost",
    }


def test_independent_scorer_uses_anonymous_tie_break_and_persistence() -> None:
    posterior = {"truth": 0.5, "other": 0.5}
    aliases = {"truth": "b", "other": "a"}
    assert score_truth_rank(posterior, aliases, "truth") == 2
    endpoint = score_endpoint(
        [6, 5, 4, 3, 2, 1],
        posterior,
        "truth",
        top_k=5,
        persistence=5,
    )
    assert endpoint.stable_identification_query == 2


@pytest.mark.parametrize(
    ("interval", "expected"),
    [([0.21, 0.40], "go"), ([0.10, 0.30], "redo"), ([-0.10, 0.19], "stop")],
)
def test_three_way_decision(interval: list[float], expected: str) -> None:
    assert _decision(interval, 0.20) == expected


def test_configuration_requires_all_preregistered_arms() -> None:
    config = _config()
    config["arms"] = config["arms"][:-1]
    with pytest.raises(ValueError, match="complete preregistered"):
        _validate_config(config)


def test_small_complete_challenge_is_reproducible(tmp_path: Path) -> None:
    config = _config()
    config.update(
        {
            "seeds_per_cluster": 1,
            "grid_size": 8,
            "steps": 3,
            "world_query_budget": 5,
            "maximum_candidates": 8,
            "active_candidates": 4,
            "maximum_questions": 5,
            "eig_samples": 8,
            "bootstrap_samples": 20,
        }
    )
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    report = run_step7_development_challenge(config_path, tmp_path / "run")
    assert report["task_count"] == 6
    assert report["run_count"] == 48
    assert report["checks"]["all_resource_ceilings_respected"]
    assert report["checks"]["strategy_view_excludes_cluster_truth_and_seeds"]
    assert report["decision"] in {"go", "redo", "stop"}
    assert (tmp_path / "run" / "manifest.json").is_file()
