"""Frozen-candidate numerical agreement diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import numpy as np

from scientific_parallax.worlds.gray_scott import GrayScottExperiment, GrayScottWorld


@dataclass(frozen=True, slots=True)
class NumericalTolerance:
    field_mean_absolute: float
    field_max_absolute: float
    summary_l2: float

    def validate(self) -> None:
        if min(asdict(self).values()) <= 0.0:
            raise ValueError("all numerical tolerances must be positive")


@dataclass(frozen=True, slots=True)
class NumericalAgreement:
    field_mean_absolute: float
    field_max_absolute: float
    summary_l2: float
    passed: bool


def compare_primary_and_reference(
    experiment: GrayScottExperiment,
    tolerance: NumericalTolerance,
    world: GrayScottWorld | None = None,
) -> NumericalAgreement:
    tolerance.validate()
    evaluation_world = world or GrayScottWorld()
    # Numerical agreement must compare solvers, not independent noise/mask draws whose
    # seeds legitimately include the complete experiment identity.
    deterministic_measurement = replace(experiment.measurement, noise_std=0.0, mask_fraction=0.0)
    primary = evaluation_world.observe(
        replace(
            experiment,
            solver="five_point",
            integrator="euler",
            measurement=deterministic_measurement,
        )
    )
    reference = evaluation_world.observe(
        replace(
            experiment,
            solver="nine_point",
            integrator="rk4",
            measurement=deterministic_measurement,
        )
    )
    if set(primary.fields) != set(reference.fields):
        raise ValueError("primary and reference measurements expose different channels")
    differences = [np.abs(primary.fields[name] - reference.fields[name]) for name in primary.fields]
    field_mean = float(np.mean([np.nanmean(item) for item in differences]))
    field_max = float(np.max([np.nanmax(item) for item in differences]))
    summary_l2 = float(np.linalg.norm(primary.summary() - reference.summary()))
    passed = (
        field_mean <= tolerance.field_mean_absolute
        and field_max <= tolerance.field_max_absolute
        and summary_l2 <= tolerance.summary_l2
    )
    return NumericalAgreement(field_mean, field_max, summary_l2, passed)
