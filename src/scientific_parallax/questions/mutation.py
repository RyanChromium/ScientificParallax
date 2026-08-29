"""Finite deterministic mutation grammar for executable Gray–Scott questions."""

from __future__ import annotations

from dataclasses import replace

from scientific_parallax.questions.model import (
    QuestionGenotype,
    QuestionMutation,
)
from scientific_parallax.worlds.gray_scott import LocalPulse

ALLOWED_QUESTION_MUTATIONS = (
    "feed_low",
    "feed_high",
    "kill_low",
    "kill_high",
    "cycle_initial_family",
    "toggle_boundary",
    "toggle_pulse",
    "sampling_frequency",
    "downsample",
    "mix_channels",
)


class FrozenQuestionMutator:
    def __init__(self, allowed_mutations: tuple[str, ...] = ALLOWED_QUESTION_MUTATIONS) -> None:
        if not allowed_mutations or len(set(allowed_mutations)) != len(allowed_mutations):
            raise ValueError("question mutation grammar must be non-empty and unique")
        unknown = set(allowed_mutations) - set(ALLOWED_QUESTION_MUTATIONS)
        if unknown:
            raise ValueError(f"unsupported question mutations: {sorted(unknown)}")
        self.allowed_mutations = allowed_mutations

    def generate(
        self,
        parent: QuestionGenotype,
        generation: int,
    ) -> tuple[tuple[QuestionGenotype, QuestionMutation], ...]:
        generated: list[tuple[QuestionGenotype, QuestionMutation]] = []
        for index, operator in enumerate(self.allowed_mutations):
            experiment, details = _mutate_experiment(parent, operator)
            child = QuestionGenotype(
                question_id=f"step5-g{generation}-{parent.question_id}-{index:02d}",
                experiment=replace(
                    experiment,
                    experiment_id=f"step5-g{generation}-{parent.question_id}-{index:02d}",
                ),
                target_paradigm_ids=parent.target_paradigm_ids,
                novelty_label=f"{parent.novelty_label}/{operator}",
            )
            mutation = QuestionMutation(
                operator,
                parent.semantic_hash,
                child.semantic_hash,
                index,
                details,
            )
            generated.append((child, mutation))
        return tuple(generated)


def _mutate_experiment(parent: QuestionGenotype, operator: str):
    experiment = parent.experiment
    parameters = experiment.parameters
    measurement = experiment.measurement
    if operator == "feed_low":
        value = max(0.005, parameters.feed - 0.008)
        return replace(experiment, parameters=replace(parameters, feed=value)), {"feed": value}
    if operator == "feed_high":
        value = min(0.080, parameters.feed + 0.008)
        return replace(experiment, parameters=replace(parameters, feed=value)), {"feed": value}
    if operator == "kill_low":
        value = max(0.030, parameters.kill - 0.004)
        return replace(experiment, parameters=replace(parameters, kill=value)), {"kill": value}
    if operator == "kill_high":
        value = min(0.080, parameters.kill + 0.004)
        return replace(experiment, parameters=replace(parameters, kill=value)), {"kill": value}
    if operator == "cycle_initial_family":
        families = ("center_square", "two_spots", "stripe", "uniform")
        family = families[(families.index(experiment.initial_family) + 1) % len(families)]
        return replace(experiment, initial_family=family), {"initial_family": family}
    if operator == "toggle_boundary":
        boundary = "reflecting" if experiment.boundary == "periodic" else "periodic"
        return replace(experiment, boundary=boundary), {"boundary": boundary}
    if operator == "toggle_pulse":
        if experiment.intervention is None:
            center = experiment.grid_size // 2
            pulse = LocalPulse(max(1, experiment.steps // 2), center, center, delta_v=0.18)
        else:
            pulse = None
        return replace(experiment, intervention=pulse), {"intervention": pulse is not None}
    if operator == "sampling_frequency":
        sample_every = max(1, measurement.sample_every // 2)
        return replace(experiment, measurement=replace(measurement, sample_every=sample_every)), {
            "sample_every": sample_every
        }
    if operator == "downsample":
        downsample = 2 if measurement.downsample == 1 else 1
        return replace(experiment, measurement=replace(measurement, downsample=downsample)), {
            "downsample": downsample
        }
    if operator == "mix_channels":
        identity = ((1.0, 0.0), (0.0, 1.0))
        mixing = ((0.8, 0.2), (0.1, 0.9)) if measurement.mixing == identity else identity
        return replace(experiment, measurement=replace(measurement, mixing=mixing)), {
            "mixing": mixing
        }
    raise AssertionError(f"unreachable mutation operator: {operator}")
