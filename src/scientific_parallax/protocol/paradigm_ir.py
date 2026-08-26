"""Finite, typed prototype Paradigm IR and conservative equivalence checks."""

from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np
from numpy.typing import ArrayLike

Operator = Literal["laplacian", "product", "source", "decay"]
ALLOWED_OPERATORS: frozenset[str] = frozenset({"laplacian", "product", "source", "decay"})


@dataclass(frozen=True, slots=True)
class StateVariable:
    name: str
    role: Literal["field", "object", "relation"] = "field"


@dataclass(frozen=True, slots=True)
class LawTerm:
    target: str
    operator: Operator
    arguments: tuple[str, ...]
    coefficient_symbol: str


@dataclass(frozen=True, slots=True)
class MeasurementModel:
    observed_channels: tuple[str, ...]
    decoder_cost: float = 0.0


@dataclass(frozen=True, slots=True)
class Scope:
    parameter_region: str
    boundary_conditions: tuple[str, ...]
    measurement_family: str


@dataclass(frozen=True, slots=True)
class ParadigmIR:
    paradigm_id: str
    variables: tuple[StateVariable, ...]
    terms: tuple[LawTerm, ...]
    measurement: MeasurementModel
    scope: Scope
    auxiliary_assumptions: tuple[str, ...] = ()

    def validate(self) -> None:
        names = [variable.name for variable in self.variables]
        if not names or len(set(names)) != len(names):
            raise ValueError("Paradigm IR variables must be non-empty and unique")
        available = set(names)
        for term in self.terms:
            if term.operator not in ALLOWED_OPERATORS:
                raise ValueError(f"operator is outside the frozen finite DSL: {term.operator}")
            if term.target not in available or not set(term.arguments).issubset(available):
                raise ValueError("law term refers to an undeclared variable")
            if not term.coefficient_symbol:
                raise ValueError("law terms require an explicit coefficient symbol")
        if not set(self.measurement.observed_channels).issubset(available):
            raise ValueError("measurement model refers to an undeclared variable")
        if self.measurement.decoder_cost < 0.0:
            raise ValueError("decoder cost cannot be negative")

    def canonical_structure(self) -> str:
        """Canonicalize finite variable permutations and commutative products."""
        self.validate()
        names = tuple(variable.name for variable in self.variables)
        candidates: list[str] = []
        for permutation in itertools.permutations(names):
            rename = {original: f"v{index}" for index, original in enumerate(permutation)}
            variable_roles = sorted((rename[item.name], item.role) for item in self.variables)
            terms = []
            for term in self.terms:
                arguments = [rename[item] for item in term.arguments]
                if term.operator == "product":
                    arguments.sort()
                terms.append(
                    (
                        rename[term.target],
                        term.operator,
                        tuple(arguments),
                        term.coefficient_symbol,
                    )
                )
            payload = {
                "variables": variable_roles,
                "terms": sorted(terms),
                "measurement": sorted(rename[item] for item in self.measurement.observed_channels),
                "scope": asdict(self.scope),
                "assumptions": sorted(self.auxiliary_assumptions),
            }
            candidates.append(json.dumps(payload, sort_keys=True, separators=(",", ":")))
        return min(candidates)


def equivalent_under_declared_transforms(
    first: ParadigmIR,
    second: ParadigmIR,
    first_behavior: ArrayLike,
    second_behavior: ArrayLike,
    *,
    tolerance: float = 1e-8,
) -> bool:
    """Require both canonical structure and observable intervention behavior."""
    if first.canonical_structure() != second.canonical_structure():
        return False
    return bool(
        np.allclose(
            np.asarray(first_behavior, dtype=float),
            np.asarray(second_behavior, dtype=float),
            rtol=tolerance,
            atol=tolerance,
        )
    )
