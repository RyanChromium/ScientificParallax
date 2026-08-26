import numpy as np
import pytest

from scientific_parallax.baselines.gray_scott import (
    GrayScottBaselineConfig,
    baseline_question_pool,
)
from scientific_parallax.baselines.surrogate import BootstrapEnsemble, FixedFeatureRegressor


def test_fixed_regressor_fits_linear_targets() -> None:
    experiments = baseline_question_pool(GrayScottBaselineConfig())[:10]
    targets = np.asarray([[item.parameters.feed, item.parameters.kill] for item in experiments])
    model = FixedFeatureRegressor(ridge=1e-6).fit(experiments, targets)
    assert np.allclose(model.predict(experiments), targets, atol=2e-4)


def test_ensemble_exposes_member_predictions_and_variance() -> None:
    experiments = baseline_question_pool(GrayScottBaselineConfig())[:10]
    targets = np.asarray([[item.parameters.feed] for item in experiments])
    ensemble = BootstrapEnsemble(members=4, seed=3).fit(experiments, targets)
    assert ensemble.predict_members(experiments[:2]).shape == (4, 2, 1)
    assert np.all(ensemble.predictive_variance(experiments[:2]) >= 0.0)
    assert ensemble.calibration_scale >= 1.0


def test_unfitted_models_fail_loudly() -> None:
    experiments = baseline_question_pool(GrayScottBaselineConfig())[:1]
    with pytest.raises(RuntimeError):
        FixedFeatureRegressor().predict(experiments)
    with pytest.raises(RuntimeError):
        BootstrapEnsemble().predict(experiments)
