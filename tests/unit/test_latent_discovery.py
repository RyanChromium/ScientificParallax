from __future__ import annotations

import numpy as np

from scientific_parallax.discovery.latent_model import (
    LatentStructureMutator,
    lineage_to_root,
    two_state_founders,
)
from scientific_parallax.worlds.gray_scott import MeasurementSpec
from scientific_parallax.worlds.latent_gray_scott import (
    LatentGrayScottExperiment,
    LatentGrayScottWorld,
    LatentLaw,
    LatentPulse,
)


def _experiment() -> LatentGrayScottExperiment:
    return LatentGrayScottExperiment(
        "latent-test",
        initial_seed=42,
        grid_size=12,
        steps=30,
        sample_every=10,
        pulses=(LatentPulse(8, 6, 6, delta_v=0.30),),
        measurement=MeasurementSpec(sample_every=10),
    )


def test_world_never_exposes_latent_field_and_is_deterministic() -> None:
    world = LatentGrayScottWorld(measurement_seed=7)
    first = world.observe(_experiment())
    second = world.observe(_experiment())
    assert set(first.fields) == {"field_0", "field_1"}
    assert np.array_equal(first.summary(), second.summary())
    assert first.summary().shape == (24,)


def test_latent_feedback_changes_interventional_prediction() -> None:
    experiment = _experiment()
    latent = LatentGrayScottWorld(law=LatentLaw()).observe(experiment).summary()
    fixed = LatentGrayScottWorld(law=LatentLaw(False, False, False)).observe(experiment).summary()
    assert np.linalg.norm(latent - fixed) > 0.01


def test_all_founders_are_wrong_and_complete_structure_requires_three_steps() -> None:
    mutator = LatentStructureMutator()
    candidates = {item.candidate_id: item for item in two_state_founders()}
    assert all(item.structural_stage == 0 for item in candidates.values())

    current = candidates["two-state-2"]
    expected = (
        "add_latent_state",
        "connect_observed_drive",
        "connect_reaction_feedback",
    )
    for operator in expected:
        current = next(
            item for item in mutator.generate(current) if item.mutation.operator == operator
        )
        candidates[current.candidate_id] = current

    lineage = lineage_to_root(current.candidate_id, candidates)
    assert current.law.complete_latent_structure
    assert current.generation == 3
    assert tuple(item.mutation.operator for item in lineage[1:]) == expected
