"""Synthetic-truth dry run for all Step 3.5 protocol mechanisms."""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.baselines.gray_scott import GrayScottBaselineConfig, baseline_question_pool
from scientific_parallax.core.budget import BudgetLedger, BudgetLimits
from scientific_parallax.core.data_manifest import load_dataset_manifest
from scientific_parallax.core.environment_spec import load_environment_spec, runtime_matches
from scientific_parallax.core.reproducibility import (
    ExperimentIdentity,
    RunManifest,
    capture_environment,
    content_hash,
)
from scientific_parallax.protocol.candidate_generator import (
    CandidateGeneratorSpec,
    FiniteCandidateGenerator,
)
from scientific_parallax.protocol.controls import residual_shuffle_control
from scientific_parallax.protocol.design import (
    build_task_design,
    estimate_clustered_power,
    frozen_candidate_clusters,
)
from scientific_parallax.protocol.evidence_layers import (
    CandidateEvidenceState,
    ProtocolGate,
    ProtocolSpec,
    SurvivalPolicy,
    SurvivalStatus,
    calibrate_noise,
)
from scientific_parallax.protocol.numerics import (
    NumericalTolerance,
    compare_primary_and_reference,
)
from scientific_parallax.protocol.paradigm_ir import (
    LawTerm,
    MeasurementModel,
    ParadigmIR,
    Scope,
    StateVariable,
    equivalent_under_declared_transforms,
)
from scientific_parallax.protocol.statistics import (
    stable_identification_query,
    stratified_bootstrap_effect,
)
from scientific_parallax.step0.benchmark import run_negative_control
from scientific_parallax.worlds.gray_scott import GrayScottWorld


def validate_protocol_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1:
        raise ValueError("unsupported protocol configuration schema")
    expected_methods = {
        "primary_solver": "five_point",
        "primary_integrator": "euler",
        "reference_solver": "nine_point",
        "reference_integrator": "rk4",
    }
    if config["numerical_methods"] != expected_methods:
        raise ValueError("configured numerical methods do not match the implemented diagnostic")
    generator = config["candidate_generator"]
    if generator["maximum_offspring_per_parent"] > config["candidate_generation_budget"]:
        raise ValueError("per-parent mutation attempts exceed the candidate generation budget")
    if generator["maximum_candidates_per_task"] > config["candidate_generation_budget"]:
        raise ValueError("per-task candidates exceed the candidate generation budget")
    if config["persistence_checkpoints"] > config["world_query_budget"]:
        raise ValueError("endpoint persistence exceeds the world query budget")
    power = config["power_design"]
    if power["design_detectable_effect"] not in power["assumed_relative_effects"]:
        raise ValueError("detectable effect must be included in the simulated power curve")


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
    validate_protocol_config(config)
    candidate_generator = CandidateGeneratorSpec(
        version=config["candidate_generator"]["version"],
        allowed_mutations=tuple(config["candidate_generator"]["allowed_mutations"]),
        maximum_offspring_per_parent=config["candidate_generator"]["maximum_offspring_per_parent"],
        maximum_candidates_per_task=config["candidate_generator"]["maximum_candidates_per_task"],
    )
    clusters = frozen_candidate_clusters(config["task_design"]["steps"])
    cluster_hash = content_hash([asdict(cluster) for cluster in clusters])
    task_design = build_task_design(**config["task_design"])
    task_design_hash = content_hash([asdict(task) for task in task_design])
    external_manifest = load_dataset_manifest(Path(config["external_data_manifest"]))
    external_fixture_manifest = load_dataset_manifest(Path(config["external_fixture_manifest"]))
    environment_lock = load_environment_spec(Path(config["execution_environment_spec"]), Path.cwd())
    return ProtocolSpec(
        schema_version=1,
        protocol_id=config["protocol_id"],
        paradigm_ir_version="paradigm-ir-v0.1/schema-v1",
        candidate_generator_hash=candidate_generator.spec_hash,
        measurement_cluster_hash=cluster_hash,
        task_design_hash=task_design_hash,
        external_data_manifest_hash=content_hash(external_manifest),
        external_fixture_manifest_hash=content_hash(external_fixture_manifest),
        execution_environment_hash=content_hash(environment_lock),
        equivalence_rule="canonical finite-variable permutations plus equal intervention behavior",
        evidence_update_rule="fixed calibrated likelihood owned by EvidenceEngine",
        noise_calibration_rule=(
            "development-world residual standard deviation with frozen positive floor"
        ),
        noise_calibration_parameters=config["noise_calibration"],
        survival_rule="hard viability gate followed by frozen niche capacities",
        survival_parameters=config["survival_parameters"],
        viability_thresholds=config["viability_thresholds"],
        niche_capacities=config["niche_capacities"],
        primary_endpoint=config["primary_endpoint"],
        endpoint_parameters={
            "top_k": config["ranking_threshold_k"],
            "persistence_checkpoints": config["persistence_checkpoints"],
        },
        statistical_method="right-censored restricted mean time with stratified bootstrap",
        statistical_parameters=config["statistical_parameters"],
        minimum_relative_effect=config["minimum_relative_effect"],
        numerical_methods=config["numerical_methods"],
        numerical_tolerances=config["numerical_tolerances"],
        power_design=config["power_design"],
        budgets={
            "world_queries": config["world_query_budget"],
            "candidate_generation": config["candidate_generation_budget"],
            "candidate_evaluation": config["candidate_evaluation_budget"],
            "cpu_hours": config["cpu_hour_budget"],
        },
        budget_scope=config["budget_scope"],
        evaluation_accounting=config["evaluation_accounting"],
        baselines=("random", "coverage", "bayesian_design_same_generator"),
        ablations=("no_question_evolution", "no_representation_mutation", "no_niches"),
        stop_rule=(
            "stop on Step 0 no-go, leakage, irreproducible ledger, or null-effect upper bound"
        ),
    )


