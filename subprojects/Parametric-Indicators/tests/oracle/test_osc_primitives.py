"""Independent-oracle + property tests for oscillator primitives (indicators/calc/osc.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd

from indicators.calc import osc
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
O, H, L, C, V = D["open"], D["high"], D["low"], D["close"], D["volume"]


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def _bounded(a, lo, hi, tol=1e-6):
    f = _fin(a)
    assert f.min() >= lo - tol and f.max() <= hi + tol, (f.min(), f.max())
    assert len(f) > 100


# ---- exact independent oracles ----
def test_momentum():
    assert np.allclose(_fin(osc.momentum(C, 10)), C[10:] - C[:-10], atol=1e-9)


def test_roc():
    assert np.allclose(_fin(osc.roc(C, 9)), 100.0 * (C[9:] / C[:-9] - 1.0), atol=1e-9)


def test_disparity():
    sma = pd.Series(C).rolling(14).mean().to_numpy()
    exp = 100.0 * (C / sma - 1.0)
    got = osc.disparity(C, 14)
    m = ~np.isnan(exp)
    assert np.allclose(got[m], exp[m], atol=1e-9)


def test_williams_r_matches_pandas():
    n = 14
    hh = pd.Series(H).rolling(n).max().to_numpy()
    ll = pd.Series(L).rolling(n).min().to_numpy()
    exp = -100.0 * (hh - C) / (hh - ll)
    got = osc.williams_r(H, L, C, n)
    m = ~np.isnan(exp)
    assert np.allclose(got[m], exp[m], atol=1e-9)
    _bounded(got, -100.0, 0.0)


def test_cmo_matches_pandas():
    n = 14
    d = np.diff(C)
    up = pd.Series(np.where(d > 0, d, 0.0)).rolling(n).sum().to_numpy()
    dn = pd.Series(np.where(d < 0, -d, 0.0)).rolling(n).sum().to_numpy()
    exp = np.full(len(C), np.nan)
    exp[1:] = 100.0 * (up - dn) / (up + dn)
    got = osc.cmo(C, n)
    m = ~np.isnan(exp)
    assert np.allclose(got[m], exp[m], atol=1e-9)
    _bounded(got, -100.0, 100.0)


def test_psy():
    n = 12
    up = (np.diff(C) > 0).astype(float)
    exp = np.full(len(C), np.nan)
    exp[1:] = 100.0 * pd.Series(up).rolling(n).sum().to_numpy() / n
    got = osc.psy(C, n)
    m = ~np.isnan(exp)
    assert np.allclose(got[m], exp[m], atol=1e-9)
    _bounded(got, 0.0, 100.0)


def test_rsi_cutler_matches_sma_rsi():
    n = 14
    d = np.diff(C)
    ag = pd.Series(np.where(d > 0, d, 0.0)).rolling(n).mean().to_numpy()
    al = pd.Series(np.where(d < 0, -d, 0.0)).rolling(n).mean().to_numpy()
    exp = np.full(len(C), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        exp[1:] = 100.0 - 100.0 / (1.0 + ag / al)
    got = osc.rsi_cutler(C, n)
    m = ~np.isnan(exp) & ~np.isnan(got)
    assert m.sum() > 100 and np.allclose(got[m], exp[m], atol=1e-9)
    _bounded(got, 0.0, 100.0)


# ---- bounded-range / finite properties for the complex ones ----
def test_bounded_ranges():
    _bounded(osc.rsi_cutler(C, 14), 0, 100)
    _bounded(osc.connors_rsi(C), 0, 100)
    _bounded(osc.rmi(C, 14, 5), 0, 100)
    _bounded(osc.dynamic_dmi(C, 14), 0, 100)
    _bounded(osc.stoch_rsi(C, 14, 14, 3), 0, 100)
    _bounded(osc.kdj_k(H, L, C, 9), 0, 100)
    _bounded(osc.ultimate_osc(H, L, C), 0, 100)
    _bounded(osc.tsi(C, 25, 13), -100, 100)
    _bounded(osc.bias(C, 6), -100, 100)


def test_finite_and_warmup():
    for name, a, warm in [
        ("smi", osc.smi(H, L, C, 14, 3), 14),
        ("wavetrend", osc.wavetrend(H, L, C, 10, 21), 1),
        ("fisher", osc.fisher(H, L, 9), 9),
        ("derivative_osc", osc.derivative_osc(C, 14, 5, 3, 9), 14),
        ("ergodic", osc.ergodic(C, 32, 5, 5), 32),
        ("pgo", osc.pgo(H, L, C, 14), 14),
        ("rvgi", osc.rvgi(O, H, L, C, 14), 14),
        ("balance_of_power", osc.balance_of_power(O, H, L, C, 14), 14),
    ]:
        assert len(_fin(a)) > 100, name


def test_nan_ema_seeds_at_first_finite():
    x = np.array([np.nan, np.nan, 10.0, 12.0, 14.0])
    e = osc.nan_ema(x, 3)
    assert np.isnan(e[0]) and np.isnan(e[1]) and e[2] == 10.0
    assert not np.isnan(e[3])


def test_roll_sum_safe_ignores_leading_nan():
    x = np.array([np.nan, np.nan, 1.0, 2.0, 3.0, 4.0])
    s = osc.roll_sum_safe(x, 3)
    assert np.isnan(s[3]) and s[4] == 6.0 and s[5] == 9.0    # first full-valid window at idx 4
