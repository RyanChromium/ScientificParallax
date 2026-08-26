"""Synthetic-truth dry run for all Step 3.5 protocol mechanisms."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.baselines.gray_scott import GrayScottBaselineConfig, baseline_question_pool
from scientific_parallax.core.reproducibility import (
    ExperimentIdentity,
    RunManifest,
    capture_environment,
    content_hash,
)
from scientific_parallax.protocol.controls import residual_shuffle_control
from scientific_parallax.protocol.evidence_layers import (
    CandidateEvidenceState,
    ProtocolGate,
    ProtocolSpec,
    SurvivalPolicy,
    SurvivalStatus,
    calibrate_noise,
)
from scientific_parallax.protocol.paradigm_ir import (
    LawTerm,
    MeasurementModel,
    ParadigmIR,
    Scope,
    StateVariable,
    equivalent_under_declared_transforms,
)
from scientific_parallax.protocol.statistics import stratified_bootstrap_effect
from scientific_parallax.step0.benchmark import run_negative_control
from scientific_parallax.worlds.gray_scott import GrayScottWorld


def gray_scott_ir(paradigm_id: str, u_name: str = "u", v_name: str = "v") -> ParadigmIR:
    return ParadigmIR(
        paradigm_id,
        (StateVariable(u_name), StateVariable(v_name)),
        (
            LawTerm(u_name, "laplacian", (u_name,), "D_u"),
            LawTerm(v_name, "laplacian", (v_name,), "D_v"),
            LawTerm(u_name, "product", (u_name, v_name, v_name), "reaction"),
            LawTerm(v_name, "product", (u_name, v_name, v_name), "reaction"),
            LawTerm(u_name, "source", (u_name,), "feed"),
            LawTerm(v_name, "decay", (v_name,), "feed_plus_kill"),
        ),
        MeasurementModel((u_name, v_name), decoder_cost=0.0),
        Scope("development-grid", ("periodic", "reflecting"), "anonymous_linear_mix"),
    )


def protocol_spec_from_config(config: dict[str, Any]) -> ProtocolSpec:
    return ProtocolSpec(
        config["protocol_id"],
        "paradigm-ir-v0.1",
        "canonical finite-variable permutations plus equal intervention behavior",
        "fixed calibrated likelihood owned by EvidenceEngine",
        "development-world residual calibration frozen before final evaluation",
        "hard viability gate followed by frozen niche capacities",
        config["primary_endpoint"],
        {
            "top_k": config["ranking_threshold_k"],
            "persistence_checkpoints": config["persistence_checkpoints"],
        },
        "right-censored restricted mean time with stratified bootstrap",
        config["minimum_relative_effect"],
        {
            "world_queries": config["world_query_budget"],
            "candidate_generation": config["candidate_generation_budget"],
            "candidate_evaluation": config["candidate_evaluation_budget"],
            "cpu_hours": config["cpu_hour_budget"],
        },
        ("random", "coverage", "bayesian_design_same_generator"),
        ("no_question_evolution", "no_representation_mutation", "no_niches"),
        "stop on Step 0 no-go, leakage, irreproducible ledger, or null-effect upper bound",
    )


def run_protocol_dry_run(config_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite protocol dry-run directory: {output_dir}")
    output_dir.mkdir(parents=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    first = gray_scott_ir("original")
    renamed = gray_scott_ir("renamed", "chemical_a", "chemical_b")
    changed = gray_scott_ir("changed")
    changed = ParadigmIR(
        changed.paradigm_id,
        changed.variables,
        changed.terms[:-1],
        changed.measurement,
        changed.scope,
    )
    behavior = np.asarray([0.1, 0.2, 0.3, 0.5])
    equivalence_checks = {
        "renaming_collapses": equivalent_under_declared_transforms(
            first, renamed, behavior, behavior
        ),
        "structural_change_remains_distinct": not equivalent_under_declared_transforms(
            first, changed, behavior, behavior
        ),
    }

    leakage_blocked = False
    second_open_blocked = False
    evaluator = ProtocolGate(lambda strategy_hash: {"strategy_hash": strategy_hash, "score": 1.0})
    try:
        evaluator.final_evaluate_once("strategy-v1")
    except PermissionError:
        leakage_blocked = True
    spec = protocol_spec_from_config(config)
    evaluator.freeze(spec, "strategy-v1")
    final_result = evaluator.final_evaluate_once("strategy-v1")
    try:
        evaluator.final_evaluate_once("strategy-v1")
    except RuntimeError:
        second_open_blocked = True

    effect = stratified_bootstrap_effect(
        {"cluster-a": [70, 80, 75], "cluster-b": [90, 85, 95]},
        {"cluster-a": [120, 130, 125], "cluster-b": [150, 145, None]},
        budget=config["world_query_budget"],
        samples=1000,
        seed=config["seed"],
    )
    residuals = np.sin(np.linspace(0.0, 8.0, 200))
    shuffle = residual_shuffle_control(residuals, config["seed"])
    calibrated_noise = calibrate_noise(residuals[:50], floor=0.01)
    survival_policy = SurvivalPolicy(dormancy_after=2, death_after=4)

    gs_config = GrayScottBaselineConfig()
    questions = baseline_question_pool(gs_config)
    world = GrayScottWorld()
    pool_stencil_updates = sum(world.estimate_cost(question) for question in questions)
    average_evaluation_updates = pool_stencil_updates / len(questions)
    benchmark_start = time.perf_counter()
    world.observe(questions[0])
    benchmark_seconds = max(time.perf_counter() - benchmark_start, 1e-9)
    updates_per_second = world.estimate_cost(questions[0]) / benchmark_seconds
    projected_stencil_updates = average_evaluation_updates * config["candidate_evaluation_budget"]
    projected_cpu_hours = projected_stencil_updates / updates_per_second / 3600.0
    checks = {
        **equivalence_checks,
        "final_world_blocked_before_freeze": leakage_blocked,
        "final_world_single_use": second_open_blocked,
        "final_result_bound_to_strategy": final_result["strategy_hash"] == "strategy-v1",
        "synthetic_effect_recovered": effect.relative_query_reduction
        > config["minimum_relative_effect"],
        "residual_shuffle_breaks_structure": abs(shuffle.shuffled_lag_correlation)
        < abs(shuffle.original_lag_correlation),
        "noise_calibration_has_positive_floor": calibrated_noise >= 0.01,
        "survival_policy_transitions": (
            survival_policy.classify(CandidateEvidenceState("a", 0)) == SurvivalStatus.ACTIVE
            and survival_policy.classify(CandidateEvidenceState("a", 2)) == SurvivalStatus.DORMANT
            and survival_policy.classify(CandidateEvidenceState("a", 4)) == SurvivalStatus.DEAD
            and survival_policy.classify(CandidateEvidenceState("a", 0, 1)) == SurvivalStatus.DEAD
        ),
        "contradictory_control_rejected": run_negative_control(config["seed"])["final_posterior"]
        < 1.0 / 9.0,
    }
    report = {
        "status": "ready_for_protocol_freeze_review" if all(checks.values()) else "redo",
        "scope": "development worlds and synthetic truth only",
        "protocol_hash": spec.protocol_hash,
        "checks": checks,
        "statistics_dry_run": asdict(effect),
        "residual_control": {
            "original_lag_correlation": shuffle.original_lag_correlation,
            "shuffled_lag_correlation": shuffle.shuffled_lag_correlation,
            "calibrated_noise": calibrated_noise,
        },
        "budget_projection": {
            "question_pool": len(questions),
            "full_pool_single_candidate_stencil_updates": pool_stencil_updates,
            "average_candidate_evaluation_stencil_updates": average_evaluation_updates,
            "declared_candidate_evaluation_ceiling": config["candidate_evaluation_budget"],
            "projected_ceiling_stencil_updates": projected_stencil_updates,
            "measured_stencil_updates_per_second": updates_per_second,
            "projected_cpu_hours_from_microbenchmark": projected_cpu_hours,
            "note": (
                "Single-process microbenchmark projection; profile the frozen evaluation mix "
                "again immediately before PF."
            ),
        },
        "protocol_freeze_candidate": asdict(spec),
        "warning": (
            "This dry run does not open or define the future final sealed Gray–Scott worlds."
        ),
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    environment = capture_environment(Path.cwd())
    identity = ExperimentIdentity(
        config["protocol_id"],
        config,
        config["seed"],
        environment["git_revision"],
    )
    RunManifest(
        1,
        identity.experiment_id,
        config["protocol_id"],
        identity.config_hash,
        config["seed"],
        environment,
        {"config": str(config_path)},
        {"report": str(report_path), "report_hash": content_hash(report)},
    ).write_once(output_dir / "manifest.json")
    return report