def run_protocol_dry_run(config_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite protocol dry-run directory: {output_dir}")
    output_dir.mkdir(parents=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_protocol_config(config)
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
    environment_spec = load_environment_spec(Path(config["execution_environment_spec"]), Path.cwd())
    environment_matches = runtime_matches(environment_spec)
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
    calibrated_noise = calibrate_noise(residuals[:50], floor=config["noise_calibration"]["floor"])
    survival_policy = SurvivalPolicy(**config["survival_parameters"])

    task_design = build_task_design(**config["task_design"])
    diagnostic_tasks = build_task_design(
        seeds_per_cluster=1,
        grid_size=config["task_design"]["grid_size"],
        steps=config["task_design"]["steps"],
    )
    numerical_tolerance = NumericalTolerance(**config["numerical_tolerances"])
    numerical_agreements = [
        compare_primary_and_reference(task.experiment, numerical_tolerance)
        for task in diagnostic_tasks
    ]
    candidate_spec = CandidateGeneratorSpec(
        version=config["candidate_generator"]["version"],
        allowed_mutations=tuple(config["candidate_generator"]["allowed_mutations"]),
        maximum_offspring_per_parent=config["candidate_generator"]["maximum_offspring_per_parent"],
        maximum_candidates_per_task=config["candidate_generator"]["maximum_candidates_per_task"],
    )
    candidate_generator = FiniteCandidateGenerator(candidate_spec)
    generation_batch = candidate_generator.generate_with_accounting(first)
    generated_candidates = generation_batch.candidates
    generated_again = candidate_generator.generate(first)
    power_estimates = [
        estimate_clustered_power(
            assumed_relative_effect=assumed_effect,
            seeds_per_cluster=config["task_design"]["seeds_per_cluster"],
            budget=config["world_query_budget"],
            minimum_effect=config["minimum_relative_effect"],
            simulations=config["power_design"]["simulations"],
            bootstrap_samples=config["power_design"]["bootstrap_samples"],
            seed=config["seed"],
        )
        for assumed_effect in config["power_design"]["assumed_relative_effects"]
    ]
    detectable_effect = config["power_design"]["design_detectable_effect"]
    detectable_power = next(
        item.estimated_power
        for item in power_estimates
        if item.assumed_relative_effect == detectable_effect
    )

    accounting = BudgetLedger(
        BudgetLimits(
            config["world_query_budget"],
            config["candidate_generation_budget"],
            config["candidate_evaluation_budget"],
        )
    )
    accounting.charge_world_query()
    accounting.charge_candidate_generation(generation_batch.attempted_mutations)
    accounting.charge_candidate_evaluation()
    accounting.charge_candidate_evaluation(cache_hit=True)

    gs_config = GrayScottBaselineConfig()
    questions = baseline_question_pool(gs_config)
    world = GrayScottWorld()
    frozen_task_stencil_updates = sum(world.estimate_cost(task.experiment) for task in task_design)
    average_evaluation_updates = frozen_task_stencil_updates / len(task_design)
    benchmark_start = time.perf_counter()
    world.observe(task_design[0].experiment)
    benchmark_seconds = max(time.perf_counter() - benchmark_start, 1e-9)
    updates_per_second = world.estimate_cost(task_design[0].experiment) / benchmark_seconds
    projected_stencil_updates = average_evaluation_updates * config["candidate_evaluation_budget"]
    projected_cpu_hours = projected_stencil_updates / updates_per_second / 3600.0
    checks = {
        **equivalence_checks,
        "final_world_blocked_before_freeze": leakage_blocked,
        "final_world_single_use": second_open_blocked,
        "final_result_bound_to_strategy": final_result["strategy_hash"] == "strategy-v1",
        "synthetic_effect_recovered": effect.relative_query_reduction
        > config["minimum_relative_effect"],
        "primary_endpoint_is_executable": stable_identification_query(
            [8, 6, 5, 4, 3, 2, 2],
            top_k=config["ranking_threshold_k"],
            persistence=config["persistence_checkpoints"],
        )
        == 3,
        "residual_shuffle_breaks_structure": abs(shuffle.shuffled_lag_correlation)
        < abs(shuffle.original_lag_correlation),
        "noise_calibration_has_positive_floor": calibrated_noise
        >= config["noise_calibration"]["floor"],
        "survival_policy_transitions": (
            survival_policy.classify(
                CandidateEvidenceState("a", config["survival_parameters"]["dormancy_after"] - 1)
            )
            == SurvivalStatus.ACTIVE
            and survival_policy.classify(
                CandidateEvidenceState("a", config["survival_parameters"]["dormancy_after"])
            )
            == SurvivalStatus.DORMANT
            and survival_policy.classify(
                CandidateEvidenceState("a", config["survival_parameters"]["death_after"])
            )
            == SurvivalStatus.DEAD
            and survival_policy.classify(CandidateEvidenceState("a", 0, 1)) == SurvivalStatus.DEAD
        ),
        "contradictory_control_rejected": run_negative_control(config["seed"])["final_posterior"]
        < 1.0 / 9.0,
        "task_design_is_six_by_five": len(task_design) == 30
        and len({task.cluster_id for task in task_design}) == 6,
        "numerical_agreement_within_frozen_tolerance": all(
            item.passed for item in numerical_agreements
        ),
        "candidate_generator_is_finite_and_deterministic": generated_candidates == generated_again
        and 0 < len(generated_candidates) <= candidate_spec.maximum_candidates_per_task,
        "candidate_generator_bound_to_protocol": (
            candidate_spec.spec_hash == spec.candidate_generator_hash
        ),
        "measurement_clusters_bound_to_protocol": spec.measurement_cluster_hash
        == content_hash(
            [
                asdict(cluster)
                for cluster in frozen_candidate_clusters(config["task_design"]["steps"])
            ]
        ),
        "task_design_bound_to_protocol": spec.task_design_hash
        == content_hash([asdict(task) for task in task_design]),
        "external_manifest_bound_to_protocol": spec.external_data_manifest_hash
        == content_hash(load_dataset_manifest(Path(config["external_data_manifest"]))),
        "external_fixture_bound_to_protocol": spec.external_fixture_manifest_hash
        == content_hash(load_dataset_manifest(Path(config["external_fixture_manifest"]))),
        "development_runtime_matches_candidate": (
            environment_matches["development_host"] or environment_matches["confirmatory_container"]
        ),
        "design_power_at_detectable_effect": detectable_power
        >= config["power_design"]["minimum_power"],
        "accounting_rules_are_executable": accounting.snapshot.world_queries == 1
        and accounting.snapshot.candidate_generations == generation_batch.attempted_mutations
        and accounting.snapshot.candidate_evaluations == 1
        and accounting.snapshot.candidate_evaluation_cache_hits == 1,
    }
    protocol_freeze_blockers = [
        "prepare final world commitment and access directory outside the development tree",
        "independently review the 30% design-detectable effect versus the 20% null boundary",
        "independently review numerical, survival, niche, generator, and accounting rules",
    ]
    if not environment_matches["runner_image_pinned"]:
        protocol_freeze_blockers.insert(
            0,
            "publish and pin the final confirmatory runner image digest",
        )
    if not environment_spec.get("frozen_mix_profiled_in_published_runner", False):
        protocol_freeze_blockers.insert(
            1 if not environment_matches["runner_image_pinned"] else 0,
            "retain the frozen-mix profile under that published runner digest",
        )
    report = {
        "schema_version": 1,
        "status": "ready_for_protocol_freeze_review" if all(checks.values()) else "redo",
        "scope": "development worlds and synthetic truth only",
        "protocol_hash": spec.protocol_hash,
        "checks": checks,
        "statistics_dry_run": asdict(effect),
        "task_design": {
            "tasks": len(task_design),
            "clusters": [
                asdict(cluster)
                for cluster in frozen_candidate_clusters(config["task_design"]["steps"])
            ],
            "cluster_hash": spec.measurement_cluster_hash,
            "task_design_hash": spec.task_design_hash,
        },
        "power_analysis": [asdict(item) for item in power_estimates],
        "numerical_agreement": {
            "tolerance": asdict(numerical_tolerance),
            "diagnostic_grid_size": config["task_design"]["grid_size"],
            "diagnostic_steps": config["task_design"]["steps"],
            "measurement_noise_and_masks_disabled": True,
            "clusters": [asdict(item) for item in numerical_agreements],
        },
        "candidate_generator": {
            "spec": asdict(candidate_spec),
            "spec_hash": candidate_spec.spec_hash,
            "generated_from_reference_parent": len(generated_candidates),
            "attempted_mutations_from_reference_parent": generation_batch.attempted_mutations,
        },
        "budget_accounting_diagnostic": asdict(accounting.snapshot),
        "execution_environment": {
            "spec": environment_spec,
            "runtime_matches": environment_matches,
            "spec_hash": spec.execution_environment_hash,
        },
        "residual_control": {
            "original_lag_correlation": shuffle.original_lag_correlation,
            "shuffled_lag_correlation": shuffle.shuffled_lag_correlation,
            "calibrated_noise": calibrated_noise,
        },
        "budget_projection": {
            "development_question_pool": len(questions),
            "frozen_task_design": len(task_design),
            "full_design_single_candidate_stencil_updates": frozen_task_stencil_updates,
            "average_candidate_evaluation_stencil_updates": average_evaluation_updates,
            "declared_candidate_evaluation_ceiling": config["candidate_evaluation_budget"],
            "projected_ceiling_stencil_updates": projected_stencil_updates,
            "measured_stencil_updates_per_second": updates_per_second,
            "projected_cpu_hours_from_microbenchmark": projected_cpu_hours,
            "note": (
                "Single-process projection over the frozen 30-task evaluation mix; rerun "
                "on the confirmatory execution environment immediately before PF."
            ),
        },
        "protocol_freeze_candidate": asdict(spec),
        "warning": (
            "This dry run does not open or define the future final sealed Gray–Scott worlds."
        ),
        "protocol_freeze_blockers": protocol_freeze_blockers,
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
        {
            "config": str(config_path),
            "external_data_manifest": config["external_data_manifest"],
            "external_data_manifest_hash": spec.external_data_manifest_hash,
            "external_fixture_manifest": config["external_fixture_manifest"],
            "external_fixture_manifest_hash": spec.external_fixture_manifest_hash,
            "execution_environment_spec": config["execution_environment_spec"],
            "execution_environment_hash": spec.execution_environment_hash,
        },
        {"report": str(report_path), "report_hash": content_hash(report)},
    ).write_once(output_dir / "manifest.json")
    return report
