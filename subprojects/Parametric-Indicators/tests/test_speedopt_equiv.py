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
