"""Fixed-representation prediction and experiment-selection baselines."""

from scientific_parallax.baselines.gray_scott import GrayScottBaselineConfig
from scientific_parallax.baselines.surrogate import BootstrapEnsemble, FixedFeatureRegressor

__all__ = ["BootstrapEnsemble", "FixedFeatureRegressor", "GrayScottBaselineConfig"]
