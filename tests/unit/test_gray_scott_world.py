from dataclasses import replace

import numpy as np
import pytest

from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottParameters,
    GrayScottWorld,
    LocalPulse,
    MeasurementSpec,
    ReactionLaw,
    block_holdout,
)
from scientific_parallax.worlds.offline import OfflineTrajectoryWorld


def _experiment(**changes: object) -> GrayScottExperiment:
    base = GrayScottExperiment("q", grid_size=16, steps=20, measurement=MeasurementSpec(10))
    return replace(base, **changes)


def test_uniform_state_is_fixed_point_for_both_solvers() -> None:
    world = GrayScottWorld()
    for solver in ("five_point", "nine_point"):
        observation = world.observe(_experiment(initial_family="uniform", solver=solver))
        assert np.allclose(observation.fields["field_0"], 1.0)
        assert np.allclose(observation.fields["field_1"], 0.0)


def test_uniform_state_is_fixed_point_for_rk4_reference() -> None:
    observation = GrayScottWorld().observe(
        _experiment(initial_family="uniform", solver="nine_point", integrator="rk4")
    )
    assert observation.integrator == "rk4"
    assert np.allclose(observation.fields["field_0"], 1.0)
    assert np.allclose(observation.fields["field_1"], 0.0)


def test_measurement_pipeline_is_reproducible_and_anonymous() -> None:
    measurement = MeasurementSpec(
        sample_every=10,
        downsample=2,
        mixing=((1.0, 0.2), (0.1, 1.0)),
        visible_channels=(1,),
        noise_std=0.01,
        mask_fraction=0.1,
    )
    experiment = _experiment(measurement=measurement)
    first = GrayScottWorld(11).observe(experiment)
    second = GrayScottWorld(11).observe(experiment)
    assert set(first.fields) == {"field_0"}
    assert first.fields["field_0"].shape == (3, 8, 8)
    assert np.allclose(first.fields["field_0"], second.fields["field_0"], equal_nan=True)


def test_local_intervention_changes_observation() -> None:
    world = GrayScottWorld()
    base = world.observe(_experiment())
    pulse = LocalPulse(5, 8, 8, delta_v=0.3)
    changed = world.intervene(_experiment(intervention=pulse))
    assert not np.allclose(base.fields["field_1"], changed.fields["field_1"])


def test_two_discretizations_agree_within_declared_diagnostic_tolerance() -> None:
    world = GrayScottWorld()
    primary = world.observe(_experiment(solver="five_point", steps=40))
    reference = world.observe(_experiment(solver="nine_point", integrator="rk4", steps=40))
    difference = np.mean(abs(primary.fields["field_1"] - reference.fields["field_1"]))
    assert difference < 0.03
    assert difference > 0.0


def test_stability_bound_is_enforced() -> None:
    unstable = _experiment(dt=2.0, parameters=GrayScottParameters(diffusion_u=0.2))
    with pytest.raises(ValueError, match="stability"):
        GrayScottWorld().observe(unstable)


def test_invalid_reaction_law_is_rejected() -> None:
    with pytest.raises(ValueError, match="reaction power"):
        GrayScottWorld(law=ReactionLaw(reaction_power=0.0)).observe(_experiment())


def test_block_holdout_never_splits_one_family() -> None:
    experiments = [
        _experiment(experiment_id="a", initial_seed=1),
        _experiment(experiment_id="b", initial_seed=2),
        _experiment(
            experiment_id="c",
            parameters=GrayScottParameters(feed=0.04),
        ),
    ]
    held_out = {experiments[-1].family_id}
    train, test = block_holdout(experiments, held_out)
    assert {item.family_id for item in train}.isdisjoint({item.family_id for item in test})


def test_offline_world_refuses_new_conditions_and_interventions() -> None:
    experiment = _experiment()
    observation = GrayScottWorld().observe(experiment)
    offline = OfflineTrajectoryWorld({experiment.experiment_id: observation}, "fixture")
    assert not offline.capabilities().supports_intervention
    assert offline.observe(experiment) is observation
    with pytest.raises(RuntimeError, match="cannot execute"):
        offline.intervene(experiment)
