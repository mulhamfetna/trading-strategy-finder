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


def test_market_structure_vectorized_matches_bruteforce():
    """task #210 — the vectorized fractal must be bit-identical to the naive per-window .all() loop
    (the implementation it replaced) for every swing_l, including ties and edges."""
    def brute(c, L):
        n = len(c); sh = np.zeros(n, bool); sl = np.zeros(n, bool)
        for t in range(L, n - L):
            left, right = c[t - L:t], c[t + 1:t + 1 + L]
            sh[t] = (c[t] > left).all() and (c[t] > right).all()
            sl[t] = (c[t] < left).all() and (c[t] < right).all()
        return sh, sl
    rng = np.random.default_rng(0)
    for series in (rng.standard_normal(2000),                       # generic
                   rng.integers(0, 5, 2000).astype(float),          # many ties (plateaus)
                   np.arange(500, dtype=float),                     # strictly increasing
                   np.zeros(50)):                                   # all equal (no swings)
        for L in (1, 2, 3, 5, 11, 19):
            sh_v, sl_v = smc.market_structure(series, L)
            sh_b, sl_b = brute(series, L)
            np.testing.assert_array_equal(sh_v, sh_b, err_msg=f"sh L={L}")
            np.testing.assert_array_equal(sl_v, sl_b, err_msg=f"sl L={L}")


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


def test_golf_engulfing_n2_bullish():
    # N=2 engulfing. Prior 2 bars both RED; current GREEN engulfs their span with a big body.
    #         t0(red)   t1(red)   t2(GREEN engulf)
    open_ = np.array([105, 103, 99.0])
    close = np.array([101,  99, 106.0])   # t0,t1 red (close<open); t2 green
    high  = np.array([106, 104, 107.0])
    low   = np.array([100,  98, 98.0])
    # prior span (t0..t1): max high 106, min low 98 → span 8 ; t2 body |106-99|=7 ≥ 0.7*8=5.6 ✓
    # engulf: t2.high 107≥106 ✓ and t2.low 98≤98 ✓ ; prior both red, t2 green → +1
    g = smc.golf_candle(open_, high, low, close, golf_n=2)
    np.testing.assert_array_equal(g, [0, 0, 1])


def test_golf_engulfing_rejects_when_body_below_70pct_or_not_opposite():
    # Bearish setup but body too small (< 70% of prior span) ⇒ rejected.
    open_ = np.array([99, 101, 106.0])
    close = np.array([101, 103, 105.0])   # t0,t1 GREEN ; t2 red but tiny body |105-106|=1
    high  = np.array([102, 104, 107.0]); low = np.array([98, 100, 98.0])
    # prior span max 104 min 98 = 6 ; need body ≥ 4.2 but body=1 ⇒ no golf
    g = smc.golf_candle(open_, high, low, close, golf_n=2)
    np.testing.assert_array_equal(g, [0, 0, 0])
    # opposite-colour-to-ALL-N fails: mix one red into the prior window
    open2 = np.array([99, 105, 99.0]); close2 = np.array([101, 101, 108.0])  # t1 red, breaks "all green"
    high2 = np.array([102, 106, 109.0]); low2 = np.array([98, 100, 98.0])
    g2 = smc.golf_candle(open2, high2, low2, close2, golf_n=2)
    assert g2[2] == 0  # prior not all the same opposite colour


# ---------------------------------------------------------------------------
# New structure detectors (LL/HL/HH/LH labels, IFVG, breaker, CISD) — task B.
# ---------------------------------------------------------------------------

def test_swing_labels_hh_hl_lh_ll():
    # rising HH/HL then falling LH/LL (same series as structure_trend test), swing_l=1
    close = np.array([10, 12, 11, 14, 13, 16, 15, 12, 13, 9, 10, 6], dtype=float)
    kind, label, conf = smc.swing_labels(close, swing_l=1)
    assert set(np.unique(kind)).issubset({-1, 0, 1})
    # confirmed swing highs at 3,5 are higher than prior highs -> HH; 8,10 lower -> LH
    assert label[3] == "HH" and label[5] == "HH"
    assert label[8] == "LH" and label[10] == "LH"
    # swing lows: 4 higher than prior low -> HL; 7,9 lower -> LL
    assert label[4] == "HL" and label[7] == "LL" and label[9] == "LL"
    # the first high (idx1) and first low (idx2) have no prior -> unlabeled
    assert label[1] == "" and label[2] == ""
    # confirmation is swing_l bars after the pivot
    assert conf[3] == 3 + 1


def test_ifvg_bullish_fvg_inverts_to_bearish_on_close_below():
    # t2: low2=13 > high0=10 -> bullish FVG [10,13]; t4 closes 8.5 < 10 -> inverts to bearish IFVG;
    # t5 trades back into [10,13] -> signal -1.
    high = np.array([10, 12, 14, 13, 9, 11.0])
    low = np.array([9, 11, 13, 12, 8, 10.0])
    close = np.array([9.5, 11.5, 13.5, 12.5, 8.5, 10.5])
    out = smc.ifvg(high, low, close)
    assert set(np.unique(out)).issubset({-1, 0, 1})
    assert out[5] == -1
    assert (out[:5] == 0).all()


def test_breaker_bearish_ob_flips_to_bullish_breaker_on_close_above():
    # bearish OB (t3 body [11.0,12.4]) is broken UP at t7 (close 12.8 > 12.4) -> bullish breaker;
    # t7/t8 overlap the zone -> +1.
    o = np.array([12, 11.6, 11.2, 11.0, 11.8, 10.5, 11.4, 11.5, 12.0], dtype=float)
    h = np.array([12.2, 11.8, 11.4, 12.6, 12.0, 11.0, 11.6, 12.9, 12.1], dtype=float)
    l = np.array([11.4, 11.0, 10.8, 10.9, 10.0, 10.2, 11.0, 11.4, 11.2], dtype=float)
    c = np.array([11.6, 11.2, 11.3, 12.4, 10.2, 10.8, 11.5, 12.8, 11.5], dtype=float)
    br = smc.breaker_blocks(o, h, l, c, swing_l=1)
    assert set(np.unique(br)).issubset({-1, 0, 1})
    assert br[7] == 1 and br[8] == 1
    assert (br[:7] == 0).all()


def test_cisd_close_through_prior_leg_open():
    # bullish leg opens at 10 (t0), runs green; t4 closes 9.8 < 10 -> bearish CISD (-1)
    o = np.array([10, 10.2, 10.4, 10.6, 10.3])
    c = np.array([10.2, 10.4, 10.6, 10.3, 9.8])
    out = smc.cisd(o, c)
    assert out[4] == -1 and (out[:4] == 0).all()
    # mirror: bearish leg opens at 10 (t0); t4 closes 10.3 > 10 -> bullish CISD (+1)
    o2 = np.array([10, 9.8, 9.6, 9.4, 9.9])
    c2 = np.array([9.8, 9.6, 9.4, 9.9, 10.3])
    out2 = smc.cisd(o2, c2)
    assert out2[4] == 1 and (out2[:4] == 0).all()


def test_new_smc_indicators_registered_and_build():
    """Q6: ifvg / breaker / cisd are wired as vote-source indicators (optimizer-searchable)."""
    from indicators import library
    for key in ("ifvg", "breaker", "cisd"):
        assert key in library.REGISTRY, f"{key} not registered"
        assert key in library.SCHEMA, f"{key} missing from SCHEMA"
        ind = library.build(key)
        assert ind.key == key
