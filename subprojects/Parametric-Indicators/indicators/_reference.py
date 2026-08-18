"""FROZEN reference implementations of indicator functions being optimized for speed (task #210).

Each function here is a verbatim copy of the ORIGINAL (pre-optimization) implementation. The optimized
versions in classic.py / smc.py must reproduce these byte-for-byte — enforced by tests/test_speedopt_equiv.py
on random + adversarial inputs. NEVER "optimize" this file; it is the spec the fast paths are checked against.
"""
from __future__ import annotations

import numpy as np


def ema_ref(close: np.ndarray, n: int) -> np.ndarray:
    """Exponential MA — ORIGINAL per-bar Python recurrence, alpha = 2/(n+1), seeded at close[0]."""
    x = np.asarray(close, dtype=float)
    out = np.full(len(x), np.nan, dtype=float)
    if len(x) == 0:
        return out
    a = 2.0 / (n + 1.0)
    out[0] = x[0]
    for t in range(1, len(x)):
        out[t] = a * x[t] + (1.0 - a) * out[t - 1]
    return out


def rma_ref(x: np.ndarray, n: int) -> np.ndarray:
    """Wilder's smoothing — ORIGINAL per-bar Python recurrence (seed at first finite, hold on NaN)."""
    v = np.asarray(x, dtype=float)
    out = np.full(len(v), np.nan, dtype=float)
    finite = np.where(~np.isnan(v))[0]
    if len(finite) == 0:
        return out
    a = 1.0 / n
    s = int(finite[0])
    out[s] = v[s]
    for t in range(s + 1, len(v)):
        if np.isnan(v[t]):
            out[t] = out[t - 1]
        else:
            out[t] = a * v[t] + (1.0 - a) * out[t - 1]
    return out


def roll_max_ref(x, n):
    """Rolling window maximum — ORIGINAL per-bar `np.max(slice)` loop (issue #62)."""
    out = np.full(len(x), np.nan)
    for t in range(n - 1, len(x)):
        out[t] = np.max(x[t - n + 1:t + 1])
    return out


def roll_min_ref(x, n):
    """Rolling window minimum — ORIGINAL per-bar `np.min(slice)` loop (issue #62)."""
    out = np.full(len(x), np.nan)
    for t in range(n - 1, len(x)):
        out[t] = np.min(x[t - n + 1:t + 1])
    return out


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
