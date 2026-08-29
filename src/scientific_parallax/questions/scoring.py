"""Prediction diagnostics and an independent evidence update engine."""

from __future__ import annotations

import hashlib
import math
from dataclasses import replace

import numpy as np
from numpy.typing import NDArray

from scientific_parallax.baselines.gray_scott import FixedParadigmCandidate
from scientific_parallax.questions.model import (
    AnticipatedOutcome,
    QuestionCost,
    QuestionCostWeights,
    QuestionDiagnostics,
    QuestionGenotype,
)
from scientific_parallax.worlds.gray_scott import GrayScottWorld

_CHANNEL_SUMMARY_NOISE = np.asarray([0.035, 0.035, 0.08, 0.008], dtype=float)


def summary_noise(dimension: int) -> NDArray[np.float64]:
    if dimension < 1 or dimension % len(_CHANNEL_SUMMARY_NOISE):
        raise ValueError("unexpected observation summary dimension")
    return np.tile(_CHANNEL_SUMMARY_NOISE, dimension // len(_CHANNEL_SUMMARY_NOISE))


def predict_question(
    question: QuestionGenotype,
    paradigms: tuple[FixedParadigmCandidate, ...],
) -> dict[str, NDArray[np.float64]]:
    noiseless = replace(
        question.experiment,
        measurement=replace(question.experiment.measurement, noise_std=0.0),
    )
    return {
        paradigm.candidate_id: GrayScottWorld(0, paradigm.law).observe(noiseless).summary()
        for paradigm in paradigms
        if paradigm.candidate_id in question.target_paradigm_ids
    }


def entropy(posterior: dict[str, float]) -> float:
    return -sum(value * math.log(value) for value in posterior.values() if value > 0.0)


def posterior_for_outcome(
    posterior: dict[str, float],
    predictions: dict[str, NDArray[np.float64]],
    outcome: NDArray[np.float64],
) -> dict[str, float]:
    noise = summary_noise(len(outcome))
    log_values: dict[str, float] = {}
    for paradigm_id, prediction in predictions.items():
        residual = (outcome - prediction) / noise
        log_values[paradigm_id] = math.log(max(posterior[paradigm_id], 1e-300)) - 0.5 * float(
            residual @ residual
        )
    maximum = max(log_values.values())
    total = sum(math.exp(value - maximum) for value in log_values.values())
    return {key: math.exp(value - maximum) / total for key, value in log_values.items()}


def expected_information_gain(
    posterior: dict[str, float],
    predictions: dict[str, NDArray[np.float64]],
    *,
    samples: int,
    seed: int,
) -> float:
    if samples < 8:
        raise ValueError("expected-information-gain sampling requires at least 8 draws")
    ids = sorted(predictions)
    probabilities = np.asarray([posterior[item] for item in ids], dtype=float)
    target_mass = float(probabilities.sum())
    probabilities /= target_mass
    noise = summary_noise(len(next(iter(predictions.values()))))
    rng = np.random.default_rng(seed)
    expected_entropy = 0.0
    restricted_prior = {item: posterior[item] / target_mass for item in ids}
    for _ in range(samples):
        source = ids[int(rng.choice(len(ids), p=probabilities))]
        outcome = predictions[source] + rng.normal(0.0, noise)
        expected_entropy += entropy(posterior_for_outcome(restricted_prior, predictions, outcome))
    prior_entropy = entropy(restricted_prior)
    return min(prior_entropy, max(0.0, prior_entropy - expected_entropy / samples))


def predicted_disagreement(
    posterior: dict[str, float],
    predictions: dict[str, NDArray[np.float64]],
) -> float:
    ids = sorted(predictions)
    probabilities = np.asarray([posterior[item] for item in ids], dtype=float)
    probabilities /= probabilities.sum()
    values = np.stack([predictions[item] for item in ids])
    noise = summary_noise(values.shape[1])
    scaled = values / noise
    center = np.average(scaled, axis=0, weights=probabilities)
    return float(np.sum(probabilities[:, None] * (scaled - center) ** 2))


def diagnose_question(
    question: QuestionGenotype,
    paradigms: tuple[FixedParadigmCandidate, ...],
    posterior: dict[str, float],
    world: GrayScottWorld,
    weights: QuestionCostWeights,
    *,
    eig_samples: int,
    seed: int,
) -> QuestionDiagnostics:
    predictions = predict_question(question, paradigms)
    if set(predictions) != set(question.target_paradigm_ids):
        raise ValueError("not all question targets have a prediction model")
    eig_seed = int.from_bytes(
        hashlib.sha256(f"{seed}:{question.semantic_hash}".encode()).digest()[:8], "big"
    )
    outcomes = tuple(
        AnticipatedOutcome(item, tuple(float(value) for value in predictions[item]))
        for item in sorted(predictions)
    )
    return QuestionDiagnostics(
        outcomes,
        predicted_disagreement(posterior, predictions),
        expected_information_gain(posterior, predictions, samples=eig_samples, seed=eig_seed),
        QuestionCost.estimate(question, world, weights),
    )


class IndependentEvidenceEngine:
    """Owns posterior updates; it never accepts a question object as an argument."""

    def __init__(self, paradigm_ids: tuple[str, ...]) -> None:
        if len(paradigm_ids) < 2 or len(set(paradigm_ids)) != len(paradigm_ids):
            raise ValueError("evidence engine requires unique competing paradigms")
        self._log_weights = {item: -math.log(len(paradigm_ids)) for item in paradigm_ids}

    @property
    def posterior(self) -> dict[str, float]:
        maximum = max(self._log_weights.values())
        total = sum(math.exp(value - maximum) for value in self._log_weights.values())
        return {key: math.exp(value - maximum) / total for key, value in self._log_weights.items()}

    def update(
        self,
        predictions: dict[str, NDArray[np.float64]],
        observation: NDArray[np.float64],
    ) -> dict[str, float]:
        if set(predictions) != set(self._log_weights):
            raise ValueError("prediction set differs from the registered evidence state")
        if not np.all(np.isfinite(observation)):
            raise ValueError("evidence observation must be finite")
        if any(
            prediction.shape != observation.shape or not np.all(np.isfinite(prediction))
            for prediction in predictions.values()
        ):
            raise ValueError("evidence predictions must be finite and match the observation shape")
        noise = summary_noise(len(observation))
        for paradigm_id, prediction in predictions.items():
            residual = (observation - prediction) / noise
            self._log_weights[paradigm_id] += -0.5 * float(residual @ residual)
        return self.posterior
