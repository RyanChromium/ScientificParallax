from __future__ import annotations

import json
from pathlib import Path

from scientific_parallax.discovery.latent_runner import run_latent_discovery_pilot

CONFIG_PATH = Path("configs/experiments/latent-discovery-pilot.json")


def test_small_latent_pilot_runs_complete_comparison(tmp_path: Path) -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config.update(
        {
            "truth_clusters": config["truth_clusters"][:2],
            "seeds_per_truth_cluster": 1,
            "null_control_seeds": 1,
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
    config_path = tmp_path / "pilot.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    report = run_latent_discovery_pilot(config_path, tmp_path / "run")
    assert report["task_count"] == 3
    assert report["run_count"] == 21
    assert report["checks"]["ordinary_founders_all_structurally_wrong"]
    assert report["checks"]["fixed_representation_never_adds_latent"]
    assert report["checks"]["held_out_conditions_never_queried"]
    assert report["checks"]["null_world_controls_present"]
    assert report["pilot_decision"] in {
        "iterate_capability",
        "capability_only_iterate_comparative_strategy",
        "eligible_to_preregister_v2",
    }
    assert (tmp_path / "run" / "manifest.json").is_file()
