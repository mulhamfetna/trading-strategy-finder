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


def order_blocks_ref(open_, high, low, close, swing_l: int = 2):
    """SMC order-block signal — ORIGINAL full per-bar loop (computes the overlap at EVERY bar).
    The frozen spec for Step E (sampled-overlap): order_blocks(..., signal_at=S)[S] must equal this[S]."""
    from indicators.smc import market_structure
    o = np.asarray(open_, float); h = np.asarray(high, float)
    l = np.asarray(low, float); c = np.asarray(close, float)
    n = len(c)
    sh, sl = market_structure(c, swing_l)
    L = int(swing_l)
    out = np.zeros(n, dtype=np.int8)
    swh = swl = None
    last_down = last_up = None
    bull, bear = [], []
    prev_above = prev_below = False
    for t in range(n):
        p = t - L
        if p >= 0:
            if sh[p]:
                swh = c[p]
            if sl[p]:
                swl = c[p]
        if swh is not None:
            above = c[t] > swh
            if above and not prev_above and last_down is not None:
                bull.append([min(o[last_down], c[last_down]), max(o[last_down], c[last_down])])
            prev_above = above
        if swl is not None:
            below = c[t] < swl
            if below and not prev_below and last_up is not None:
                bear.append([min(o[last_up], c[last_up]), max(o[last_up], c[last_up])])
            prev_below = below
        s = 0
        for z in bull:
            if l[t] <= z[1] and h[t] >= z[0]:
                s = 1; break
        if s == 0:
            for z in bear:
                if l[t] <= z[1] and h[t] >= z[0]:
                    s = -1; break
        out[t] = s
        bull = [z for z in bull if not (c[t] < z[0])]
        bear = [z for z in bear if not (c[t] > z[1])]
        if c[t] < o[t]:
            last_down = t
        elif c[t] > o[t]:
            last_up = t
    return out


def cci_ref(high, low, close, n: int):
    """CCI — ORIGINAL per-bar rolling mean-abs-deviation loop. TP=(H+L+C)/3, factor 0.015; mad==0 ⇒ 0."""
    from indicators.classic import sma, _nan_like
    h = np.asarray(high, float); l = np.asarray(low, float); c = np.asarray(close, float)
    tp = (h + l + c) / 3.0
    m = sma(tp, n)
    out = _nan_like(c)
    for t in range(n - 1, len(c)):
        win = tp[t - n + 1:t + 1]
        mad = np.mean(np.abs(win - m[t]))
        out[t] = 0.0 if mad == 0 else (tp[t] - m[t]) / (0.015 * mad)
    return out
