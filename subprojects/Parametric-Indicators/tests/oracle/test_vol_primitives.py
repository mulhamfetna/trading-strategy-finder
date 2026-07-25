"""Independent-oracle + property tests for volatility primitives (indicators/calc/vol.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd

from indicators import library
from indicators.base import MarketContext
from indicators.calc import vol as V
from indicators import classic
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
O, H, L, C = D["open"], D["high"], D["low"], D["close"]
CTX = MarketContext(O, H, L, C, D["volume"], np.zeros(300, int))


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def test_stddev_matches_pandas():
    n = 20
    exp = pd.Series(C).rolling(n).std(ddof=0).to_numpy()
    got = V.stddev(C, n)
    m = ~np.isnan(exp)
    assert np.allclose(got[m], exp[m], atol=1e-9)


def test_atr_norm_matches_classic():
    n = 14
    exp = classic.atr(H, L, C, n) / C
    got = V.atr_norm(H, L, C, n)
    m = ~np.isnan(exp)
    assert np.allclose(got[m], exp[m], atol=1e-12)


def test_positive_vol_estimators():
    for a in (V.parkinson(H, L, 20), V.garman_klass(O, H, L, C, 20),
              V.rogers_satchell(O, H, L, C, 20), V.yang_zhang(O, H, L, C, 20),
              V.hist_vol(C, 20), V.ulcer(C, 14)):
        f = _fin(a)
        assert len(f) > 100 and f.min() >= 0.0


def test_choppiness_and_mass_finite_positive():
    ch = _fin(V.choppiness(H, L, C, 14))
    assert ch.min() >= 0.0 and len(ch) > 100
    mi = _fin(V.mass_index(H, L, 25))
    assert mi.min() > 0.0 and len(mi) > 100


def test_ttm_squeeze_is_binary():
    sq = V.ttm_squeeze(H, L, C, 20)
    assert set(np.unique(sq).tolist()).issubset({0.0, 1.0})


def test_rvi_dorsey_bounded():
    v = _fin(V.rvi_dorsey(C, 14))
    assert v.min() >= -1e-6 and v.max() <= 100 + 1e-6


def test_magnitude_veto_fires_with_permissive_threshold():
    # threshold 1.05 ⇒ veto whenever value < 1.05·EMA(value) — should fire on many bars.
    ind = library.from_specs([{"key": "stddev", "enabled": True, "mode": "veto",
                               "params": {"n": 20, "m": 50, "threshold": 1.05}}])[0]
    _, vdir = ind.directions(CTX)
    assert (vdir != 0).sum() > 30


def test_choppiness_veto_fires_with_low_threshold():
    ind = library.from_specs([{"key": "choppiness", "enabled": True, "mode": "veto",
                               "params": {"n": 14, "threshold": 30.0}}])[0]
    _, vdir = ind.directions(CTX)
    assert (vdir != 0).sum() > 30
