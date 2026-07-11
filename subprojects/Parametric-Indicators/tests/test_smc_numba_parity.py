"""The Numba SMC kernels must be BIT-IDENTICAL to the pure-Python references they replace.

`breaker_blocks` is the hottest function in an optimizer campaign (a stateful per-bar scan over the
~1M-bar 1-minute frame). It is JITted for speed — which is only safe if it computes exactly the same
array. These tests are the lock: if the kernel and the reference ever disagree by a single bar, the
golden results would silently move.

Order is load-bearing inside that scan (the per-bar signal takes the FIRST overlapping bullish breaker,
else the LAST overlapping bearish one), so the fast path must compact its live lists IN ORDER. A naive
"filter into a new array" that reorders would pass a casual eyeball and fail here.
"""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from indicators import smc  # noqa: E402


def _synthetic(n=4000, seed=7):
    """A random walk with real OHLC geometry — enough structure to birth, flip and kill many breakers."""
    rng = np.random.default_rng(seed)
    c = 100 + np.cumsum(rng.normal(0, 0.5, n))
    o = c + rng.normal(0, 0.3, n)
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.2, n))
    l = np.minimum(o, c) - np.abs(rng.normal(0, 0.2, n))
    return o, h, l, c


@pytest.mark.skipif(not smc._HAVE_NUMBA, reason="numba not installed; pure-Python path is in use")
@pytest.mark.parametrize("swing_l", [1, 2, 3, 5, 8, 13, 20])
def test_breaker_kernel_matches_reference_across_swing_l(swing_l):
    o, h, l, c = _synthetic()
    fast = smc.breaker_blocks(o, h, l, c, swing_l=swing_l)
    ref = smc._breaker_blocks_py(o, h, l, c, swing_l=swing_l)
    assert fast.dtype == ref.dtype == np.int8
    assert np.array_equal(fast, ref), (
        f"swing_l={swing_l}: {int((fast != ref).sum())} bars differ "
        f"(first at {int(np.flatnonzero(fast != ref)[0])})")
    assert np.any(ref != 0), "fixture produced no breaker signals — the test would prove nothing"


@pytest.mark.skipif(not smc._HAVE_NUMBA, reason="numba not installed")
def test_breaker_kernel_matches_reference_with_signal_at_mask():
    """signal_at restricts WHICH bars emit a signal, but the breaker state machine must still advance on
    every bar. A kernel that skipped state updates for masked-out bars would pass the unmasked test."""
    o, h, l, c = _synthetic()
    at = np.arange(0, len(c), 7)                       # sparse decision bars
    fast = smc.breaker_blocks(o, h, l, c, swing_l=2, signal_at=at)
    ref = smc._breaker_blocks_py(o, h, l, c, swing_l=2, signal_at=at)
    assert np.array_equal(fast, ref)
    off = np.setdiff1d(np.arange(len(c)), at)
    assert np.all(fast[off] == 0), "masked-out bars must stay 0"
    assert np.any(fast[at] != 0), "masked run produced no signals — test would prove nothing"


@pytest.mark.skipif(not smc._HAVE_NUMBA, reason="numba not installed")
def test_breaker_kernel_matches_reference_on_real_1min_data():
    """The case that actually matters: the real 1-minute frame the optimizer runs on."""
    from optimize import data as D
    _dec, df1, _box, _vf, _n = D.load_inputs("4h")
    o = df1["Open"].to_numpy(float)[:200_000]
    h = df1["High"].to_numpy(float)[:200_000]
    l = df1["Low"].to_numpy(float)[:200_000]
    c = df1["Close"].to_numpy(float)[:200_000]
    for swing_l in (2, 7):
        fast = smc.breaker_blocks(o, h, l, c, swing_l=swing_l)
        ref = smc._breaker_blocks_py(o, h, l, c, swing_l=swing_l)
        assert np.array_equal(fast, ref), f"real-data mismatch at swing_l={swing_l}"


@pytest.mark.skipif(not smc._HAVE_NUMBA, reason="numba not installed")
def test_breaker_kernel_is_actually_faster():
    """Guard against the JIT silently falling back to object mode (which would be SLOWER, not faster)."""
    import time
    o, h, l, c = _synthetic(n=60_000)
    smc.breaker_blocks(o, h, l, c, swing_l=2)          # warm the JIT (compile once)

    t0 = time.perf_counter(); smc.breaker_blocks(o, h, l, c, swing_l=2); t_fast = time.perf_counter() - t0
    t0 = time.perf_counter(); smc._breaker_blocks_py(o, h, l, c, swing_l=2); t_ref = time.perf_counter() - t0

    assert t_fast < t_ref / 3, f"JIT only {t_ref / max(t_fast, 1e-9):.1f}x — expected a large speedup"
