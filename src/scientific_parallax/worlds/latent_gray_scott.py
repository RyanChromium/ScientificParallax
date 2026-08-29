"""Three-state Gray–Scott variant with an unobserved dynamical catalyst."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

import numpy as np
from numpy.typing import NDArray

from scientific_parallax.worlds.gray_scott import (
    BoundaryName,
    InitialFamily,
    MeasurementSpec,
    _initial_state,
    _laplacian_periodic,
    _laplacian_reflecting,
)


@dataclass(frozen=True, slots=True)
class LatentLaw:
    """Executable candidate law; connectivity records representational structure."""

    has_latent_state: bool = True
    observed_drive_connected: bool = True
    reaction_feedback_connected: bool = True
    reaction_scale: float = 1.0
    latent_diffusion: float = 0.035
    latent_drive: float = 0.08
    latent_decay: float = 0.04
    latent_feedback: float = 2.5

    def validate(self) -> None:
        values = (
            self.reaction_scale,
            self.latent_diffusion,
            self.latent_drive,
            self.latent_decay,
            self.latent_feedback,
        )
        if not all(np.isfinite(value) and value >= 0.0 for value in values):
            raise ValueError("latent-law coefficients must be finite and non-negative")
        if not self.has_latent_state and (
            self.observed_drive_connected or self.reaction_feedback_connected
        ):
            raise ValueError("latent connections require a latent state")
        if self.reaction_feedback_connected and not self.observed_drive_connected:
            raise ValueError("feedback requires an observed-to-latent drive")

    @property
    def structural_stage(self) -> int:
        return sum(
            (
                self.has_latent_state,
                self.observed_drive_connected,
                self.reaction_feedback_connected,
            )
        )

    @property
    def complete_latent_structure(self) -> bool:
        return self.structural_stage == 3


@dataclass(frozen=True, slots=True)
class LatentPulse:
    at_step: int
    center_y: int
    center_x: int
    radius: int = 2
    delta_v: float = 0.15


@dataclass(frozen=True, slots=True)
class LatentGrayScottExperiment:
    experiment_id: str
    feed: float = 0.035
    kill: float = 0.060
    initial_family: InitialFamily = "center_square"
    initial_seed: int = 0
    grid_size: int = 16
    steps: int = 40
    sample_every: int = 20
    boundary: BoundaryName = "periodic"
    pulses: tuple[LatentPulse, ...] = ()
    measurement: MeasurementSpec = field(default_factory=lambda: MeasurementSpec(sample_every=20))

    @property
    def content_hash(self) -> str:
        payload = asdict(self)
        payload.pop("experiment_id")
        payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class LatentObservation:
    experiment_hash: str
    times: NDArray[np.float64]
    fields: dict[str, NDArray[np.float64]]

    def summary(self) -> NDArray[np.float64]:
        features: list[float] = []
        for name in sorted(self.fields):
            for frame in self.fields[name]:
                finite = frame[np.isfinite(frame)]
                if finite.size == 0:
                    raise ValueError("latent-world measurement frame is fully masked")
                mean = float(np.mean(finite))
                standard_deviation = float(np.std(finite))
                filled = np.nan_to_num(frame, nan=mean)
                gy, gx = np.gradient(filled)
                features.extend(
                    (
                        mean,
                        standard_deviation,
                        float(np.mean(finite > mean + standard_deviation)),
                        float(np.mean(gx * gx + gy * gy)),
                    )
                )
        return np.asarray(features, dtype=float)


class LatentGrayScottWorld:
    """World exposes only two anonymous fields; the catalyst is never measured."""

    def __init__(self, measurement_seed: int = 0, law: LatentLaw | None = None) -> None:
        self.measurement_seed = measurement_seed
        self.law = law or LatentLaw()
        self.law.validate()

    @staticmethod
    def validate_experiment(experiment: LatentGrayScottExperiment) -> None:
        experiment.measurement.validate()
        if experiment.grid_size < 8 or experiment.steps < 2:
            raise ValueError("latent-world grid and duration are too small")
        if experiment.sample_every < 1 or experiment.sample_every > experiment.steps:
            raise ValueError("invalid latent-world sampling interval")
        if min(experiment.feed, experiment.kill) < 0.0:
            raise ValueError("feed and kill must be non-negative")
        pulse_steps = [pulse.at_step for pulse in experiment.pulses]
        if len(pulse_steps) != len(set(pulse_steps)):
            raise ValueError("latent-world pulse times must be unique")
        for pulse in experiment.pulses:
            if not 1 <= pulse.at_step <= experiment.steps:
                raise ValueError("pulse time lies outside the experiment")
            if not 0 <= pulse.center_y < experiment.grid_size:
                raise ValueError("pulse y coordinate lies outside the grid")
            if not 0 <= pulse.center_x < experiment.grid_size:
                raise ValueError("pulse x coordinate lies outside the grid")

    @staticmethod
    def estimate_cost(experiment: LatentGrayScottExperiment) -> int:
        return experiment.grid_size**2 * experiment.steps

    def observe(self, experiment: LatentGrayScottExperiment) -> LatentObservation:
        self.validate_experiment(experiment)
        times, visible = simulate_latent_gray_scott(experiment, self.law)
        measurement = experiment.measurement
        mixed = np.einsum("ij,tjxy->tixy", np.asarray(measurement.mixing), visible)
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
        return LatentObservation(experiment.content_hash, times, fields)


def simulate_latent_gray_scott(
    experiment: LatentGrayScottExperiment,
    law: LatentLaw,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return sample times and the two visible fields; latent state stays internal."""

    LatentGrayScottWorld.validate_experiment(experiment)
    law.validate()
    u, v = _initial_state(
        experiment.grid_size,
        experiment.initial_family,
        experiment.initial_seed,
    )
    z = np.zeros_like(u)
    laplacian = _laplacian_periodic if experiment.boundary == "periodic" else _laplacian_reflecting
    pulse_by_step = {pulse.at_step: pulse for pulse in experiment.pulses}
    samples: list[NDArray[np.float64]] = []
    times: list[float] = []
    for step in range(1, experiment.steps + 1):
        if pulse := pulse_by_step.get(step):
            _apply_visible_pulse(v, pulse)
        catalyst = 1.0
        if law.reaction_feedback_connected:
            catalyst = 1.0 + law.latent_feedback * z
        reaction = law.reaction_scale * catalyst * u * v * v
        du = 0.16 * laplacian(u, "five_point") - reaction + experiment.feed * (1.0 - u)
        dv = 0.08 * laplacian(v, "five_point") + reaction - (experiment.feed + experiment.kill) * v
        if law.has_latent_state:
            drive = law.latent_drive * v if law.observed_drive_connected else 0.0
            dz = law.latent_diffusion * laplacian(z, "five_point") + drive - law.latent_decay * z
        else:
            dz = 0.0
        u = np.clip(u + du, 0.0, 1.5)
        v = np.clip(v + dv, 0.0, 1.5)
        z = np.clip(z + dz, 0.0, 1.5)
        if step % experiment.sample_every == 0 or step == experiment.steps:
            samples.append(np.stack((u.copy(), v.copy())))
            times.append(float(step))
    return np.asarray(times), np.stack(samples)


def _apply_visible_pulse(v: NDArray[np.float64], pulse: LatentPulse) -> None:
    yy, xx = np.ogrid[: v.shape[0], : v.shape[1]]
    mask = (yy - pulse.center_y) ** 2 + (xx - pulse.center_x) ** 2 <= pulse.radius**2
    v[mask] += pulse.delta_v
    np.clip(v, 0.0, 1.5, out=v)
