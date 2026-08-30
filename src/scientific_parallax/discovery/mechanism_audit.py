"""Factorial attribution audit; does not modify or reopen either v2 final world.

Run with ``python -m scientific_parallax.discovery.mechanism_audit``.
The strategy never receives validation observations or task-kind labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.coevolution.evidence import calibrated_noise
from scientific_parallax.core.budget import BudgetLedger, BudgetLimits
from scientific_parallax.core.reproducibility import capture_environment, content_hash
from scientific_parallax.discovery.latent_model import (
    LatentCandidate,
    LatentStructureMutator,
    two_state_founders,
)
from scientific_parallax.discovery.latent_questions import LatentQuestionMutator
from scientific_parallax.discovery.latent_runner import (
    _active_candidates,
    _aliases,
    _build_tasks,
    _derived_seed,
    _diagnose_questions,
    _evolve_questions,
    _expand_parent,
    _initial_question_pool,
    _LatentTask,
    _model_selection_scores,
    _posterior,
    _predict,
    _score_validation,
    _select_parent,
    _select_question,
    _stable_success_query,
    _validate_config,
    _validation_rmse,
)
from scientific_parallax.worlds.latent_gray_scott import (
    LatentGrayScottExperiment,
    LatentGrayScottWorld,
    LatentLaw,
)


@dataclass(frozen=True)
class AuditPolicy:
    parent_priority: bool = False
    ensemble_niches: bool = False
    passive: bool = False
    parent_mode: str = "legacy"


POLICIES = {
    **{f"p{p}e{e}": AuditPolicy(bool(p), bool(e)) for p in range(2) for e in range(2)},
    **{
        f"passive_p{p}e{e}": AuditPolicy(bool(p), bool(e), passive=True)
        for p in range(2)
        for e in range(2)
    },
    "uniform": AuditPolicy(ensemble_niches=True, parent_mode="uniform"),
    "breadth_first": AuditPolicy(ensemble_niches=True, parent_mode="breadth_first"),
    "map_elites": AuditPolicy(ensemble_niches=True, parent_mode="map_elites"),
    "scalar_archive": AuditPolicy(ensemble_niches=True, parent_mode="scalar_archive"),
}


def graph_descriptor(candidate: LatentCandidate) -> tuple[int, tuple[tuple[int, int], ...]]:
    """Unlabelled degree signature, without stage, task or correctness access.

    In the *restricted* v2 grammar this can still coincide with stage classes.
    It is not a claim of answer-independent search in an unrestricted grammar.
    """
    law = candidate.law
    nodes = 3 if law.has_latent_state else 2
    edges = [(0, 1), (1, 0)]
    if law.observed_drive_connected:
        edges.append((1, 2))
    if law.reaction_feedback_connected:
        edges.extend([(2, 0), (2, 1)])
    degrees = tuple(
        sorted(
            (sum(v == node for _, v in edges), sum(u == node for u, _ in edges))
            for node in range(nodes)
        )
    )
    return nodes, degrees


def retain_archive(
    eligible: set[str],
    candidates: dict[str, LatentCandidate],
    posterior: dict[str, float],
    aliases: dict[str, str],
    capacity: int,
    mode: str,
) -> set[str]:
    scores = _model_selection_scores(candidates, posterior)
    ranked = sorted(eligible, key=lambda key: (-scores[key], aliases[key]))
    if mode == "scalar_archive":
        return set(ranked[:capacity])
    if mode != "map_elites":
        raise ValueError("unsupported archive mode")
    cells: dict[tuple, str] = {}
    for key in ranked:
        cells.setdefault(graph_descriptor(candidates[key]), key)
    # In this grammar there are four descriptors; refuse hidden truncation.
    if len(cells) > capacity:
        raise ValueError("archive capacity is smaller than the descriptor space")
    return set(cells.values())


def select_search_parent(
    candidates: dict[str, LatentCandidate],
    posterior: dict[str, float],
    aliases: dict[str, str],
    expanded: set[str],
    policy: AuditPolicy,
    archive: set[str],
    rng: np.random.Generator,
) -> str | None:
    if policy.parent_mode == "legacy":
        return _select_parent(candidates, posterior, aliases, expanded, policy.parent_priority)
    pool = archive if policy.parent_mode in {"map_elites", "scalar_archive"} else set(candidates)
    available = sorted(pool - expanded, key=lambda key: aliases[key])
    if not available:
        return None
    if policy.parent_mode == "breadth_first":
        return min(available, key=lambda key: (candidates[key].generation, aliases[key]))
    return available[int(rng.integers(len(available)))]


def training_choice(
    candidates: dict[str, LatentCandidate],
    posterior: dict[str, float],
    aliases: dict[str, str],
) -> str:
    """Select any representation by data fit; prefer smaller structures on exact ties."""
    scores = _model_selection_scores(candidates, posterior)
    return max(
        candidates,
        key=lambda key: (scores[key], -candidates[key].structural_stage, aliases[key]),
    )


def search(
    task_token: str,
    questions_seed: tuple[LatentGrayScottExperiment, ...],
    observe: Any,
    policy: AuditPolicy,
    config: dict[str, Any],
    archive_capacity: int,
) -> dict[str, Any]:
    """Only receives an observation callback, not the task truth or validation."""
    budget = BudgetLedger(
        BudgetLimits(
            config["world_query_budget"],
            config["candidate_generation_budget"],
            config["candidate_evaluation_budget"],
        )
    )
    candidates = {item.candidate_id: item for item in two_state_founders()}
    known_hashes = {item.model_hash for item in candidates.values()}
    expanded: set[str] = set()
    archive = set(candidates)
    mutator = LatentStructureMutator()
    q_mutator = LatentQuestionMutator(tuple(config["question_mutations"]))
    # Construct the original pool without passing a truth-bearing task object.
    questions = {item.content_hash: item for item in questions_seed}
    if policy.passive:
        for generation, parent in enumerate(questions_seed, start=1):
            for child in q_mutator.generate(parent, generation):
                questions.setdefault(child.content_hash, child)
                if len(questions) >= config["maximum_questions"]:
                    break
            if len(questions) >= config["maximum_questions"]:
                break
    aliases = _aliases(candidates, config["seed"], task_token)
    cache: dict[tuple[str, str], tuple[float, ...]] = {}
    history: list[tuple[LatentGrayScottExperiment, tuple[float, ...]]] = []
    selected_questions: set[str] = set()
    checkpoints = []
    trace = []
    rng = np.random.default_rng(_derived_seed(config["seed"], task_token, 0))

    for round_index in range(config["world_query_budget"]):
        prior = _posterior(candidates, history, cache, budget, config)
        if policy.parent_mode in {"map_elites", "scalar_archive"}:
            archive = retain_archive(
                archive, candidates, prior, aliases, archive_capacity, policy.parent_mode
            )
        parent = select_search_parent(candidates, prior, aliases, expanded, policy, archive, rng)
        before = set(candidates)
        if parent is not None:
            _expand_parent(
                parent, candidates, known_hashes, expanded, mutator, budget, config, True
            )
            aliases.update(_aliases(candidates, config["seed"], task_token))
            prior = _posterior(candidates, history, cache, budget, config)
            archive.update(set(candidates) - before)
        if policy.parent_mode in {"map_elites", "scalar_archive"}:
            archive = retain_archive(
                archive, candidates, prior, aliases, archive_capacity, policy.parent_mode
            )
        active = _active_candidates(
            candidates, prior, aliases, config["active_candidates"], policy.ensemble_niches
        )
        if policy.passive:
            unused = sorted(set(questions) - selected_questions)
            selected_hash = (unused or sorted(questions))[0]
        else:
            diagnostics = _diagnose_questions(
                questions, candidates, active, prior, cache, budget, config, round_index
            )
            selected, _ = _select_question(
                diagnostics, "three_niches", selected_questions, round_index, rng
            )
            selected_hash = selected.question_hash
        experiment = questions[selected_hash]
        predictions = {
            key: _predict(item, experiment, cache, budget) for key, item in candidates.items()
        }
        prediction_commitment = content_hash(predictions)
        budget.charge_world_query()
        observation = tuple(float(value) for value in observe(experiment).summary())
        history.append((experiment, observation))
        posterior = _posterior(candidates, history, cache, budget, config)
        chosen = training_choice(candidates, posterior, aliases)
        trace.append(
            {
                "query": round_index + 1,
                "question_hash": selected_hash,
                "parent_model_hash": candidates[parent].model_hash if parent else None,
                "prediction_commitment": prediction_commitment,
                "candidate_count": len(candidates),
                "eligible_parent_count": len(archive)
                if policy.parent_mode in {"map_elites", "scalar_archive"}
                else len(candidates),
                "maximum_stage": max(item.structural_stage for item in candidates.values()),
                "chosen_model_hash": candidates[chosen].model_hash,
                "chosen_stage": candidates[chosen].structural_stage,
            }
        )
        # Only identifiers/posteriors are stored; held-out evaluation is later.
        checkpoints.append((tuple(candidates), posterior.copy()))
        selected_questions.add(selected_hash)
        if not policy.passive:
            questions = _evolve_questions(
                questions, selected_hash, q_mutator, round_index, config["maximum_questions"]
            )
    return {
        "candidates": candidates,
        "chosen": candidates[chosen],
        "history": history,
        "trace": trace,
        "checkpoints": checkpoints,
        "budget": asdict(budget.snapshot),
        "budget_limits": asdict(budget.limits),
    }


def fixed_reference(
    history: list[tuple[LatentGrayScottExperiment, tuple[float, ...]]],
    scales: list[float],
    noise_floor: float,
) -> tuple[LatentCandidate, dict[str, int]]:
    """Training-only grid fit; no latent-class requirement or oracle test selection."""
    budget = BudgetLedger(BudgetLimits(len(history), len(scales), len(scales) * len(history)))
    cache: dict[tuple[str, str], tuple[float, ...]] = {}
    fits = []
    for index, scale in enumerate(scales):
        budget.charge_candidate_generation()
        candidate = LatentCandidate(
            f"fixed-grid-{index}",
            LatentLaw(False, False, False, reaction_scale=scale),
            0,
            None,
            None,
        )
        error = 0.0
        for experiment, observed in history:
            predicted = np.asarray(_predict(candidate, experiment, cache, budget))
            noise = calibrated_noise(len(observed), noise_floor)
            error += float(np.sum(((predicted - np.asarray(observed)) / noise) ** 2))
        fits.append((error, index, candidate))
    chosen = min(fits, key=lambda item: (item[0], item[1]))[2]
    return chosen, {
        **asdict(budget.snapshot),
        "shared_observation_count": len(history),
        "grid_size": len(scales),
    }


def field_rmse(
    candidate: LatentCandidate,
    experiments: tuple[LatentGrayScottExperiment, ...],
    observations: dict[str, Any],
) -> float:
    """Secondary pointwise visible-field error, never a search/selection input."""
    squared_error = 0.0
    count = 0
    for experiment in experiments:
        noiseless = replace(
            experiment,
            measurement=replace(experiment.measurement, noise_std=0.0, mask_fraction=0.0),
        )
        predicted = LatentGrayScottWorld(0, candidate.law).observe(noiseless)
        observed = observations[experiment.content_hash]
        for key, target in observed.fields.items():
            residual = predicted.fields[key] - target
            finite = residual[np.isfinite(residual)]
            squared_error += float(np.sum(finite**2))
            count += finite.size
    if count == 0:
        raise ValueError("validation fields have no finite observations")
    return math.sqrt(squared_error / count)


def run_task(
    task: _LatentTask, arm: str, config: dict[str, Any], audit: dict[str, Any]
) -> dict[str, Any]:
    world = LatentGrayScottWorld(task.measurement_seed, task.law)
    search_result = search(
        task.task_token,
        task.questions,
        world.observe,
        POLICIES[arm],
        config,
        audit["archive_capacity"],
    )
    reference, reference_budget = fixed_reference(
        search_result["history"], audit["fixed_reaction_scales"], config["likelihood_noise_floor"]
    )
    # This is the first point where validation observations are obtained.
    observed_fields = {
        experiment.content_hash: world.observe(experiment) for experiment in task.validation
    }
    validation = {
        key: tuple(float(x) for x in observed.summary())
        for key, observed in observed_fields.items()
    }
    validation_cache: dict[tuple[str, str], tuple[float, ...]] = {}
    chosen = search_result["chosen"]
    error = _validation_rmse(chosen, task.validation, validation, validation_cache)
    reference_error = _validation_rmse(reference, task.validation, validation, validation_cache)
    field_error = field_rmse(chosen, task.validation, observed_fields)
    reference_field_error = field_rmse(reference, task.validation, observed_fields)
    improvement = 1.0 - error / max(reference_error, np.finfo(float).eps)
    compatibility = []
    for keys, posterior in search_result["checkpoints"]:
        subset = {key: search_result["candidates"][key] for key in keys}
        compatibility.append(
            _score_validation(
                subset, posterior, task.validation, validation, validation_cache, config
            )
        )
    compatibility_query = _stable_success_query(
        [item["success"] for item in compatibility], config["persistence_checkpoints"]
    )
    seed_pool = _initial_question_pool(task, config, True)
    queried = {row["question_hash"] for row in search_result["trace"]}
    held_out = set(validation)
    limits = search_result["budget_limits"]
    budget = search_result["budget"]
    return {
        "task_token": task.task_token,
        "task_kind": task.task_kind,
        "truth_cluster": task.truth_cluster,
        "arm": arm,
        "policy": asdict(POLICIES[arm]),
        "validation_rmse": error,
        "validation_metric": "RMSE of four visible-field summary features per frame",
        "secondary_full_field_rmse": field_error,
        "secondary_fixed_reference_field_rmse": reference_field_error,
        "fixed_reference_rmse": reference_error,
        "fixed_reference_scale": reference.law.reaction_scale,
        "relative_improvement_vs_fixed": improvement,
        "predictive_win": improvement >= config["minimum_validation_improvement"],
        "complete_structure_selected": chosen.law.complete_latent_structure,
        "selected_law": asdict(chosen.law),
        "compatibility_v2_success": compatibility_query is not None,
        "compatibility_v2_query": compatibility_query,
        "first_complete_generated_query": next(
            (row["query"] for row in search_result["trace"] if row["maximum_stage"] == 3), None
        ),
        "trace": search_result["trace"],
        "budget": budget,
        "budget_limits": limits,
        "fixed_reference_budget": reference_budget,
        "validation_model_evaluations": len(validation_cache),
        "secondary_field_model_evaluations": 2 * len(task.validation),
        "held_out_conditions_never_queried": not (held_out & queried or held_out & set(seed_pool)),
        "resource_ceilings_respected": all(budget[key] <= value for key, value in limits.items()),
    }


def _task_worker(payload: tuple) -> list[dict[str, Any]]:
    task, config, audit = payload
    return [run_task(task, arm, config, audit) for arm in POLICIES]


def _interval(rows: list[tuple[str, float]], draws: int, seed: int) -> dict[str, Any]:
    groups: dict[str, list[float]] = {}
    for cluster, value in rows:
        groups.setdefault(cluster, []).append(value)
    arrays = [np.asarray(group) for group in groups.values()]
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(draws):
        values = []
        for index in rng.integers(0, len(arrays), len(arrays)):
            array = arrays[index]
            values.extend(rng.choice(array, len(array), replace=True).tolist())
        means.append(float(np.mean(values)))
    return {
        "mean": float(np.mean([value for _, value in rows])),
        "interval_95": np.quantile(means, [0.025, 0.975]).tolist(),
        "task_count": len(rows),
        "cluster_count": len(groups),
        "uncertainty": "descriptive hierarchical cluster/task bootstrap; few clusters",
    }


def summarize(results: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    index = {(row["task_token"], row["arm"]): row for row in results}
    latent = [row for row in results if row["task_kind"] == "latent" and row["arm"] == "p0e0"]
    summaries = {}
    for arm in POLICIES:
        rows = [row for row in results if row["arm"] == arm]
        positives = [row for row in rows if row["task_kind"] == "latent"]
        nulls = [row for row in rows if row["task_kind"] == "null"]
        summaries[arm] = {
            "latent_tasks": len(positives),
            "mean_validation_rmse": float(np.mean([x["validation_rmse"] for x in positives])),
            "mean_full_field_rmse": float(
                np.mean([x["secondary_full_field_rmse"] for x in positives])
            ),
            "predictive_wins": sum(x["predictive_win"] for x in positives),
            "complete_structure_selected": sum(x["complete_structure_selected"] for x in positives),
            "compatibility_v2_successes": sum(x["compatibility_v2_success"] for x in positives),
            "mean_generation_attempts": float(
                np.mean([x["budget"]["candidate_generations"] for x in rows])
            ),
            "mean_candidate_evaluations": float(
                np.mean([x["budget"]["candidate_evaluations"] for x in rows])
            ),
            "null_tasks": len(nulls),
            "null_complete_structure_selected": sum(
                x["complete_structure_selected"] for x in nulls
            ),
            "null_latent_predictive_wins": sum(
                x["complete_structure_selected"] and x["predictive_win"] for x in nulls
            ),
        }
    comparisons = {}
    pairs = {
        "priority_at_e0": ("p1e0", "p0e0"),
        "priority_at_e1": ("p1e1", "p0e1"),
        "ensemble_at_p0": ("p0e1", "p0e0"),
        "ensemble_at_p1": ("p1e1", "p1e0"),
        "map_vs_scalar_archive": ("map_elites", "scalar_archive"),
        "guided_vs_map": ("p1e1", "map_elites"),
        "guided_vs_uniform": ("p1e1", "uniform"),
        "guided_vs_breadth_first": ("p1e1", "breadth_first"),
    }
    for name, (treatment, control) in pairs.items():
        rows = []
        for task in latent:
            a = index[(task["task_token"], treatment)]["validation_rmse"]
            b = index[(task["task_token"], control)]["validation_rmse"]
            rows.append((task["truth_cluster"], 1.0 - a / max(b, np.finfo(float).eps)))
        comparisons[name] = {
            "treatment": treatment,
            "control": control,
            "metric": "paired relative terminal RMSE reduction; positive favors treatment",
            **_interval(rows, config["bootstrap_samples"], config["seed"]),
        }
    factorial = {}
    for metric in ("validation_rmse", "secondary_full_field_rmse"):
        values = {
            "parent_priority_main_benefit": [],
            "ensemble_main_benefit": [],
            "interaction": [],
        }
        for task in latent:
            y00, y01, y10, y11 = [
                index[(task["task_token"], arm)][metric] for arm in ("p0e0", "p0e1", "p1e0", "p1e1")
            ]
            values["parent_priority_main_benefit"].append(
                (task["truth_cluster"], (y00 - y10 + y01 - y11) / 2)
            )
            values["ensemble_main_benefit"].append(
                (task["truth_cluster"], (y00 - y01 + y10 - y11) / 2)
            )
            values["interaction"].append((task["truth_cluster"], (y01 - y11) - (y00 - y10)))
        factorial[metric] = {
            name: _interval(rows, config["bootstrap_samples"], config["seed"])
            for name, rows in values.items()
        }
    passive_checks = []
    for token, _ in index:
        for p in range(2):
            a, b = index[(token, f"passive_p{p}e0")], index[(token, f"passive_p{p}e1")]
            passive_checks.append(
                a["trace"] == b["trace"]
                and a["selected_law"] == b["selected_law"]
                and a["validation_rmse"] == b["validation_rmse"]
            )
    checks = {
        "unique_task_arm_pairs": len(index) == len(results),
        "complete_arm_set_per_task": all(
            sum(row["task_token"] == token for row in results) == len(POLICIES)
            for token in {row["task_token"] for row in results}
        ),
        "passive_ensemble_toggle_is_exact_null": all(passive_checks),
        "held_out_conditions_never_queried": all(
            x["held_out_conditions_never_queried"] for x in results
        ),
        "resource_ceilings_respected": all(x["resource_ceilings_respected"] for x in results),
        "equal_world_query_counts": {x["budget"]["world_queries"] for x in results}
        == {config["world_query_budget"]},
        "finite_prediction_scores": all(
            math.isfinite(x[key])
            for x in results
            for key in (
                "validation_rmse",
                "fixed_reference_rmse",
                "relative_improvement_vs_fixed",
                "secondary_full_field_rmse",
                "secondary_fixed_reference_field_rmse",
            )
        ),
    }
    return {
        "arm_summaries": summaries,
        "paired_comparisons": comparisons,
        "factorial_raw_rmse_effects": factorial,
        "factorial_sign_convention": (
            "positive main effect = lower error when enabled; "
            "interaction = priority benefit at E1 minus priority benefit at E0"
        ),
        "checks": checks,
        "interpretation_boundary": [
            "Factorial cells separate parent priority from ensemble balancing, not survival.",
            "The generic archive remains confined to the hand-designed three-step grammar.",
            "Predictive wins do not identify a unique physical hidden state.",
            "Intervals are descriptive, not multiplicity-corrected evidence of superiority.",
            "SymDer, QDSR and history-based dynamical models have not been run on these tasks.",
        ],
    }


def _source_hashes(root: Path) -> dict[str, str]:
    paths = sorted((root / "src/scientific_parallax").rglob("*.py"))
    paths += [root / "pyproject.toml", root / "uv.lock"]
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths
    }


def load_config(path: Path, root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    audit = json.loads(path.read_text(encoding="utf-8"))
    if audit["schema_version"] != 1 or audit["scope"] not in {"development", "frozen_validation"}:
        raise ValueError("unsupported mechanism audit config")
    if not isinstance(audit["workers"], int) or not 1 <= audit["workers"] <= 4:
        raise ValueError("audit workers must be between one and four")
    if audit["archive_capacity"] < 4:
        raise ValueError("archive must fit all four graph descriptors")
    scales = audit["fixed_reaction_scales"]
    if (
        not scales
        or len(scales) != len(set(scales))
        or any(not math.isfinite(value) or value <= 0 for value in scales)
    ):
        raise ValueError("reference grid must contain unique positive finite scales")
    base_path = (root / audit["base_config"]).resolve()
    if not base_path.is_relative_to(root.resolve()):
        raise ValueError("base config must be repository-local")
    config = json.loads(base_path.read_text(encoding="utf-8"))
    config.update(audit["overrides"])
    _validate_config(config)
    return audit, config


def run_audit(config_path: Path, output: Path, root: Path | None = None) -> dict[str, Any]:
    root = (root or Path.cwd()).resolve()
    audit, config = load_config(config_path, root)
    environment = capture_environment(root)
    if audit["scope"] == "frozen_validation" and (
        environment["git_dirty"] or not environment["git_revision"]
    ):
        raise RuntimeError("frozen validation requires a clean committed worktree")
    sources = _source_hashes(root)
    output.mkdir(parents=True, exist_ok=False)
    metadata = {
        "schema_version": 1,
        "experiment_version": audit["experiment_version"],
        "scope": audit["scope"],
        "assurance": (
            "local frozen out-of-sample replication; not independent custody"
            if audit["scope"] == "frozen_validation"
            else "local development experiment; no independent custody"
        ),
        "audit_config": audit,
        "resolved_config": config,
        "config_hash": content_hash({"audit": audit, "resolved": config}),
        "environment": environment,
        "source_hashes": sources,
        "source_hash": content_hash(sources),
    }
    _write_once(output / "registration.json", metadata)
    tasks = _build_tasks(config)
    results: list[dict[str, Any]] = []
    payloads = [(task, config, audit) for task in tasks]
    with (output / "task-results.jsonl").open("x", encoding="utf-8") as handle:
        if audit["workers"] == 1:
            batches = map(_task_worker, payloads)
            for batch in batches:
                _record_batch(batch, results, handle, len(tasks))
        else:
            with ProcessPoolExecutor(max_workers=audit["workers"]) as executor:
                for batch in executor.map(_task_worker, payloads):
                    _record_batch(batch, results, handle, len(tasks))
    report = {
        **metadata,
        "task_count": len(tasks),
        "run_count": len(results),
        **summarize(results, config),
        "task_results_sha256": hashlib.sha256(
            (output / "task-results.jsonl").read_bytes()
        ).hexdigest(),
    }
    report["checks"]["source_bytes_unchanged_during_run"] = sources == _source_hashes(root)
    report["status"] = "complete" if all(report["checks"].values()) else "invalid"
    _write_once(output / "report.json", report)
    if report["status"] != "complete":
        raise RuntimeError("mechanism audit failed integrity checks; inspect report")
    return report


def _record_batch(batch: list[dict[str, Any]], results: list, handle: Any, tasks: int) -> None:
    results.extend(batch)
    for row in batch:
        handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")
    handle.flush()
    print(f"Completed {len(results) // len(POLICIES)}/{tasks} task blocks", flush=True)


def _write_once(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_audit(args.config, args.output)
    print(json.dumps({"status": report["status"], "checks": report["checks"]}, indent=2))


if __name__ == "__main__":
    main()
