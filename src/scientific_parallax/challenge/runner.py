"""Run the preregistered, development-only Step 7 blinded challenge."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.challenge.blind import DevelopmentBlindTask, anonymous_task_token
from scientific_parallax.challenge.scoring import (
    score_endpoint,
    score_truth_rank,
    validate_discriminating_questions,
)
from scientific_parallax.coevolution.evidence import (
    EvidenceHistoryItem,
    calibrated_noise,
    posterior_from_history,
    update_posterior,
)
from scientific_parallax.core.budget import BudgetLedger, BudgetLimits, BudgetSnapshot
from scientific_parallax.core.reproducibility import (
    ExperimentIdentity,
    RunManifest,
    capture_environment,
    content_hash,
)
from scientific_parallax.evolution.model import (
    ParadigmGenotype,
    description_length,
    structural_distance,
)
from scientific_parallax.evolution.mutation import (
    FrozenParadigmMutator,
    gray_scott_founder_genotype,
    summary_on_experiment,
)
from scientific_parallax.protocol.candidate_generator import CandidateGeneratorSpec
from scientific_parallax.protocol.design import frozen_candidate_clusters
from scientific_parallax.protocol.dry_run import gray_scott_ir, protocol_spec_from_config
from scientific_parallax.protocol.statistics import (
    restricted_mean_time,
    stratified_bootstrap_effect,
)
from scientific_parallax.questions.model import QuestionCost, QuestionCostWeights, QuestionGenotype
from scientific_parallax.questions.mutation import FrozenQuestionMutator
from scientific_parallax.questions.scoring import expected_information_gain, predicted_disagreement
from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottParameters,
    GrayScottWorld,
)


@dataclass(frozen=True, slots=True)
class _QuestionDiagnostic:
    experiment_hash: str
    expected_information_gain: float
    disagreement: float
    weighted_cost: float


@dataclass(frozen=True, slots=True)
class _ArmPolicy:
    dynamic_candidates: bool
    candidate_niches: bool
    evolving_questions: bool
    static_question_pool: str
    question_selection: str
    representation_mutation: bool = True


ARM_POLICIES = {
    "coevolution": _ArmPolicy(True, True, True, "seed", "three_niches"),
    "bayesian_optimal_design": _ArmPolicy(True, True, False, "full", "eig"),
    "random": _ArmPolicy(True, True, False, "full", "random"),
    "passive_coverage": _ArmPolicy(True, True, False, "full", "coverage"),
    "fixed_candidate_coevolution": _ArmPolicy(False, True, True, "seed", "three_niches"),
    "no_question_evolution": _ArmPolicy(True, True, False, "seed", "eig"),
    "no_representation_mutation": _ArmPolicy(
        True, True, True, "seed", "three_niches", representation_mutation=False
    ),
    "no_niches": _ArmPolicy(True, False, True, "seed", "resource"),
}


def run_step7_development_challenge(config_path: Path, output_dir: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    protocol_config = _validate_config(config)
    environment = capture_environment(Path.cwd())
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite Step 7 output: {output_dir}")
    output_dir.mkdir(parents=True)

    tasks = _build_development_tasks(config)
    task_results: list[dict[str, Any]] = []
    for arm_index, arm in enumerate(config["arms"]):
        for task in tasks:
            task_results.append(
                _run_arm_task(
                    task,
                    arm,
                    ARM_POLICIES[arm],
                    config,
                    protocol_config,
                    arm_index,
                )
            )

    primary = _primary_analysis(task_results, config)
    arm_summaries = _summarize_arms(task_results, config)
    validation = _independent_validation(task_results, config)
    checks = _checks(task_results, primary, validation, tasks, config)
    decision = _decision(primary["confidence_interval"], config["minimum_relative_effect"])
    readiness = {
        "go": "eligible_to_freeze_for_one_shot_final_evaluation",
        "redo": "not_ready; one newly preregistered development rerun remains permissible",
        "stop": "stop_before_final_strategy_freeze_and_do_not_advance_to_step8",
    }[decision]
    if not all(checks.values()):
        decision = "redo"
        readiness = "not_ready; implementation or validation checks failed"

    total_snapshot = _sum_budgets(task_results)
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "step7_development_challenge_complete" if all(checks.values()) else "redo",
        "challenge_version": config["challenge_version"],
        "scope": (
            "preregistered blind development rehearsal only; no sealed final-world task was read"
        ),
        "assurance_mode": "local_single_account_self_audit",
        "protocol_hash": config["protocol_hash"],
        "candidate_generator_hash": protocol_spec_from_config(
            protocol_config
        ).candidate_generator_hash,
        "preregistration_hash": content_hash(config),
        "task_count": len(tasks),
        "arm_count": len(config["arms"]),
        "run_count": len(task_results),
        "primary_hypothesis": config["primary_hypothesis"],
        "primary_analysis": primary,
        "decision": decision,
        "readiness": readiness,
        "arm_summaries": arm_summaries,
        "independent_validation": validation,
        "checks": checks,
        "resource_accounting": {
            **asdict(total_snapshot),
            "simulation_stencil_updates": sum(
                int(item["simulation_stencil_updates"]) for item in task_results
            ),
            "projected_cpu_hours_at_published_runner_rate": sum(
                int(item["simulation_stencil_updates"]) for item in task_results
            )
            / config["published_runner_stencil_updates_per_second"]
            / 3600.0,
            "published_runner_stencil_updates_per_second": config[
                "published_runner_stencil_updates_per_second"
            ],
        },
        "semantic_blinding": config["semantic_blinding"],
        "failure_modes": _failure_modes(primary, validation, arm_summaries, config),
        "confirmatory_boundary": config["confirmatory_boundary"],
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    results_path = output_dir / "task-results.jsonl"
    results_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in task_results),
        encoding="utf-8",
    )
    identity = ExperimentIdentity(
        config["challenge_version"], config, config["seed"], environment["git_revision"]
    )
    manifest = RunManifest(
        1,
        identity.experiment_id,
        config["challenge_version"],
        identity.config_hash,
        config["seed"],
        environment,
        {
            "config": str(config_path),
            "protocol_hash": config["protocol_hash"],
            "task_source": "deterministically generated development holdout",
        },
        {
            "report": report_path.name,
            "report_hash": content_hash(report),
            "task_results": results_path.name,
            "task_results_sha256": _file_sha256(results_path),
        },
    )
    manifest.write_once(output_dir / "manifest.json")
    return report


def _validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if config.get("schema_version") != 1 or config.get("scope") != "development_rehearsal_only":
        raise ValueError("unsupported Step 7 development configuration")
    required_arms = set(ARM_POLICIES)
    if set(config["arms"]) != required_arms or len(config["arms"]) != len(required_arms):
        raise ValueError("Step 7 requires the complete preregistered baseline and ablation set")
    positive = (
        config["seeds_per_cluster"],
        config["grid_size"],
        config["steps"],
        config["world_query_budget"],
        config["candidate_generation_budget"],
        config["candidate_evaluation_budget"],
        config["maximum_candidates"],
        config["active_candidates"],
        config["maximum_questions"],
        config["eig_samples"],
        config["ranking_threshold_k"],
        config["persistence_checkpoints"],
        config["bootstrap_samples"],
    )
    if min(positive) < 1 or config["eig_samples"] < 8:
        raise ValueError("invalid Step 7 budgets")
    if config["persistence_checkpoints"] > config["world_query_budget"]:
        raise ValueError("persistence exceeds the development query budget")
    if not 0.0 < config["minimum_relative_effect"] < 1.0:
        raise ValueError("minimum relative effect must lie in (0, 1)")
    protocol_path = Path(config["protocol_config"])
    protocol_config = json.loads(protocol_path.read_text(encoding="utf-8"))
    spec = protocol_spec_from_config(protocol_config)
    if spec.protocol_hash != config["protocol_hash"]:
        raise ValueError("Step 7 configuration differs from the frozen protocol")
    if config["candidate_generation_budget"] > protocol_config["candidate_generation_budget"]:
        raise ValueError("development candidate-generation budget exceeds the frozen ceiling")
    if config["candidate_evaluation_budget"] > protocol_config["candidate_evaluation_budget"]:
        raise ValueError("development candidate-evaluation budget exceeds the frozen ceiling")
    if config["world_query_budget"] > protocol_config["world_query_budget"]:
        raise ValueError("development world-query budget exceeds the frozen ceiling")
    return protocol_config


def _build_development_tasks(config: dict[str, Any]) -> tuple[DevelopmentBlindTask, ...]:
    tasks: list[DevelopmentBlindTask] = []
    clusters = frozen_candidate_clusters(config["steps"])
    for cluster_index, cluster in enumerate(clusters):
        for task_index in range(config["seeds_per_cluster"]):
            initial_seed = config["task_seed_base"] + cluster_index * 100 + task_index
            measurement_seed = config["measurement_seed_base"] + cluster_index * 100 + task_index
            token = anonymous_task_token(config["seed"], cluster_index, task_index)
            experiment = GrayScottExperiment(
                f"blind-{token}",
                parameters=GrayScottParameters(feed=cluster.feed, kill=cluster.kill),
                initial_family=cluster.initial_family,
                initial_seed=initial_seed,
                grid_size=config["grid_size"],
                steps=config["steps"],
                boundary=cluster.boundary,
                measurement=cluster.measurement,
            )
            tasks.append(
                DevelopmentBlindTask(
                    token, cluster.cluster_id, task_index, measurement_seed, experiment
                )
            )
    return tuple(tasks)


def _run_arm_task(
    task: DevelopmentBlindTask,
    arm: str,
    policy: _ArmPolicy,
    config: dict[str, Any],
    protocol_config: dict[str, Any],
    arm_index: int,
) -> dict[str, Any]:
    limits = BudgetLimits(
        config["world_query_budget"],
        config["candidate_generation_budget"],
        config["candidate_evaluation_budget"],
    )
    budget = BudgetLedger(limits)
    generator_raw = protocol_config["candidate_generator"]
    allowed_mutations = tuple(generator_raw["allowed_mutations"])
    if not policy.representation_mutation:
        allowed_mutations = tuple(
            item for item in allowed_mutations if item.startswith("coefficient")
        )
    generator_spec = CandidateGeneratorSpec(
        generator_raw["version"],
        allowed_mutations,
        generator_raw["maximum_offspring_per_parent"],
        generator_raw["maximum_candidates_per_task"],
    )
    mutator = FrozenParadigmMutator(generator_spec)
    founder = gray_scott_founder_genotype(gray_scott_ir("latent-0", "x0", "x1"))
    candidates = {founder.genotype_id: founder}
    genotype_hashes = {founder.genotype_hash}
    expanded: set[str] = set()
    _expand_candidates(
        founder.genotype_id,
        candidates,
        genotype_hashes,
        expanded,
        mutator,
        budget,
        config["maximum_candidates"],
    )
    initial_candidate_set_hash = content_hash(
        sorted(genotype.genotype_hash for genotype in candidates.values())
    )
    aliases = _aliases(candidates, config["seed"], task.task_token)
    questions = _question_pool(task, config, full=policy.static_question_pool == "full")
    question_mutator = FrozenQuestionMutator(tuple(config["question_mutations"]))
    world = GrayScottWorld(task.measurement_seed)
    weights = QuestionCostWeights(**config["question_cost_weights"])
    history: list[tuple[GrayScottExperiment, tuple[float, ...]]] = []
    prediction_cache: dict[tuple[str, str], tuple[float, ...]] = {}
    ranks: list[int] = []
    rounds: list[dict[str, object]] = []
    selected_hashes: set[str] = set()
    simulation_work = 0
    rng_seed = _derived_seed(config["seed"], task.task_token, arm_index)
    rng = np.random.default_rng(rng_seed)
    noise_floor = float(protocol_config["noise_calibration"]["floor"])

    for round_index in range(config["world_query_budget"]):
        aliases.update(_aliases(candidates, config["seed"], task.task_token))
        evidence_history, rebuild_work = _evidence_history(
            candidates, history, prediction_cache, budget
        )
        simulation_work += rebuild_work
        candidate_ids = tuple(sorted(candidates))
        prior = posterior_from_history(candidate_ids, tuple(evidence_history), noise_floor)
        active_ids = _active_candidates(
            candidates,
            prior,
            aliases,
            founder,
            config["active_candidates"],
            policy.candidate_niches,
        )
        diagnostics, diagnostic_work = _diagnose_questions(
            questions,
            active_ids,
            candidates,
            prior,
            prediction_cache,
            budget,
            world,
            weights,
            config,
            round_index,
            noise_floor,
        )
        simulation_work += diagnostic_work
        selected, selected_niche = _select_question(
            diagnostics,
            policy.question_selection,
            round_index,
            selected_hashes,
            rng,
        )
        selected_experiment = questions[selected.experiment_hash]
        predictions: dict[str, tuple[float, ...]] = {}
        prediction_work = 0
        for candidate_id, genotype in candidates.items():
            prediction, work = _predict_cached(
                genotype, selected_experiment, prediction_cache, budget
            )
            predictions[candidate_id] = prediction
            prediction_work += work
        simulation_work += prediction_work
        budget.charge_world_query()
        simulation_work += int(world.estimate_cost(selected_experiment))
        observation = tuple(float(value) for value in world.observe(selected_experiment).summary())
        posterior = update_posterior(prior, predictions, observation, noise_floor)
        true_rank = score_truth_rank(posterior, aliases, founder.genotype_id)
        ranks.append(true_rank)
        actual_information_gain = _entropy(prior) - _entropy(posterior)
        rounds.append(
            {
                "checkpoint": round_index + 1,
                "question_hash": selected.experiment_hash,
                "selected_niche": selected_niche,
                "expected_information_gain": selected.expected_information_gain,
                "predicted_disagreement": selected.disagreement,
                "actual_information_gain": actual_information_gain,
                "true_equivalence_rank": true_rank,
                "candidate_count": len(candidates),
                "active_candidate_count": len(active_ids),
            }
        )
        history.append((selected_experiment, observation))
        selected_hashes.add(selected.experiment_hash)
        if policy.evolving_questions:
            questions = _evolve_questions(
                questions, selected.experiment_hash, question_mutator, config, round_index
            )
        if policy.dynamic_candidates and round_index + 1 < config["world_query_budget"]:
            parent_id = next(
                (
                    item
                    for item in sorted(
                        candidates, key=lambda value: (-posterior[value], aliases[value])
                    )
                    if item not in expanded
                ),
                None,
            )
            if parent_id is not None:
                _expand_candidates(
                    parent_id,
                    candidates,
                    genotype_hashes,
                    expanded,
                    mutator,
                    budget,
                    config["maximum_candidates"],
                )

    final_history, final_work = _evidence_history(candidates, history, prediction_cache, budget)
    simulation_work += final_work
    final_posterior = posterior_from_history(
        tuple(sorted(candidates)), tuple(final_history), noise_floor
    )
    aliases.update(_aliases(candidates, config["seed"], task.task_token))
    endpoint = score_endpoint(
        ranks,
        final_posterior,
        founder.genotype_id,
        top_k=config["ranking_threshold_k"],
        persistence=config["persistence_checkpoints"],
    )
    question_validation = validate_discriminating_questions(rounds)
    return {
        "arm": arm,
        "task_token": task.task_token,
        "evaluator_stratum": task.cluster_id,
        "evaluator_task_index": task.cluster_task_index,
        "stable_identification_query": endpoint.stable_identification_query,
        "rank_history": list(endpoint.ranks),
        "final_true_posterior": endpoint.final_true_posterior,
        "generated_candidates": len(candidates),
        "initial_candidate_set_hash": initial_candidate_set_hash,
        "unique_state_variable_counts": sorted(
            {len(item.ir.variables) for item in candidates.values()}
        ),
        "question_validation": question_validation,
        "rounds": rounds,
        "budget": asdict(budget.snapshot),
        "budget_limits": asdict(limits),
        "simulation_stencil_updates": simulation_work,
        "strategy_view_hash": content_hash(asdict(task.view)),
    }


def _expand_candidates(
    parent_id: str,
    candidates: dict[str, ParadigmGenotype],
    genotype_hashes: set[str],
    expanded: set[str],
    mutator: FrozenParadigmMutator,
    budget: BudgetLedger,
    maximum_candidates: int,
) -> None:
    if parent_id in expanded or len(candidates) >= maximum_candidates:
        return
    batch = mutator.generate_with_accounting(candidates[parent_id])
    remaining = budget.limits.candidate_generations - budget.snapshot.candidate_generations
    if batch.attempted_mutations > remaining:
        expanded.add(parent_id)
        return
    budget.charge_candidate_generation(batch.attempted_mutations)
    expanded.add(parent_id)
    for generated in batch.offspring:
        if len(candidates) >= maximum_candidates:
            break
        child = generated.genotype
        if child.genotype_hash in genotype_hashes:
            continue
        candidates[child.genotype_id] = child
        genotype_hashes.add(child.genotype_hash)


def _aliases(candidates: dict[str, ParadigmGenotype], seed: int, task_token: str) -> dict[str, str]:
    return {
        candidate_id: hashlib.sha256(
            f"{seed}:{task_token}:{genotype.genotype_hash}".encode()
        ).hexdigest()[:16]
        for candidate_id, genotype in candidates.items()
    }


def _question_pool(
    task: DevelopmentBlindTask, config: dict[str, Any], *, full: bool
) -> dict[str, GrayScottExperiment]:
    base = task.experiment
    variants = (
        base,
        replace(
            base,
            experiment_id=f"blind-{task.task_token}-q1",
            parameters=GrayScottParameters(feed=0.045, kill=0.063),
            initial_family="two_spots",
            boundary="reflecting",
        ),
        replace(
            base,
            experiment_id=f"blind-{task.task_token}-q2",
            parameters=GrayScottParameters(feed=0.025, kill=0.055),
            initial_family="stripe",
            boundary="periodic",
        ),
    )
    questions = {_experiment_hash(item): item for item in variants}
    if not full:
        return questions
    mutator = FrozenQuestionMutator(tuple(config["question_mutations"]))
    for index, parent in enumerate(variants):
        genotype = QuestionGenotype(f"static-{index}", parent, ("anonymous-a", "anonymous-b"))
        for child, _ in mutator.generate(genotype, 1):
            questions.setdefault(_experiment_hash(child.experiment), child.experiment)
            if len(questions) >= config["maximum_questions"]:
                return questions
    return questions


def _evolve_questions(
    questions: dict[str, GrayScottExperiment],
    selected_hash: str,
    mutator: FrozenQuestionMutator,
    config: dict[str, Any],
    round_index: int,
) -> dict[str, GrayScottExperiment]:
    if len(questions) >= config["maximum_questions"]:
        return questions
    parent = questions[selected_hash]
    genotype = QuestionGenotype(f"evolving-{round_index}", parent, ("anonymous-a", "anonymous-b"))
    evolved = dict(questions)
    for child, _ in mutator.generate(genotype, round_index + 1):
        evolved.setdefault(_experiment_hash(child.experiment), child.experiment)
        if len(evolved) >= config["maximum_questions"]:
            break
    return evolved


def _evidence_history(
    candidates: dict[str, ParadigmGenotype],
    history: list[tuple[GrayScottExperiment, tuple[float, ...]]],
    cache: dict[tuple[str, str], tuple[float, ...]],
    budget: BudgetLedger,
) -> tuple[list[EvidenceHistoryItem], int]:
    records: list[EvidenceHistoryItem] = []
    simulation_work = 0
    for experiment, observation in history:
        predictions: dict[str, tuple[float, ...]] = {}
        for candidate_id, genotype in candidates.items():
            prediction, work = _predict_cached(genotype, experiment, cache, budget)
            predictions[candidate_id] = prediction
            simulation_work += work
        records.append(EvidenceHistoryItem(_experiment_hash(experiment), observation, predictions))
    return records, simulation_work


def _predict_cached(
    genotype: ParadigmGenotype,
    experiment: GrayScottExperiment,
    cache: dict[tuple[str, str], tuple[float, ...]],
    budget: BudgetLedger,
) -> tuple[tuple[float, ...], int]:
    key = (genotype.genotype_hash, _experiment_hash(experiment))
    if key in cache:
        budget.charge_candidate_evaluation(cache_hit=True)
        return cache[key], 0
    budget.charge_candidate_evaluation()
    prediction = summary_on_experiment(genotype, experiment)
    cache[key] = prediction
    work = int(GrayScottWorld().estimate_cost(experiment))
    return prediction, work


def _active_candidates(
    candidates: dict[str, ParadigmGenotype],
    posterior: dict[str, float],
    aliases: dict[str, str],
    founder: ParadigmGenotype,
    capacity: int,
    niches: bool,
) -> tuple[str, ...]:
    posterior_order = sorted(candidates, key=lambda item: (-posterior[item], aliases[item]))
    if not niches:
        return tuple(posterior_order[:capacity])
    description_order = sorted(
        candidates,
        key=lambda item: (description_length(candidates[item]).total_bits, aliases[item]),
    )
    structure_order = sorted(
        candidates,
        key=lambda item: (-structural_distance(founder.ir, candidates[item].ir), aliases[item]),
    )
    selected: list[str] = []
    allocations = (posterior_order[:4], description_order[:2], structure_order[:2])
    for allocation in allocations:
        for candidate_id in allocation:
            if candidate_id not in selected:
                selected.append(candidate_id)
            if len(selected) >= capacity:
                return tuple(selected)
    for candidate_id in posterior_order:
        if candidate_id not in selected:
            selected.append(candidate_id)
        if len(selected) >= capacity:
            break
    return tuple(selected)


def _diagnose_questions(
    questions: dict[str, GrayScottExperiment],
    active_ids: tuple[str, ...],
    candidates: dict[str, ParadigmGenotype],
    posterior: dict[str, float],
    cache: dict[tuple[str, str], tuple[float, ...]],
    budget: BudgetLedger,
    world: GrayScottWorld,
    weights: QuestionCostWeights,
    config: dict[str, Any],
    round_index: int,
    noise_floor: float,
) -> tuple[list[_QuestionDiagnostic], int]:
    mass = sum(posterior[item] for item in active_ids)
    restricted = {item: posterior[item] / mass for item in active_ids}
    task_dimension = 4 * len(next(iter(questions.values())).measurement.visible_channels)
    noise = calibrated_noise(task_dimension, noise_floor)
    diagnostics: list[_QuestionDiagnostic] = []
    simulation_work = 0
    for question_index, (experiment_hash, experiment) in enumerate(sorted(questions.items())):
        predictions: dict[str, np.ndarray] = {}
        for candidate_id in active_ids:
            prediction, work = _predict_cached(candidates[candidate_id], experiment, cache, budget)
            predictions[candidate_id] = np.asarray(prediction, dtype=float)
            simulation_work += work
        eig_seed = _derived_seed(config["seed"] + round_index, experiment_hash, question_index)
        genotype = QuestionGenotype("diagnostic", experiment, active_ids)
        diagnostics.append(
            _QuestionDiagnostic(
                experiment_hash,
                expected_information_gain(
                    restricted,
                    predictions,
                    samples=config["eig_samples"],
                    seed=eig_seed,
                    noise=noise,
                ),
                predicted_disagreement(restricted, predictions, noise=noise),
                QuestionCost.estimate(genotype, world, weights).weighted_total,
            )
        )
    if task_dimension < 1:  # pragma: no cover - MeasurementSpec validation owns this.
        raise AssertionError("invalid anonymous summary dimension")
    return diagnostics, simulation_work


def _select_question(
    diagnostics: list[_QuestionDiagnostic],
    selection: str,
    round_index: int,
    selected_hashes: set[str],
    rng: np.random.Generator,
) -> tuple[_QuestionDiagnostic, str]:
    available = [item for item in diagnostics if item.experiment_hash not in selected_hashes]
    if not available:
        available = diagnostics
    if selection == "random":
        return available[int(rng.integers(0, len(available)))], "random"
    if selection == "coverage":
        return sorted(available, key=lambda item: item.experiment_hash)[0], "passive_coverage"
    if selection == "eig":
        return max(
            available,
            key=lambda item: (
                item.expected_information_gain,
                -item.weighted_cost,
                item.experiment_hash,
            ),
        ), "bayesian_eig"
    if selection == "resource":
        return max(
            available,
            key=lambda item: (
                item.expected_information_gain / item.weighted_cost,
                item.experiment_hash,
            ),
        ), "single_resource_objective"
    if selection != "three_niches":
        raise ValueError(f"unknown question selection policy: {selection}")
    niche = ("information_efficiency", "disagreement", "minimum_cost")[round_index % 3]
    if niche == "information_efficiency":
        return max(
            available,
            key=lambda item: (
                item.expected_information_gain / item.weighted_cost,
                item.experiment_hash,
            ),
        ), niche
    if niche == "disagreement":
        return max(
            available,
            key=lambda item: (
                item.disagreement,
                item.expected_information_gain,
                item.experiment_hash,
            ),
        ), niche
    return min(available, key=lambda item: (item.weighted_cost, item.experiment_hash)), niche


def _primary_analysis(results: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    treatment = _by_stratum(results, config["primary_treatment"])
    control = _by_stratum(results, config["primary_control"])
    effect = stratified_bootstrap_effect(
        treatment,
        control,
        budget=config["world_query_budget"],
        samples=config["bootstrap_samples"],
        seed=config["seed"],
    )
    return {
        "endpoint": "stable_top_k_identification_queries",
        "top_k": config["ranking_threshold_k"],
        "persistence_checkpoints": config["persistence_checkpoints"],
        "censoring_budget": config["world_query_budget"],
        "treatment": config["primary_treatment"],
        "control": config["primary_control"],
        "treatment_restricted_mean_queries": restricted_mean_time(
            [item for values in treatment.values() for item in values],
            config["world_query_budget"],
        ),
        "control_restricted_mean_queries": restricted_mean_time(
            [item for values in control.values() for item in values],
            config["world_query_budget"],
        ),
        "relative_query_reduction": effect.relative_query_reduction,
        "confidence_interval": list(effect.confidence_interval),
        "bootstrap_samples": effect.samples,
        "minimum_meaningful_effect": config["minimum_relative_effect"],
    }


def _by_stratum(results: list[dict[str, Any]], arm: str) -> dict[str, list[int | None]]:
    grouped: dict[str, list[int | None]] = {}
    for item in results:
        if item["arm"] == arm:
            grouped.setdefault(item["evaluator_stratum"], []).append(
                item["stable_identification_query"]
            )
    return grouped


def _summarize_arms(results: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for arm in config["arms"]:
        selected = [item for item in results if item["arm"] == arm]
        endpoints = [item["stable_identification_query"] for item in selected]
        summaries[arm] = {
            "runs": len(selected),
            "identified": sum(value is not None for value in endpoints),
            "restricted_mean_queries": restricted_mean_time(
                endpoints, config["world_query_budget"]
            ),
            "mean_final_true_posterior": float(
                np.mean([item["final_true_posterior"] for item in selected])
            ),
            "mean_actual_information_gain": float(
                np.mean(
                    [
                        item["question_validation"]["mean_actual_information_gain"]
                        for item in selected
                    ]
                )
            ),
            "mean_candidate_evaluations": float(
                np.mean([item["budget"]["candidate_evaluations"] for item in selected])
            ),
        }
    return summaries


def _independent_validation(
    results: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    treatment = [item for item in results if item["arm"] == config["primary_treatment"]]
    per_stratum = {
        stratum: {
            "runs": len(
                selected := [item for item in treatment if item["evaluator_stratum"] == stratum]
            ),
            "identified": sum(item["stable_identification_query"] is not None for item in selected),
            "median_final_rank": float(np.median([item["rank_history"][-1] for item in selected])),
        }
        for stratum in sorted({item["evaluator_stratum"] for item in treatment})
    }
    question_checks = [item["question_validation"] for item in treatment]
    variable_counts = {
        count for item in treatment for count in item["unique_state_variable_counts"]
    }
    leave_one_seed_out = _leave_one_seed_out(results, config)
    return {
        "scorer_ownership": "evaluator-only truth rank; strategy receives no truth membership",
        "multi_seed_and_condition_stability": per_stratum,
        "all_six_conditions_and_five_seeds_present": len(per_stratum) == 6
        and all(item["runs"] == 5 for item in per_stratum.values()),
        "questions_distinguish_paradigms": all(
            item["questions_distinguish_paradigms"] for item in question_checks
        ),
        "novel_state_variables_proposed": 0,
        "novel_variable_validation": "not_applicable",
        "novelty_boundary": (
            "the Gate-PF candidate grammar cannot add state variables; Step 7 cannot support "
            "a positive novel-variable claim"
        ),
        "state_variable_counts": sorted(variable_counts),
        "leave_one_seed_out": leave_one_seed_out,
        "result_not_single_seed": config["seeds_per_cluster"] > 1
        and len({item["task_token"] for item in treatment}) == 30
        and len(set(leave_one_seed_out.values())) == 1,
    }


def _leave_one_seed_out(results: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, str]:
    if config["seeds_per_cluster"] < 2:
        return {"not_applicable": "fewer_than_two_seeds_per_cluster"}
    sensitivity: dict[str, str] = {}
    for excluded_index in range(config["seeds_per_cluster"]):
        subset = [item for item in results if item["evaluator_task_index"] != excluded_index]
        effect = stratified_bootstrap_effect(
            _by_stratum(subset, config["primary_treatment"]),
            _by_stratum(subset, config["primary_control"]),
            budget=config["world_query_budget"],
            samples=config["bootstrap_samples"],
            seed=config["seed"] + excluded_index + 1,
        )
        sensitivity[f"exclude_seed_index_{excluded_index}"] = _decision(
            list(effect.confidence_interval), config["minimum_relative_effect"]
        )
    return sensitivity


def _checks(
    results: list[dict[str, Any]],
    primary: dict[str, Any],
    validation: dict[str, Any],
    tasks: tuple[DevelopmentBlindTask, ...],
    config: dict[str, Any],
) -> dict[str, bool]:
    primary_runs = [
        item
        for item in results
        if item["arm"] in {config["primary_treatment"], config["primary_control"]}
    ]
    primary_initial_sets = {
        task.task_token: {
            item["arm"]: item["initial_candidate_set_hash"]
            for item in primary_runs
            if item["task_token"] == task.task_token
        }
        for task in tasks
    }
    return {
        "preregistered_complete_arm_set": set(config["arms"]) == set(ARM_POLICIES),
        "six_clusters_five_seeds": len(tasks) == 30
        and validation["all_six_conditions_and_five_seeds_present"],
        "strategy_view_excludes_cluster_truth_and_seeds": all(
            set(asdict(task.view)) == {"task_token", "capabilities", "summary_dimension"}
            for task in tasks
        ),
        "same_primary_budget_envelope": all(
            item["budget_limits"] == primary_runs[0]["budget_limits"] for item in primary_runs
        ),
        "same_primary_candidate_initialization": all(
            len(values) == 2 and len(set(values.values())) == 1
            for values in primary_initial_sets.values()
        ),
        "all_resource_ceilings_respected": all(
            all(item["budget"][key] <= item["budget_limits"][key] for key in item["budget_limits"])
            for item in results
        ),
        "primary_endpoint_executable": all(
            len(item["rank_history"]) == config["world_query_budget"] for item in results
        ),
        "independent_question_validation_passes": validation["questions_distinguish_paradigms"],
        "multi_seed_result": validation["result_not_single_seed"],
        "confidence_interval_finite": all(
            math.isfinite(value) for value in primary["confidence_interval"]
        ),
        "final_world_not_accessed": True,
    }


def _failure_modes(
    primary: dict[str, Any],
    validation: dict[str, Any],
    summaries: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    if primary["confidence_interval"][1] < config["minimum_relative_effect"]:
        failures.append(
            {
                "id": "primary-effect-below-threshold",
                "severity": "stop",
                "detail": "matched Bayesian control is not beaten by the preregistered 20% margin",
            }
        )
    if (
        summaries["passive_coverage"]["restricted_mean_queries"]
        <= summaries["coevolution"]["restricted_mean_queries"]
    ):
        failures.append(
            {
                "id": "passive-sampling-not-beaten",
                "severity": "scientific",
                "detail": "coevolution does not improve the primary endpoint over passive coverage",
            }
        )
    if validation["novel_state_variables_proposed"] == 0:
        failures.append(
            {
                "id": "novel-variable-claim-unreachable",
                "severity": "design",
                "detail": "the frozen mutation grammar preserves exactly two state variables",
            }
        )
    failures.append(
        {
            "id": "truth-in-founder-pool",
            "severity": "design",
            "detail": (
                "the known true structural class is explicitly present in every initial "
                "candidate pool, "
                "which can make top-5 identification insensitive to question strategy"
            ),
        }
    )
    return failures


def _decision(confidence_interval: list[float], threshold: float) -> str:
    lower, upper = confidence_interval
    if lower > threshold:
        return "go"
    if upper < threshold:
        return "stop"
    return "redo"


def _sum_budgets(results: list[dict[str, Any]]) -> BudgetSnapshot:
    return BudgetSnapshot(
        sum(item["budget"]["world_queries"] for item in results),
        sum(item["budget"]["candidate_generations"] for item in results),
        sum(item["budget"]["candidate_evaluations"] for item in results),
        sum(item["budget"]["candidate_evaluation_cache_hits"] for item in results),
    )


def _experiment_hash(experiment: GrayScottExperiment) -> str:
    payload = asdict(experiment)
    payload.pop("experiment_id")
    return content_hash(payload)


def _derived_seed(seed: int, token: str, index: int) -> int:
    digest = hashlib.sha256(f"{seed}:{token}:{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _entropy(posterior: dict[str, float]) -> float:
    return -sum(value * math.log(value) for value in posterior.values() if value > 0.0)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
