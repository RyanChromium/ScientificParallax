"""Question-selection strategies with no access to realized outcomes."""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from statistics import NormalDist
from typing import Protocol

from scientific_parallax.step0.domain import Question
from scientific_parallax.step0.evidence import entropy


class PredictiveParadigm(Protocol):
    paradigm_id: str

    def predict_mean(self, question: Question) -> float: ...


def _means(
    question: Question,
    paradigms: Sequence[PredictiveParadigm],
) -> dict[str, float]:
    return {paradigm.paradigm_id: paradigm.predict_mean(question) for paradigm in paradigms}


def select_random(
    questions: Sequence[Question],
    _paradigms: Sequence[PredictiveParadigm],
    _posterior: Mapping[str, float],
    rng: random.Random,
    _quadrature_points: int,
) -> Question:
    return rng.choice(questions)


def select_max_disagreement(
    questions: Sequence[Question],
    paradigms: Sequence[PredictiveParadigm],
    posterior: Mapping[str, float],
    _rng: random.Random,
    _quadrature_points: int,
) -> Question:
    def score(question: Question) -> tuple[float, str]:
        means = _means(question, paradigms)
        center = sum(posterior[key] * value for key, value in means.items())
        variance = sum(posterior[key] * (value - center) ** 2 for key, value in means.items())
        return variance, question.question_id

    return max(questions, key=score)


def expected_information_gain(
    question: Question,
    paradigms: Sequence[PredictiveParadigm],
    posterior: Mapping[str, float],
    quadrature_points: int = 41,
) -> float:
    """Numerically integrate expected posterior entropy under a Normal mixture."""
    if quadrature_points < 9 or quadrature_points % 2 == 0:
        raise ValueError("quadrature_points must be an odd integer of at least 9")
    means = _means(question, paradigms)
    sigma = question.noise_std
    low = min(means.values()) - 5.0 * sigma
    high = max(means.values()) + 5.0 * sigma
    step = (high - low) / (quadrature_points - 1)
    expected_entropy = 0.0
    normal = NormalDist(0.0, sigma)
    for index in range(quadrature_points):
        y = low + index * step
        likelihoods = {key: normal.pdf(y - mean) for key, mean in means.items()}
        mixture_density = sum(posterior[key] * likelihoods[key] for key in means)
        if mixture_density == 0.0:
            continue
        updated = {key: posterior[key] * likelihoods[key] / mixture_density for key in means}
        trapezoid_weight = 0.5 if index in (0, quadrature_points - 1) else 1.0
        expected_entropy += trapezoid_weight * mixture_density * entropy(updated) * step
    return entropy(posterior) - expected_entropy


def select_bayesian_design(
    questions: Sequence[Question],
    paradigms: Sequence[PredictiveParadigm],
    posterior: Mapping[str, float],
    _rng: random.Random,
    quadrature_points: int,
) -> Question:
    def score(question: Question) -> tuple[float, str]:
        information_per_cost = (
            expected_information_gain(question, paradigms, posterior, quadrature_points)
            / question.cost
        )
        return information_per_cost, question.question_id

    return max(questions, key=score)


SELECTORS = {
    "random": select_random,
    "max_disagreement": select_max_disagreement,
    "bayesian_design": select_bayesian_design,
}
