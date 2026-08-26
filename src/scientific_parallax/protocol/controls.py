"""Negative controls required before Protocol Freeze."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray


def lag_one_correlation(values: ArrayLike) -> float:
    array = np.asarray(values, dtype=float)
    if array.size < 3 or np.std(array[:-1]) == 0.0 or np.std(array[1:]) == 0.0:
        return 0.0
    return float(np.corrcoef(array[:-1], array[1:])[0, 1])


@dataclass(frozen=True, slots=True)
class ResidualShuffleResult:
    shuffled: NDArray[np.float64]
    original_lag_correlation: float
    shuffled_lag_correlation: float


def residual_shuffle_control(values: ArrayLike, seed: int) -> ResidualShuffleResult:
    original = np.asarray(values, dtype=float)
    shuffled = np.random.default_rng(seed).permutation(original)
    return ResidualShuffleResult(
        shuffled,
        lag_one_correlation(original),
        lag_one_correlation(shuffled),
    )
