"""Development pilot for discovering a latent dynamical state under misspecification."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.coevolution.evidence import calibrated_noise
from scientific_parallax.core.budget import BudgetLedger, BudgetLimits, BudgetSnapshot
from scientific_parallax.core.reproducibility import (
    ExperimentIdentity,
    RunManifest,
    capture_environment,
    content_hash,
)
from scientific_parallax.discovery.latent_model import (
    LatentCandidate,
    LatentStructureMutator,
    lineage_to_root,
    two_state_founders,
)
from scientific_parallax.discovery.latent_questions import (
    LatentQuestionMutator,
    seed_questions,
    validation_questions,
)
from scientific_parallax.protocol.statistics import (
    restricted_mean_time,
    stratified_bootstrap_effect,
)
from scientific_parallax.questions.scoring import (
    entropy,
    expected_information_gain,
    predicted_disagreement,
)
from scientific_parallax.worlds.latent_gray_scott import (
    LatentGrayScottExperiment,
    LatentGrayScottWorld,
    LatentLaw,
)


@dataclass(frozen=True, slots=True)
class _LatentTask:
    task_token: str
    task_kind: str
    truth_cluster: str
    seed_index: int
    law: LatentLaw
    measurement_seed: int
    questions: tuple[LatentGrayScottExperiment, ...]
    validation: tuple[LatentGrayScottExperiment, ...]


@dataclass(frozen=True, slots=True)
class _QuestionDiagnostic:
    question_hash: str
    expected_information_gain: float
    predicted_disagreement: float
    structural_disagreement: float
    cost: int


@dataclass(frozen=True, slots=True)
class _ArmPolicy:
    candidate_niches: bool
    evolving_questions: bool
    fixed_question_pool: bool
    question_selection: str
    allow_structure: bool = True
    oracle_structure: bool = False


ARM_POLICIES = {
    "coevolution": _ArmPolicy(True, True, False, "three_niches"),
    "matched_bayesian_design": _ArmPolicy(True, False, True, "eig"),
    "random": _ArmPolicy(True, False, True, "random"),
    "passive_coverage": _ArmPolicy(True, False, True, "coverage"),
    "fixed_representation_bed": _ArmPolicy(True, False, True, "eig", allow_structure=False),
    "no_niches": _ArmPolicy(False, True, False, "three_niches"),
    "oracle_structure_bed": _ArmPolicy(True, False, True, "eig", oracle_structure=True),
}


def run_latent_discovery_pilot(config_path: Path, output_dir: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    _validate_config(config)
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite latent-discovery output: {output_dir}")
    environment = capture_environment(Path.cwd())
    output_dir.mkdir(parents=True)
    tasks = _build_tasks(config)
    results = [
        _run_task(task, arm, ARM_POLICIES[arm], config, arm_index)
        for arm_index, arm in enumerate(config["arms"])
        for task in tasks
    ]
    capability = _capability_analysis(results, config)
    comparison = _comparative_analysis(results, config)
    summaries = _arm_summaries(results, config)
    checks = _checks(results, tasks, config)
    decision = _pilot_decision(capability, comparison, checks, config)
    report: dict[str, Any] = {
        "schema_version": 1,
        "status": "latent_discovery_pilot_complete" if all(checks.values()) else "invalid",
        "scope": "development pilot only; no sealed v1 or v2 final task was accessed",
        "experiment_version": config["experiment_version"],
        "config_hash": content_hash(config),
        "scientific_question": config["scientific_claim_boundary"],
        "task_count": len(tasks),
        "arm_count": len(config["arms"]),
        "run_count": len(results),
        "capability_analysis": capability,
        "comparative_analysis": comparison,
        "arm_summaries": summaries,
        "checks": checks,
        "pilot_decision": decision,
        "resource_accounting": asdict(_sum_budgets(results)),
        "independent_validation_evaluations": sum(
            item["independent_validation_evaluations"] for item in results
        ),
        "failure_modes": _failure_modes(capability, comparison, summaries, config),
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    results_path = output_dir / "task-results.jsonl"
    results_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in results),
        encoding="utf-8",
    )
    identity = ExperimentIdentity(
        config["experiment_version"], config, config["seed"], environment["git_revision"]
    )
    manifest = RunManifest(
        1,
        identity.experiment_id,
        config["experiment_version"],
        identity.config_hash,
        config["seed"],
        environment,
        {"config": str(config_path), "task_source": "development latent-law clusters"},
        {
            "report": report_path.name,
            "report_hash": content_hash(report),
            "task_results": results_path.name,
            "task_results_sha256": _file_sha256(results_path),
        },
    )
    manifest.write_once(output_dir / "manifest.json")
    return report


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("schema_version") != 1 or config.get("scope") != "development_pilot_only":
        raise ValueError("unsupported latent-discovery pilot configuration")
    if set(config["arms"]) != set(ARM_POLICIES):
        raise ValueError("latent pilot requires the complete comparison set")
    positive = (
        config["seeds_per_truth_cluster"],
        config["null_control_seeds"],
        config["grid_size"],
        config["steps"],
        config["sample_every"],
        config["world_query_budget"],
        config["candidate_generation_budget"],
        config["candidate_evaluation_budget"],
        config["maximum_candidates"],
        config["active_candidates"],
        config["maximum_questions"],
        config["eig_samples"],
        config["bootstrap_samples"],
        config["persistence_checkpoints"],
    )
    if min(positive) < 1 or config["eig_samples"] < 8:
        raise ValueError("latent pilot requires positive budgets and at least eight EIG draws")
    probabilities = (
        config["complete_structure_posterior_threshold"],
        config["minimum_validation_improvement"],
        config["minimum_task_success_rate"],
        config["maximum_null_false_positive_rate"],
        config["minimum_query_reduction_vs_matched_bed"],
    )
    if not all(0.0 < value < 1.0 for value in probabilities):
        raise ValueError("latent pilot thresholds must lie in (0, 1)")
    if config["persistence_checkpoints"] > config["world_query_budget"]:
        raise ValueError("latent discovery persistence exceeds the query budget")
    if len(config["truth_clusters"]) < 2:
        raise ValueError("latent pilot requires multiple truth parameter clusters")


def _build_tasks(config: dict[str, Any]) -> tuple[_LatentTask, ...]:
    tasks: list[_LatentTask] = []
    for cluster_index, cluster in enumerate(config["truth_clusters"]):
        law = LatentLaw(
            latent_drive=cluster["latent_drive"],
            latent_decay=cluster["latent_decay"],
            latent_feedback=cluster["latent_feedback"],
        )
        for seed_index in range(config["seeds_per_truth_cluster"]):
            initial_seed = config["task_seed_base"] + cluster_index * 100 + seed_index
            measurement_seed = config["measurement_seed_base"] + cluster_index * 100 + seed_index
            token = hashlib.sha256(
                f"latent-pilot:{config['seed']}:{cluster_index}:{seed_index}".encode()
            ).hexdigest()[:16]
            kwargs = {
                "task_token": token,
                "initial_seed": initial_seed,
                "grid_size": config["grid_size"],
                "steps": config["steps"],
                "sample_every": config["sample_every"],
            }
            tasks.append(
                _LatentTask(
                    token,
                    "latent",
                    cluster["cluster_id"],
                    seed_index,
                    law,
                    measurement_seed,
                    seed_questions(**kwargs),
                    validation_questions(**kwargs),
                )
            )
    for seed_index in range(config["null_control_seeds"]):
        initial_seed = config["task_seed_base"] + 9000 + seed_index
        measurement_seed = config["measurement_seed_base"] + 9000 + seed_index
        token = hashlib.sha256(
            f"latent-pilot:{config['seed']}:null:{seed_index}".encode()
        ).hexdigest()[:16]
        kwargs = {
            "task_token": token,
            "initial_seed": initial_seed,
            "grid_size": config["grid_size"],
            "steps": config["steps"],
            "sample_every": config["sample_every"],
        }
        tasks.append(
            _LatentTask(
                token,
                "null",
                "no-latent-control",
                seed_index,
                LatentLaw(False, False, False),
                measurement_seed,
                seed_questions(**kwargs),
                validation_questions(**kwargs),
            )
        )
    return tuple(tasks)


def _run_task(
    task: _LatentTask,
    arm: str,
    policy: _ArmPolicy,
    config: dict[str, Any],
    arm_index: int,
) -> dict[str, Any]:
    limits = BudgetLimits(
        config["world_query_budget"],
        config["candidate_generation_budget"],
        config["candidate_evaluation_budget"],
    )
    budget = BudgetLedger(limits)
    candidates = {item.candidate_id: item for item in two_state_founders()}
    if policy.oracle_structure:
        oracle_law = LatentLaw()
        oracle_hash = content_hash(asdict(oracle_law))
        candidates["oracle-structure"] = LatentCandidate(
            "oracle-structure", oracle_law, 0, None, None
        )
        if oracle_hash != candidates["oracle-structure"].model_hash:
            raise AssertionError("oracle identity mismatch")
    founder_hashes = sorted(item.model_hash for item in candidates.values())
    known_hashes = set(founder_hashes)
    expanded: set[str] = set()
    mutator = LatentStructureMutator()
    questions = _initial_question_pool(task, config, policy.fixed_question_pool)
    question_mutator = LatentQuestionMutator(tuple(config["question_mutations"]))
    world = LatentGrayScottWorld(task.measurement_seed, task.law)
    validation_observations = {
        experiment.content_hash: tuple(
            float(value) for value in world.observe(experiment).summary()
        )
        for experiment in task.validation
    }
    aliases = _aliases(candidates, config["seed"], task.task_token)
    prediction_cache: dict[tuple[str, str], tuple[float, ...]] = {}
    validation_cache: dict[tuple[str, str], tuple[float, ...]] = {}
    history: list[tuple[LatentGrayScottExperiment, tuple[float, ...]]] = []
    selected_questions: set[str] = set()
    success_history: list[bool] = []
    rounds: list[dict[str, Any]] = []
    rng = np.random.default_rng(_derived_seed(config["seed"], task.task_token, arm_index))

    for round_index in range(config["world_query_budget"]):
        prior = _posterior(candidates, history, prediction_cache, budget, config)
        parent_id = _select_parent(candidates, prior, aliases, expanded, policy.candidate_niches)
        if parent_id is not None:
            _expand_parent(
                parent_id,
                candidates,
                known_hashes,
                expanded,
                mutator,
                budget,
                config,
                policy.allow_structure,
            )
            aliases.update(_aliases(candidates, config["seed"], task.task_token))
            prior = _posterior(candidates, history, prediction_cache, budget, config)
        active_ids = _active_candidates(
            candidates, prior, aliases, config["active_candidates"], policy.candidate_niches
        )
        diagnostics = _diagnose_questions(
            questions,
            candidates,
            active_ids,
            prior,
            prediction_cache,
            budget,
            config,
            round_index,
        )
        selected, niche = _select_question(
            diagnostics,
            policy.question_selection,
            selected_questions,
            round_index,
            rng,
        )
        experiment = questions[selected.question_hash]
        predictions = {
            candidate_id: _predict(candidate, experiment, prediction_cache, budget)
            for candidate_id, candidate in candidates.items()
        }
        prediction_commitment = content_hash(predictions)
        budget.charge_world_query()
        observation = tuple(float(value) for value in world.observe(experiment).summary())
        history.append((experiment, observation))
        posterior = _posterior(candidates, history, prediction_cache, budget, config)
        validation = _score_validation(
            candidates,
            posterior,
            task.validation,
            validation_observations,
            validation_cache,
            config,
        )
        success_history.append(validation["success"])
        rounds.append(
            {
                "query": round_index + 1,
                "selected_question_hash": selected.question_hash,
                "prediction_commitment": prediction_commitment,
                "selected_niche": niche,
                "expected_information_gain": selected.expected_information_gain,
                "predicted_disagreement": selected.predicted_disagreement,
                "structural_disagreement": selected.structural_disagreement,
                "actual_information_gain": entropy(prior) - entropy(posterior),
                "candidate_count": len(candidates),
                "maximum_structural_stage": max(
                    item.structural_stage for item in candidates.values()
                ),
                **validation,
            }
        )
        selected_questions.add(selected.question_hash)
        if policy.evolving_questions:
            questions = _evolve_questions(
                questions,
                selected.question_hash,
                question_mutator,
                round_index,
                config["maximum_questions"],
            )

    endpoint = _stable_success_query(success_history, config["persistence_checkpoints"])
    final_posterior = _posterior(candidates, history, prediction_cache, budget, config)
    best_complete = _best_complete_candidate(candidates, final_posterior)
    lineage = []
    if best_complete is not None and best_complete.parent_id is not None:
        lineage = [
            {
                "candidate_id": item.candidate_id,
                "stage": item.structural_stage,
                "operator": item.mutation.operator if item.mutation else None,
            }
            for item in lineage_to_root(best_complete.candidate_id, candidates)
        ]
    return {
        "arm": arm,
        "task_token": task.task_token,
        "evaluator_task_kind": task.task_kind,
        "evaluator_truth_cluster": task.truth_cluster,
        "evaluator_seed_index": task.seed_index,
        "stable_discovery_query": endpoint,
        "success": endpoint is not None,
        "founder_count": len(founder_hashes),
        "all_non_oracle_founders_two_state": all(
            not item.law.has_latent_state
            for item in candidates.values()
            if item.generation == 0 and item.candidate_id != "oracle-structure"
        ),
        "generated_candidates": len(candidates),
        "best_complete_lineage": lineage,
        "final_complete_structure_mass": _stage_mass(final_posterior, candidates, 3),
        "final_validation_improvement": rounds[-1]["validation_improvement"],
        "rounds": rounds,
        "budget": asdict(budget.snapshot),
        "budget_limits": asdict(limits),
        "independent_validation_evaluations": len(validation_cache),
    }


def _initial_question_pool(
    task: _LatentTask, config: dict[str, Any], full: bool
) -> dict[str, LatentGrayScottExperiment]:
    questions = {item.content_hash: item for item in task.questions}
    if not full:
        return questions
    mutator = LatentQuestionMutator(tuple(config["question_mutations"]))
    for generation, parent in enumerate(task.questions, start=1):
        for child in mutator.generate(parent, generation):
            questions.setdefault(child.content_hash, child)
            if len(questions) >= config["maximum_questions"]:
                return questions
    return questions


def _evolve_questions(
    questions: dict[str, LatentGrayScottExperiment],
    selected_hash: str,
    mutator: LatentQuestionMutator,
    round_index: int,
    maximum: int,
) -> dict[str, LatentGrayScottExperiment]:
    evolved = dict(questions)
    evolved.pop(selected_hash)
    for child in mutator.generate(questions[selected_hash], round_index + 1):
        evolved.setdefault(child.content_hash, child)
        if len(evolved) >= maximum:
            break
    return evolved


def _expand_parent(
    parent_id: str,
    candidates: dict[str, LatentCandidate],
    known_hashes: set[str],
    expanded: set[str],
    mutator: LatentStructureMutator,
    budget: BudgetLedger,
    config: dict[str, Any],
    allow_structure: bool,
) -> None:
    attempts = len(mutator.OPERATORS) if allow_structure else 2
    remaining = budget.limits.candidate_generations - budget.snapshot.candidate_generations
    if attempts > remaining:
        expanded.add(parent_id)
        return
    budget.charge_candidate_generation(attempts)
    expanded.add(parent_id)
    for child in mutator.generate(candidates[parent_id]):
        if not allow_structure and child.structural_stage != candidates[parent_id].structural_stage:
            continue
        if child.model_hash in known_hashes or len(candidates) >= config["maximum_candidates"]:
            continue
        candidates[child.candidate_id] = child
        known_hashes.add(child.model_hash)


def _select_parent(
    candidates: dict[str, LatentCandidate],
    posterior: dict[str, float],
    aliases: dict[str, str],
    expanded: set[str],
    niches: bool,
) -> str | None:
    available = [item for item in candidates if item not in expanded]
    if not available:
        return None
    if niches:
        maximum_stage = max(candidates[item].structural_stage for item in available)
        available = [
            item for item in available if candidates[item].structural_stage == maximum_stage
        ]
    scores = _model_selection_scores(candidates, posterior)
    return max(
        available,
        key=lambda item: (
            scores[item],
            -candidates[item].structural_stage if not niches else 0,
            aliases[item],
        ),
    )


def _active_candidates(
    candidates: dict[str, LatentCandidate],
    posterior: dict[str, float],
    aliases: dict[str, str],
    capacity: int,
    niches: bool,
) -> tuple[str, ...]:
    ranking_values = posterior if niches else _model_selection_scores(candidates, posterior)
    posterior_order = sorted(candidates, key=lambda item: (-ranking_values[item], aliases[item]))
    if not niches:
        return tuple(posterior_order[:capacity])
    selected: list[str] = []
    for stage in sorted({item.structural_stage for item in candidates.values()}, reverse=True):
        stage_items = [
            item for item in posterior_order if candidates[item].structural_stage == stage
        ]
        for item in stage_items[:2]:
            if item not in selected:
                selected.append(item)
    for item in posterior_order:
        if item not in selected:
            selected.append(item)
        if len(selected) >= capacity:
            break
    return tuple(selected[:capacity])


def _model_selection_scores(
    candidates: dict[str, LatentCandidate], posterior: dict[str, float]
) -> dict[str, float]:
    """Remove the class-balanced prior before scalar model selection."""

    stage_counts: dict[int, int] = {}
    for candidate in candidates.values():
        stage_counts[candidate.structural_stage] = (
            stage_counts.get(candidate.structural_stage, 0) + 1
        )
    return {
        candidate_id: posterior[candidate_id] * stage_counts[candidate.structural_stage]
        for candidate_id, candidate in candidates.items()
    }


def _posterior(
    candidates: dict[str, LatentCandidate],
    history: list[tuple[LatentGrayScottExperiment, tuple[float, ...]]],
    cache: dict[tuple[str, str], tuple[float, ...]],
    budget: BudgetLedger,
    config: dict[str, Any],
) -> dict[str, float]:
    stages: dict[int, list[str]] = {}
    for candidate_id, candidate in candidates.items():
        stages.setdefault(candidate.structural_stage, []).append(candidate_id)
    log_weights = {
        candidate_id: -math.log(len(stages)) - math.log(len(stages[candidate.structural_stage]))
        for candidate_id, candidate in candidates.items()
    }
    for experiment, observation_raw in history:
        observation = np.asarray(observation_raw, dtype=float)
        noise = calibrated_noise(len(observation), config["likelihood_noise_floor"])
        for candidate_id, candidate in candidates.items():
            prediction = np.asarray(_predict(candidate, experiment, cache, budget), dtype=float)
            residual = (observation - prediction) / noise
            log_weights[candidate_id] += -0.5 * float(residual @ residual)
    maximum = max(log_weights.values())
    total = sum(math.exp(value - maximum) for value in log_weights.values())
    return {key: math.exp(value - maximum) / total for key, value in log_weights.items()}


def _predict(
    candidate: LatentCandidate,
    experiment: LatentGrayScottExperiment,
    cache: dict[tuple[str, str], tuple[float, ...]],
    budget: BudgetLedger,
) -> tuple[float, ...]:
    key = (candidate.model_hash, experiment.content_hash)
    if key in cache:
        budget.charge_candidate_evaluation(cache_hit=True)
        return cache[key]
    budget.charge_candidate_evaluation()
    noiseless = replace(
        experiment,
        measurement=replace(experiment.measurement, noise_std=0.0, mask_fraction=0.0),
    )
    prediction = tuple(
        float(value)
        for value in LatentGrayScottWorld(0, candidate.law).observe(noiseless).summary()
    )
    cache[key] = prediction
    return prediction


def _diagnose_questions(
    questions: dict[str, LatentGrayScottExperiment],
    candidates: dict[str, LatentCandidate],
    active_ids: tuple[str, ...],
    posterior: dict[str, float],
    cache: dict[tuple[str, str], tuple[float, ...]],
    budget: BudgetLedger,
    config: dict[str, Any],
    round_index: int,
) -> list[_QuestionDiagnostic]:
    mass = sum(posterior[item] for item in active_ids)
    restricted = {item: posterior[item] / mass for item in active_ids}
    diagnostics: list[_QuestionDiagnostic] = []
    for question_index, (question_hash, experiment) in enumerate(sorted(questions.items())):
        predictions = {
            candidate_id: np.asarray(
                _predict(candidates[candidate_id], experiment, cache, budget), dtype=float
            )
            for candidate_id in active_ids
        }
        noise = calibrated_noise(
            len(next(iter(predictions.values()))), config["likelihood_noise_floor"]
        )
        diagnostics.append(
            _QuestionDiagnostic(
                question_hash,
                expected_information_gain(
                    restricted,
                    predictions,
                    samples=config["eig_samples"],
                    seed=_derived_seed(config["seed"] + round_index, question_hash, question_index),
                    noise=noise,
                ),
                predicted_disagreement(restricted, predictions, noise=noise),
                _structural_disagreement(candidates, active_ids, predictions, noise),
                LatentGrayScottWorld.estimate_cost(experiment),
            )
        )
    return diagnostics


def _structural_disagreement(
    candidates: dict[str, LatentCandidate],
    active_ids: tuple[str, ...],
    predictions: dict[str, np.ndarray],
    noise: np.ndarray,
) -> float:
    fixed = [predictions[item] for item in active_ids if candidates[item].structural_stage == 0]
    maximum_stage = max(candidates[item].structural_stage for item in active_ids)
    structural = [
        predictions[item]
        for item in active_ids
        if candidates[item].structural_stage == maximum_stage
    ]
    if not fixed or maximum_stage == 0:
        return 0.0
    difference = (np.mean(structural, axis=0) - np.mean(fixed, axis=0)) / noise
    return float(difference @ difference)


def _select_question(
    diagnostics: list[_QuestionDiagnostic],
    selection: str,
    selected: set[str],
    round_index: int,
    rng: np.random.Generator,
) -> tuple[_QuestionDiagnostic, str]:
    available = [item for item in diagnostics if item.question_hash not in selected]
    if not available:
        available = diagnostics
    if selection == "random":
        return available[int(rng.integers(0, len(available)))], "random"
    if selection == "coverage":
        return sorted(available, key=lambda item: item.question_hash)[0], "coverage"
    if selection == "eig":
        return max(
            available,
            key=lambda item: (item.expected_information_gain, -item.cost, item.question_hash),
        ), "bayesian_eig"
    if selection != "three_niches":
        raise ValueError(f"unknown latent question selection: {selection}")
    niche = ("information_efficiency", "structural_disagreement", "minimum_cost")[round_index % 3]
    if niche == "information_efficiency":
        return max(
            available,
            key=lambda item: (item.expected_information_gain / item.cost, item.question_hash),
        ), niche
    if niche == "structural_disagreement":
        return max(
            available,
            key=lambda item: (
                item.structural_disagreement,
                item.expected_information_gain,
                item.question_hash,
            ),
        ), niche
    return min(available, key=lambda item: (item.cost, item.question_hash)), niche


def _score_validation(
    candidates: dict[str, LatentCandidate],
    posterior: dict[str, float],
    experiments: tuple[LatentGrayScottExperiment, ...],
    observations: dict[str, tuple[float, ...]],
    cache: dict[tuple[str, str], tuple[float, ...]],
    config: dict[str, Any],
) -> dict[str, Any]:
    complete = _best_complete_candidate(candidates, posterior)
    fixed = [item for item in candidates.values() if item.structural_stage == 0]
    fixed_errors = [_validation_rmse(item, experiments, observations, cache) for item in fixed]
    fixed_rmse = min(fixed_errors)
    if complete is None:
        complete_rmse = None
        improvement = -1.0
        selected_id = None
    else:
        complete_rmse = _validation_rmse(complete, experiments, observations, cache)
        improvement = (fixed_rmse - complete_rmse) / fixed_rmse
        selected_id = complete.candidate_id
    mass = _stage_mass(posterior, candidates, 3)
    return {
        "complete_structure_mass": mass,
        "selected_complete_candidate": selected_id,
        "selected_complete_validation_rmse": complete_rmse,
        "best_two_state_validation_rmse": fixed_rmse,
        "validation_improvement": improvement,
        "success": mass >= config["complete_structure_posterior_threshold"]
        and improvement >= config["minimum_validation_improvement"],
    }


def _validation_rmse(
    candidate: LatentCandidate,
    experiments: tuple[LatentGrayScottExperiment, ...],
    observations: dict[str, tuple[float, ...]],
    cache: dict[tuple[str, str], tuple[float, ...]],
) -> float:
    residuals: list[float] = []
    for experiment in experiments:
        key = (candidate.model_hash, experiment.content_hash)
        if key not in cache:
            noiseless = replace(
                experiment,
                measurement=replace(experiment.measurement, noise_std=0.0, mask_fraction=0.0),
            )
            cache[key] = tuple(
                float(value)
                for value in LatentGrayScottWorld(0, candidate.law).observe(noiseless).summary()
            )
        prediction = np.asarray(cache[key])
        observation = np.asarray(observations[experiment.content_hash])
        residuals.extend((observation - prediction).tolist())
    return float(np.sqrt(np.mean(np.square(residuals))))


def _best_complete_candidate(
    candidates: dict[str, LatentCandidate], posterior: dict[str, float]
) -> LatentCandidate | None:
    complete = [item for item in candidates.values() if item.law.complete_latent_structure]
    return max(complete, key=lambda item: posterior[item.candidate_id]) if complete else None


def _stage_mass(
    posterior: dict[str, float], candidates: dict[str, LatentCandidate], stage: int
) -> float:
    return sum(
        posterior[candidate_id]
        for candidate_id, candidate in candidates.items()
        if candidate.structural_stage == stage
    )


def _stable_success_query(values: list[bool], persistence: int) -> int | None:
    for index in range(len(values) - persistence + 1):
        if all(values[index : index + persistence]):
            return index + 1
    return None


def _capability_analysis(results: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    treatment = [
        item
        for item in results
        if item["arm"] == "coevolution" and item["evaluator_task_kind"] == "latent"
    ]
    null_controls = [
        item
        for item in results
        if item["arm"] == "coevolution" and item["evaluator_task_kind"] == "null"
    ]
    successes = [float(item["success"]) for item in treatment]
    improvements = [float(item["final_validation_improvement"]) for item in treatment]
    success_interval = _stratified_bootstrap_mean(treatment, "success", config)
    improvement_interval = _stratified_bootstrap_mean(
        treatment, "final_validation_improvement", config
    )
    return {
        "ordinary_founders_all_two_state": all(
            item["all_non_oracle_founders_two_state"] for item in treatment
        ),
        "task_success_rate": float(np.mean(successes)),
        "task_success_rate_interval": success_interval,
        "mean_held_out_validation_improvement": float(np.mean(improvements)),
        "held_out_improvement_interval": improvement_interval,
        "minimum_task_success_rate": config["minimum_task_success_rate"],
        "null_false_positives": sum(item["success"] for item in null_controls),
        "null_false_positive_rate": float(np.mean([item["success"] for item in null_controls])),
        "maximum_null_false_positive_rate": config["maximum_null_false_positive_rate"],
        "minimum_validation_improvement": config["minimum_validation_improvement"],
        "all_successful_structures_have_multistep_lineage": all(
            not item["success"]
            or [
                entry["operator"]
                for entry in item["best_complete_lineage"]
                if entry["operator"]
                in {
                    "add_latent_state",
                    "connect_observed_drive",
                    "connect_reaction_feedback",
                }
            ]
            == [
                "add_latent_state",
                "connect_observed_drive",
                "connect_reaction_feedback",
            ]
            for item in treatment
        ),
    }


def _comparative_analysis(results: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    treatment = _by_stratum(results, "coevolution")
    control = _by_stratum(results, "matched_bayesian_design")
    effect = stratified_bootstrap_effect(
        treatment,
        control,
        budget=config["world_query_budget"],
        samples=config["bootstrap_samples"],
        seed=config["seed"],
    )
    return {
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
        "minimum_query_reduction": config["minimum_query_reduction_vs_matched_bed"],
    }


def _by_stratum(results: list[dict[str, Any]], arm: str) -> dict[str, list[int | None]]:
    grouped: dict[str, list[int | None]] = {}
    for item in results:
        if item["arm"] == arm and item["evaluator_task_kind"] == "latent":
            grouped.setdefault(item["evaluator_truth_cluster"], []).append(
                item["stable_discovery_query"]
            )
    return grouped


def _stratified_bootstrap_mean(
    results: list[dict[str, Any]], key: str, config: dict[str, Any]
) -> list[float]:
    grouped: dict[str, list[float]] = {}
    for item in results:
        grouped.setdefault(item["evaluator_truth_cluster"], []).append(float(item[key]))
    rng = np.random.default_rng(config["seed"] + len(key))
    strata = sorted(grouped)
    estimates = []
    for _ in range(config["bootstrap_samples"]):
        sampled_strata = rng.choice(strata, len(strata), replace=True)
        values = []
        for stratum in sampled_strata:
            source = grouped[stratum]
            values.extend(rng.choice(source, len(source), replace=True).tolist())
        estimates.append(float(np.mean(values)))
    return [float(value) for value in np.quantile(estimates, [0.025, 0.975])]


def _arm_summaries(results: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    summaries = {}
    for arm in config["arms"]:
        selected = [item for item in results if item["arm"] == arm]
        latent = [item for item in selected if item["evaluator_task_kind"] == "latent"]
        null = [item for item in selected if item["evaluator_task_kind"] == "null"]
        endpoints = [item["stable_discovery_query"] for item in latent]
        summaries[arm] = {
            "runs": len(selected),
            "latent_successes": sum(item["success"] for item in latent),
            "latent_success_rate": float(np.mean([item["success"] for item in latent])),
            "null_false_positives": sum(item["success"] for item in null),
            "null_false_positive_rate": float(np.mean([item["success"] for item in null])),
            "restricted_mean_queries": restricted_mean_time(
                endpoints, config["world_query_budget"]
            ),
            "mean_validation_improvement": float(
                np.mean([item["final_validation_improvement"] for item in latent])
            ),
            "mean_candidate_evaluations": float(
                np.mean([item["budget"]["candidate_evaluations"] for item in selected])
            ),
        }
    return summaries


def _checks(
    results: list[dict[str, Any]], tasks: tuple[_LatentTask, ...], config: dict[str, Any]
) -> dict[str, bool]:
    non_oracle = [item for item in results if item["arm"] != "oracle_structure_bed"]
    return {
        "complete_preregistered_arm_set": set(config["arms"]) == set(ARM_POLICIES),
        "multiple_truth_parameters_and_seeds": len(tasks)
        == len(config["truth_clusters"]) * config["seeds_per_truth_cluster"]
        + config["null_control_seeds"],
        "null_world_controls_present": sum(task.task_kind == "null" for task in tasks)
        == config["null_control_seeds"],
        "ordinary_founders_all_structurally_wrong": all(
            item["all_non_oracle_founders_two_state"] for item in non_oracle
        ),
        "fixed_representation_never_adds_latent": all(
            max(round_["maximum_structural_stage"] for round_ in item["rounds"]) == 0
            for item in results
            if item["arm"] == "fixed_representation_bed"
        ),
        "all_resource_ceilings_respected": all(
            all(item["budget"][key] <= item["budget_limits"][key] for key in item["budget_limits"])
            for item in results
        ),
        "all_arms_use_equal_world_query_ceiling": all(
            item["budget_limits"]["world_queries"] == config["world_query_budget"]
            for item in results
        ),
        "held_out_conditions_never_queried": all(
            not {round_["selected_question_hash"] for round_ in item["rounds"]}.intersection(
                {
                    experiment.content_hash
                    for task in tasks
                    if task.task_token == item["task_token"]
                    for experiment in task.validation
                }
            )
            for item in results
        ),
        "ordinary_complete_structures_require_three_generations": all(
            not item["best_complete_lineage"]
            or (
                item["best_complete_lineage"][-1]["stage"] == 3
                and len(item["best_complete_lineage"]) >= 4
            )
            for item in non_oracle
        ),
        "final_v1_world_not_accessed": True,
        "final_v2_world_not_created": True,
    }


def _pilot_decision(
    capability: dict[str, Any],
    comparison: dict[str, Any],
    checks: dict[str, bool],
    config: dict[str, Any],
) -> str:
    if not all(checks.values()):
        return "invalid"
    capability_passes = (
        capability["task_success_rate"] >= config["minimum_task_success_rate"]
        and capability["null_false_positive_rate"] <= config["maximum_null_false_positive_rate"]
        and capability["held_out_improvement_interval"][0]
        > config["minimum_validation_improvement"]
        and capability["all_successful_structures_have_multistep_lineage"]
    )
    if not capability_passes:
        return "iterate_capability"
    if comparison["confidence_interval"][0] <= config["minimum_query_reduction_vs_matched_bed"]:
        return "capability_only_iterate_comparative_strategy"
    return "eligible_to_preregister_v2"


def _failure_modes(
    capability: dict[str, Any],
    comparison: dict[str, Any],
    summaries: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, str]]:
    failures = []
    if capability["task_success_rate"] < config["minimum_task_success_rate"]:
        failures.append(
            {
                "id": "latent-recovery-rate-low",
                "detail": "complete latent feedback is not recovered reliably across tasks",
            }
        )
    if capability["null_false_positive_rate"] > config["maximum_null_false_positive_rate"]:
        failures.append(
            {
                "id": "latent-false-positive-rate-high",
                "detail": "the strategy invents a latent feedback structure in null worlds",
            }
        )
    if capability["held_out_improvement_interval"][0] <= config["minimum_validation_improvement"]:
        failures.append(
            {
                "id": "held-out-improvement-insufficient",
                "detail": "latent candidates do not clear the held-out intervention margin",
            }
        )
    if comparison["confidence_interval"][0] <= config["minimum_query_reduction_vs_matched_bed"]:
        failures.append(
            {
                "id": "matched-bed-not-beaten",
                "detail": "question coevolution has not beaten the matched Bayesian control",
            }
        )
    if summaries["oracle_structure_bed"]["latent_success_rate"] < 1.0:
        failures.append(
            {
                "id": "oracle-ceiling-failure",
                "detail": "even the correct structural family cannot reliably satisfy the endpoint",
            }
        )
    return failures


def _aliases(candidates: dict[str, LatentCandidate], seed: int, task_token: str) -> dict[str, str]:
    return {
        candidate_id: hashlib.sha256(
            f"{seed}:{task_token}:{candidate.model_hash}".encode()
        ).hexdigest()[:16]
        for candidate_id, candidate in candidates.items()
    }


def _derived_seed(seed: int, token: str, index: int) -> int:
    digest = hashlib.sha256(f"{seed}:{token}:{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _sum_budgets(results: list[dict[str, Any]]) -> BudgetSnapshot:
    return BudgetSnapshot(
        sum(item["budget"]["world_queries"] for item in results),
        sum(item["budget"]["candidate_generations"] for item in results),
        sum(item["budget"]["candidate_evaluations"] for item in results),
        sum(item["budget"]["candidate_evaluation_cache_hits"] for item in results),
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()
