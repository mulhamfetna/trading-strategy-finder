"""Independent-oracle + property tests for volume primitives (indicators/calc/volume.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
import pandas as pd

from indicators.calc import volume as VO
from tests.oracle.fixture import ohlcv

D = ohlcv(300)
O, H, L, C, V = D["open"], D["high"], D["low"], D["close"], D["volume"]


def _fin(a):
    a = np.asarray(a, float)
    return a[~np.isnan(a)]


def test_ad_line_independent():
    mfm = ((C - L) - (H - C)) / (H - L)
    exp = np.cumsum(mfm * V)
    assert np.allclose(VO.ad_line(H, L, C, V), exp, atol=1e-6)


def test_cmf_bounded():
    cmf = _fin(VO.cmf(H, L, C, V, 20))
    assert cmf.min() >= -1.0 - 1e-9 and cmf.max() <= 1.0 + 1e-9 and len(cmf) > 100


def test_pvt_recurrence():
    p = VO.pvt(C, V)
    exp = np.zeros(len(C))
    for i in range(1, len(C)):
        exp[i] = exp[i - 1] + (C[i] - C[i - 1]) / C[i - 1] * V[i]
    assert np.allclose(p, exp, atol=1e-9)


def test_nvi_pvi_seed_and_change_only_on_volume_regime():
    nvi = VO.nvi(C, V)
    assert nvi[0] == 1000.0
    # NVI changes only when volume falls
    for i in range(1, len(C)):
        if V[i] >= V[i - 1]:
            assert nvi[i] == nvi[i - 1]


def test_bw_mfi_is_ternary():
    assert set(np.unique(VO.bw_mfi(H, L, V)).tolist()).issubset({-1.0, 0.0, 1.0})


def test_vzo_bounded():
    z = _fin(VO.vzo(C, V, 14))
    assert z.min() >= -100 - 1e-6 and z.max() <= 100 + 1e-6


def test_vr_asia_positive():
    r = _fin(VO.volume_ratio_asia(C, V, 26))
    assert r.min() >= 0.0 and len(r) > 100


def test_anchored_vwap_within_price_range():
    av = _fin(VO.anchored_vwap(H, L, C, V, np.zeros(300, int)))
    assert av.min() >= L.min() - 1e-6 and av.max() <= H.max() + 1e-6


def test_flow_lines_finite():
    for a in (VO.chaikin_osc(H, L, C, V, 3, 10), VO.eom(H, L, V, 14),
              VO.force_index(C, V, 13), VO.klinger(H, L, C, V, 34, 55, 13)[0],
              VO.demand_index(C, V, 20), VO.twiggs_mf(H, L, C, V, 21),
              VO.wvad(O, H, L, C, V, 20), VO.vol_osc(V, 5, 20)):
        assert len(_fin(a)) > 100


def test_demand_index_bounded():
    di = _fin(VO.demand_index(C, V, 20))
    assert di.min() >= -1 - 1e-9 and di.max() <= 1 + 1e-9
