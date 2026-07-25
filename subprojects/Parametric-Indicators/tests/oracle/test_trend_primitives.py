"""Independent-oracle + property tests for trend/directional primitives (indicators/calc/trend.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np

from indicators.calc import trend as T
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
O, H, L, C = D["open"], D["high"], D["low"], D["close"]


def _ema_ref(x, n):
    a = 2.0 / (n + 1.0)
    out = np.empty(len(x))
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1.0 - a) * out[i - 1]
    return out


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def test_ppo_apo_independent():
    ef, es = _ema_ref(C, 12), _ema_ref(C, 26)
    assert np.allclose(_fin(T.ppo(C, 12, 26)), 100.0 * (ef - es) / es, atol=1e-9)
    assert np.allclose(_fin(T.apo(C, 12, 26)), ef - es, atol=1e-9)


def test_dpo_independent():
    import pandas as pd
    n = 20
    sma = pd.Series(C).rolling(n).mean().to_numpy()
    shift = n // 2 + 1
    exp = C - np.concatenate([np.full(shift, np.nan), sma[:-shift]])
    got = T.dpo(C, n)
    m = ~np.isnan(exp) & ~np.isnan(got)
    assert m.sum() > 100 and np.allclose(got[m], exp[m], atol=1e-9)


def test_aroon_on_monotonic():
    up_series = np.arange(1.0, 101.0)          # strictly increasing
    up, dn = T.aroon(up_series, up_series, 25)
    assert np.nanmax(up) == 100.0 and np.nanmin(_fin(up)) >= 0.0
    assert _fin(up)[-1] == 100.0 and _fin(dn)[-1] == 0.0   # newest bar is the high, oldest-in-window the low


def test_di_bounded_and_directional():
    pdi, mdi = T.plus_minus_di(H, L, C, 14)
    for a in (pdi, mdi):
        f = _fin(a)
        assert f.min() >= -1e-6 and f.max() <= 100 + 1e-6
    # strong uptrend ⇒ +DI dominates
    up = np.cumsum(np.abs(np.sin(np.arange(200)))) + 100
    p2, m2 = T.plus_minus_di(up + 1, up - 1, up, 14)
    assert np.nanmean(p2[50:]) > np.nanmean(m2[50:])


def test_psar_and_supertrend_follow_uptrend():
    up = np.linspace(100, 200, 150)
    sar = T.psar(up + 1, up - 1, 0.02, 0.2)
    assert np.nanmean((up - sar)[30:] > 0) > 0.9      # SAR below price in an uptrend
    st = T.supertrend(up + 1, up - 1, up, 10, 3.0)
    assert np.nanmean(_fin(st)[30:]) > 0.5            # mostly +1


def test_qqe_and_supertrend_are_pm1():
    for a in (T.qqe(C, 14, 5, 4.236), T.supertrend(H, L, C, 10, 3.0)):
        u = np.unique(_fin(a))
        assert set(u.tolist()).issubset({-1.0, 1.0})


def test_trend_intensity_bounded():
    v = _fin(T.trend_intensity(C, 60))
    assert v.min() >= -1e-6 and v.max() <= 100 + 1e-6


def test_linreg_slope_sign_on_ramp():
    up = np.linspace(50, 150, 120)
    assert np.nanmean(T.linreg_slope(up, 14)[20:]) > 0
    down = np.linspace(150, 50, 120)
    assert np.nanmean(T.linreg_slope(down, 14)[20:]) < 0


def test_bbi_and_trix_finite():
    assert len(_fin(T.bbi(C))) > 100
    assert len(_fin(T.trix(C, 15))) > 100
    assert len(_fin(T.kst(C))) > 100
    assert len(_fin(T.coppock(C))) > 100


def test_asi_and_dma_finite():
    assert len(_fin(T.asi(O, H, L, C, 3.0))) > 100
    ddd, ama = T.dma(C, 10, 50, 10)
    assert len(_fin(ddd)) > 100 and len(_fin(ama)) > 100


def test_chandelier_stops_bracket_swing():
    from indicators.classic import _roll_max, _roll_min
    n = 22
    ls, ss = T.chandelier(H, L, C, n, 3.0)
    hh, ll = _roll_max(H, n), _roll_min(L, n)
    m = ~np.isnan(ls)
    # long stop = HHn − m·ATR < HHn ; short stop = LLn + m·ATR > LLn  (ATR>0)
    assert np.all(ls[m] < hh[m] + 1e-9) and np.all(ss[m] > ll[m] - 1e-9)
    assert m.sum() > 100
