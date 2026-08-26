"""Pre-freeze endpoint and stratified uncertainty calculations."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def stable_identification_query(
    ranks: list[int],
    *,
    top_k: int,
    persistence: int,
) -> int | None:
    if top_k < 1 or persistence < 1:
        raise ValueError("top_k and persistence must be positive")
    for index in range(len(ranks) - persistence + 1):
        if all(rank <= top_k for rank in ranks[index : index + persistence]):
            return index + 1
    return None


def restricted_mean_time(values: list[int | None], budget: int) -> float:
    if budget < 1 or not values:
        raise ValueError("budget and observations must be positive")
    return float(np.mean([budget if value is None else min(value, budget) for value in values]))


@dataclass(frozen=True, slots=True)
class BootstrapEffect:
    relative_query_reduction: float
    confidence_interval: tuple[float, float]
    samples: int


def stratified_bootstrap_effect(
    treatment_by_stratum: dict[str, list[int | None]],
    control_by_stratum: dict[str, list[int | None]],
    *,
    budget: int,
    samples: int = 2000,
    seed: int = 0,
) -> BootstrapEffect:
    if set(treatment_by_stratum) != set(control_by_stratum) or not treatment_by_stratum:
        raise ValueError("treatment and control strata must match and be non-empty")
    strata = sorted(treatment_by_stratum)

    def effect(selected_strata: list[str], rng: np.random.Generator | None) -> float:
        treatment: list[int | None] = []
        control: list[int | None] = []
        for stratum in selected_strata:
            t_values = treatment_by_stratum[stratum]
            c_values = control_by_stratum[stratum]
            if not t_values or not c_values:
                raise ValueError("each stratum requires treatment and control observations")
            if rng is None:
                treatment.extend(t_values)
                control.extend(c_values)
            else:
                treatment.extend(rng.choice(t_values, len(t_values), replace=True).tolist())
                control.extend(rng.choice(c_values, len(c_values), replace=True).tolist())
        treatment_mean = restricted_mean_time(treatment, budget)
        control_mean = restricted_mean_time(control, budget)
        return (control_mean - treatment_mean) / control_mean

    point = effect(strata, None)
    rng = np.random.default_rng(seed)
    bootstrap = []
    for _ in range(samples):
        sampled_strata = rng.choice(strata, len(strata), replace=True).tolist()
        bootstrap.append(effect(sampled_strata, rng))
    lower, upper = np.quantile(bootstrap, [0.025, 0.975])
    return BootstrapEffect(point, (float(lower), float(upper)), samples)
