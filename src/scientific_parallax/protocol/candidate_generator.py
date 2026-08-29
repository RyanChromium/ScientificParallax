"""Deterministic finite candidate generator shared by treatment and H2 control."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

from scientific_parallax.core.reproducibility import content_hash
from scientific_parallax.protocol.paradigm_ir import LawTerm, ParadigmIR


@dataclass(frozen=True, slots=True)
class CandidateGeneratorSpec:
    version: str = "candidate-generator-v0.1"
    allowed_mutations: tuple[str, ...] = (
        "remove_term",
        "coefficient_low",
        "coefficient_high",
        "add_decay",
    )
    maximum_offspring_per_parent: int = 32
    maximum_candidates_per_task: int = 128

    @property
    def spec_hash(self) -> str:
        return content_hash(asdict(self))


@dataclass(frozen=True, slots=True)
class CandidateGenerationBatch:
    candidates: tuple[ParadigmIR, ...]
    attempted_mutations: int


class FiniteCandidateGenerator:
    def __init__(self, spec: CandidateGeneratorSpec | None = None) -> None:
        self.spec = spec or CandidateGeneratorSpec()
        if (
            min(
                self.spec.maximum_offspring_per_parent,
                self.spec.maximum_candidates_per_task,
            )
            < 1
        ):
            raise ValueError("candidate generator budgets must be positive")
        supported = {"remove_term", "coefficient_low", "coefficient_high", "add_decay"}
        if not set(self.spec.allowed_mutations).issubset(supported):
            raise ValueError("candidate generator contains an unsupported mutation")

    def generate(self, parent: ParadigmIR) -> tuple[ParadigmIR, ...]:
        return self.generate_with_accounting(parent).candidates

    def generate_with_accounting(self, parent: ParadigmIR) -> CandidateGenerationBatch:
        parent.validate()
        candidates: dict[str, ParadigmIR] = {}
        attempted_mutations = 0

        def add(terms: tuple[LawTerm, ...], mutation: str) -> None:
            nonlocal attempted_mutations
            if attempted_mutations >= self.spec.maximum_offspring_per_parent:
                return
            attempted_mutations += 1
            candidate_id = f"{parent.paradigm_id}:{mutation}:{len(candidates)}"
            candidate = replace(parent, paradigm_id=candidate_id, terms=terms)
            candidate.validate()
            candidates.setdefault(candidate.canonical_structure(), candidate)

        if "remove_term" in self.spec.allowed_mutations:
            for index in range(len(parent.terms)):
                add(parent.terms[:index] + parent.terms[index + 1 :], f"remove-{index}")
        for direction in ("low", "high"):
            mutation_name = f"coefficient_{direction}"
            if mutation_name not in self.spec.allowed_mutations:
                continue
            for index, term in enumerate(parent.terms):
                changed = replace(
                    term,
                    coefficient_symbol=f"{term.coefficient_symbol}__{direction}",
                )
                add(
                    parent.terms[:index] + (changed,) + parent.terms[index + 1 :],
                    f"coefficient-{direction}-{index}",
                )
        if "add_decay" in self.spec.allowed_mutations:
            for variable in parent.variables:
                extra = LawTerm(variable.name, "decay", (variable.name,), "new_decay")
                add((*parent.terms, extra), f"add-decay-{variable.name}")
        return CandidateGenerationBatch(
            tuple(candidates.values())[: self.spec.maximum_candidates_per_task],
            attempted_mutations,
        )
