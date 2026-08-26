"""Independent Bayesian evidence updates for fixed candidate predictions."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from scientific_parallax.step0.domain import Observation, Prediction


def _logsumexp(values: Sequence[float]) -> float:
    maximum = max(values)
    return maximum + math.log(sum(math.exp(value - maximum) for value in values))


class EvidenceEngine:
    """Owns posterior state; paradigms and questions cannot modify its rules."""

    def __init__(self, paradigm_ids: Sequence[str]) -> None:
        if not paradigm_ids or len(set(paradigm_ids)) != len(paradigm_ids):
            raise ValueError("paradigm IDs must be non-empty and unique")
        prior = -math.log(len(paradigm_ids))
        self._log_weights = {paradigm_id: prior for paradigm_id in paradigm_ids}

    @property
    def posterior(self) -> dict[str, float]:
        normalizer = _logsumexp(tuple(self._log_weights.values()))
        return {
            paradigm_id: math.exp(weight - normalizer)
            for paradigm_id, weight in self._log_weights.items()
        }

    def update(
        self,
        predictions: Mapping[str, Prediction],
        observation: Observation,
    ) -> dict[str, float]:
        if set(predictions) != set(self._log_weights):
            raise ValueError("predictions must exactly match the registered candidate pool")
        for paradigm_id, prediction in predictions.items():
            if prediction.paradigm_id != paradigm_id:
                raise ValueError("prediction key and paradigm ID disagree")
            if not math.isclose(prediction.noise_std, observation.noise_std):
                raise ValueError("prediction and observation noise models disagree")
            residual = (observation.value - prediction.mean) / prediction.noise_std
            log_likelihood = -math.log(prediction.noise_std) - 0.5 * residual * residual
            self._log_weights[paradigm_id] += log_likelihood
        return self.posterior


def entropy(probabilities: Mapping[str, float]) -> float:
    return -sum(p * math.log(p) for p in probabilities.values() if p > 0.0)
