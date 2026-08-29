"""Question niches, Pareto fronts, and the frozen recombination decision boundary."""

from __future__ import annotations

from dataclasses import dataclass

from scientific_parallax.evolution.model import ParadigmIndividual
from scientific_parallax.questions.model import QuestionIndividual
from scientific_parallax.questions.population import QuestionPopulation, RejectedQuestion
from scientific_parallax.worlds.gray_scott import GrayScottWorld


@dataclass(frozen=True, slots=True)
class QuestionNicheSelection:
    selected: tuple[QuestionIndividual, ...]
    niches: dict[str, tuple[str, ...]]
    pareto_front: tuple[str, ...]
    rejected: tuple[RejectedQuestion, ...]


@dataclass(frozen=True, slots=True)
class RecombinationDecision:
    left_parent_id: str
    right_parent_id: str
    allowed: bool
    reason: str


def consider_recombination(
    left_parent_id: str,
    right_parent_id: str,
    allowed_mutations: tuple[str, ...],
) -> RecombinationDecision:
    if not left_parent_id or not right_parent_id or left_parent_id == right_parent_id:
        raise ValueError("recombination requires two distinct named parents")
    allowed = "recombine" in allowed_mutations
    return RecombinationDecision(
        left_parent_id,
        right_parent_id,
        allowed,
        "allowed_by_candidate_generator"
        if allowed
        else "blocked because recombination was not frozen at Gate PF",
    )


class QuestionNichePopulation:
    REQUIRED_NICHES = ("information_efficiency", "raw_disagreement", "minimum_cost")

    def __init__(
        self,
        capacity_per_niche: int,
        minimum_disagreement: float = 1e-12,
        minimum_expected_information_gain: float = 1e-12,
    ) -> None:
        if capacity_per_niche < 1:
            raise ValueError("question niche capacity must be positive")
        self.capacity_per_niche = capacity_per_niche
        self.minimum_disagreement = minimum_disagreement
        self.minimum_expected_information_gain = minimum_expected_information_gain

    def select(
        self,
        candidates: tuple[QuestionIndividual, ...],
        world: GrayScottWorld,
        registered_paradigm_ids: set[str],
    ) -> QuestionNicheSelection:
        base = QuestionPopulation(
            max(1, len(candidates)),
            self.minimum_disagreement,
            self.minimum_expected_information_gain,
        ).select(candidates, world, registered_paradigm_ids)
        accepted = base.selected
        scorers = {
            "information_efficiency": lambda item: (
                -item.diagnostics.resource_score,
                item.genotype.semantic_hash,
            ),
            "raw_disagreement": lambda item: (
                -item.diagnostics.predicted_disagreement,
                item.genotype.semantic_hash,
            ),
            "minimum_cost": lambda item: (
                item.diagnostics.cost.weighted_total,
                -item.diagnostics.expected_information_gain,
                item.genotype.semantic_hash,
            ),
        }
        niches = {
            name: tuple(
                item.genotype.semantic_hash
                for item in sorted(accepted, key=scorer)[: self.capacity_per_niche]
            )
            for name, scorer in scorers.items()
        }
        retained = {identifier for identifiers in niches.values() for identifier in identifiers}
        selected = tuple(
            item
            for item in sorted(accepted, key=lambda value: value.genotype.semantic_hash)
            if item.genotype.semantic_hash in retained
        )
        pareto = tuple(item.genotype.semantic_hash for item in _question_pareto_front(accepted))
        return QuestionNicheSelection(selected, niches, pareto, base.rejected)


def paradigm_pareto_front(
    individuals: tuple[ParadigmIndividual, ...],
) -> tuple[ParadigmIndividual, ...]:
    return tuple(
        item
        for item in sorted(individuals, key=lambda value: value.individual_id)
        if not any(
            _dominates_paradigm(other, item)
            for other in individuals
            if other.individual_id != item.individual_id
        )
    )


def _question_pareto_front(
    individuals: tuple[QuestionIndividual, ...],
) -> tuple[QuestionIndividual, ...]:
    return tuple(
        item
        for item in sorted(individuals, key=lambda value: value.genotype.semantic_hash)
        if not any(
            _dominates_question(other, item)
            for other in individuals
            if other.genotype.semantic_hash != item.genotype.semantic_hash
        )
    )


def _dominates_paradigm(left: ParadigmIndividual, right: ParadigmIndividual) -> bool:
    left_values = (
        left.evidence_score,
        -left.description.total_bits,
        left.validated_structure_gain,
    )
    right_values = (
        right.evidence_score,
        -right.description.total_bits,
        right.validated_structure_gain,
    )
    return all(a >= b for a, b in zip(left_values, right_values, strict=True)) and any(
        a > b for a, b in zip(left_values, right_values, strict=True)
    )


def _dominates_question(left: QuestionIndividual, right: QuestionIndividual) -> bool:
    left_values = (
        left.diagnostics.expected_information_gain,
        left.diagnostics.predicted_disagreement,
        -left.diagnostics.cost.weighted_total,
    )
    right_values = (
        right.diagnostics.expected_information_gain,
        right.diagnostics.predicted_disagreement,
        -right.diagnostics.cost.weighted_total,
    )
    return all(a >= b for a, b in zip(left_values, right_values, strict=True)) and any(
        a > b for a, b in zip(left_values, right_values, strict=True)
    )
