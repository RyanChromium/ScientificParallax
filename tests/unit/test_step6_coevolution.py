import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from scientific_parallax.coevolution.checkpoint import (
    load_latest_checkpoint,
    write_checkpoint,
)
from scientific_parallax.coevolution.evidence import (
    EvidenceHistoryItem,
    posterior_from_history,
    update_posterior,
)
from scientific_parallax.coevolution.selection import consider_recombination
from scientific_parallax.core.budget import BudgetLedger, BudgetLimits, BudgetSnapshot
from scientific_parallax.evolution.experiment import _individual
from scientific_parallax.evolution.lineage import LineageLedger, rebuild_lineage
from scientific_parallax.evolution.model import PatchCost, PatchCostWeights
from scientific_parallax.evolution.mutation import (
    FrozenParadigmMutator,
    gray_scott_founder_genotype,
    phenotype_on_probes,
    summary_on_experiment,
)
from scientific_parallax.protocol.dry_run import gray_scott_ir
from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottWorld,
    LocalPulse,
    MeasurementSpec,
)


def test_dynamic_evidence_backfills_new_candidates_without_question_access() -> None:
    history = (
        EvidenceHistoryItem(
            "q",
            (0.0,) * 8,
            {"right": (0.0,) * 8, "wrong": (1.0,) * 8},
        ),
    )
    posterior = posterior_from_history(("right", "wrong"), history, 0.01)
    assert posterior["right"] > 0.999
    updated = update_posterior(
        posterior,
        {"right": (0.0,) * 8, "wrong": (1.0,) * 8},
        (0.0,) * 8,
        0.01,
    )
    assert updated["right"] >= posterior["right"]


def test_recombination_is_typed_but_blocked_by_frozen_generator() -> None:
    decision = consider_recombination(
        "left", "right", ("remove_term", "coefficient_low", "coefficient_high", "add_decay")
    )
    assert not decision.allowed
    assert "Gate PF" in decision.reason


def test_budget_and_lineage_resume_without_resetting_counts(tmp_path: Path) -> None:
    limits = BudgetLimits(4, 10, 20)
    resumed_budget = BudgetLedger.resume(limits, BudgetSnapshot(2, 3, 4, 5))
    resumed_budget.charge_world_query()
    assert resumed_budget.snapshot == BudgetSnapshot(3, 3, 4, 5)

    probe = GrayScottExperiment(
        "probe", grid_size=12, steps=8, measurement=MeasurementSpec(sample_every=8)
    )
    founder_genotype = gray_scott_founder_genotype(gray_scott_ir("founder"))
    founder = _individual(
        genotype=founder_genotype,
        phenotype=phenotype_on_probes(founder_genotype, (probe,)),
        truth_phenotype=phenotype_on_probes(founder_genotype, (probe,)),
        generation=0,
        parent=None,
        mutation=None,
        patch_cost=PatchCost(),
        weights=PatchCostWeights(),
        thresholds={"minimum_predictive_gain": 0.01},
    )
    path = tmp_path / "lineage.jsonl"
    ledger = LineageLedger(path)
    ledger.add_founder(founder)
    generated = FrozenParadigmMutator().generate(founder.genotype)[0]
    child = _individual(
        genotype=generated.genotype,
        phenotype=phenotype_on_probes(generated.genotype, (probe,)),
        truth_phenotype=phenotype_on_probes(founder.genotype, (probe,)),
        generation=1,
        parent=founder,
        mutation=generated.mutation,
        patch_cost=generated.patch_cost,
        weights=PatchCostWeights(),
        thresholds={"minimum_predictive_gain": 0.01},
    )
    LineageLedger.resume(path).add_offspring(child)
    rebuilt = rebuild_lineage(path)
    assert rebuilt.event_count == 2
    assert rebuilt.parents[child.individual_id] == founder.individual_id


def test_checkpoint_chain_detects_tampering(tmp_path: Path) -> None:
    directory = tmp_path / "checkpoints"
    first = write_checkpoint(directory, 0, {"value": 1}, "0" * 64)
    write_checkpoint(directory, 1, {"value": 2}, first)
    assert load_latest_checkpoint(directory).state == {"value": 2}
    path = directory / "round-0001.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["value"] = 3
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="modified"):
        load_latest_checkpoint(directory)


def test_paradigm_prediction_honors_measurement_mixing_and_downsampling() -> None:
    genotype = gray_scott_founder_genotype(gray_scott_ir("founder"))
    base = GrayScottExperiment(
        "base", grid_size=12, steps=8, measurement=MeasurementSpec(sample_every=8)
    )
    changed = replace(
        base,
        experiment_id="changed",
        measurement=MeasurementSpec(
            sample_every=8,
            downsample=2,
            mixing=((0.8, 0.2), (0.1, 0.9)),
        ),
    )
    first = np.asarray(summary_on_experiment(genotype, base))
    second = np.asarray(summary_on_experiment(genotype, changed))
    assert first.shape == second.shape == (8,)
    assert not np.allclose(first, second)


def test_founder_prediction_matches_executable_world_with_intervention() -> None:
    genotype = gray_scott_founder_genotype(gray_scott_ir("founder"))
    experiment = GrayScottExperiment(
        "pulse",
        grid_size=12,
        steps=8,
        intervention=LocalPulse(4, 6, 6, delta_v=0.18),
        measurement=MeasurementSpec(
            sample_every=8,
            downsample=2,
            mixing=((0.8, 0.2), (0.1, 0.9)),
        ),
    )
    predicted = np.asarray(summary_on_experiment(genotype, experiment))
    observed = GrayScottWorld().observe(experiment).summary()
    assert predicted == pytest.approx(observed, abs=1e-12)
