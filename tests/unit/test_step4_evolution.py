import json
from pathlib import Path

import pytest

from scientific_parallax.evolution.lineage import (
    LineageLedger,
    rebuild_lineage,
    verify_lineage,
)
from scientific_parallax.evolution.model import (
    LineageStatus,
    ParadigmGenotype,
    ParadigmIndividual,
    PatchCost,
    PatchCostWeights,
    behavior_distance,
    description_length,
    structural_distance,
)
from scientific_parallax.evolution.mutation import (
    FrozenParadigmMutator,
    gray_scott_founder_genotype,
    phenotype_on_probes,
    world_phenotype_on_probes,
)
from scientific_parallax.evolution.population import ParadigmPopulation
from scientific_parallax.protocol.dry_run import gray_scott_ir
from scientific_parallax.protocol.evidence_layers import SurvivalPolicy
from scientific_parallax.worlds.gray_scott import GrayScottExperiment, MeasurementSpec


def _probes() -> tuple[GrayScottExperiment, ...]:
    return (
        GrayScottExperiment(
            "probe",
            grid_size=12,
            steps=8,
            measurement=MeasurementSpec(sample_every=8),
        ),
    )


def _individual(
    genotype: ParadigmGenotype,
    *,
    identifier_parent: ParadigmIndividual | None = None,
) -> ParadigmIndividual:
    phenotype = phenotype_on_probes(genotype, _probes())
    mutation = None
    patch = PatchCost()
    generation = 0
    if identifier_parent is not None:
        generated = FrozenParadigmMutator().generate(identifier_parent.genotype)[0]
        genotype = generated.genotype
        phenotype = phenotype_on_probes(genotype, _probes())
        mutation = generated.mutation
        patch = generated.patch_cost
        generation = identifier_parent.generation + 1
    return ParadigmIndividual(
        genotype=genotype,
        phenotype=phenotype,
        generation=generation,
        parent_id=None if identifier_parent is None else identifier_parent.individual_id,
        mutation=mutation,
        patch_cost=patch,
        cumulative_patch_cost=(
            patch if identifier_parent is None else identifier_parent.cumulative_patch_cost + patch
        ),
        description=description_length(genotype),
        evidence_score=1.0,
        predictive_gain=0.05,
        validated_structure_gain=0.0,
    )


def test_frozen_mutations_are_executable_traceable_and_accounted() -> None:
    founder = gray_scott_founder_genotype(gray_scott_ir("founder"))
    batch = FrozenParadigmMutator().generate_with_accounting(founder)
    assert batch.attempted_mutations == 20
    assert len(batch.offspring) == 20
    assert {item.mutation.operator for item in batch.offspring} == {
        "remove_term",
        "coefficient_low",
        "coefficient_high",
        "add_decay",
    }
    assert len({item.mutation.attempted_index for item in batch.offspring}) == 20
    assert all(
        item.mutation.parent_genotype_hash == founder.genotype_hash for item in batch.offspring
    )
    assert all(
        item.mutation.child_genotype_hash == item.genotype.genotype_hash for item in batch.offspring
    )
    assert any(
        behavior_distance(
            phenotype_on_probes(founder, _probes()),
            phenotype_on_probes(item.genotype, _probes()),
        )
        > 0.0
        for item in batch.offspring
    )


def test_renaming_has_zero_structure_and_behavior_distance() -> None:
    first = gray_scott_founder_genotype(gray_scott_ir("a"))
    second = gray_scott_founder_genotype(gray_scott_ir("b", "x", "y"))
    assert structural_distance(first.ir, second.ir) == 0.0
    assert description_length(first).total_bits == description_length(second).total_bits
    assert behavior_distance(
        phenotype_on_probes(first, _probes()),
        phenotype_on_probes(second, _probes()),
    ) == pytest.approx(0.0)
    assert behavior_distance(
        phenotype_on_probes(first, _probes()),
        world_phenotype_on_probes(_probes()),
    ) == pytest.approx(0.0, abs=1e-12)


def test_patch_cost_exposes_overfit_components() -> None:
    weights = PatchCostWeights()
    simple = PatchCost(new_parameters=1)
    overfit = PatchCost(special_conditions=3, scope_contraction=0.5)
    assert overfit.weighted_total(weights) > simple.weighted_total(weights)
    assert (simple + overfit).special_conditions == 3


def test_parameter_mutation_changes_behavior_without_claiming_structure_gain() -> None:
    founder = gray_scott_founder_genotype(gray_scott_ir("founder"))
    parameter_child = next(
        item
        for item in FrozenParadigmMutator().generate(founder)
        if item.mutation.operator == "coefficient_low"
    )
    assert structural_distance(founder.ir, parameter_child.genotype.ir) == 0.0
    assert (
        behavior_distance(
            phenotype_on_probes(founder, _probes()),
            phenotype_on_probes(parameter_child.genotype, _probes()),
        )
        > 0.0
    )


def test_lineage_rebuilds_and_detects_tampering(tmp_path: Path) -> None:
    founder = _individual(gray_scott_founder_genotype(gray_scott_ir("founder")))
    child = _individual(founder.genotype, identifier_parent=founder)
    path = tmp_path / "lineage.jsonl"
    ledger = LineageLedger(path)
    ledger.add_founder(founder)
    ledger.add_offspring(child)
    ledger.set_status(child.individual_id, LineageStatus.DEAD, reason="test fossil")
    rebuilt = rebuild_lineage(path)
    assert rebuilt.parents[child.individual_id] == founder.individual_id
    assert rebuilt.failure_reasons[child.individual_id] == "test fossil"
    verify_lineage(path)

    events = path.read_text(encoding="utf-8").splitlines()
    event = json.loads(events[1])
    event["payload"]["individual"]["evidence_score"] = 999.0
    events[1] = json.dumps(event, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(events) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="modified"):
        verify_lineage(path)


def test_population_collapses_equivalent_alias_and_keeps_three_niches(tmp_path: Path) -> None:
    founder = _individual(gray_scott_founder_genotype(gray_scott_ir("founder")))
    alias = _individual(gray_scott_founder_genotype(gray_scott_ir("zz-alias", "x", "y")))
    ledger = LineageLedger(tmp_path / "lineage.jsonl")
    ledger.add_founder(founder)
    ledger.add_founder(alias)
    population = ParadigmPopulation(
        niche_capacities={
            "current_predictive_best": 4,
            "minimum_description": 4,
            "validated_structure_gain": 4,
        },
        survival_policy=SurvivalPolicy(2, 4),
        minimum_evidence_score=0.0,
        minimum_predictive_gain=0.01,
        maximum_decoder_cost=1.0,
    )
    snapshot = population.select((founder, alias), ledger)
    assert alias.individual_id in snapshot.equivalent_to
    assert alias.individual_id in snapshot.fossil_ids
    assert set(snapshot.niches) == set(ParadigmPopulation.REQUIRED_NICHES)
    assert snapshot.active_ids == (founder.individual_id,)
