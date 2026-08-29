"""Safety filtering, semantic deduplication, and resource allocation for questions."""

from __future__ import annotations

from dataclasses import dataclass

from scientific_parallax.questions.model import QuestionIndividual
from scientific_parallax.worlds.gray_scott import GrayScottWorld, MeasurementSpec


@dataclass(frozen=True, slots=True)
class RejectedQuestion:
    question_id: str
    semantic_hash: str
    reason: str


@dataclass(frozen=True, slots=True)
class QuestionSelection:
    selected: tuple[QuestionIndividual, ...]
    rejected: tuple[RejectedQuestion, ...]


class QuestionPopulation:
    def __init__(
        self,
        capacity: int,
        minimum_disagreement: float = 1e-12,
        minimum_expected_information_gain: float = 1e-12,
    ) -> None:
        if capacity < 1:
            raise ValueError("question population capacity must be positive")
        self.capacity = capacity
        self.minimum_disagreement = minimum_disagreement
        self.minimum_expected_information_gain = minimum_expected_information_gain

    def select(
        self,
        candidates: tuple[QuestionIndividual, ...],
        world: GrayScottWorld,
        registered_paradigm_ids: set[str],
    ) -> QuestionSelection:
        accepted: list[QuestionIndividual] = []
        rejected: list[RejectedQuestion] = []
        seen: set[str] = set()
        capabilities = world.capabilities()
        for candidate in sorted(candidates, key=lambda item: item.genotype.question_id):
            question = candidate.genotype
            semantic_hash = question.semantic_hash
            try:
                question.validate(world, registered_paradigm_ids)
            except ValueError as error:
                rejected.append(
                    RejectedQuestion(question.question_id, semantic_hash, f"invalid:{error}")
                )
                continue
            if semantic_hash in seen:
                rejected.append(
                    RejectedQuestion(question.question_id, semantic_hash, "semantic_duplicate")
                )
                continue
            seen.add(semantic_hash)
            if (
                question.experiment.intervention is not None
                and not capabilities.supports_intervention
            ):
                rejected.append(
                    RejectedQuestion(
                        question.question_id, semantic_hash, "unsupported_intervention"
                    )
                )
                continue
            if (
                question.experiment.measurement != MeasurementSpec()
                and not capabilities.supports_new_measurement
            ):
                rejected.append(
                    RejectedQuestion(question.question_id, semantic_hash, "unsupported_measurement")
                )
                continue
            if candidate.diagnostics.predicted_disagreement <= self.minimum_disagreement:
                rejected.append(
                    RejectedQuestion(
                        question.question_id, semantic_hash, "no_predictive_difference"
                    )
                )
                continue
            if (
                candidate.diagnostics.expected_information_gain
                <= self.minimum_expected_information_gain
            ):
                rejected.append(
                    RejectedQuestion(
                        question.question_id, semantic_hash, "no_expected_information_gain"
                    )
                )
                continue
            accepted.append(candidate)

        ranked = sorted(
            accepted,
            key=lambda item: (
                -item.diagnostics.resource_score,
                -item.diagnostics.predicted_disagreement,
                item.genotype.semantic_hash,
            ),
        )
        for candidate in ranked[self.capacity :]:
            rejected.append(
                RejectedQuestion(
                    candidate.genotype.question_id,
                    candidate.genotype.semantic_hash,
                    "capacity_limit",
                )
            )
        return QuestionSelection(tuple(ranked[: self.capacity]), tuple(rejected))
