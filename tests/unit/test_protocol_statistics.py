import pytest

from scientific_parallax.protocol.statistics import (
    restricted_mean_time,
    stable_identification_query,
    stratified_bootstrap_effect,
)


def test_stable_identification_requires_persistence() -> None:
    assert stable_identification_query([8, 4, 7, 3, 2, 1], top_k=5, persistence=3) == 4
    assert stable_identification_query([1, 8, 1], top_k=5, persistence=2) is None


def test_restricted_mean_applies_right_censoring() -> None:
    assert restricted_mean_time([10, None, 30], budget=20) == pytest.approx(50 / 3)


def test_stratified_bootstrap_recovers_large_query_reduction() -> None:
    effect = stratified_bootstrap_effect(
        {"a": [5, 6, 7], "b": [8, 9, 10]},
        {"a": [12, 13, 14], "b": [16, 17, None]},
        budget=20,
        samples=200,
        seed=4,
    )
    assert effect.relative_query_reduction > 0.3
    assert effect.confidence_interval[0] > 0.0
