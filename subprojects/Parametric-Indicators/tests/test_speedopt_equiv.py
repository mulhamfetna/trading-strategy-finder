"""Equivalence tests for the backtester speed-optimization (task #210).

Each optimized indicator MUST equal its frozen reference (indicators/_reference.py) byte-for-byte
(NaN-for-NaN, tight tolerance) on random AND adversarial inputs. These run in the normal pytest suite,
so any divergence fails CI immediately. Fast (synthetic data) — the primary precision gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))
sys.path.insert(0, str(_PROJ / "perf"))

import equiv  # noqa: E402  (perf/equiv.py — random + adversarial generators + assert_equiv)
from indicators import classic, _reference  # noqa: E402


# ----- Step D: obv ---------------------------------------------------------------------------------
@pytest.mark.parametrize("n,seed", [(1, 1), (2, 2), (50, 3), (1000, 4), (486969 % 50000 + 1000, 5)])
def test_obv_random(n, seed):
    _o, _h, _l, c, v = equiv.ohlcv(n, seed)
    equiv.assert_equiv(f"obv random n={n}", classic.obv(c, v), _reference.obv_ref(c, v))


def test_obv_edge_cases():
    g = equiv.rng(123)
    for name, close in equiv.edge_cases(400):
        vol = np.abs(g.normal(1000, 300, size=len(close))) + 1.0
        equiv.assert_equiv(f"obv edge[{name}]", classic.obv(close, vol), _reference.obv_ref(close, vol))


def test_obv_empty_and_single():
    equiv.assert_equiv("obv n=0", classic.obv(np.array([]), np.array([])),
                       _reference.obv_ref(np.array([]), np.array([])))
    equiv.assert_equiv("obv n=1", classic.obv(np.array([21000.0]), np.array([5.0])),
                       _reference.obv_ref(np.array([21000.0]), np.array([5.0])))


# ----- Step A1: bollinger (rolling population std) -------------------------------------------------
@pytest.mark.parametrize("nbar,seed", [(50, 1), (300, 2), (2000, 3), (49000, 4)])
@pytest.mark.parametrize("win,k", [(20, 2.0), (45, 4.3), (5, 1.0)])
def test_bollinger_random(nbar, seed, win, k):
    c = equiv.price_series(nbar, seed)
    got = classic.bollinger(c, win, k)
    ref = _reference.bollinger_ref(c, win, k)
    for nm, g, r in zip(("mid", "upper", "lower"), got, ref):
        equiv.assert_equiv(f"bollinger {nm} n={nbar} win={win} k={k}", g, r)


def test_bollinger_edge_cases():
    for name, close in equiv.edge_cases(400):
        for win, k in ((20, 2.0), (45, 4.3)):
            got = classic.bollinger(close, win, k)
            ref = _reference.bollinger_ref(close, win, k)
            for nm, g, r in zip(("mid", "upper", "lower"), got, ref):
                equiv.assert_equiv(f"bollinger edge[{name}] {nm} win={win}", g, r)


def test_bollinger_window_longer_than_series():
    c = equiv.price_series(10, 5)
    got = classic.bollinger(c, 50, 2.0)            # win > len → all-NaN std
    ref = _reference.bollinger_ref(c, 50, 2.0)
    for nm, g, r in zip(("mid", "upper", "lower"), got, ref):
        equiv.assert_equiv(f"bollinger win>len {nm}", g, r)


# ----- Step A2: cci (rolling mean-abs-deviation, mad==0 -> 0 guard) --------------------------------
@pytest.mark.parametrize("nbar,seed", [(50, 1), (300, 2), (2000, 3), (49000, 4)])
@pytest.mark.parametrize("win", [20, 122, 138, 5])
def test_cci_random(nbar, seed, win):
    o, h, l, c, _v = equiv.ohlcv(nbar, seed)
    equiv.assert_equiv(f"cci n={nbar} win={win}", classic.cci(h, l, c, win),
                       _reference.cci_ref(h, l, c, win))


def test_cci_edge_cases():
    # includes 'constant' → mean-abs-deviation is exactly 0 → must hit the mad==0 → 0 guard
    for name, close in equiv.edge_cases(400):
        h = close + 1.0; l = close - 1.0
        for win in (20, 138):
            equiv.assert_equiv(f"cci edge[{name}] win={win}", classic.cci(h, l, close, win),
                               _reference.cci_ref(h, l, close, win))


def test_cci_constant_mad_zero():
    c = np.full(200, 21000.0); h = c + 1.0; l = c - 1.0       # constant TP within each window → mad=0
    equiv.assert_equiv("cci constant mad=0", classic.cci(h, l, c, 20), _reference.cci_ref(h, l, c, 20))


# ----- Step E: order_blocks sampled-overlap (signal_at) --------------------------------------------
from indicators import smc  # noqa: E402


@pytest.mark.parametrize("nbar,seed", [(60, 1), (400, 2), (3000, 3), (30000, 4)])
@pytest.mark.parametrize("swing_l", [2, 6, 10])
def test_order_blocks_full_equals_reference(nbar, seed, swing_l):
    """signal_at=None must reproduce the original full computation bit-for-bit (the decision-TF path)."""
    o, h, l, c, _v = equiv.ohlcv(nbar, seed)
    got = smc.order_blocks(o, h, l, c, swing_l)               # signal_at=None
    ref = _reference.order_blocks_ref(o, h, l, c, swing_l)
    assert np.array_equal(got, ref), f"full order_blocks != ref (n={nbar}, swing_l={swing_l})"


@pytest.mark.parametrize("nbar,seed", [(400, 11), (3000, 12), (30000, 13)])
@pytest.mark.parametrize("swing_l", [2, 6, 10])
def test_order_blocks_sampled_matches_reference_at_read_indices(nbar, seed, swing_l):
    """The KEY property: order_blocks(signal_at=S)[S] == full_reference[S] for arbitrary index sets S
    (the unsampled bars are never read). Tests several S shapes incl. empty / all / sparse / clustered."""
    o, h, l, c, _v = equiv.ohlcv(nbar, seed)
    ref = _reference.order_blocks_ref(o, h, l, c, swing_l)
    g = equiv.rng(seed)
    subsets = {
        "empty": np.array([], dtype=int),
        "all": np.arange(nbar),
        "sparse": np.unique(g.integers(0, nbar, size=max(1, nbar // 50))),
        "clustered": np.arange(nbar // 3, min(nbar, nbar // 3 + 200)),
        "endpoints": np.array([0, nbar - 1]),
    }
    for name, S in subsets.items():
        out = smc.order_blocks(o, h, l, c, swing_l, signal_at=S)
        if len(S):
            assert np.array_equal(out[S], ref[S]), f"sampled[{name}] != ref at read indices"
        # bars NOT in S must be left at 0 (never read)
        mask = np.ones(nbar, bool); mask[S] = False
        assert np.all(out[mask] == 0), f"sampled[{name}] wrote a non-zero at an unsampled bar"
