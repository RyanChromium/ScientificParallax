"""Replicated comparison and negative-control diagnostics for Step 0."""

from __future__ import annotations

import json
import random
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from scientific_parallax.step0.domain import Prediction
from scientific_parallax.step0.evidence import EvidenceEngine
from scientific_parallax.step0.experiment import ExperimentConfig, RunResult, run_experiment
from scientific_parallax.step0.paradigms import (
    TRUE_PARADIGM_ID,
    ContradictoryControl,
    fixed_paradigms,
)
from scientific_parallax.step0.strategies import select_max_disagreement
from scientific_parallax.step0.world import MisleadingScienceWorld, finite_question_pool


@dataclass(frozen=True, slots=True)
class StrategySummary:
    strategy: str
    replicates: int
    successes: int
    success_rate: float
    median_queries_with_censoring: float
    median_final_true_posterior: float


def _summarize(strategy: str, results: list[RunResult], budget: int) -> StrategySummary:
    query_counts = [result.sustained_identification_query or budget for result in results]
    successes = sum(result.sustained_identification_query is not None for result in results)
    return StrategySummary(
        strategy=strategy,
        replicates=len(results),
        successes=successes,
        success_rate=successes / len(results),
        median_queries_with_censoring=statistics.median(query_counts),
        median_final_true_posterior=statistics.median(
            result.final_true_posterior for result in results
        ),
    )


def run_negative_control(seed: int) -> dict[str, float | int | str | None]:
    """Run disagreement selection with a nonsense model in the candidate pool."""
    paradigms = fixed_paradigms()
    control = ContradictoryControl()
    candidates = (*paradigms, control)
    evidence = EvidenceEngine([candidate.paradigm_id for candidate in candidates])
    world = MisleadingScienceWorld(seed)
    remaining = list(finite_question_pool())
    initial_posterior = evidence.posterior[control.paradigm_id]
    first_query_below_prior: int | None = None
    maximum_posterior_after_evidence = 0.0
    for query_index in range(1, len(remaining) + 1):
        question = select_max_disagreement(
            remaining,
            candidates,
            evidence.posterior,
            random.Random(seed),
            41,
        )
        predictions = {
            candidate.paradigm_id: Prediction(
                candidate.paradigm_id,
                candidate.predict_mean(question),
                question.noise_std,
            )
            for candidate in candidates
        }
        posterior = evidence.update(predictions, world.observe(question))
        control_posterior = posterior[control.paradigm_id]
        maximum_posterior_after_evidence = max(
            maximum_posterior_after_evidence,
            control_posterior,
        )
        if first_query_below_prior is None and control_posterior < initial_posterior:
            first_query_below_prior = query_index
        remaining.remove(question)
    posterior = evidence.posterior
    return {
        "control_id": control.paradigm_id,
        "selection_strategy": "max_disagreement",
        "initial_posterior": initial_posterior,
        "first_query_below_prior": first_query_below_prior,
        "maximum_posterior_after_evidence": maximum_posterior_after_evidence,
        "final_posterior": posterior[control.paradigm_id],
        "true_final_posterior": posterior[TRUE_PARADIGM_ID],
    }


def run_benchmark(
    config: ExperimentConfig,
    output_dir: Path,
    strategies: list[str],
    replicates: int,
) -> dict[str, Any]:
    if replicates < 1:
        raise ValueError("replicates must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_results: dict[str, list[RunResult]] = {}
    for strategy in strategies:
        results = []
        for replicate in range(replicates):
            seed = config.noise_seed + replicate
            run_dir = output_dir / "runs" / strategy / f"seed-{seed}"
            results.append(run_experiment(config, strategy, run_dir, seed=seed))
        all_results[strategy] = results

    summaries = {
        strategy: asdict(_summarize(strategy, results, config.max_queries))
        for strategy, results in all_results.items()
    }
    batches: list[dict[str, Any]] = []
    batch_count = min(3, replicates)
    base_size, extra = divmod(replicates, batch_count)
    batch_start = 0
    for batch_index in range(1, batch_count + 1):
        batch_end = batch_start + base_size + (1 if batch_index <= extra else 0)
        batches.append(
            {
                "batch": batch_index,
                "seed_offset_range": [batch_start, batch_end - 1],
                "strategies": {
                    strategy: asdict(
                        _summarize(
                            strategy,
                            results[batch_start:batch_end],
                            config.max_queries,
                        )
                    )
                    for strategy, results in all_results.items()
                },
            }
        )
        batch_start = batch_end
    negative_control = run_negative_control(config.noise_seed)
    required_strategies_present = {"random", "bayesian_design"}.issubset(all_results)
    bayesian_beats_random_in_each_batch = required_strategies_present and all(
        batch["strategies"]["bayesian_design"]["median_queries_with_censoring"]
        < batch["strategies"]["random"]["median_queries_with_censoring"]
        for batch in batches
    )
    endpoint_measurable = all(summary["successes"] > 0 for summary in summaries.values())
    contradictory_control_rejected = (
        negative_control["final_posterior"] < negative_control["initial_posterior"]
        and negative_control["maximum_posterior_after_evidence"]
        < negative_control["initial_posterior"]
    )
    checks = {
        "endpoint_measurable": endpoint_measurable,
        "bayesian_design_beats_random_in_each_batch": bayesian_beats_random_in_each_batch,
        "contradictory_control_rejected": contradictory_control_rejected,
    }
    report: dict[str, Any] = {
        "schema_version": 1,
        "protocol_id": config.protocol_id,
        "config_hash": config.config_hash,
        "replicates": replicates,
        "summaries": summaries,
        "batches": batches,
        "negative_control": negative_control,
        "decision": {
            "status": "go" if all(checks.values()) else "redo",
            "scope": "Step 0 mechanics and evaluation design only",
            "checks": checks,
        },
        "interpretation": (
            "Diagnostic only: Step 0 validates mechanics and evaluation design; "
            "it does not establish a benefit from co-evolution."
        ),
    }
    (output_dir / "benchmark.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
