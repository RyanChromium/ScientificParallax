"""Evaluator-only scoring and validation for blinded challenge runs."""

from __future__ import annotations

import math
from dataclasses import dataclass

from scientific_parallax.protocol.statistics import stable_identification_query


@dataclass(frozen=True, slots=True)
class EndpointScore:
    ranks: tuple[int, ...]
    stable_identification_query: int | None
    final_true_posterior: float


def score_truth_rank(
    posterior: dict[str, float],
    aliases: dict[str, str],
    true_candidate_id: str,
) -> int:
    """Rank truth with a precomputed anonymous tie break, outside the strategy."""

    if set(posterior) != set(aliases) or true_candidate_id not in posterior:
        raise ValueError("independent scorer received inconsistent candidates")
    ordered = sorted(posterior, key=lambda item: (-posterior[item], aliases[item]))
    return ordered.index(true_candidate_id) + 1


def score_endpoint(
    ranks: list[int],
    posterior: dict[str, float],
    true_candidate_id: str,
    *,
    top_k: int,
    persistence: int,
) -> EndpointScore:
    if not ranks or not math.isclose(sum(posterior.values()), 1.0, abs_tol=1e-10):
        raise ValueError("independent endpoint scoring requires a normalized completed run")
    return EndpointScore(
        tuple(ranks),
        stable_identification_query(ranks, top_k=top_k, persistence=persistence),
        posterior[true_candidate_id],
    )


def validate_discriminating_questions(rounds: list[dict[str, object]]) -> dict[str, object]:
    gains = [float(item["actual_information_gain"]) for item in rounds]
    disagreements = [float(item["predicted_disagreement"]) for item in rounds]
    positive = sum(gain > 1e-12 for gain in gains)
    return {
        "executed_questions": len(rounds),
        "positive_actual_information_gain": positive,
        "positive_predicted_disagreement": sum(value > 1e-12 for value in disagreements),
        "mean_actual_information_gain": sum(gains) / len(gains),
        "questions_distinguish_paradigms": positive > 0
        and any(value > 1e-12 for value in disagreements),
    }
