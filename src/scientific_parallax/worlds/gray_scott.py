"""Online Gray–Scott world with two independent spatial discretizations."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from scientific_parallax.worlds.base import WorldCapabilities

SolverName = Literal["five_point", "nine_point"]
IntegratorName = Literal["euler", "rk4"]
BoundaryName = Literal["periodic", "reflecting"]
InitialFamily = Literal["center_square", "two_spots", "stripe", "uniform"]
Laplacian = Callable[
    [NDArray[np.float64], SolverName],
    NDArray[np.float64],
]


@dataclass(frozen=True, slots=True)
class GrayScottParameters:
    diffusion_u: float = 0.16
    diffusion_v: float = 0.08
    feed: float = 0.035
    kill: float = 0.060

    def validate(self) -> None:
        if min(self.diffusion_u, self.diffusion_v, self.feed, self.kill) < 0.0:
            raise ValueError("Gray–Scott parameters must be non-negative")


@dataclass(frozen=True, slots=True)
class ReactionLaw:
    """Finite fixed-representation variants used by Step 3 baselines."""

    reaction_power: float = 2.0
    reaction_scale: float = 1.0
    feed_scale: float = 1.0
    kill_offset: float = 0.0
    diffusion_u_scale: float = 1.0
    diffusion_v_scale: float = 1.0

    def validate(self) -> None:
        if self.reaction_power <= 0.0:
            raise ValueError("reaction power must be positive")
        if (
            min(
                self.reaction_scale,
                self.feed_scale,
                self.diffusion_u_scale,
                self.diffusion_v_scale,
            )
            < 0.0
        ):
            raise ValueError("reaction-law scales must be non-negative")


@dataclass(frozen=True, slots=True)
class LocalPulse:
    at_step: int
    center_y: int
    center_x: int
    radius: int = 2
    delta_u: float = 0.0
    delta_v: float = 0.15


@dataclass(frozen=True, slots=True)
class MeasurementSpec:
    sample_every: int = 20
    downsample: int = 1
    mixing: tuple[tuple[float, float], tuple[float, float]] = ((1.0, 0.0), (0.0, 1.0))
    visible_channels: tuple[int, ...] = (0, 1)
    noise_std: float = 0.0
    mask_fraction: float = 0.0

    def validate(self) -> None:
        if self.sample_every < 1 or self.downsample < 1:
            raise ValueError("sampling and downsampling factors must be positive")
        if not set(self.visible_channels).issubset({0, 1}) or not self.visible_channels:
            raise ValueError("visible_channels must be a non-empty subset of {0, 1}")
        if self.noise_std < 0.0 or not 0.0 <= self.mask_fraction < 1.0:
            raise ValueError("invalid noise or masking specification")
        matrix = np.asarray(self.mixing, dtype=float)
        if matrix.shape != (2, 2) or abs(np.linalg.det(matrix)) < 1e-8:
            raise ValueError("measurement mixing must be an invertible 2x2 matrix")


@dataclass(frozen=True, slots=True)
class GrayScottExperiment:
    experiment_id: str
    parameters: GrayScottParameters = field(default_factory=GrayScottParameters)
    initial_family: InitialFamily = "center_square"
    initial_seed: int = 0
    grid_size: int = 32
    steps: int = 100
    dt: float = 1.0
    spatial_spacing: float = 1.0
    clip_bounds: tuple[float, float] | None = (0.0, 1.5)
    boundary: BoundaryName = "periodic"
    solver: SolverName = "five_point"
    integrator: IntegratorName = "euler"
    intervention: LocalPulse | None = None
    measurement: MeasurementSpec = field(default_factory=MeasurementSpec)

    @property
    def family_id(self) -> str:
        p = self.parameters
        measurement_payload = json.dumps(
            asdict(self.measurement), sort_keys=True, separators=(",", ":")
        )
        measurement_id = hashlib.sha256(measurement_payload.encode()).hexdigest()[:10]
        return (
            f"f{p.feed:.5f}-k{p.kill:.5f}-{self.initial_family}-{self.boundary}-m{measurement_id}"
        )

    @property
    def content_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class GrayScottObservation:
    experiment_id: str
    experiment_hash: str
    times: NDArray[np.float64]
    fields: dict[str, NDArray[np.float64]]
    solver: SolverName
    integrator: IntegratorName
    capabilities: WorldCapabilities

    def summary(self) -> NDArray[np.float64]:
        """Fixed, anonymous representation used by initial baselines."""
        features: list[float] = []
        for name in sorted(self.fields):
            final = self.fields[name][-1]
            finite = final[np.isfinite(final)]
            if finite.size == 0:
                raise ValueError("measurement channel is fully masked")
            features.extend(
                [
                    float(np.mean(finite)),
                    float(np.std(finite)),
                    float(np.mean(finite > np.mean(finite) + np.std(finite))),
                ]
            )
            gy, gx = np.gradient(np.nan_to_num(final, nan=float(np.mean(finite))))
            features.append(float(np.mean(gx * gx + gy * gy)))
        return np.asarray(features, dtype=float)


def _laplacian_periodic(field: NDArray[np.float64], solver: SolverName) -> NDArray[np.float64]:
    north = np.roll(field, 1, axis=0)
    south = np.roll(field, -1, axis=0)
    west = np.roll(field, 1, axis=1)
    east = np.roll(field, -1, axis=1)
    if solver == "five_point":
        return north + south + west + east - 4.0 * field
    diagonals = (
        np.roll(north, 1, axis=1)
        + np.roll(north, -1, axis=1)
        + np.roll(south, 1, axis=1)
        + np.roll(south, -1, axis=1)
    )
    return (4.0 * (north + south + west + east) + diagonals - 20.0 * field) / 6.0


def _laplacian_reflecting(values: NDArray[np.float64], solver: SolverName) -> NDArray[np.float64]:
    padded = np.pad(values, 1, mode="edge")
    north = padded[:-2, 1:-1]
    south = padded[2:, 1:-1]
    west = padded[1:-1, :-2]
    east = padded[1:-1, 2:]
    if solver == "five_point":
        return north + south + west + east - 4.0 * values
    diagonals = padded[:-2, :-2] + padded[:-2, 2:] + padded[2:, :-2] + padded[2:, 2:]
    return (4.0 * (north + south + west + east) + diagonals - 20.0 * values) / 6.0


def _initial_state(
    size: int,
    family: InitialFamily,
    seed: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    rng = np.random.default_rng(seed)
    u = np.ones((size, size), dtype=float)
    v = np.zeros((size, size), dtype=float)
    center = size // 2
    width = max(2, size // 10)
    if family == "center_square":
        v[center - width : center + width, center - width : center + width] = 0.25
        u[center - width : center + width, center - width : center + width] = 0.50
    elif family == "two_spots":
        for offset in (-size // 5, size // 5):
            yy, xx = np.ogrid[:size, :size]
            mask = (yy - center) ** 2 + (xx - center - offset) ** 2 <= width**2
            v[mask] = 0.25
            u[mask] = 0.50
    elif family == "stripe":
        v[:, center - width : center + width] = 0.20
        u[:, center - width : center + width] = 0.55
    elif family != "uniform":
        raise ValueError(f"unknown initial condition family: {family}")
    if family != "uniform":
        u += rng.normal(0.0, 0.005, u.shape)
        v += rng.normal(0.0, 0.005, v.shape)
    return np.clip(u, 0.0, 1.0), np.clip(v, 0.0, 1.0)


def _apply_pulse(
    u: NDArray[np.float64],
    v: NDArray[np.float64],
    pulse: LocalPulse,
) -> None:
    yy, xx = np.ogrid[: u.shape[0], : u.shape[1]]
    mask = (yy - pulse.center_y) ** 2 + (xx - pulse.center_x) ** 2 <= pulse.radius**2
    u[mask] += pulse.delta_u
    v[mask] += pulse.delta_v
    np.clip(u, 0.0, 1.5, out=u)
    np.clip(v, 0.0, 1.5, out=v)


def _right_hand_side(
    u: NDArray[np.float64],
    v: NDArray[np.float64],
    parameters: GrayScottParameters,
    law: ReactionLaw,
    laplacian: Laplacian,
    solver: SolverName,
    spatial_spacing: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    inverse_spacing_squared = 1.0 / spatial_spacing**2
    reaction = law.reaction_scale * u * np.power(np.clip(v, 0.0, None), law.reaction_power)
    du = (
        parameters.diffusion_u
        * law.diffusion_u_scale
        * laplacian(u, solver)
        * inverse_spacing_squared
        - reaction
        + parameters.feed * law.feed_scale * (1.0 - u)
    )
    dv = (
        parameters.diffusion_v
        * law.diffusion_v_scale
        * laplacian(v, solver)
        * inverse_spacing_squared
        + reaction
        - (parameters.feed * law.feed_scale + parameters.kill + law.kill_offset) * v
    )
    return du, dv


def simulate_gray_scott(
    experiment: GrayScottExperiment,
    law: ReactionLaw | None = None,
    initial_state: tuple[NDArray[np.float64], NDArray[np.float64]] | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    GrayScottWorld.validate_static(experiment)
    law = law or ReactionLaw()
    law.validate()
    p = experiment.parameters
    if initial_state is None:
        u, v = _initial_state(
            experiment.grid_size,
            experiment.initial_family,
            experiment.initial_seed,
        )
    else:
        u = np.asarray(initial_state[0], dtype=float).copy()
        v = np.asarray(initial_state[1], dtype=float).copy()
        expected_shape = (experiment.grid_size, experiment.grid_size)
        if u.shape != expected_shape or v.shape != expected_shape:
            raise ValueError("initial state shape does not match the experiment grid")
        if not np.all(np.isfinite(u)) or not np.all(np.isfinite(v)):
            raise ValueError("initial state must be finite")
    recorded_u = [u.copy()]
    recorded_v = [v.copy()]
    times = [0.0]
    laplacian = _laplacian_periodic if experiment.boundary == "periodic" else _laplacian_reflecting
    for step in range(1, experiment.steps + 1):
        if experiment.intervention is not None and step == experiment.intervention.at_step:
            _apply_pulse(u, v, experiment.intervention)
        if experiment.integrator == "euler":
            du, dv = _right_hand_side(
                u,
                v,
                p,
                law,
                laplacian,
                experiment.solver,
                experiment.spatial_spacing,
            )
            u_next = u + experiment.dt * du
            v_next = v + experiment.dt * dv
        else:
            k1_u, k1_v = _right_hand_side(
                u,
                v,
                p,
                law,
                laplacian,
                experiment.solver,
                experiment.spatial_spacing,
            )
            k2_u, k2_v = _right_hand_side(
                u + 0.5 * experiment.dt * k1_u,
                v + 0.5 * experiment.dt * k1_v,
                p,
                law,
                laplacian,
                experiment.solver,
                experiment.spatial_spacing,
            )
            k3_u, k3_v = _right_hand_side(
                u + 0.5 * experiment.dt * k2_u,
                v + 0.5 * experiment.dt * k2_v,
                p,
                law,
                laplacian,
                experiment.solver,
                experiment.spatial_spacing,
            )
            k4_u, k4_v = _right_hand_side(
                u + experiment.dt * k3_u,
                v + experiment.dt * k3_v,
                p,
                law,
                laplacian,
                experiment.solver,
                experiment.spatial_spacing,
            )
            u_next = u + experiment.dt * (k1_u + 2.0 * k2_u + 2.0 * k3_u + k4_u) / 6.0
            v_next = v + experiment.dt * (k1_v + 2.0 * k2_v + 2.0 * k3_v + k4_v) / 6.0
        if experiment.clip_bounds is None:
            u, v = u_next, v_next
        else:
            u = np.clip(u_next, *experiment.clip_bounds)
            v = np.clip(v_next, *experiment.clip_bounds)
        if step % experiment.measurement.sample_every == 0 or step == experiment.steps:
            recorded_u.append(u.copy())
            recorded_v.append(v.copy())
            times.append(step * experiment.dt)
    return np.asarray(times), np.asarray(recorded_u), np.asarray(recorded_v)


class GrayScottWorld:
    """Online world that can execute novel conditions and local interventions."""

    def __init__(self, measurement_seed: int = 0, law: ReactionLaw | None = None) -> None:
        self.measurement_seed = measurement_seed
        self.law = law or ReactionLaw()

    def capabilities(self) -> WorldCapabilities:
        return WorldCapabilities(True, True, True, True, True)

    @staticmethod
    def validate_static(experiment: GrayScottExperiment) -> None:
        experiment.parameters.validate()
        experiment.measurement.validate()
        if (
            experiment.grid_size < 8
            or experiment.steps < 1
            or experiment.dt <= 0.0
            or experiment.spatial_spacing <= 0.0
        ):
            raise ValueError("invalid grid, step count, or timestep")
        if experiment.integrator not in ("euler", "rk4"):
            raise ValueError("unsupported time integrator")
        if experiment.clip_bounds is not None:
            lower, upper = experiment.clip_bounds
            if not np.isfinite(lower) or not np.isfinite(upper) or lower >= upper:
                raise ValueError("clip bounds must be finite and increasing")
        maximum_diffusion = max(
            experiment.parameters.diffusion_u,
            experiment.parameters.diffusion_v,
        )
        diffusion_number = experiment.dt * maximum_diffusion / experiment.spatial_spacing**2
        if diffusion_number > 0.24:
            raise ValueError("explicit diffusion step violates the conservative stability bound")
        pulse = experiment.intervention
        if pulse is not None:
            if not 1 <= pulse.at_step <= experiment.steps:
                raise ValueError("intervention step must lie inside the simulation")
            if not (0 <= pulse.center_y < experiment.grid_size):
                raise ValueError("intervention y coordinate is outside the grid")
            if not (0 <= pulse.center_x < experiment.grid_size):
                raise ValueError("intervention x coordinate is outside the grid")

    def validate_experiment(self, experiment: GrayScottExperiment) -> None:
        self.validate_static(experiment)
        self.law.validate()

    def estimate_cost(self, experiment: GrayScottExperiment) -> float:
        stencil_factor = 1.0 if experiment.solver == "five_point" else 1.6
        integrator_factor = 1.0 if experiment.integrator == "euler" else 4.0
        return integrator_factor * stencil_factor * experiment.grid_size**2 * experiment.steps

    def observe(self, experiment: GrayScottExperiment) -> GrayScottObservation:
        self.validate_experiment(experiment)
        times, u, v = simulate_gray_scott(experiment, self.law)
        measurement = experiment.measurement
        mixed = np.einsum("ij,tjxy->tixy", np.asarray(measurement.mixing), np.stack([u, v], axis=1))
        mixed = mixed[:, :, :: measurement.downsample, :: measurement.downsample]
        seed_bytes = hashlib.sha256(
            f"{self.measurement_seed}:{experiment.content_hash}".encode()
        ).digest()[:8]
        rng = np.random.default_rng(int.from_bytes(seed_bytes, "big"))
        if measurement.noise_std:
            mixed += rng.normal(0.0, measurement.noise_std, mixed.shape)
        if measurement.mask_fraction:
            mask = rng.random(mixed.shape[-2:]) < measurement.mask_fraction
            mixed[:, :, mask] = np.nan
        fields = {
            f"field_{anonymous_index}": mixed[:, source_index]
            for anonymous_index, source_index in enumerate(measurement.visible_channels)
        }
        return GrayScottObservation(
            experiment.experiment_id,
            experiment.content_hash,
            times,
            fields,
            experiment.solver,
            experiment.integrator,
            self.capabilities(),
        )

    def intervene(self, experiment: GrayScottExperiment) -> GrayScottObservation:
        if experiment.intervention is None:
            raise ValueError("intervene requires a declared intervention")
        return self.observe(experiment)

    def describe(self) -> dict[str, object]:
        return {
            "world": "gray_scott_2d",
            "measurement_seed": self.measurement_seed,
            "law": asdict(self.law),
            "capabilities": self.capabilities().to_dict(),
        }


def block_holdout(
    experiments: list[GrayScottExperiment],
    held_out_families: set[str],
) -> tuple[list[GrayScottExperiment], list[GrayScottExperiment]]:
    train = [
        experiment for experiment in experiments if experiment.family_id not in held_out_families
    ]
    test = [experiment for experiment in experiments if experiment.family_id in held_out_families]
    if not train or not test:
        raise ValueError("block holdout must produce non-empty train and test sets")
    return train, test
