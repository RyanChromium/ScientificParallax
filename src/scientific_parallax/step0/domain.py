"""Typed domain objects for the Step 0 protocol."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

Instrument = Literal["primary", "reference"]
Solver = Literal["primary", "reference"]


@dataclass(frozen=True, slots=True)
class Question:
    """A fully specified, finite-pool experiment."""

    question_id: str
    x: float
    instrument: Instrument
    solver: Solver
    noise_std: float
    cost: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Observation:
    """An immutable observation returned by the world."""

    question_id: str
    value: float
    noise_std: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Prediction:
    """A candidate's predictive Normal distribution for one question."""

    paradigm_id: str
    mean: float
    noise_std: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
