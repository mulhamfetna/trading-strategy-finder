"""Oracle + property tests for Ichimoku/pivot (calc/levels.py) and Bill-Williams (calc/bw.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np

from indicators.calc import bw as BW, levels as LV
from indicators.classic import _roll_max, _roll_min
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
O, H, L, C = D["open"], D["high"], D["low"], D["close"]


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def test_ichimoku_tenkan_independent():
    t = 9
    exp = (_roll_max(H, t) + _roll_min(L, t)) / 2.0
    tenkan, _, _, _ = LV.ichimoku_lines(H, L, t, 26, 52)
    m = ~np.isnan(exp)
    assert np.allclose(tenkan[m], exp[m], atol=1e-12)


def test_prior_session_ohlc_hand_case():
    o = np.array([1, 2, 3, 4.0]); h = np.array([10, 11, 5, 6.0])
    l = np.array([1, 2, 0, 1.0]); c = np.array([9, 8, 4, 5.0])
    sid = np.array([0, 0, 1, 1])
    pO, pH, pL, pC = LV.prior_session_ohlc(o, h, l, c, sid)
    assert np.isnan(pH[0]) and np.isnan(pH[1])          # no prior session yet
    assert pH[2] == 11 and pL[2] == 1 and pC[2] == 8 and pO[2] == 1
    assert pH[3] == 11 and pL[3] == 1 and pC[3] == 8    # constant within session 1


def test_pivot_formulas():
    pO, pH, pL, pC = LV.prior_session_ohlc(O, H, L, C, np.repeat(np.arange(15), 20))
    assert np.allclose(_fin(LV.floor_pp(pH, pL, pC)),
                       _fin((pH + pL + pC) / 3.0), atol=1e-12)
    top, bot = LV.cpr_levels(pH, pL, pC)
    m = ~np.isnan(top)
    assert np.all(top[m] >= bot[m] - 1e-9)


def test_awesome_uses_median_ewo_uses_close():
    ao = BW.awesome((H + L) / 2.0)
    ew = BW.ewo(C)
    # different inputs ⇒ generally different series
    m = ~np.isnan(ao) & ~np.isnan(ew)
    assert m.sum() > 100 and not np.allclose(ao[m], ew[m])


def test_accel_finite_after_fix():
    assert len(_fin(BW.accel((H + L) / 2.0))) > 100


def test_fractal_detects_peak():
    x = np.array([1, 2, 3, 10, 3, 2, 1.0])       # clear peak at index 3
    up, dn = BW.fractal_levels(x, x)
    # peak (center=3) is confirmed at bar 5 (center+2)
    assert up[5] == 10.0


def test_alligator_finite():
    jaw, teeth, lips = BW.alligator(H, L)
    assert len(_fin(jaw)) > 100 and len(_fin(lips)) > 100
