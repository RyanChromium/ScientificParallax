"""Minimal frozen-niche maintenance and failed-lineage preservation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from scientific_parallax.evolution.lineage import LineageLedger
from scientific_parallax.evolution.model import LineageStatus, ParadigmIndividual
from scientific_parallax.protocol.evidence_layers import (
    CandidateEvidenceState,
    SurvivalPolicy,
    SurvivalStatus,
)
from scientific_parallax.protocol.paradigm_ir import equivalent_under_declared_transforms


@dataclass(frozen=True, slots=True)
class PopulationSnapshot:
    active_ids: tuple[str, ...]
    dormant_ids: tuple[str, ...]
    fossil_ids: tuple[str, ...]
    niches: dict[str, tuple[str, ...]]
    equivalent_to: dict[str, str]


class ParadigmPopulation:
    """Keep three Protocol Freeze niches after hard survival and equivalence gates."""

    REQUIRED_NICHES = (
        "current_predictive_best",
        "minimum_description",
        "validated_structure_gain",
    )

    def __init__(
        self,
        *,
        niche_capacities: dict[str, int],
        survival_policy: SurvivalPolicy,
        minimum_evidence_score: float,
        minimum_predictive_gain: float,
        maximum_decoder_cost: float,
    ) -> None:
        if set(niche_capacities) != set(self.REQUIRED_NICHES):
            raise ValueError("Step 4 requires the three frozen Protocol Freeze niches")
        if any(value < 1 for value in niche_capacities.values()):
            raise ValueError("niche capacities must be positive")
        self.niche_capacities = dict(niche_capacities)
        self.survival_policy = survival_policy
        self.minimum_evidence_score = minimum_evidence_score
        self.minimum_predictive_gain = minimum_predictive_gain
        self.maximum_decoder_cost = maximum_decoder_cost
        self.fossils: dict[str, ParadigmIndividual] = {}
        self.failure_reasons: dict[str, str] = {}

    def select(
        self,
        individuals: tuple[ParadigmIndividual, ...],
        ledger: LineageLedger,
    ) -> PopulationSnapshot:
        representatives: list[ParadigmIndividual] = []
        equivalent_to: dict[str, str] = {}
        ordered = sorted(
            individuals,
            key=lambda item: (
                -item.evidence_score,
                item.description.total_bits,
                item.individual_id,
            ),
        )
        for individual in ordered:
            duplicate = next(
                (
                    representative
                    for representative in representatives
                    if equivalent_under_declared_transforms(
                        representative.genotype.ir,
                        individual.genotype.ir,
                        representative.phenotype.behavior_signature,
                        individual.phenotype.behavior_signature,
                    )
                ),
                None,
            )
            if duplicate is not None:
                archived = replace(individual, status=LineageStatus.EQUIVALENT_DUPLICATE)
                self._fossilize(
                    archived,
                    f"equivalent to retained lineage {duplicate.individual_id}",
                    ledger,
                )
                equivalent_to[individual.individual_id] = duplicate.individual_id
            else:
                representatives.append(individual)

        viable: list[ParadigmIndividual] = []
        dormant: list[ParadigmIndividual] = []
        for individual in representatives:
            survival = self.survival_policy.classify(
                CandidateEvidenceState(
                    individual.individual_id,
                    individual.checkpoints_below_viability,
                    individual.hard_contradictions,
                )
            )
            if survival == SurvivalStatus.DEAD:
                dead = replace(individual, status=LineageStatus.DEAD)
                self._fossilize(dead, "frozen survival rule marked lineage dead", ledger)
                continue
            passes_viability = (
                individual.evidence_score >= self.minimum_evidence_score
                and individual.predictive_gain >= self.minimum_predictive_gain
                and individual.genotype.ir.measurement.decoder_cost <= self.maximum_decoder_cost
            )
            if survival == SurvivalStatus.DORMANT or not passes_viability:
                sleeping = replace(individual, status=LineageStatus.DORMANT)
                dormant.append(sleeping)
                ledger.set_status(
                    sleeping.individual_id,
                    LineageStatus.DORMANT,
                    reason="below viability gate or dormancy checkpoint",
                )
                continue
            viable.append(replace(individual, status=LineageStatus.ACTIVE))

        scoring = {
            "current_predictive_best": lambda item: (
                -item.evidence_score,
                item.description.total_bits,
                item.individual_id,
            ),
            "minimum_description": lambda item: (
                item.description.total_bits,
                -item.evidence_score,
                item.individual_id,
            ),
            "validated_structure_gain": lambda item: (
                -item.validated_structure_gain,
                -item.evidence_score,
                item.individual_id,
            ),
        }
        niches = {
            name: tuple(
                item.individual_id
                for item in sorted(viable, key=key)[: self.niche_capacities[name]]
            )
            for name, key in scoring.items()
        }
        active_ids = tuple(sorted({identifier for ids in niches.values() for identifier in ids}))
        for individual in viable:
            if individual.individual_id not in active_ids:
                sleeping = replace(individual, status=LineageStatus.DORMANT)
                dormant.append(sleeping)
                ledger.set_status(
                    sleeping.individual_id,
                    LineageStatus.DORMANT,
                    reason="viable lineage was outside all frozen niche capacities",
                )
        return PopulationSnapshot(
            active_ids,
            tuple(sorted(item.individual_id for item in dormant)),
            tuple(sorted(self.fossils)),
            niches,
            equivalent_to,
        )

    def _fossilize(
        self,
        individual: ParadigmIndividual,
        reason: str,
        ledger: LineageLedger,
    ) -> None:
        self.fossils[individual.individual_id] = individual
        self.failure_reasons[individual.individual_id] = reason
        ledger.set_status(individual.individual_id, individual.status, reason=reason)
