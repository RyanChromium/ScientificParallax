"""Step 4 paradigm genotype, phenotype, cost, and distance models."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

import numpy as np

from scientific_parallax.core.reproducibility import canonical_json, content_hash
from scientific_parallax.protocol.paradigm_ir import (
    LawTerm,
    MeasurementModel,
    ParadigmIR,
    Scope,
    StateVariable,
)


@dataclass(frozen=True, slots=True)
class CoefficientValue:
    target: str
    symbol: str
    value: float

    def __post_init__(self) -> None:
        if not self.target or not self.symbol or not math.isfinite(self.value):
            raise ValueError("coefficient values require finite named entries")


@dataclass(frozen=True, slots=True)
class ParadigmGenotype:
    genotype_id: str
    ir: ParadigmIR
    coefficients: tuple[CoefficientValue, ...]
    schema_version: int = 1

    def validate(self) -> None:
        if self.schema_version != 1 or not self.genotype_id:
            raise ValueError("unsupported or unnamed paradigm genotype")
        self.ir.validate()
        keys = [(item.target, item.symbol) for item in self.coefficients]
        if len(keys) != len(set(keys)):
            raise ValueError("genotype coefficient keys must be unique")
        for term in self.ir.terms:
            self.coefficient_for(term)

    def coefficient_for(self, term: LawTerm) -> float:
        values = {(item.target, item.symbol): item.value for item in self.coefficients}
        exact = values.get((term.target, term.coefficient_symbol))
        if exact is not None:
            return exact
        factor = 1.0
        base_symbol = term.coefficient_symbol
        if base_symbol.endswith("__low"):
            factor = 0.5
            base_symbol = base_symbol.removesuffix("__low")
        elif base_symbol.endswith("__high"):
            factor = 1.5
            base_symbol = base_symbol.removesuffix("__high")
        base = values.get((term.target, base_symbol))
        if base is None:
            raise ValueError(f"missing coefficient for {term.target}:{term.coefficient_symbol}")
        return factor * base

    @property
    def genotype_hash(self) -> str:
        self.validate()
        return content_hash(genotype_to_dict(self))


@dataclass(frozen=True, slots=True)
class ParadigmPhenotype:
    behavior_signature: tuple[float, ...]
    probe_set_hash: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1 or len(self.probe_set_hash) != 64:
            raise ValueError("invalid paradigm phenotype identity")
        if not self.behavior_signature or not all(
            math.isfinite(value) for value in self.behavior_signature
        ):
            raise ValueError("phenotype behavior signature must be finite and non-empty")

    @property
    def phenotype_hash(self) -> str:
        return content_hash(asdict(self))


@dataclass(frozen=True, slots=True)
class PatchCostWeights:
    new_entity: float = 8.0
    new_parameter: float = 4.0
    special_condition: float = 6.0
    scope_contraction: float = 10.0
    preregistration_violation: float = 100.0

    def __post_init__(self) -> None:
        if any(value < 0.0 or not math.isfinite(value) for value in asdict(self).values()):
            raise ValueError("patch-cost weights must be finite and non-negative")


@dataclass(frozen=True, slots=True)
class PatchCost:
    new_entities: int = 0
    new_parameters: int = 0
    special_conditions: int = 0
    scope_contraction: float = 0.0
    preregistration_violations: int = 0

    def __post_init__(self) -> None:
        counts = (
            self.new_entities,
            self.new_parameters,
            self.special_conditions,
            self.preregistration_violations,
        )
        if any(value < 0 for value in counts):
            raise ValueError("patch-cost counts cannot be negative")
        if self.scope_contraction < 0.0 or not math.isfinite(self.scope_contraction):
            raise ValueError("scope contraction must be finite and non-negative")

    def weighted_total(self, weights: PatchCostWeights) -> float:
        return (
            weights.new_entity * self.new_entities
            + weights.new_parameter * self.new_parameters
            + weights.special_condition * self.special_conditions
            + weights.scope_contraction * self.scope_contraction
            + weights.preregistration_violation * self.preregistration_violations
        )

    def __add__(self, other: PatchCost) -> PatchCost:
        return PatchCost(
            self.new_entities + other.new_entities,
            self.new_parameters + other.new_parameters,
            self.special_conditions + other.special_conditions,
            self.scope_contraction + other.scope_contraction,
            self.preregistration_violations + other.preregistration_violations,
        )


@dataclass(frozen=True, slots=True)
class DescriptionLength:
    structure_bits: int
    parameter_bits: int
    decoder_bits: int
    measurement_bits: int
    assumption_bits: int
    residual_bits: int
    search_metadata_bits: int

    def __post_init__(self) -> None:
        if any(value < 0 for value in asdict(self).values()):
            raise ValueError("description-length components cannot be negative")

    @property
    def total_bits(self) -> int:
        return sum(asdict(self).values())


def _encoded_bits(value: object) -> int:
    return len(canonical_json(value).encode("utf-8")) * 8


def description_length(
    genotype: ParadigmGenotype,
    *,
    residual_bits: int = 0,
    search_metadata: dict[str, Any] | None = None,
) -> DescriptionLength:
    genotype.validate()
    if residual_bits < 0:
        raise ValueError("residual description length cannot be negative")
    ir = genotype.ir
    canonical = json.loads(ir.canonical_structure())
    canonical_terms = [
        [*term[:3], _base_coefficient_symbol(term[3])] for term in canonical["terms"]
    ]
    return DescriptionLength(
        structure_bits=_encoded_bits(
            {
                "variables": canonical["variables"],
                "terms": canonical_terms,
            }
        ),
        parameter_bits=_encoded_bits(sorted(item.value for item in genotype.coefficients)),
        decoder_bits=_encoded_bits({"decoder_cost": ir.measurement.decoder_cost}),
        measurement_bits=_encoded_bits(
            {"observed_channel_count": len(ir.measurement.observed_channels)}
        ),
        assumption_bits=_encoded_bits(sorted(ir.auxiliary_assumptions)),
        residual_bits=residual_bits,
        search_metadata_bits=_encoded_bits(search_metadata or {}),
    )


class LineageStatus(StrEnum):
    ACTIVE = "active"
    DORMANT = "dormant"
    DEAD = "dead"
    EQUIVALENT_DUPLICATE = "equivalent_duplicate"


@dataclass(frozen=True, slots=True)
class MutationRecord:
    operator: str
    parent_genotype_hash: str
    child_genotype_hash: str
    details: dict[str, Any]
    attempted_index: int
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1 or not self.operator or self.attempted_index < 0:
            raise ValueError("invalid mutation record")
        if len(self.parent_genotype_hash) != 64 or len(self.child_genotype_hash) != 64:
            raise ValueError("mutation record requires parent and child hashes")

    @property
    def record_hash(self) -> str:
        return content_hash(asdict(self))


@dataclass(frozen=True, slots=True)
class ParadigmIndividual:
    genotype: ParadigmGenotype
    phenotype: ParadigmPhenotype
    generation: int
    parent_id: str | None
    mutation: MutationRecord | None
    patch_cost: PatchCost
    cumulative_patch_cost: PatchCost
    description: DescriptionLength
    evidence_score: float
    predictive_gain: float
    validated_structure_gain: float
    checkpoints_below_viability: int = 0
    hard_contradictions: int = 0
    status: LineageStatus = LineageStatus.ACTIVE

    def __post_init__(self) -> None:
        self.genotype.validate()
        if self.generation < 0:
            raise ValueError("generation cannot be negative")
        if (self.generation == 0) != (self.parent_id is None):
            raise ValueError("only founders may omit a parent")
        if (self.parent_id is None) != (self.mutation is None):
            raise ValueError("non-founders require a mutation record")
        values = (self.evidence_score, self.predictive_gain, self.validated_structure_gain)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("paradigm fitness diagnostics must be finite")

    @property
    def individual_id(self) -> str:
        return self.genotype.genotype_id


@dataclass(frozen=True, slots=True)
class ParadigmDistance:
    structural: float
    behavioral: float
    combined: float


def structural_distance(first: ParadigmIR, second: ParadigmIR) -> float:
    first_payload = json.loads(first.canonical_structure())
    second_payload = json.loads(second.canonical_structure())
    first_terms = {_structural_term(item) for item in first_payload["terms"]}
    second_terms = {_structural_term(item) for item in second_payload["terms"]}
    union = first_terms | second_terms
    term_distance = 0.0 if not union else len(first_terms ^ second_terms) / len(union)
    assumption_union = set(first_payload["assumptions"]) | set(second_payload["assumptions"])
    assumption_distance = (
        0.0
        if not assumption_union
        else len(set(first_payload["assumptions"]) ^ set(second_payload["assumptions"]))
        / len(assumption_union)
    )
    return 0.8 * term_distance + 0.2 * assumption_distance


def _base_coefficient_symbol(symbol: str) -> str:
    while symbol.endswith("__low") or symbol.endswith("__high"):
        symbol = symbol.rsplit("__", 1)[0]
    return symbol


def _structural_term(term: list[object]) -> str:
    return canonical_json([*term[:3], _base_coefficient_symbol(str(term[3]))])


def behavior_distance(first: ParadigmPhenotype, second: ParadigmPhenotype) -> float:
    if first.probe_set_hash != second.probe_set_hash:
        raise ValueError("behavior distance requires the same probe set")
    left = np.asarray(first.behavior_signature, dtype=float)
    right = np.asarray(second.behavior_signature, dtype=float)
    if left.shape != right.shape:
        raise ValueError("behavior signatures have different shapes")
    scale = max(float(np.sqrt(np.mean(left * left))), float(np.sqrt(np.mean(right * right))), 1e-12)
    return float(np.sqrt(np.mean((left - right) ** 2)) / scale)


def paradigm_distance(first: ParadigmIndividual, second: ParadigmIndividual) -> ParadigmDistance:
    structural = structural_distance(first.genotype.ir, second.genotype.ir)
    behavioral = behavior_distance(first.phenotype, second.phenotype)
    return ParadigmDistance(structural, behavioral, 0.5 * (structural + behavioral))


def genotype_to_dict(genotype: ParadigmGenotype) -> dict[str, Any]:
    return {
        "schema_version": genotype.schema_version,
        "genotype_id": genotype.genotype_id,
        "ir": asdict(genotype.ir),
        "coefficients": [asdict(item) for item in genotype.coefficients],
    }


def genotype_from_dict(payload: dict[str, Any]) -> ParadigmGenotype:
    ir_payload = payload["ir"]
    ir = ParadigmIR(
        paradigm_id=ir_payload["paradigm_id"],
        variables=tuple(StateVariable(**item) for item in ir_payload["variables"]),
        terms=tuple(
            LawTerm(
                target=item["target"],
                operator=item["operator"],
                arguments=tuple(item["arguments"]),
                coefficient_symbol=item["coefficient_symbol"],
            )
            for item in ir_payload["terms"]
        ),
        measurement=MeasurementModel(
            tuple(ir_payload["measurement"]["observed_channels"]),
            ir_payload["measurement"]["decoder_cost"],
        ),
        scope=Scope(
            ir_payload["scope"]["parameter_region"],
            tuple(ir_payload["scope"]["boundary_conditions"]),
            ir_payload["scope"]["measurement_family"],
        ),
        auxiliary_assumptions=tuple(ir_payload["auxiliary_assumptions"]),
        schema_version=ir_payload["schema_version"],
    )
    genotype = ParadigmGenotype(
        payload["genotype_id"],
        ir,
        tuple(CoefficientValue(**item) for item in payload["coefficients"]),
        payload["schema_version"],
    )
    genotype.validate()
    return genotype
