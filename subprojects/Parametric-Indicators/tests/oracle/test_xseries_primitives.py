"""Tests for cross-series primitives (indicators/calc/xseries.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np

from indicators.calc import xseries as xs


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def test_rolling_corr_bounded_and_extremes():
    rng = np.random.default_rng(0)
    r = np.cumsum(rng.normal(0, 1, 400))
    c_same = r.copy()                       # identical returns ⇒ corr ≈ 1
    corr = _fin(xs.rolling_corr(c_same, r, 50))
    assert corr.min() >= -1 - 1e-9 and corr.max() <= 1 + 1e-9
    assert corr[-1] > 0.99
    c_indep = np.cumsum(rng.normal(0, 1, 400))  # independent ⇒ corr near 0
    assert abs(np.median(_fin(xs.rolling_corr(c_indep, r, 50)))) < 0.4


def test_rolling_beta_recovers_known_slope():
    rng = np.random.default_rng(1)
    r = np.cumsum(rng.normal(0, 1, 400))
    c = 2.0 * r + 5.0                        # primary returns = 2× reference returns
    beta = _fin(xs.rolling_beta(c, r, 50))
    assert np.allclose(beta, 2.0, atol=1e-6)


def test_spread_zscore_centered():
    rng = np.random.default_rng(2)
    r = np.cumsum(rng.normal(0, 1, 400))
    c = 1.5 * r + np.cumsum(rng.normal(0, 0.3, 400))
    z = _fin(xs.spread_zscore(c, r, 50))
    assert abs(z.mean()) < 1.0 and z.min() >= -6 and z.max() <= 6


def test_pca_factor_finite():
    rng = np.random.default_rng(3)
    r = np.cumsum(rng.normal(0, 1, 400))
    c = r + np.cumsum(rng.normal(0, 0.5, 400))
    assert len(_fin(xs.pca_factor(c, r, 50))) > 200


def test_reference_nan_propagates_to_nan_not_crash():
    rng = np.random.default_rng(4)
    c = np.cumsum(rng.normal(0, 1, 100))                               # non-degenerate primary
    r = np.concatenate([np.full(40, np.nan), np.cumsum(rng.normal(0, 1, 60))])  # leading ref NaN
    out = xs.rolling_corr(c, r, 20)
    assert np.isnan(out[:41]).all()          # windows touching the NaN region are NaN
    assert not np.isnan(out[70:]).all()      # once past the NaN region, finite again
