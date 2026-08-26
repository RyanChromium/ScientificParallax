"""Capability-honest adapter for immutable offline trajectories."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from scientific_parallax.worlds.base import WorldCapabilities


class OfflineTrajectoryWorld[ExperimentT, ObservationT]:
    def __init__(self, records: Mapping[str, ObservationT], dataset_id: str) -> None:
        if not records:
            raise ValueError("offline world requires at least one trajectory")
        self._records = dict(records)
        self.dataset_id = dataset_id

    def capabilities(self) -> WorldCapabilities:
        return WorldCapabilities(False, False, False, False, False)

    @staticmethod
    def _key(experiment: ExperimentT) -> str:
        key = getattr(experiment, "experiment_id", None)
        if not isinstance(key, str):
            raise TypeError("offline experiments must expose a string experiment_id")
        return key

    def validate_experiment(self, experiment: ExperimentT) -> None:
        if self._key(experiment) not in self._records:
            raise ValueError("offline dataset does not contain the requested condition")

    def estimate_cost(self, experiment: ExperimentT) -> float:
        self.validate_experiment(experiment)
        return 0.0

    def observe(self, experiment: ExperimentT) -> ObservationT:
        self.validate_experiment(experiment)
        return self._records[self._key(experiment)]

    def intervene(self, _experiment: ExperimentT) -> ObservationT:
        raise RuntimeError("offline datasets cannot execute new interventions")

    def describe(self) -> dict[str, Any]:
        return {
            "world": "offline_trajectory_dataset",
            "dataset_id": self.dataset_id,
            "records": len(self._records),
            "capabilities": self.capabilities().to_dict(),
        }
