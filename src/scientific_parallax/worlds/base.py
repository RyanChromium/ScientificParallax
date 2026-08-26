"""Capabilities shared by online and offline scientific worlds."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol, TypeVar

ExperimentT = TypeVar("ExperimentT")
ObservationT = TypeVar("ObservationT")


@dataclass(frozen=True, slots=True)
class WorldCapabilities:
    supports_novel_conditions: bool
    supports_intervention: bool
    supports_new_measurement: bool
    is_simulated: bool
    has_sealed_ground_truth: bool

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


class World(Protocol[ExperimentT, ObservationT]):
    def capabilities(self) -> WorldCapabilities: ...

    def validate_experiment(self, experiment: ExperimentT) -> None: ...

    def estimate_cost(self, experiment: ExperimentT) -> float: ...

    def observe(self, experiment: ExperimentT) -> ObservationT: ...

    def describe(self) -> dict[str, Any]: ...
