"""TDD — the two-phase structure generator (assembles SMC detectors + a generation report)."""
import numpy as np

from indicators import generate, smc
from indicators.base import MarketContext


def _ctx():
    o = np.array([10, 11, 10.5, 9.5, 11.5, 12.5, 10.2, 13.0, 12.0, 14.0], dtype=float)
    h = np.array([10.5, 11.2, 10.8, 9.8, 13.0, 13.0, 10.6, 13.5, 12.5, 14.5], dtype=float)
    l = np.array([9.0, 10.0, 9.2, 8.8, 11.0, 12.0, 9.0, 12.5, 11.5, 13.5], dtype=float)
    c = np.array([10.2, 11.0, 9.3, 9.6, 12.8, 12.7, 9.4, 13.2, 11.8, 14.2], dtype=float)
    return MarketContext(open=o, high=h, low=l, close=c, volume=np.full(10, 100.0))


def test_generate_returns_structures_and_report():
    ctx = _ctx()
    out = generate.generate_structures(ctx, swing_l=1, golf_n=2)
    s = out["structures"]
    for key in ("bull_fvg", "bear_fvg", "swing_high", "swing_low", "structure_trend",
                "order_block", "golf"):
        assert key in s and len(s[key]) == len(ctx)


def test_report_counts_match_detectors():
    ctx = _ctx()
    out = generate.generate_structures(ctx, swing_l=1, golf_n=2)
    rep = out["report"]
    bull, bear, _, _ = smc.fvg(ctx.high, ctx.low)
    sh, sl = smc.market_structure(ctx.close, 1)
    assert rep["bars"] == len(ctx)
    assert rep["n_bull_fvg"] == int(bull.sum())
    assert rep["n_bear_fvg"] == int(bear.sum())
    assert rep["n_swing_high"] == int(sh.sum())
    assert rep["n_swing_low"] == int(sl.sum())
    assert rep["params"] == {"swing_l": 1, "golf_n": 2}


def test_generation_is_deterministic():
    ctx = _ctx()
    a = generate.generate_structures(ctx, swing_l=1, golf_n=2)["report"]
    b = generate.generate_structures(ctx, swing_l=1, golf_n=2)["report"]
    assert a == b
