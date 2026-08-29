"""Executable frozen mutations and development-probe phenotypes for Step 4."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

import numpy as np

from scientific_parallax.core.reproducibility import content_hash
from scientific_parallax.evolution.model import (
    CoefficientValue,
    MutationRecord,
    ParadigmGenotype,
    ParadigmPhenotype,
    PatchCost,
)
from scientific_parallax.protocol.candidate_generator import (
    CandidateGeneratorSpec,
    FiniteCandidateGenerator,
)
from scientific_parallax.protocol.paradigm_ir import LawTerm, ParadigmIR
from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottWorld,
    _apply_pulse,
    _initial_state,
    _laplacian_periodic,
    _laplacian_reflecting,
)

Laplacian = Callable[[np.ndarray, str], np.ndarray]


@dataclass(frozen=True, slots=True)
class GeneratedGenotype:
    genotype: ParadigmGenotype
    mutation: MutationRecord
    patch_cost: PatchCost


@dataclass(frozen=True, slots=True)
class GeneratedBatch:
    offspring: tuple[GeneratedGenotype, ...]
    attempted_mutations: int


def gray_scott_founder_genotype(ir: ParadigmIR) -> ParadigmGenotype:
    """Attach executable signed coefficients to the frozen Gray–Scott IR."""

    ir.validate()
    variable_order = {item.name: index for index, item in enumerate(ir.variables)}
    values: list[CoefficientValue] = []
    for term in ir.terms:
        index = variable_order[term.target]
        if term.operator == "laplacian":
            value = 0.16 if index == 0 else 0.08
        elif term.operator == "product":
            value = -1.0 if index == 0 else 1.0
        elif term.operator == "source":
            value = 1.0
        elif term.operator == "decay":
            value = -1.0
        else:  # pragma: no cover - ParadigmIR validation owns the finite operator set.
            raise ValueError(f"unsupported founder term: {term.operator}")
        values.append(CoefficientValue(term.target, term.coefficient_symbol, value))
    genotype = ParadigmGenotype(ir.paradigm_id, ir, tuple(values))
    genotype.validate()
    return genotype


class FrozenParadigmMutator:
    """Wrap the exact Protocol Freeze candidate generator with audit records."""

    def __init__(self, spec: CandidateGeneratorSpec | None = None) -> None:
        self.generator = FiniteCandidateGenerator(spec)

    def generate(self, parent: ParadigmGenotype) -> tuple[GeneratedGenotype, ...]:
        return self.generate_with_accounting(parent).offspring

    def generate_with_accounting(self, parent: ParadigmGenotype) -> GeneratedBatch:
        parent.validate()
        batch = self.generator.generate_with_accounting(parent.ir)
        generated: list[GeneratedGenotype] = []
        for child_ir in batch.candidates:
            operator, details = _infer_mutation(parent.ir, child_ir)
            attempted_index = _attempted_index(parent.ir, self.generator.spec, operator, details)
            coefficients = _child_coefficients(parent, child_ir)
            child = ParadigmGenotype(child_ir.paradigm_id, child_ir, coefficients)
            child.validate()
            new_parameter_count = max(0, len(coefficients) - len(parent.coefficients))
            patch = PatchCost(new_parameters=new_parameter_count)
            mutation = MutationRecord(
                operator=operator,
                parent_genotype_hash=parent.genotype_hash,
                child_genotype_hash=child.genotype_hash,
                details=details,
                attempted_index=attempted_index,
            )
            generated.append(GeneratedGenotype(child, mutation, patch))
        return GeneratedBatch(tuple(generated), batch.attempted_mutations)


def _infer_mutation(parent: ParadigmIR, child: ParadigmIR) -> tuple[str, dict[str, object]]:
    if len(child.terms) == len(parent.terms) - 1:
        for index in range(len(parent.terms)):
            if parent.terms[:index] + parent.terms[index + 1 :] == child.terms:
                return "remove_term", {"term_index": index, "term": asdict(parent.terms[index])}
    if len(child.terms) == len(parent.terms) + 1 and child.terms[:-1] == parent.terms:
        return "add_decay", {"term": asdict(child.terms[-1])}
    if len(child.terms) == len(parent.terms):
        changes = [
            index
            for index, (before, after) in enumerate(zip(parent.terms, child.terms, strict=True))
            if before != after
        ]
        if len(changes) == 1:
            index = changes[0]
            symbol = child.terms[index].coefficient_symbol
            if symbol.endswith("__low") or symbol.endswith("__high"):
                direction = "low" if symbol.endswith("__low") else "high"
                return f"coefficient_{direction}", {
                    "term_index": index,
                    "before": asdict(parent.terms[index]),
                    "after": asdict(child.terms[index]),
                }
    raise ValueError("candidate is not one frozen single-step mutation from its parent")


def _child_coefficients(
    parent: ParadigmGenotype,
    child_ir: ParadigmIR,
) -> tuple[CoefficientValue, ...]:
    values: list[CoefficientValue] = []
    for term in child_ir.terms:
        value = -0.01 if term.coefficient_symbol == "new_decay" else parent.coefficient_for(term)
        item = CoefficientValue(term.target, term.coefficient_symbol, value)
        if (item.target, item.symbol) not in {(value.target, value.symbol) for value in values}:
            values.append(item)
    return tuple(values)


def _attempted_index(
    parent: ParadigmIR,
    spec: CandidateGeneratorSpec,
    operator: str,
    details: dict[str, object],
) -> int:
    offset = 0
    if "remove_term" in spec.allowed_mutations:
        if operator == "remove_term":
            return int(details["term_index"])
        offset += len(parent.terms)
    for direction in ("low", "high"):
        mutation_name = f"coefficient_{direction}"
        if mutation_name in spec.allowed_mutations:
            if operator == mutation_name:
                return offset + int(details["term_index"])
            offset += len(parent.terms)
    if "add_decay" in spec.allowed_mutations and operator == "add_decay":
        target = str(details["term"]["target"])
        variable_index = next(
            index for index, variable in enumerate(parent.variables) if variable.name == target
        )
        return offset + variable_index
    raise ValueError("mutation is outside the frozen candidate-generator attempt order")


def phenotype_on_probes(
    genotype: ParadigmGenotype,
    probes: tuple[GrayScottExperiment, ...],
) -> ParadigmPhenotype:
    if not probes:
        raise ValueError("phenotype requires at least one development probe")
    signature: list[float] = []
    for probe in probes:
        signature.extend(_simulate_summary(genotype, probe))
    probe_set_hash = content_hash([asdict(probe) for probe in probes])
    return ParadigmPhenotype(tuple(signature), probe_set_hash)


def summary_on_experiment(
    genotype: ParadigmGenotype,
    experiment: GrayScottExperiment,
) -> tuple[float, ...]:
    """Predict one executable question without access to its realized outcome."""
    return _simulate_summary(genotype, experiment)


def world_phenotype_on_probes(
    probes: tuple[GrayScottExperiment, ...],
) -> ParadigmPhenotype:
    if not probes:
        raise ValueError("world phenotype requires at least one development probe")
    world = GrayScottWorld()
    signature: list[float] = []
    for probe in probes:
        signature.extend(float(value) for value in world.observe(probe).summary())
    return ParadigmPhenotype(
        tuple(signature),
        content_hash([asdict(probe) for probe in probes]),
    )


def _simulate_summary(
    genotype: ParadigmGenotype,
    experiment: GrayScottExperiment,
) -> tuple[float, ...]:
    genotype.validate()
    variable_names = tuple(item.name for item in genotype.ir.variables)
    if len(variable_names) != 2:
        raise ValueError("the Step 4 Gray–Scott phenotype compiler requires two fields")
    u, v = _initial_state(
        experiment.grid_size,
        experiment.initial_family,
        experiment.initial_seed,
    )
    state = {variable_names[0]: u, variable_names[1]: v}
    laplacian = _laplacian_periodic if experiment.boundary == "periodic" else _laplacian_reflecting
    for step in range(1, experiment.steps + 1):
        if experiment.intervention is not None and step == experiment.intervention.at_step:
            _apply_pulse(
                state[variable_names[0]],
                state[variable_names[1]],
                experiment.intervention,
            )
        derivatives = {name: np.zeros_like(value) for name, value in state.items()}
        for term in genotype.ir.terms:
            basis = _term_basis(term, state, laplacian, experiment)
            derivatives[term.target] += _effective_coefficient(genotype, term, experiment) * basis
        state = {
            name: np.clip(value + experiment.dt * derivatives[name], 0.0, 1.5)
            for name, value in state.items()
        }
    ordered_state = np.stack([state[name] for name in variable_names])
    measurement = experiment.measurement
    mixed = np.einsum("ij,jxy->ixy", np.asarray(measurement.mixing), ordered_state)
    mixed = mixed[:, :: measurement.downsample, :: measurement.downsample]
    features: list[float] = []
    for channel_index in measurement.visible_channels:
        final = mixed[channel_index]
        mean = float(np.mean(final))
        standard_deviation = float(np.std(final))
        gy, gx = np.gradient(final)
        features.extend(
            (
                mean,
                standard_deviation,
                float(np.mean(final > mean + standard_deviation)),
                float(np.mean(gx * gx + gy * gy)),
            )
        )
    return tuple(features)


def _effective_coefficient(
    genotype: ParadigmGenotype,
    term: LawTerm,
    experiment: GrayScottExperiment,
) -> float:
    value = genotype.coefficient_for(term)
    base_symbol = term.coefficient_symbol
    while base_symbol.endswith("__low") or base_symbol.endswith("__high"):
        base_symbol = base_symbol.rsplit("__", 1)[0]
    if base_symbol == "feed":
        return value * experiment.parameters.feed
    if base_symbol == "feed_plus_kill":
        return value * (experiment.parameters.feed + experiment.parameters.kill)
    return value


def _term_basis(
    term: LawTerm,
    state: dict[str, np.ndarray],
    laplacian: Laplacian,
    experiment: GrayScottExperiment,
) -> np.ndarray:
    if term.operator == "laplacian":
        return laplacian(state[term.arguments[0]], "five_point") / experiment.spatial_spacing**2
    if term.operator == "product":
        result = np.ones_like(next(iter(state.values())))
        for argument in term.arguments:
            result *= state[argument]
        return result
    if term.operator == "source":
        return 1.0 - state[term.arguments[0]]
    if term.operator == "decay":
        return state[term.arguments[0]]
    raise ValueError(f"unsupported executable Paradigm IR operator: {term.operator}")
