"""Tier-2 DSP / adaptive-MA primitives (Ehlers filters, single-series, causal).

These are the deferred "hard" indicators — exact where a published closed form exists (Ehlers 2-pole
filters), documented as approximate otherwise. Reuse the NaN-safe helpers from calc/osc.py."""
from __future__ import annotations

import numpy as np


def super_smoother(x, n):
    """Ehlers 2-pole SuperSmoother (Butterworth). Zero warm-up NaN — seeded from the raw series."""
    x = np.asarray(x, dtype=float)
    N = len(x)
    out = np.full(N, np.nan)
    if N == 0:
        return out
    a1 = np.exp(-np.sqrt(2.0) * np.pi / n)
    b1 = 2.0 * a1 * np.cos(np.sqrt(2.0) * np.pi / n)
    c2, c3 = b1, -a1 * a1
    c1 = 1.0 - c2 - c3
    out[0] = x[0]
    out[1] = x[1] if N > 1 else x[0]
    for i in range(2, N):
        out[i] = c1 * (x[i] + x[i - 1]) / 2.0 + c2 * out[i - 1] + c3 * out[i - 2]
    return out
