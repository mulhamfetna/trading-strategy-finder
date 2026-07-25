"""Oracle + property tests for quant primitives (indicators/calc/quant.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd

from indicators.calc import quant as Q
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
H, L, C = D["high"], D["low"], D["close"]


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def test_zscore_independent():
    n = 20
    sma = pd.Series(C).rolling(n).mean().to_numpy()
    std = pd.Series(C).rolling(n).std(ddof=0).to_numpy()
    exp = (C - sma) / std
    got = Q.zscore(C, n)
    m = ~np.isnan(exp)
    assert np.allclose(got[m], exp[m], atol=1e-9)


def test_hurst_dfa_near_half_for_random_walk():
    hu = _fin(Q.hurst_exp(C, 100))
    df = _fin(Q.dfa(C, 100))
    assert 0.3 < hu.mean() < 0.8 and 0.3 < df.mean() < 0.9
    assert hu.min() >= 0.0 and df.min() >= 0.0


def test_autocorr_bounded():
    a = _fin(Q.autocorr(C, 50))
    assert a.min() >= -1 - 1e-9 and a.max() <= 1 + 1e-9


def test_demarker_bounded_unit():
    d = _fin(Q.demarker(H, L, 14))
    assert d.min() >= -1e-9 and d.max() <= 1 + 1e-9


def test_td_rei_bounded():
    r = _fin(Q.td_rei(H, L, 5))
    assert r.min() >= -100 - 1e-6 and r.max() <= 100 + 1e-6


def test_linreg_r2_bounded_and_one_on_line():
    r2 = _fin(Q.linreg_r2(C, 20))
    assert r2.min() >= -1e-9 and r2.max() <= 1 + 1e-9
    line = np.linspace(10, 50, 60)              # perfect line ⇒ R²=1
    assert np.isclose(_fin(Q.linreg_r2(line, 20))[-1], 1.0, atol=1e-9)


def test_efficiency_ratio_bounded_and_one_on_monotonic():
    er = _fin(Q.efficiency_ratio(C, 10))
    assert er.min() >= -1e-9 and er.max() <= 1 + 1e-9
    up = np.arange(1.0, 61.0)                    # strictly monotonic ⇒ ER=1
    assert np.isclose(_fin(Q.efficiency_ratio(up, 10))[-1], 1.0, atol=1e-9)
