"""Phase 0 — equivalence-test framework (task #210). Helpers to prove an OPTIMIZED indicator function
returns the SAME numbers as its kept pure-Python reference, on random AND adversarial inputs.

Used by the per-step tests in Phase 1/2: each optimization keeps the original implementation as a
reference (e.g. indicators/_reference.py) and a test asserts `optimized(x) ≈ reference(x)` to tight
tolerance, NaN-for-NaN, across many stress cases — the "high precision / high redundancy" guarantee.
"""
from __future__ import annotations

import numpy as np

# A deterministic generator (no global Math.random/seed surprises): seed is explicit per call.
def rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def price_series(n: int, seed: int, start: float = 20000.0) -> np.ndarray:
    """A realistic-ish positive price path (random walk), length n."""
    g = rng(seed)
    steps = g.normal(0, 8.0, size=n)
    return start + np.cumsum(steps)


def ohlcv(n: int, seed: int):
    """(open, high, low, close, volume) consistent OHLC with high>=max(o,c), low<=min(o,c)."""
    g = rng(seed)
    close = price_series(n, seed)
    open_ = np.concatenate([[close[0]], close[:-1]]) + g.normal(0, 2, size=n)
    spread = np.abs(g.normal(0, 6, size=n)) + 1.0
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    vol = np.abs(g.normal(1000, 300, size=n)) + 1.0
    return open_, high, low, close, vol


# Adversarial edge cases that have historically broken vectorized rewrites:
def edge_cases(n: int = 300):
    """Yield (name, close) degenerate series that stress NaN/boundary/constant handling."""
    yield "constant", np.full(n, 21000.0)
    yield "monotonic_up", np.linspace(20000, 22000, n)
    yield "monotonic_down", np.linspace(22000, 20000, n)
    s = price_series(n, 7); s[:3] = np.nan                       # leading NaNs (warm-up region)
    yield "leading_nan", s
    s2 = price_series(n, 9); s2[n // 2] = np.nan                 # a hole mid-series
    yield "mid_nan", s2
    yield "tiny", price_series(5, 11)                            # shorter than typical windows
    yield "two_equal_then_jump", np.concatenate([np.full(n - 1, 21000.0), [25000.0]])


def assert_equiv(name: str, a: np.ndarray, b: np.ndarray, atol: float = 1e-9, rtol: float = 1e-9):
    """Assert two arrays are equal INCLUDING NaN positions, to tight tolerance. Raises on mismatch."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    assert a.shape == b.shape, f"{name}: shape {a.shape} != {b.shape}"
    na, nb = np.isnan(a), np.isnan(b)
    assert np.array_equal(na, nb), f"{name}: NaN pattern differs ({na.sum()} vs {nb.sum()})"
    m = ~na
    if m.any():
        diff = np.abs(a[m] - b[m])
        tol = atol + rtol * np.abs(b[m])
        bad = diff > tol
        if bad.any():
            i = int(np.argmax(diff))
            raise AssertionError(f"{name}: {bad.sum()} elems exceed tol; worst |Δ|={diff.max():.3e} "
                                 f"(a={a[m][i]!r} b={b[m][i]!r})")
