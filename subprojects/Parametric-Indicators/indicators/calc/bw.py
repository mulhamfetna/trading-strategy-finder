"""Bill Williams + Elliott-wave-oscillator primitives (pure, causal)."""
from __future__ import annotations

import numpy as np

from ..classic import rma as _rma
from ..classic import sma as _sma
from .osc import _shift, nan_sma


def _median(high, low):
    return (np.asarray(high, float) + np.asarray(low, float)) / 2.0


def alligator(high, low):
    """Displaced smoothed MAs of the median price: jaw(13,+8), teeth(8,+5), lips(5,+3).
    Returned already displaced into the past (causal read of the future-plotted lines)."""
    med = _median(high, low)
    jaw = _shift(_rma(med, 13), 8)
    teeth = _shift(_rma(med, 8), 5)
    lips = _shift(_rma(med, 5), 3)
    return jaw, teeth, lips


def awesome(price):
    """AO = SMA(median,5) − SMA(median,34) (pass median price)."""
    return _sma(price, 5) - _sma(price, 34)


def accel(price):
    """Accelerator = AO − SMA(AO,5). nan_sma so AO's warm-up NaNs don't poison the SMA."""
    ao = awesome(price)
    return ao - nan_sma(ao, 5)


def ewo(close):
    """Elliott Wave Oscillator = SMA(close,5) − SMA(close,34) (uses CLOSE, unlike AO's median)."""
    c = np.asarray(close, float)
    return _sma(c, 5) - _sma(c, 34)


def fractal_levels(high, low):
    """Last CONFIRMED Williams 5-bar fractal high/low available at each bar (centre confirmed +2 bars)."""
    h, l = np.asarray(high, float), np.asarray(low, float)
    N = len(h)
    up = np.full(N, np.nan)
    dn = np.full(N, np.nan)
    last_up = np.nan
    last_dn = np.nan
    for i in range(N):
        if i >= 4:
            j = i - 2
            if h[j] > h[j - 1] and h[j] > h[j - 2] and h[j] > h[j + 1] and h[j] > h[j + 2]:
                last_up = h[j]
            if l[j] < l[j - 1] and l[j] < l[j - 2] and l[j] < l[j + 1] and l[j] < l[j + 2]:
                last_dn = l[j]
        up[i], dn[i] = last_up, last_dn
    return up, dn
