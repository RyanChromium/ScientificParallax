"""Typed executable questions and their separately computed diagnostics."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from scientific_parallax.core.reproducibility import content_hash
from scientific_parallax.worlds.gray_scott import GrayScottExperiment, GrayScottWorld


@dataclass(frozen=True, slots=True)
class QuestionGenotype:
    """An executable experiment proposal with no observation or update authority."""

    question_id: str
    experiment: GrayScottExperiment
    target_paradigm_ids: tuple[str, ...]
    novelty_label: str = ""
    schema_version: int = 1

    def validate(self, world: GrayScottWorld, registered_paradigm_ids: set[str]) -> None:
        if self.schema_version != 1:
            raise ValueError("unsupported question schema")
        if len(self.target_paradigm_ids) < 2:
            raise ValueError("a question must distinguish at least two paradigms")
        if len(set(self.target_paradigm_ids)) != len(self.target_paradigm_ids):
            raise ValueError("target paradigms must be unique")
        if not set(self.target_paradigm_ids).issubset(registered_paradigm_ids):
            raise ValueError("question references an unregistered paradigm")
        world.validate_experiment(self.experiment)

    @property
    def semantic_payload(self) -> dict[str, Any]:
        experiment = asdict(self.experiment)
        experiment.pop("experiment_id")
        return {
            "schema_version": self.schema_version,
            "experiment": experiment,
            "target_paradigm_ids": sorted(self.target_paradigm_ids),
        }

    @property
    def semantic_hash(self) -> str:
        """Identity excludes prose and display IDs, so relabeling cannot create novelty."""
        return content_hash(self.semantic_payload)


@dataclass(frozen=True, slots=True)
class QuestionCostWeights:
    simulation: float = 0.000001
    measurement: float = 0.0001
    intervention: float = 0.25

    def __post_init__(self) -> None:
        values = (self.simulation, self.measurement, self.intervention)
        if (
            not all(math.isfinite(value) for value in values)
            or min(values) < 0.0
            or not any(value > 0.0 for value in values)
        ):
            raise ValueError("question cost weights must be finite, non-negative, and non-zero")


@dataclass(frozen=True, slots=True)
class QuestionCost:
    simulation_work: float
    measured_values: int
    interventions: int
    weighted_total: float

    @classmethod
    def estimate(
        cls,
        question: QuestionGenotype,
        world: GrayScottWorld,
        weights: QuestionCostWeights,
    ) -> QuestionCost:
        experiment = question.experiment
        measurement = experiment.measurement
        frames_after_initial = experiment.steps // measurement.sample_every
        if experiment.steps % measurement.sample_every:
            frames_after_initial += 1
        frames = 1 + frames_after_initial
        spatial_side = (experiment.grid_size + measurement.downsample - 1) // measurement.downsample
        measured_values = frames * len(measurement.visible_channels) * spatial_side**2
        interventions = int(experiment.intervention is not None)
        simulation_work = world.estimate_cost(experiment)
        total = (
            weights.simulation * simulation_work
            + weights.measurement * measured_values
            + weights.intervention * interventions
        )
        return cls(simulation_work, measured_values, interventions, total)


@dataclass(frozen=True, slots=True)
class AnticipatedOutcome:
    paradigm_id: str
    summary: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class QuestionDiagnostics:
    anticipated_outcomes: tuple[AnticipatedOutcome, ...]
    predicted_disagreement: float
    expected_information_gain: float
    cost: QuestionCost

    @property
    def resource_score(self) -> float:
        if self.cost.weighted_total <= 0.0:
            return 0.0
        return self.expected_information_gain / self.cost.weighted_total


@dataclass(frozen=True, slots=True)
class QuestionMutation:
    operator: str
    parent_semantic_hash: str
    child_semantic_hash: str
    attempted_index: int
    details: dict[str, Any]


@dataclass(frozen=True, slots=True)
class QuestionIndividual:
    genotype: QuestionGenotype
    diagnostics: QuestionDiagnostics
    generation: int
    parent_semantic_hash: str | None = None
    mutation: QuestionMutation | None = None
