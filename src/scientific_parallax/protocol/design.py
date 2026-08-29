"""Pre-freeze task clusters and simulation-based power diagnostics."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from scientific_parallax.protocol.statistics import stratified_bootstrap_effect
from scientific_parallax.worlds.gray_scott import (
    BoundaryName,
    GrayScottExperiment,
    GrayScottParameters,
    InitialFamily,
    MeasurementSpec,
)


@dataclass(frozen=True, slots=True)
class MeasurementCluster:
    cluster_id: str
    feed: float
    kill: float
    initial_family: InitialFamily
    boundary: BoundaryName
    measurement: MeasurementSpec


@dataclass(frozen=True, slots=True)
class TaskDesignItem:
    cluster_id: str
    experiment: GrayScottExperiment


def frozen_candidate_clusters(steps: int = 100) -> tuple[MeasurementCluster, ...]:
    return (
        MeasurementCluster(
            "clean-spots",
            0.030,
            0.062,
            "center_square",
            "periodic",
            MeasurementSpec(sample_every=steps),
        ),
        MeasurementCluster(
            "mixed-maze",
            0.029,
            0.057,
            "two_spots",
            "periodic",
            MeasurementSpec(sample_every=steps, mixing=((1.0, 0.3), (0.2, 1.0))),
        ),
        MeasurementCluster(
            "partial-spirals",
            0.018,
            0.051,
            "stripe",
            "periodic",
            MeasurementSpec(sample_every=steps, visible_channels=(0,)),
        ),
        MeasurementCluster(
            "downsampled-worms",
            0.058,
            0.065,
            "center_square",
            "periodic",
            MeasurementSpec(sample_every=steps, downsample=2),
        ),
        MeasurementCluster(
            "noisy-gliders",
            0.014,
            0.054,
            "two_spots",
            "periodic",
            MeasurementSpec(sample_every=steps, noise_std=0.01),
        ),
        MeasurementCluster(
            "masked-reflecting",
            0.035,
            0.060,
            "center_square",
            "reflecting",
            MeasurementSpec(sample_every=steps, mask_fraction=0.15),
        ),
    )


def build_task_design(
    *,
    seeds_per_cluster: int = 5,
    grid_size: int = 32,
    steps: int = 100,
) -> tuple[TaskDesignItem, ...]:
    if seeds_per_cluster < 1:
        raise ValueError("each cluster needs at least one independent initial seed")
    tasks: list[TaskDesignItem] = []
    for cluster_index, cluster in enumerate(frozen_candidate_clusters(steps)):
        for seed_offset in range(seeds_per_cluster):
            experiment = GrayScottExperiment(
                f"pf-{cluster.cluster_id}-s{seed_offset}",
                parameters=GrayScottParameters(feed=cluster.feed, kill=cluster.kill),
                initial_family=cluster.initial_family,
                initial_seed=10000 + cluster_index * 100 + seed_offset,
                grid_size=grid_size,
                steps=steps,
                boundary=cluster.boundary,
                measurement=cluster.measurement,
            )
            tasks.append(TaskDesignItem(cluster.cluster_id, experiment))
    return tuple(tasks)


@dataclass(frozen=True, slots=True)
class PowerEstimate:
    assumed_relative_effect: float
    estimated_power: float
    simulations: int
    tasks: int


def estimate_clustered_power(
    *,
    assumed_relative_effect: float,
    seeds_per_cluster: int = 5,
    budget: int = 200,
    minimum_effect: float = 0.20,
    simulations: int = 100,
    bootstrap_samples: int = 200,
    seed: int = 0,
) -> PowerEstimate:
    if not 0.0 < assumed_relative_effect < 1.0:
        raise ValueError("assumed effect must lie strictly between zero and one")
    if simulations < 1 or bootstrap_samples < 2:
        raise ValueError("power analysis requires simulations and at least two bootstrap samples")
    rng = np.random.default_rng(seed)
    cluster_means = np.asarray([95.0, 110.0, 125.0, 140.0, 155.0, 170.0])
    successes = 0
    for simulation in range(simulations):
        treatment: dict[str, list[int | None]] = {}
        control: dict[str, list[int | None]] = {}
        for cluster_index, cluster_mean in enumerate(cluster_means):
            cluster_id = f"cluster-{cluster_index}"
            shared_difficulty = rng.lognormal(0.0, 0.12, seeds_per_cluster)
            control_times = (
                cluster_mean * shared_difficulty * rng.lognormal(0.0, 0.10, seeds_per_cluster)
            )
            treatment_times = (
                cluster_mean
                * (1.0 - assumed_relative_effect)
                * shared_difficulty
                * rng.lognormal(0.0, 0.10, seeds_per_cluster)
            )

            def censor(values: np.ndarray) -> list[int | None]:
                return [
                    None if value >= budget else max(1, int(math.ceil(value))) for value in values
                ]

            control[cluster_id] = censor(control_times)
            treatment[cluster_id] = censor(treatment_times)
        effect = stratified_bootstrap_effect(
            treatment,
            control,
            budget=budget,
            samples=bootstrap_samples,
            seed=seed + simulation,
        )
        if effect.confidence_interval[0] > minimum_effect:
            successes += 1
    return PowerEstimate(
        assumed_relative_effect,
        successes / simulations,
        simulations,
        len(cluster_means) * seeds_per_cluster,
    )
