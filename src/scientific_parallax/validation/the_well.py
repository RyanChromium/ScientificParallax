"""Offline numerical validation against a pinned The Well Gray–Scott shard."""

from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import numpy as np

from scientific_parallax.worlds.gray_scott import (
    GrayScottExperiment,
    GrayScottParameters,
    MeasurementSpec,
    simulate_gray_scott,
)

MINIMUM_REFERENCE_RMSE_IMPROVEMENT = 0.25
MAXIMUM_REFERENCE_FIELD_RMSE = 0.02
MAXIMUM_REFERENCE_WORST_TRAJECTORY_RMSE = 0.04


@dataclass(frozen=True, slots=True)
class MethodError:
    field_mean_absolute: float
    field_rmse: float
    worst_trajectory_mean_absolute: float
    worst_trajectory_rmse: float


@dataclass(frozen=True, slots=True)
class TheWellValidation:
    dataset_name: str
    feed: float
    kill: float
    trajectories: int
    source_interval: float
    primary: MethodError
    reference: MethodError
    reference_improvement: float
    minimum_reference_improvement: float
    maximum_reference_field_rmse: float
    maximum_reference_worst_trajectory_rmse: float
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TheWellFixture:
    fields: np.ndarray
    time: np.ndarray
    x: np.ndarray
    y: np.ndarray
    metadata: dict[str, Any]


def load_the_well_fixture(path: Path) -> TheWellFixture:
    with zipfile.ZipFile(path) as archive:
        metadata = json.loads(archive.read("metadata.json"))
    with np.load(path, allow_pickle=False) as arrays:
        fields = np.asarray(arrays["fields"])
        time = np.asarray(arrays["time"])
        x = np.asarray(arrays["x"])
        y = np.asarray(arrays["y"])
    if metadata.get("schema_version") != 1 or metadata.get("license") != "CC-BY-4.0":
        raise ValueError("The Well fixture metadata is invalid")
    if fields.shape != (2, 2, 32, 32) or time.shape != (2,):
        raise ValueError("The Well fixture has an unexpected field or time shape")
    if x.shape != (32,) or y.shape != (32,) or not np.all(np.isfinite(fields)):
        raise ValueError("The Well fixture coordinates or fields are invalid")
    return TheWellFixture(fields, time, x, y, metadata)


def _summarize(errors: list[tuple[float, float]]) -> MethodError:
    values = np.asarray(errors)
    return MethodError(
        field_mean_absolute=float(np.mean(values[:, 0])),
        field_rmse=float(np.mean(values[:, 1])),
        worst_trajectory_mean_absolute=float(np.max(values[:, 0])),
        worst_trajectory_rmse=float(np.max(values[:, 1])),
    )


def validate_the_well_shard(path: Path, trajectories: int = 20) -> TheWellValidation:
    try:
        import h5py
    except ImportError as error:  # pragma: no cover - depends on optional environment
        raise RuntimeError("The Well validation requires the external-data extra") from error

    with h5py.File(path, "r") as source:
        dataset_name = str(source.attrs["dataset_name"])
        if dataset_name != "gray_scott_reaction_diffusion":
            raise ValueError("external shard is not The Well Gray–Scott data")
        if str(source.attrs["grid_type"]) != "cartesian":
            raise ValueError("external shard must use a Cartesian grid")
        available = int(source.attrs["n_trajectories"])
        if not 1 <= trajectories <= available:
            raise ValueError("requested trajectory count is outside the shard")
        fields = set(source["t0_fields"].attrs["field_names"].astype(str))
        if fields != {"A", "B"}:
            raise ValueError("external shard does not expose the expected A/B fields")
        time = np.asarray(source["dimensions/time"], dtype=float)
        x = np.asarray(source["dimensions/x"], dtype=float)
        y = np.asarray(source["dimensions/y"], dtype=float)
        if time.size < 2 or x.size != y.size or x.size < 8:
            raise ValueError("external shard dimensions are incomplete")
        if not np.allclose(x, y) or not np.allclose(np.diff(x), np.diff(x)[0]):
            raise ValueError("external shard must use one uniform square grid")
        if set(source["boundary_conditions"]) != {"x_periodic", "y_periodic"}:
            raise ValueError("external shard must declare periodic boundaries")
        interval = float(time[1] - time[0])
        if interval <= 0.0 or not np.isclose(interval, round(interval)):
            raise ValueError("external shard time coordinate is not increasing")
        feed = float(source["scalars/F"][()])
        kill = float(source["scalars/k"][()])
        grid_size = int(x.size)
        # The generator uses a periodic Fourier grid with N samples over its declared
        # [-1, 1] domain; the stored coordinate labels include both displayed endpoints.
        spatial_spacing = float((x[-1] - x[0]) / grid_size)
        steps = max(1, int(round(interval)))
        experiment = GrayScottExperiment(
            "the-well-one-interval",
            parameters=GrayScottParameters(2e-5, 1e-5, feed, kill),
            initial_family="uniform",
            grid_size=grid_size,
            steps=steps,
            dt=interval / steps,
            spatial_spacing=spatial_spacing,
            clip_bounds=None,
            boundary="periodic",
            measurement=MeasurementSpec(sample_every=steps),
        )
        method_errors: dict[str, list[tuple[float, float]]] = {
            "primary": [],
            "reference": [],
        }
        methods = {
            "primary": ("five_point", "euler"),
            "reference": ("nine_point", "rk4"),
        }
        for trajectory in range(trajectories):
            initial = (
                np.asarray(source["t0_fields/A"][trajectory, 0], dtype=float),
                np.asarray(source["t0_fields/B"][trajectory, 0], dtype=float),
            )
            target = np.stack(
                (
                    np.asarray(source["t0_fields/A"][trajectory, 1], dtype=float),
                    np.asarray(source["t0_fields/B"][trajectory, 1], dtype=float),
                )
            )
            for method_name, (solver, integrator) in methods.items():
                _, predicted_a, predicted_b = simulate_gray_scott(
                    replace(experiment, solver=solver, integrator=integrator),
                    initial_state=initial,
                )
                difference = np.abs(np.stack((predicted_a[-1], predicted_b[-1])) - target)
                method_errors[method_name].append(
                    (float(np.mean(difference)), float(np.sqrt(np.mean(difference**2))))
                )

    primary = _summarize(method_errors["primary"])
    reference = _summarize(method_errors["reference"])
    improvement = 1.0 - reference.field_rmse / primary.field_rmse
    passed = (
        np.isfinite(improvement)
        and improvement >= MINIMUM_REFERENCE_RMSE_IMPROVEMENT
        and reference.field_mean_absolute < primary.field_mean_absolute
        and reference.field_rmse <= MAXIMUM_REFERENCE_FIELD_RMSE
        and reference.worst_trajectory_rmse
        <= MAXIMUM_REFERENCE_WORST_TRAJECTORY_RMSE
    )
    return TheWellValidation(
        dataset_name,
        feed,
        kill,
        trajectories,
        interval,
        primary,
        reference,
        float(improvement),
        MINIMUM_REFERENCE_RMSE_IMPROVEMENT,
        MAXIMUM_REFERENCE_FIELD_RMSE,
        MAXIMUM_REFERENCE_WORST_TRAJECTORY_RMSE,
        bool(passed),
    )
