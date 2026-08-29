"""Reconstructable dynamic-candidate evidence updates owned outside both populations."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from scientific_parallax.questions.scoring import summary_noise
from scientific_parallax.step0.ledger import verify_ledger


@dataclass(frozen=True, slots=True)
class EvidenceHistoryItem:
    question_hash: str
    observation: tuple[float, ...]
    predictions: dict[str, tuple[float, ...]]


@dataclass(frozen=True, slots=True)
class RebuiltEvidence:
    posterior: dict[str, float]
    observations: int
    state_rebuilds: int


def calibrated_noise(dimension: int, floor: float) -> NDArray[np.float64]:
    if not math.isfinite(floor) or floor <= 0.0:
        raise ValueError("evidence noise floor must be finite and positive")
    return np.maximum(summary_noise(dimension), floor)


def posterior_from_history(
    candidate_ids: tuple[str, ...],
    history: tuple[EvidenceHistoryItem, ...],
    noise_floor: float,
) -> dict[str, float]:
    if len(candidate_ids) < 2 or len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("dynamic evidence requires at least two unique candidates")
    log_weights = {item: -math.log(len(candidate_ids)) for item in candidate_ids}
    for record in history:
        if set(record.predictions) != set(candidate_ids):
            raise ValueError("historical prediction set differs from candidate registration")
        observation = np.asarray(record.observation, dtype=float)
        noise = calibrated_noise(len(observation), noise_floor)
        if not np.all(np.isfinite(observation)):
            raise ValueError("historical observation must be finite")
        for candidate_id in candidate_ids:
            prediction = np.asarray(record.predictions[candidate_id], dtype=float)
            if prediction.shape != observation.shape or not np.all(np.isfinite(prediction)):
                raise ValueError("historical prediction is malformed")
            residual = (observation - prediction) / noise
            log_weights[candidate_id] += -0.5 * float(residual @ residual)
    return _normalize_log_weights(log_weights)


def update_posterior(
    prior: dict[str, float],
    predictions: dict[str, tuple[float, ...]],
    observation: tuple[float, ...],
    noise_floor: float,
) -> dict[str, float]:
    if set(prior) != set(predictions) or len(prior) < 2:
        raise ValueError("evidence update requires matching registered candidates")
    observed = np.asarray(observation, dtype=float)
    if not np.all(np.isfinite(observed)):
        raise ValueError("evidence observation must be finite")
    noise = calibrated_noise(len(observed), noise_floor)
    log_weights: dict[str, float] = {}
    for candidate_id, raw_prediction in predictions.items():
        prediction = np.asarray(raw_prediction, dtype=float)
        if prediction.shape != observed.shape or not np.all(np.isfinite(prediction)):
            raise ValueError("evidence prediction is malformed")
        residual = (observed - prediction) / noise
        log_weights[candidate_id] = math.log(max(prior[candidate_id], 1e-300)) - 0.5 * float(
            residual @ residual
        )
    return _normalize_log_weights(log_weights)


def rebuild_coevolution_evidence(path: Path, noise_floor: float) -> RebuiltEvidence:
    verify_ledger(path)
    pending: dict[str, object] | None = None
    posterior: dict[str, float] = {}
    observations = 0
    state_rebuilds = 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            event_type = event["event_type"]
            payload = event["payload"]
            if event_type == "evidence_state_rebuilt":
                candidate_ids = tuple(payload["candidate_ids"])
                history = tuple(
                    EvidenceHistoryItem(
                        item["question_hash"],
                        tuple(item["observation"]),
                        {key: tuple(values) for key, values in item["predictions"].items()},
                    )
                    for item in payload["history"]
                )
                calculated = posterior_from_history(candidate_ids, history, noise_floor)
                _assert_posterior_close(calculated, payload["posterior"])
                posterior = calculated
                state_rebuilds += 1
            elif event_type == "prediction_preregistered":
                pending = payload
            elif event_type == "observation_received":
                if pending is None:
                    raise ValueError("observation has no visible preregistration")
                posterior = update_posterior(
                    {key: float(value) for key, value in pending["prior"].items()},
                    {key: tuple(values) for key, values in pending["predictions"].items()},
                    tuple(payload["observation"]),
                    noise_floor,
                )
                _assert_posterior_close(posterior, payload["posterior"])
                pending = None
                observations += 1
    if pending is not None:
        raise ValueError("evidence rebuild ended with a pending prediction")
    return RebuiltEvidence(posterior, observations, state_rebuilds)


def _normalize_log_weights(log_weights: dict[str, float]) -> dict[str, float]:
    maximum = max(log_weights.values())
    total = sum(math.exp(value - maximum) for value in log_weights.values())
    return {key: math.exp(value - maximum) / total for key, value in log_weights.items()}


def _assert_posterior_close(calculated: dict[str, float], recorded: dict[str, float]) -> None:
    if set(calculated) != set(recorded) or any(
        not math.isclose(calculated[key], recorded[key], rel_tol=1e-12, abs_tol=1e-12)
        for key in calculated
    ):
        raise ValueError("recorded posterior cannot be reconstructed from evidence")
