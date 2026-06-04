"""TDD — SMC structure detectors (FVG, market structure, golf candle). Causal, crafted series."""
import numpy as np

from indicators import smc


def test_fvg_bullish_detection_and_zone():
    high = np.array([10, 12, 14, 13, 15], dtype=float)
    low = np.array([9, 11, 13, 12, 14], dtype=float)
    bull, bear, zlo, zhi = smc.fvg(high, low)
    # t2: low2=13 > high0=10 -> bullish, zone [10,13]; no other gaps
    np.testing.assert_array_equal(bull, [False, False, True, False, False])
    np.testing.assert_array_equal(bear, [False, False, False, False, False])
    assert zlo[2] == 10 and zhi[2] == 13


def test_fvg_bearish_detection_and_zone():
    high = np.array([20, 18, 16, 17, 15], dtype=float)
    low = np.array([19, 17, 15, 16, 14], dtype=float)
    bull, bear, zlo, zhi = smc.fvg(high, low)
    # t2: high2=16 < low0=19 -> bearish, zone [high2=16, low0=19]
    np.testing.assert_array_equal(bear, [False, False, True, False, False])
    np.testing.assert_array_equal(bull, [False, False, False, False, False])
    assert zlo[2] == 16 and zhi[2] == 19


def test_market_structure_swings_l1():
    close = np.array([1, 3, 2, 5, 4, 6, 1], dtype=float)
    sh, sl = smc.market_structure(close, swing_l=1)
    np.testing.assert_array_equal(sh, [False, True, False, True, False, True, False])
    np.testing.assert_array_equal(sl, [False, False, True, False, True, False, False])


def test_structure_trend_uptrend_then_downtrend():
    # rising HH/HL then falling LH/LL; L=1 swings
    close = np.array([10, 12, 11, 14, 13, 16, 15,   12, 13, 9, 10, 6], dtype=float)
    st = smc.structure_trend(close, swing_l=1)
    assert st[6] == 1            # by bar 6 we have HH (12<14<16) + HL (11<13<15) -> uptrend
    assert st[-1] == -1          # tail breaks down into LH/LL -> downtrend
    assert set(np.unique(st)).issubset({-1, 0, 1})


def test_order_block_bullish_zone_after_break():
    # down candle (the OB) then strong up-close that breaks the prior swing high; price later
    # trades back into the OB body -> +1 reaction zone.
    o = np.array([10, 11, 10.5,  9.5, 11.5, 12.5, 10.2], dtype=float)
    h = np.array([10.5, 11.2, 10.8, 9.8, 13.0, 13.0, 10.6], dtype=float)
    l = np.array([9.0, 10.0,  9.2,  8.8, 11.0, 12.0,  9.0], dtype=float)
    c = np.array([10.2, 11.0, 9.3, 9.6, 12.8, 12.7, 9.4], dtype=float)
    sig = smc.order_blocks(o, h, l, c, swing_l=1)
    assert set(np.unique(sig)).issubset({-1, 0, 1})
    assert (sig == 1).any()      # at least one bullish OB reaction bar is flagged


def test_fvg_active_direction_lookback():
    high = np.array([10, 12, 14, 13, 15, 16], dtype=float)
    low = np.array([9, 11, 13, 12, 14, 15], dtype=float)
    # bullish FVG at t2 (low2=13 > high0=10) persists for lookback bars; a SECOND bullish FVG
    # re-triggers at t5 (low5=15 > high3=13), so the bias stays +1 there.
    out = smc.fvg_active_direction(high, low, lookback=2)
    np.testing.assert_array_equal(out, [0, 0, 1, 1, 1, 1])


def test_fvg_active_direction_decays_with_no_retrigger():
    # one bullish FVG at t2, then a flat tail with no new gaps ⇒ bias decays to 0 after lookback
    high = np.array([10, 12, 14, 13.5, 13.5, 13.5], dtype=float)
    low = np.array([9, 11, 13, 12, 12, 12], dtype=float)  # one bull FVG at t2, no further gaps
    out = smc.fvg_active_direction(high, low, lookback=1)
    np.testing.assert_array_equal(out, [0, 0, 1, 1, 0, 0])


def test_golf_candle_n2():
    open_ = np.array([10, 10, 10, 10], dtype=float)
    close = np.array([11, 12, 10.5, 15], dtype=float)  # bodies 1,2,0.5,5
    g = smc.golf_candle(open_, close, golf_n=2)
    # t3 body 5 > max(body1=2, body2=0.5)=2 -> golf; t2 body .5 not > 2
    np.testing.assert_array_equal(g, [False, False, False, True])
