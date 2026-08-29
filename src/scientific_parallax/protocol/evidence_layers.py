"""Mechanical separation of training, development, and one-shot final evidence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from numpy.typing import ArrayLike

from scientific_parallax.core.reproducibility import content_hash


class EvidenceTier(StrEnum):
    TRAINING = "training"
    DEVELOPMENT = "development"
    FINAL_SEALED = "final_sealed"


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    tier: EvidenceTier
    question_hash: str
    observation_hash: str


class EvidenceStore:
    def __init__(self) -> None:
        self._training: list[EvidenceRecord] = []
        self._development: list[EvidenceRecord] = []

    def append(self, record: EvidenceRecord) -> None:
        if record.tier == EvidenceTier.FINAL_SEALED:
            raise ValueError("final evidence can only be handled by the sealed evaluator")
        target = self._training if record.tier == EvidenceTier.TRAINING else self._development
        target.append(record)

    def records(self, tier: EvidenceTier) -> tuple[EvidenceRecord, ...]:
        if tier == EvidenceTier.FINAL_SEALED:
            raise PermissionError("final sealed evidence is not repeatedly accessible")
        source = self._training if tier == EvidenceTier.TRAINING else self._development
        return tuple(source)


@dataclass(frozen=True, slots=True)
class ProtocolSpec:
    schema_version: int
    protocol_id: str
    paradigm_ir_version: str
    candidate_generator_hash: str
    measurement_cluster_hash: str
    task_design_hash: str
    external_data_manifest_hash: str
    external_fixture_manifest_hash: str
    execution_environment_hash: str
    equivalence_rule: str
    evidence_update_rule: str
    noise_calibration_rule: str
    noise_calibration_parameters: dict[str, float | str]
    survival_rule: str
    survival_parameters: dict[str, bool | int]
    viability_thresholds: dict[str, float]
    niche_capacities: dict[str, int]
    primary_endpoint: str
    endpoint_parameters: dict[str, float | int]
    statistical_method: str
    statistical_parameters: dict[str, Any]
    minimum_relative_effect: float
    numerical_methods: dict[str, str]
    numerical_tolerances: dict[str, float]
    power_design: dict[str, Any]
    budgets: dict[str, float | int]
    budget_scope: dict[str, str]
    evaluation_accounting: dict[str, str]
    baselines: tuple[str, ...]
    ablations: tuple[str, ...]
    stop_rule: str

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported protocol schema")
        hashes = (
            self.candidate_generator_hash,
            self.measurement_cluster_hash,
            self.task_design_hash,
            self.external_data_manifest_hash,
            self.external_fixture_manifest_hash,
            self.execution_environment_hash,
        )
        if any(
            len(value) != 64 or any(char not in "0123456789abcdef" for char in value)
            for value in hashes
        ):
            raise ValueError("protocol component hashes must be lowercase SHA-256 digests")
        if not 0.0 < self.minimum_relative_effect < 1.0:
            raise ValueError("minimum relative effect must lie strictly between zero and one")
        if any(value <= 0 for value in self.budgets.values()):
            raise ValueError("all protocol budgets must be positive")
        if any(value < 1 for value in self.niche_capacities.values()):
            raise ValueError("all niche capacities must be positive")
        if (
            self.endpoint_parameters.get("top_k", 0) < 1
            or self.endpoint_parameters.get("persistence_checkpoints", 0) < 1
        ):
            raise ValueError("endpoint parameters must be positive")

    @property
    def protocol_hash(self) -> str:
        return content_hash(asdict(self))


class SurvivalStatus(StrEnum):
    ACTIVE = "active"
    DORMANT = "dormant"
    DEAD = "dead"


@dataclass(frozen=True, slots=True)
class CandidateEvidenceState:
    candidate_id: str
    checkpoints_below_viability: int
    hard_contradictions: int = 0


@dataclass(frozen=True, slots=True)
class SurvivalPolicy:
    dormancy_after: int
    death_after: int
    death_on_hard_contradiction: bool = True

    def __post_init__(self) -> None:
        if self.dormancy_after < 1 or self.death_after <= self.dormancy_after:
            raise ValueError("death must occur strictly after a positive dormancy threshold")

    def classify(self, state: CandidateEvidenceState) -> SurvivalStatus:
        if self.death_on_hard_contradiction and state.hard_contradictions:
            return SurvivalStatus.DEAD
        if state.checkpoints_below_viability >= self.death_after:
            return SurvivalStatus.DEAD
        if state.checkpoints_below_viability >= self.dormancy_after:
            return SurvivalStatus.DORMANT
        return SurvivalStatus.ACTIVE


def calibrate_noise(residuals: ArrayLike, floor: float) -> float:
    values = np.asarray(residuals, dtype=float)
    if values.size < 2 or floor <= 0.0 or not np.all(np.isfinite(values)):
        raise ValueError("noise calibration needs finite residuals and a positive floor")
    return max(float(np.std(values, ddof=1)), floor)


class ProtocolGate:
    """A small state machine preventing final evidence access before freeze."""

    def __init__(self, final_evaluator: Callable[[str], dict[str, Any]]) -> None:
        self._final_evaluator = final_evaluator
        self._spec: ProtocolSpec | None = None
        self._frozen_strategy_hash: str | None = None
        self._opened = False

    @property
    def is_frozen(self) -> bool:
        return self._spec is not None

    def freeze(self, spec: ProtocolSpec, strategy_hash: str) -> str:
        if self.is_frozen:
            raise RuntimeError("protocol is already frozen")
        if not strategy_hash:
            raise ValueError("strategy hash is required at protocol freeze")
        self._spec = spec
        self._frozen_strategy_hash = strategy_hash
        return spec.protocol_hash

    def final_evaluate_once(self, strategy_hash: str) -> dict[str, Any]:
        if not self.is_frozen:
            raise PermissionError("final world cannot be opened before Protocol Freeze")
        if self._opened:
            raise RuntimeError("final world has already been opened")
        if strategy_hash != self._frozen_strategy_hash:
            raise PermissionError("strategy differs from the version frozen in the protocol")
        self._opened = True
        return self._final_evaluator(strategy_hash)
