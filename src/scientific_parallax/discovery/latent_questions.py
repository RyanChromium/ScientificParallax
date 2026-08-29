"""Finite interventions for exposing delayed latent feedback."""

from __future__ import annotations

from dataclasses import replace

from scientific_parallax.worlds.gray_scott import MeasurementSpec
from scientific_parallax.worlds.latent_gray_scott import (
    LatentGrayScottExperiment,
    LatentPulse,
)

ALLOWED_LATENT_QUESTION_MUTATIONS = (
    "pulse_early",
    "pulse_late",
    "pulse_strong",
    "double_pulse",
    "feed_low",
    "feed_high",
    "kill_low",
    "kill_high",
    "cycle_initial_family",
    "toggle_boundary",
    "extend_duration",
)


class LatentQuestionMutator:
    def __init__(self, allowed_mutations: tuple[str, ...]) -> None:
        if not allowed_mutations or len(set(allowed_mutations)) != len(allowed_mutations):
            raise ValueError("latent question mutations must be non-empty and unique")
        unknown = set(allowed_mutations) - set(ALLOWED_LATENT_QUESTION_MUTATIONS)
        if unknown:
            raise ValueError(f"unsupported latent question mutations: {sorted(unknown)}")
        self.allowed_mutations = allowed_mutations

    def generate(
        self, parent: LatentGrayScottExperiment, generation: int
    ) -> tuple[LatentGrayScottExperiment, ...]:
        return tuple(
            replace(
                _mutate(parent, operator),
                experiment_id=f"latent-q-g{generation}-{index}",
            )
            for index, operator in enumerate(self.allowed_mutations)
        )


def seed_questions(
    *, task_token: str, initial_seed: int, grid_size: int, steps: int, sample_every: int
) -> tuple[LatentGrayScottExperiment, ...]:
    center = grid_size // 2
    base = LatentGrayScottExperiment(
        f"latent-{task_token}-seed-0",
        initial_seed=initial_seed,
        grid_size=grid_size,
        steps=steps,
        sample_every=sample_every,
        measurement=MeasurementSpec(sample_every=sample_every, noise_std=0.004),
    )
    return (
        base,
        replace(
            base,
            experiment_id=f"latent-{task_token}-seed-1",
            pulses=(LatentPulse(max(2, steps // 4), center, center, delta_v=0.24),),
        ),
        replace(
            base,
            experiment_id=f"latent-{task_token}-seed-2",
            feed=0.025,
            kill=0.054,
            initial_family="stripe",
            boundary="reflecting",
        ),
    )


def validation_questions(
    *, task_token: str, initial_seed: int, grid_size: int, steps: int, sample_every: int
) -> tuple[LatentGrayScottExperiment, ...]:
    """Conditions are disjoint from the seed pool and never enter strategy selection."""

    center = grid_size // 2
    return (
        LatentGrayScottExperiment(
            f"latent-{task_token}-validation-late",
            feed=0.031,
            kill=0.059,
            initial_family="two_spots",
            initial_seed=initial_seed + 10000,
            grid_size=grid_size,
            steps=steps + 8,
            sample_every=sample_every,
            pulses=(LatentPulse(steps * 2 // 3, center, center, delta_v=0.30),),
            measurement=MeasurementSpec(sample_every=sample_every, noise_std=0.004),
        ),
        LatentGrayScottExperiment(
            f"latent-{task_token}-validation-double",
            feed=0.020,
            kill=0.052,
            initial_family="center_square",
            initial_seed=initial_seed + 20000,
            grid_size=grid_size,
            steps=steps + 8,
            sample_every=sample_every,
            boundary="reflecting",
            pulses=(
                LatentPulse(max(2, steps // 5), center - 2, center, delta_v=0.20),
                LatentPulse(steps * 3 // 5, center + 2, center, delta_v=0.20),
            ),
            measurement=MeasurementSpec(sample_every=sample_every, noise_std=0.004),
        ),
        LatentGrayScottExperiment(
            f"latent-{task_token}-validation-shift",
            feed=0.046,
            kill=0.064,
            initial_family="stripe",
            initial_seed=initial_seed + 30000,
            grid_size=grid_size,
            steps=steps + 8,
            sample_every=sample_every,
            pulses=(LatentPulse(steps // 2, center, center, delta_v=0.26),),
            measurement=MeasurementSpec(sample_every=sample_every, noise_std=0.004),
        ),
    )


def _mutate(experiment: LatentGrayScottExperiment, operator: str) -> LatentGrayScottExperiment:
    center = experiment.grid_size // 2
    pulse = experiment.pulses[0] if experiment.pulses else None
    if operator == "pulse_early":
        item = pulse or LatentPulse(2, center, center, delta_v=0.20)
        return replace(
            experiment,
            pulses=(replace(item, at_step=max(2, experiment.steps // 5)),),
        )
    if operator == "pulse_late":
        item = pulse or LatentPulse(2, center, center, delta_v=0.20)
        return replace(
            experiment,
            pulses=(replace(item, at_step=experiment.steps * 3 // 4),),
        )
    if operator == "pulse_strong":
        item = pulse or LatentPulse(experiment.steps // 3, center, center)
        return replace(experiment, pulses=(replace(item, delta_v=0.38),))
    if operator == "double_pulse":
        first = LatentPulse(max(2, experiment.steps // 5), center - 2, center, delta_v=0.20)
        second = LatentPulse(experiment.steps * 3 // 5, center + 2, center, delta_v=0.20)
        return replace(experiment, pulses=(first, second))
    if operator == "feed_low":
        return replace(experiment, feed=max(0.01, experiment.feed - 0.008))
    if operator == "feed_high":
        return replace(experiment, feed=min(0.07, experiment.feed + 0.008))
    if operator == "kill_low":
        return replace(experiment, kill=max(0.03, experiment.kill - 0.005))
    if operator == "kill_high":
        return replace(experiment, kill=min(0.08, experiment.kill + 0.005))
    if operator == "cycle_initial_family":
        families = ("center_square", "two_spots", "stripe", "uniform")
        family = families[(families.index(experiment.initial_family) + 1) % len(families)]
        return replace(experiment, initial_family=family)
    if operator == "toggle_boundary":
        boundary = "reflecting" if experiment.boundary == "periodic" else "periodic"
        return replace(experiment, boundary=boundary)
    if operator == "extend_duration":
        return replace(experiment, steps=experiment.steps + max(4, experiment.steps // 4))
    raise AssertionError(f"unreachable latent question mutation: {operator}")
