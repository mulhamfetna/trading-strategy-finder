"""Tier-2 approximate / stateful primitives (pure, causal). Honestly labeled where approximate:
  * jma        — commonly-cited open APPROXIMATION of the proprietary Jurik MA.
  * ewma_vol   — RiskMetrics EWMA volatility (full GARCH-MLE deferred).
  * ehlers_emd — Ehlers' bandpass-based Empirical Mode Decomposition (NOT Hilbert-Huang sifting).
  * td_setup / td_combo — DeMark TD *Setup* phase (Countdown left to a follow-up).
  * kalman     — 1-D random-walk Kalman smoother.
  * ou_halflife— Ornstein-Uhlenbeck mean-reversion coefficient / half-life."""
from __future__ import annotations

import numpy as np

from ..classic import sma as _sma
from .dsp import bandpass


def jma(price, length, phase, power):
    """Jurik MA (open approximation). Adaptive triple-stage filter."""
    p = np.asarray(price, dtype=float)
    N = len(p)
    out = np.full(N, np.nan)
    if N == 0:
        return out
    phase_ratio = 0.5 if phase < -100 else (2.5 if phase > 100 else phase / 100.0 + 1.5)
    beta = 0.45 * (length - 1) / (0.45 * (length - 1) + 2)
    alpha = beta ** power
    e0, e1, e2 = p[0], 0.0, 0.0     # seed e0 at first price (0-seed integrates a permanent offset)
    jval = p[0]
    for i in range(N):
        e0 = (1 - alpha) * p[i] + alpha * e0
        e1 = (p[i] - e0) * (1 - beta) + beta * e1
        e2 = (e0 + phase_ratio * e1 - jval) * (1 - alpha) ** 2 + alpha ** 2 * e2
        jval = jval + e2
        out[i] = jval
    return out


def ewma_vol(close, lam):
    """RiskMetrics EWMA volatility of log returns (var = lam*var[-1] + (1-lam)*ret^2)."""
    c = np.asarray(close, dtype=float)
    N = len(c)
    ret = np.zeros(N)
    ret[1:] = np.diff(np.log(c))
    var = np.full(N, np.nan)
    if N < 2:
        return var
    var[1] = ret[1] ** 2
    for i in range(2, N):
        var[i] = lam * var[i - 1] + (1 - lam) * ret[i] ** 2
    return np.sqrt(var)


def ehlers_emd(high, low, period, bandwidth):
    """Ehlers EMD: (mean, avg-peak, avg-valley) of the band-pass — trend vs cycle mode."""
    mid = (np.asarray(high, float) + np.asarray(low, float)) / 2.0
    bp = bandpass(mid, period, bandwidth)
    N = len(bp)
    peak = np.zeros(N)
    valley = np.zeros(N)
    for i in range(2, N):
        peak[i], valley[i] = peak[i - 1], valley[i - 1]
        if bp[i - 1] > bp[i] and bp[i - 1] > bp[i - 2]:
            peak[i] = bp[i - 1]
        if bp[i - 1] < bp[i] and bp[i - 1] < bp[i - 2]:
            valley[i] = bp[i - 1]
    w = 2 * period
    mean = _sma(bp, w)
    return mean, 0.1 * _sma(peak, w), 0.1 * _sma(valley, w)


def _td_setup_core(close, perfected):
    """TD buy/sell setup completion signal: +1 at a 9-bar buy setup, -1 at a 9-bar sell setup.
    `perfected` requires the DeMark perfection (bar 8/9 extreme vs bar 6/7)."""
    c = np.asarray(close, dtype=float)
    N = len(c)
    sig = np.zeros(N)
    buy = sell = 0
    for i in range(N):
        if i < 4:
            continue
        if c[i] < c[i - 4]:
            buy, sell = buy + 1, 0
        elif c[i] > c[i - 4]:
            sell, buy = sell + 1, 0
        else:
            buy = sell = 0
        if buy == 9:
            ok = (not perfected) or (i >= 2 and (c[i] <= c[i - 2] and c[i] <= c[i - 3]))
            if ok:
                sig[i] = 1
            buy = 0
        elif sell == 9:
            ok = (not perfected) or (i >= 2 and (c[i] >= c[i - 2] and c[i] >= c[i - 3]))
            if ok:
                sig[i] = -1
            sell = 0
    return sig


def td_sequential(close):
    return _td_setup_core(close, perfected=False)


def td_combo(close):
    return _td_setup_core(close, perfected=True)


def kalman(price, q, r):
    """1-D random-walk Kalman smoother. q=process var, r=measurement var."""
    p = np.asarray(price, dtype=float)
    N = len(p)
    out = np.full(N, np.nan)
    if N == 0:
        return out
    x, P = p[0], 1.0
    for i in range(N):
        P = P + q
        k = P / (P + r)
        x = x + k * (p[i] - x)
        P = (1 - k) * P
        out[i] = x
    return out


def ou_coefficient(close, n):
    """OU mean-reversion coefficient b from ΔP = a + b·P[-1] over a rolling window (b<0 ⇒ reverting)."""
    c = np.asarray(close, dtype=float)
    N = len(c)
    out = np.full(N, np.nan)
    for i in range(n, N):
        lag = c[i - n:i]
        dy = c[i - n + 1:i + 1] - lag
        v = lag.var()
        if v > 0:
            out[i] = ((lag - lag.mean()) * (dy - dy.mean())).sum() / (n * v)
    return out
