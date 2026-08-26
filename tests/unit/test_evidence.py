import pytest

from scientific_parallax.step0.domain import Observation, Prediction
from scientific_parallax.step0.evidence import EvidenceEngine, entropy


def test_likelihood_update_favors_matching_candidate() -> None:
    engine = EvidenceEngine(["near", "far"])
    posterior = engine.update(
        {
            "near": Prediction("near", 1.0, 0.1),
            "far": Prediction("far", 2.0, 0.1),
        },
        Observation("q", 1.02, 0.1),
    )
    assert posterior["near"] > 0.999
    assert posterior["far"] < 0.001


def test_update_rejects_incomplete_prediction_pool() -> None:
    engine = EvidenceEngine(["a", "b"])
    with pytest.raises(ValueError, match="exactly match"):
        engine.update({"a": Prediction("a", 0.0, 1.0)}, Observation("q", 0.0, 1.0))


def test_entropy_ignores_zero_probability() -> None:
    assert entropy({"certain": 1.0, "impossible": 0.0}) == 0.0
