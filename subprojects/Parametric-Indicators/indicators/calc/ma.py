"""Moving-average primitives (pure, vectorized, causal). Each returns a float array the length of the
input with NaN during warm-up. No framework imports — unit-testable in isolation against an
independent pandas/numpy oracle (see tests/oracle/)."""
from __future__ import annotations

import numpy as np


def wma(x: np.ndarray, n: int) -> np.ndarray:
    """Linearly-weighted MA: weights 1..n (most recent = n). NaN for the first n-1 bars."""
    x = np.asarray(x, dtype=float)
    w = np.arange(1, n + 1, dtype=float)
    denom = w.sum()
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = np.dot(x[i - n + 1:i + 1], w) / denom
    return out
