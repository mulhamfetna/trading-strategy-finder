"""FROZEN reference implementations of indicator functions being optimized for speed (task #210).

Each function here is a verbatim copy of the ORIGINAL (pre-optimization) implementation. The optimized
versions in classic.py / smc.py must reproduce these byte-for-byte — enforced by tests/test_speedopt_equiv.py
on random + adversarial inputs. NEVER "optimize" this file; it is the spec the fast paths are checked against.
"""
from __future__ import annotations

import numpy as np


def obv_ref(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """On-Balance Volume — ORIGINAL per-bar loop. OBV[0]=0; += sign(close[t]-close[t-1]) * volume[t]."""
    c = np.asarray(close, dtype=float)
    vol = np.asarray(volume, dtype=float)
    out = np.zeros(len(c), dtype=float)
    for t in range(1, len(c)):
        out[t] = out[t - 1] + np.sign(c[t] - c[t - 1]) * vol[t]
    return out


def bollinger_ref(close, n: int, k: float):
    """Bollinger bands — ORIGINAL per-bar rolling-std loop. mid=SMA(n); band = mid ± k*std(population).
    (mid uses classic.sma, a stable helper not under optimization.)"""
    from indicators.classic import sma, _nan_like
    c = np.asarray(close, float)
    mid = sma(c, n)
    std = _nan_like(c)
    for t in range(n - 1, len(c)):
        std[t] = np.std(c[t - n + 1:t + 1])
    return mid, mid + k * std, mid - k * std
