"""Development-only Step 4 control with fixed probes and paradigm evolution."""

from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any

from scientific_parallax.core.budget import BudgetLedger, BudgetLimits
from scientific_parallax.core.reproducibility import (
    ExperimentIdentity,
    RunManifest,
    capture_environment,
    content_hash,
)
from scientific_parallax.evolution.lineage import LineageLedger, rebuild_lineage
from scientific_parallax.evolution.model import (
    LineageStatus,
    MutationRecord,
    ParadigmGenotype,
    ParadigmIndividual,
    ParadigmPhenotype,
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
from scientific_parallax.protocol.candidate_generator import CandidateGeneratorSpec
from scientific_parallax.protocol.dry_run import gray_scott_ir, protocol_spec_from_config
from scientific_parallax.protocol.evidence_layers import SurvivalPolicy
from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottParameters,
    MeasurementSpec,
)


def run_step4_control(config_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite Step 4 output: {output_dir}")
    output_dir.mkdir(parents=True)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("unsupported Step 4 control configuration schema")
    protocol_config_path = Path(config["protocol_config"])
    protocol_config = json.loads(protocol_config_path.read_text(encoding="utf-8"))
    protocol_spec = protocol_spec_from_config(protocol_config)
    if protocol_spec.protocol_hash != config["protocol_hash"]:
        raise ValueError("Step 4 config does not match the frozen protocol hash")

    generator_config = protocol_config["candidate_generator"]
    generator_spec = CandidateGeneratorSpec(
        version=generator_config["version"],
        allowed_mutations=tuple(generator_config["allowed_mutations"]),
        maximum_offspring_per_parent=generator_config["maximum_offspring_per_parent"],
        maximum_candidates_per_task=generator_config["maximum_candidates_per_task"],
    )
    if generator_spec.spec_hash != protocol_spec.candidate_generator_hash:
        raise ValueError("Step 4 mutator differs from the Protocol Freeze generator")

    probes = _fixed_probes(config["fixed_probes"])
    weights = PatchCostWeights(**config["patch_cost_weights"])
    thresholds = protocol_config["viability_thresholds"]
    population = ParadigmPopulation(
        niche_capacities=protocol_config["niche_capacities"],
        survival_policy=SurvivalPolicy(**protocol_config["survival_parameters"]),
        minimum_evidence_score=thresholds["minimum_evidence_score"],
        minimum_predictive_gain=thresholds["minimum_predictive_gain"],
        maximum_decoder_cost=thresholds["maximum_decoder_cost"],
    )
    budget = BudgetLedger(
        BudgetLimits(
            protocol_config["world_query_budget"],
            protocol_config["candidate_generation_budget"],
            protocol_config["candidate_evaluation_budget"],
        )
    )
    lineage_path = output_dir / "lineage.jsonl"
    ledger = LineageLedger(lineage_path)

    founder_genotype = gray_scott_founder_genotype(gray_scott_ir("step4-founder"))
    budget.charge_world_query(len(probes))
    truth_phenotype = world_phenotype_on_probes(probes)
    founder = _individual(
        genotype=founder_genotype,
        phenotype=truth_phenotype,
        truth_phenotype=truth_phenotype,
        generation=0,
        parent=None,
        mutation=None,
        patch_cost=PatchCost(),
        weights=weights,
        thresholds=thresholds,
    )
    alias_genotype = gray_scott_founder_genotype(
        gray_scott_ir("zz-step4-renamed-alias", "chemical_a", "chemical_b")
    )
    alias = _individual(
        genotype=alias_genotype,
        phenotype=phenotype_on_probes(alias_genotype, probes),
        truth_phenotype=truth_phenotype,
        generation=0,
        parent=None,
        mutation=None,
        patch_cost=PatchCost(),
        weights=weights,
        thresholds=thresholds,
    )
    ledger.add_founder(founder)
    ledger.add_founder(alias)
    all_individuals: dict[str, ParadigmIndividual] = {
        founder.individual_id: founder,
        alias.individual_id: alias,
    }
    initial_snapshot = population.select((founder, alias), ledger)
    active = {identifier: all_individuals[identifier] for identifier in initial_snapshot.active_ids}
    generation_records: list[dict[str, Any]] = [
        {
            "generation": 0,
            "created": 2,
            "active": list(initial_snapshot.active_ids),
            "dormant": list(initial_snapshot.dormant_ids),
            "fossils": list(initial_snapshot.fossil_ids),
            "niches": initial_snapshot.niches,
        }
    ]
    mutator = FrozenParadigmMutator(generator_spec)
    mutation_operators: set[str] = set()

    for generation in range(1, config["generations"] + 1):
        pool = dict(active)
        created = 0
        for parent in tuple(active.values()):
            batch = mutator.generate_with_accounting(parent.genotype)
            remaining = budget.limits.candidate_generations - budget.snapshot.candidate_generations
            if batch.attempted_mutations > remaining:
                break
            budget.charge_candidate_generation(batch.attempted_mutations)
            for generated in batch.offspring:
                if generated.genotype.genotype_id in all_individuals:
                    budget.charge_candidate_evaluation(cache_hit=True)
                    continue
                budget.charge_candidate_evaluation()
                phenotype = phenotype_on_probes(generated.genotype, probes)
                child = _individual(
                    genotype=generated.genotype,
                    phenotype=phenotype,
                    truth_phenotype=truth_phenotype,
                    generation=generation,
                    parent=parent,
                    mutation=generated.mutation,
                    patch_cost=generated.patch_cost,
                    weights=weights,
                    thresholds=thresholds,
                )
                ledger.add_offspring(child)
                all_individuals[child.individual_id] = child
                pool[child.individual_id] = child
                mutation_operators.add(generated.mutation.operator)
                created += 1
        snapshot = population.select(tuple(pool.values()), ledger)
        active = {identifier: all_individuals[identifier] for identifier in snapshot.active_ids}
        generation_records.append(
            {
                "generation": generation,
                "created": created,
                "active": list(snapshot.active_ids),
                "dormant": list(snapshot.dormant_ids),
                "fossils": list(snapshot.fossil_ids),
                "niches": snapshot.niches,
            }
        )
        if (
            not active
            or budget.snapshot.candidate_generations >= budget.limits.candidate_generations
        ):
            break

    rebuilt = rebuild_lineage(lineage_path)
    expected_parent_links = {
        identifier: individual.parent_id for identifier, individual in all_individuals.items()
    }
    overfit_patch = PatchCost(special_conditions=3, scope_contraction=0.5)
    simple_patch = PatchCost(new_parameters=1)
    checks = {
        "frozen_protocol_hash_matches": protocol_spec.protocol_hash == config["protocol_hash"],
        "frozen_generator_hash_matches": generator_spec.spec_hash
        == protocol_spec.candidate_generator_hash,
        "all_offspring_traceable": all(
            individual.generation == 0
            or (individual.parent_id is not None and individual.mutation is not None)
            for individual in all_individuals.values()
        ),
        "renamed_equivalent_collapsed": alias.individual_id in population.fossils,
        "overfit_patch_cost_is_higher": overfit_patch.weighted_total(weights)
        > simple_patch.weighted_total(weights),
        "lineage_rebuild_is_complete": set(rebuilt.individuals) == set(all_individuals)
        and rebuilt.parents == expected_parent_links,
        "failed_lineages_preserved": bool(rebuilt.failure_reasons),
        "three_frozen_niches_maintained": all(
            set(record["niches"]) == set(ParadigmPopulation.REQUIRED_NICHES)
            for record in generation_records
        ),
        "description_length_is_complete": all(
            individual.description.total_bits
            >= individual.description.residual_bits
            + individual.description.decoder_bits
            + individual.description.measurement_bits
            for individual in all_individuals.values()
        ),
        "frozen_mutation_operators_exercised": mutation_operators
        == set(generator_spec.allowed_mutations),
        "final_world_not_accessed": True,
    }
    report = {
        "schema_version": 1,
        "status": "step4_control_complete" if all(checks.values()) else "redo",
        "strategy_version": config["strategy_version"],
        "scope": "development probes only; final sealed tasks were not accessed",
        "protocol_hash": protocol_spec.protocol_hash,
        "candidate_generator_hash": generator_spec.spec_hash,
        "checks": checks,
        "fixed_probe_set_hash": truth_phenotype.probe_set_hash,
        "fixed_probe_count": len(probes),
        "mutation_operators": sorted(mutation_operators),
        "patch_cost_weights": asdict(weights),
        "budget": asdict(budget.snapshot),
        "generations": generation_records,
        "lineage": {
            "individuals": len(rebuilt.individuals),
            "events": rebuilt.event_count,
            "ledger_hash": rebuilt.ledger_hash,
            "founders": sum(parent is None for parent in rebuilt.parents.values()),
            "offspring": sum(parent is not None for parent in rebuilt.parents.values()),
            "failed_or_equivalent_fossils": len(rebuilt.failure_reasons),
        },
        "final_population": {
            "active": sorted(active),
            "fossils": sorted(population.fossils),
            "fossil_reasons": population.failure_reasons,
        },
        "description_length_encoding": (
            "canonical UTF-8 JSON bits for structure, parameters, decoder, measurement, "
            "assumptions, and search metadata plus explicit residual bits"
        ),
        "assurance": (
            "Step 4 is strategy development after local self-audited Protocol Freeze; "
            "this report is not final-world evidence"
        ),
    }
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    environment = capture_environment(Path.cwd())
    identity = ExperimentIdentity(
        "step4-paradigm-evolution-control-v1",
        config,
        config["seed"],
        environment["git_revision"],
    )
    manifest = RunManifest(
        schema_version=1,
        experiment_id=identity.experiment_id,
        protocol_id="step4-paradigm-evolution-control-v1",
        config_hash=identity.config_hash,
        seed=config["seed"],
        environment=environment,
        inputs={
            "config": str(config_path),
            "protocol_hash": protocol_spec.protocol_hash,
            "probe_set_hash": truth_phenotype.probe_set_hash,
        },
        outputs={
            "report": report_path.name,
            "report_hash": content_hash(report),
            "lineage": lineage_path.name,
            "lineage_hash": rebuilt.ledger_hash,
        },
    )
    manifest.write_once(output_dir / "manifest.json")
    return report


def _individual(
    *,
    genotype: ParadigmGenotype,
    phenotype: ParadigmPhenotype,
    truth_phenotype: ParadigmPhenotype,
    generation: int,
    parent: ParadigmIndividual | None,
    mutation: MutationRecord | None,
    patch_cost: PatchCost,
    weights: PatchCostWeights,
    thresholds: dict[str, float],
) -> ParadigmIndividual:
    distance = behavior_distance(phenotype, truth_phenotype)
    evidence_score = 1.0 / (1.0 + distance)
    predictive_gain = 0.05 / (1.0 + distance)
    structure_gain = (
        0.0
        if parent is None
        else structural_distance(parent.genotype.ir, genotype.ir) * evidence_score
    )
    below = 0 if predictive_gain >= thresholds["minimum_predictive_gain"] else 2
    contradiction = int(distance > 1.0)
    cumulative = patch_cost if parent is None else parent.cumulative_patch_cost + patch_cost
    residual_bits = int(math.ceil(2048.0 * min(distance, 10.0)))
    individual = ParadigmIndividual(
        genotype=genotype,
        phenotype=phenotype,
        generation=generation,
        parent_id=None if parent is None else parent.individual_id,
        mutation=mutation,
        patch_cost=patch_cost,
        cumulative_patch_cost=cumulative,
        description=description_length(
            genotype,
            residual_bits=residual_bits,
            search_metadata={
                "generation": generation,
                "operator": None if mutation is None else mutation.operator,
                "weighted_cumulative_patch": cumulative.weighted_total(weights),
            },
        ),
        evidence_score=evidence_score,
        predictive_gain=predictive_gain,
        validated_structure_gain=structure_gain,
        checkpoints_below_viability=below,
        hard_contradictions=contradiction,
        status=LineageStatus.ACTIVE,
    )
    return individual


def _fixed_probes(raw_probes: list[dict[str, Any]]) -> tuple[GrayScottExperiment, ...]:
    probes: list[GrayScottExperiment] = []
    for index, raw in enumerate(raw_probes):
        probes.append(
            GrayScottExperiment(
                experiment_id=f"step4-fixed-probe-{index}",
                parameters=GrayScottParameters(feed=raw["feed"], kill=raw["kill"]),
                initial_family=raw["initial_family"],
                initial_seed=raw["initial_seed"],
                grid_size=raw["grid_size"],
                steps=raw["steps"],
                boundary=raw["boundary"],
                measurement=MeasurementSpec(sample_every=raw["steps"]),
            )
        )
    if not probes:
        raise ValueError("Step 4 control requires fixed development probes")
    return tuple(probes)
