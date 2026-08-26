"""Small fixed-feature regressors used as honest Step 3 baselines."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from scientific_parallax.worlds.gray_scott import GrayScottExperiment


def experiment_features(experiment: GrayScottExperiment) -> NDArray[np.float64]:
    """A frozen representation with no access to observed fields or hidden labels."""
    p = experiment.parameters
    pulse = experiment.intervention
    family_names = ("center_square", "two_spots", "stripe", "uniform")
    family = [float(experiment.initial_family == name) for name in family_names]
    pulse_features = [0.0, 0.0, 0.0] if pulse is None else [1.0, pulse.delta_u, pulse.delta_v]
    return np.asarray(
        [
            1.0,
            p.feed / 0.05,
            p.kill / 0.06,
            (p.feed / 0.05) ** 2,
            (p.kill / 0.06) ** 2,
            (p.feed / 0.05) * (p.kill / 0.06),
            p.diffusion_u / 0.16,
            p.diffusion_v / 0.08,
            float(experiment.boundary == "reflecting"),
            *family,
            *pulse_features,
        ],
        dtype=float,
    )


@dataclass(slots=True)
class FixedFeatureRegressor:
    ridge: float = 1.0
    coefficients: NDArray[np.float64] | None = None

    def fit(
        self,
        experiments: list[GrayScottExperiment],
        targets: NDArray[np.float64],
    ) -> FixedFeatureRegressor:
        if len(experiments) != len(targets) or not experiments:
            raise ValueError("experiments and targets must have equal non-zero length")
        design = np.stack([experiment_features(item) for item in experiments])
        regularizer = self.ridge * np.eye(design.shape[1])
        regularizer[0, 0] = 0.0
        self.coefficients = np.linalg.solve(design.T @ design + regularizer, design.T @ targets)
        return self

    def predict(self, experiments: list[GrayScottExperiment]) -> NDArray[np.float64]:
        if self.coefficients is None:
            raise RuntimeError("regressor must be fitted before prediction")
        design = np.stack([experiment_features(item) for item in experiments])
        return design @ self.coefficients


class BootstrapEnsemble:
    def __init__(self, members: int = 8, ridge: float = 1.0, seed: int = 0) -> None:
        if members < 2:
            raise ValueError("an ensemble requires at least two members")
        self.members = members
        self.ridge = ridge
        self.seed = seed
        self.models: list[FixedFeatureRegressor] = []
        self.calibration_scale = 1.0

    def fit(
        self,
        experiments: list[GrayScottExperiment],
        targets: NDArray[np.float64],
    ) -> BootstrapEnsemble:
        if len(experiments) != len(targets) or not experiments:
            raise ValueError("experiments and targets must have equal non-zero length")
        rng = np.random.default_rng(self.seed)
        self.models = []
        out_of_bag: list[list[NDArray[np.float64]]] = [[] for _ in experiments]
        for _ in range(self.members):
            indices = rng.integers(0, len(experiments), len(experiments))
            sampled_experiments = [experiments[int(index)] for index in indices]
            sampled_targets = targets[indices]
            model = FixedFeatureRegressor(self.ridge).fit(sampled_experiments, sampled_targets)
            self.models.append(model)
            in_bag = set(int(index) for index in indices)
            predictions = model.predict(experiments)
            for index, prediction in enumerate(predictions):
                if index not in in_bag:
                    out_of_bag[index].append(prediction)
        squared_errors: list[float] = []
        predicted_variances: list[float] = []
        for target, predictions in zip(targets, out_of_bag, strict=True):
            if len(predictions) < 2:
                continue
            array = np.stack(predictions)
            squared_errors.extend(np.square(np.mean(array, axis=0) - target).tolist())
            predicted_variances.extend(np.var(array, axis=0).tolist())
        total_variance = sum(predicted_variances)
        if squared_errors and total_variance > 1e-15:
            self.calibration_scale = max(1.0, float(np.sqrt(sum(squared_errors) / total_variance)))
        return self

    def predict_members(self, experiments: list[GrayScottExperiment]) -> NDArray[np.float64]:
        if not self.models:
            raise RuntimeError("ensemble must be fitted before prediction")
        return np.stack([model.predict(experiments) for model in self.models])

    def predict(self, experiments: list[GrayScottExperiment]) -> NDArray[np.float64]:
        return np.mean(self.predict_members(experiments), axis=0)

    def predictive_variance(self, experiments: list[GrayScottExperiment]) -> NDArray[np.float64]:
        return np.var(self.predict_members(experiments), axis=0) * self.calibration_scale**2
