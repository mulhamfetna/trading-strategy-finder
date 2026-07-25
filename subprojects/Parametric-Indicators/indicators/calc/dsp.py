"""Tier-2 DSP / adaptive-MA primitives (Ehlers filters, single-series, causal).

These are the deferred "hard" indicators — exact where a published closed form exists (Ehlers 2-pole
filters), documented as approximate otherwise. Reuse the NaN-safe helpers from calc/osc.py."""
from __future__ import annotations

import numpy as np

from ..classic import _roll_max, _roll_min
from ..classic import ema as _ema


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


def highpass(x, period):
    """Ehlers 2-pole high-pass filter (removes trend below `period`)."""
    x = np.asarray(x, dtype=float)
    N = len(x)
    hp = np.zeros(N)
    a = ((np.cos(0.707 * 2 * np.pi / period) + np.sin(0.707 * 2 * np.pi / period) - 1)
         / np.cos(0.707 * 2 * np.pi / period))
    for i in range(2, N):
        hp[i] = ((1 - a / 2) ** 2 * (x[i] - 2 * x[i - 1] + x[i - 2])
                 + 2 * (1 - a) * hp[i - 1] - (1 - a) ** 2 * hp[i - 2])
    return hp


def roofing(x, hp_period, lp_period):
    """Ehlers Roofing Filter = SuperSmoother(HighPass(x)). A band-limited cycle oscillator ~0."""
    return super_smoother(highpass(x, hp_period), lp_period)


def bandpass(x, period, bandwidth):
    """Ehlers Band-Pass filter centred on `period`."""
    x = np.asarray(x, dtype=float)
    N = len(x)
    bp = np.zeros(N)
    beta = np.cos(2 * np.pi / period)
    gamma = 1.0 / np.cos(4 * np.pi * bandwidth / period)
    alpha = gamma - np.sqrt(gamma * gamma - 1.0)
    for i in range(2, N):
        bp[i] = (0.5 * (1 - alpha) * (x[i] - x[i - 2])
                 + beta * (1 + alpha) * bp[i - 1] - alpha * bp[i - 2])
    return bp


def frama(high, low, close, n):
    """Ehlers Fractal Adaptive MA. Fractal dimension of high/low → adaptive EMA of close."""
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    N = len(c)
    if n % 2:
        n += 1
    half = n // 2
    fr = np.full(N, np.nan)
    for i in range(N):
        if i < n:
            fr[i] = c[i]
            continue
        h1, l1 = h[i - n + 1:i - half + 1], l[i - n + 1:i - half + 1]     # older half
        h2, l2 = h[i - half + 1:i + 1], l[i - half + 1:i + 1]             # recent half
        n1 = (h1.max() - l1.min()) / half
        n2 = (h2.max() - l2.min()) / half
        n3 = (h[i - n + 1:i + 1].max() - l[i - n + 1:i + 1].min()) / n
        d = (np.log(n1 + n2) - np.log(n3)) / np.log(2) if (n1 > 0 and n2 > 0 and n3 > 0) else 1.0
        alpha = min(max(np.exp(-4.6 * (d - 1)), 0.01), 1.0)
        fr[i] = alpha * c[i] + (1 - alpha) * fr[i - 1]
    return fr


def mama_fama(price, fast=0.5, slow=0.05):
    """Ehlers MESA Adaptive MA (MAMA) + Following AMA (FAMA), via the Hilbert-transform homodyne
    discriminator. Returns (mama, fama). Canonical Ehlers algorithm (phase in degrees)."""
    p = np.asarray(price, dtype=float)
    N = len(p)
    z = lambda: np.zeros(N)  # noqa: E731
    sm, dt, i1, q1 = z(), z(), z(), z()
    ji, jq, i2, q2 = z(), z(), z(), z()
    re, im, per, sper, phase = z(), z(), z(), z(), z()
    mama, fama = np.full(N, np.nan), np.full(N, np.nan)
    for i in range(N):
        if i < 6:
            mama[i] = fama[i] = p[i]
            continue
        adj = 0.075 * per[i - 1] + 0.54
        sm[i] = (4 * p[i] + 3 * p[i - 1] + 2 * p[i - 2] + p[i - 3]) / 10.0
        dt[i] = (0.0962 * sm[i] + 0.5769 * sm[i - 2] - 0.5769 * sm[i - 4] - 0.0962 * sm[i - 6]) * adj
        q1[i] = (0.0962 * dt[i] + 0.5769 * dt[i - 2] - 0.5769 * dt[i - 4] - 0.0962 * dt[i - 6]) * adj
        i1[i] = dt[i - 3]
        ji[i] = (0.0962 * i1[i] + 0.5769 * i1[i - 2] - 0.5769 * i1[i - 4] - 0.0962 * i1[i - 6]) * adj
        jq[i] = (0.0962 * q1[i] + 0.5769 * q1[i - 2] - 0.5769 * q1[i - 4] - 0.0962 * q1[i - 6]) * adj
        i2[i] = 0.2 * (i1[i] - jq[i]) + 0.8 * i2[i - 1]
        q2[i] = 0.2 * (q1[i] + ji[i]) + 0.8 * q2[i - 1]
        re[i] = 0.2 * (i2[i] * i2[i - 1] + q2[i] * q2[i - 1]) + 0.8 * re[i - 1]
        im[i] = 0.2 * (i2[i] * q2[i - 1] - q2[i] * i2[i - 1]) + 0.8 * im[i - 1]
        pv = 360.0 / np.degrees(np.arctan(im[i] / re[i])) if (im[i] != 0 and re[i] != 0) else per[i - 1]
        if per[i - 1] > 0:
            pv = min(pv, 1.5 * per[i - 1])
            pv = max(pv, 0.67 * per[i - 1])
        pv = min(max(pv, 6.0), 50.0)
        per[i] = 0.2 * pv + 0.8 * per[i - 1]
        sper[i] = 0.33 * per[i] + 0.67 * sper[i - 1]
        phase[i] = np.degrees(np.arctan(q1[i] / i1[i])) if i1[i] != 0 else phase[i - 1]
        dphase = max(phase[i - 1] - phase[i], 1.0)
        alpha = min(max(fast / dphase, slow), fast)
        mama[i] = alpha * p[i] + (1 - alpha) * mama[i - 1]
        fama[i] = 0.5 * alpha * mama[i] + (1 - 0.5 * alpha) * fama[i - 1]
    return mama, fama


def laguerre_rsi(price, gamma):
    """Ehlers Laguerre RSI (0..1): RSI logic over a 4-stage Laguerre filter."""
    p = np.asarray(price, dtype=float)
    N = len(p)
    out = np.full(N, np.nan)
    l0p = l1p = l2p = l3p = 0.0
    for i in range(N):
        l0 = (1 - gamma) * p[i] + gamma * l0p
        l1 = -gamma * l0 + l0p + gamma * l1p
        l2 = -gamma * l1 + l1p + gamma * l2p
        l3 = -gamma * l2 + l2p + gamma * l3p
        cu = max(l0 - l1, 0) + max(l1 - l2, 0) + max(l2 - l3, 0)
        cd = max(l1 - l0, 0) + max(l2 - l1, 0) + max(l3 - l2, 0)
        out[i] = cu / (cu + cd) if (cu + cd) > 0 else 0.5
        l0p, l1p, l2p, l3p = l0, l1, l2, l3
    return out


def schaff_trend_cycle(close, fast, slow, cycle):
    """Schaff Trend Cycle (0..100): double stochastic of the MACD line."""
    c = np.asarray(close, dtype=float)
    macd = _ema(c, fast) - _ema(c, slow)
    N = len(c)

    def _stoch_smooth(x):
        lo, hi = _roll_min(x, cycle), _roll_max(x, cycle)
        out = np.full(N, np.nan)
        pf = np.nan
        for i in range(N):
            if np.isnan(lo[i]) or hi[i] == lo[i]:
                k = pf if not np.isnan(pf) else 50.0
            else:
                k = 100.0 * (x[i] - lo[i]) / (hi[i] - lo[i])
            pf = k if np.isnan(pf) else pf + 0.5 * (k - pf)
            out[i] = pf
        return out

    return _stoch_smooth(_stoch_smooth(macd))


def cyber_cycle(price, alpha):
    """Ehlers Cyber Cycle oscillator (~0)."""
    p = np.asarray(price, dtype=float)
    N = len(p)
    sm = np.zeros(N)
    cy = np.zeros(N)
    for i in range(N):
        if i < 3:
            sm[i] = p[i]
            continue
        sm[i] = (p[i] + 2 * p[i - 1] + 2 * p[i - 2] + p[i - 3]) / 6.0
        cy[i] = ((1 - 0.5 * alpha) ** 2 * (sm[i] - 2 * sm[i - 1] + sm[i - 2])
                 + 2 * (1 - alpha) * cy[i - 1] - (1 - alpha) ** 2 * cy[i - 2])
    return cy


def center_of_gravity(price, n):
    """Ehlers Center-of-Gravity oscillator (~0)."""
    p = np.asarray(price, dtype=float)
    N = len(p)
    out = np.full(N, np.nan)
    w = 1 + np.arange(n)
    for i in range(n - 1, N):
        seg = p[i - n + 1:i + 1][::-1]     # seg[j] = price[i-j]
        den = seg.sum()
        out[i] = (-np.dot(w, seg) / den + (n + 1) / 2.0) if den != 0 else 0.0
    return out


def dominant_cycle(price):
    """Ehlers homodyne-discriminator dominant cycle period + the 4-bar weighted smooth price."""
    p = np.asarray(price, dtype=float)
    N = len(p)
    z = lambda: np.zeros(N)  # noqa: E731
    sm, dt, i1, q1, ji, jq, i2, q2, re, im, per, sper = (z() for _ in range(12))
    for i in range(N):
        if i < 6:
            continue
        adj = 0.075 * per[i - 1] + 0.54
        sm[i] = (4 * p[i] + 3 * p[i - 1] + 2 * p[i - 2] + p[i - 3]) / 10.0
        dt[i] = (0.0962 * sm[i] + 0.5769 * sm[i - 2] - 0.5769 * sm[i - 4] - 0.0962 * sm[i - 6]) * adj
        q1[i] = (0.0962 * dt[i] + 0.5769 * dt[i - 2] - 0.5769 * dt[i - 4] - 0.0962 * dt[i - 6]) * adj
        i1[i] = dt[i - 3]
        ji[i] = (0.0962 * i1[i] + 0.5769 * i1[i - 2] - 0.5769 * i1[i - 4] - 0.0962 * i1[i - 6]) * adj
        jq[i] = (0.0962 * q1[i] + 0.5769 * q1[i - 2] - 0.5769 * q1[i - 4] - 0.0962 * q1[i - 6]) * adj
        i2[i] = 0.2 * (i1[i] - jq[i]) + 0.8 * i2[i - 1]
        q2[i] = 0.2 * (q1[i] + ji[i]) + 0.8 * q2[i - 1]
        re[i] = 0.2 * (i2[i] * i2[i - 1] + q2[i] * q2[i - 1]) + 0.8 * re[i - 1]
        im[i] = 0.2 * (i2[i] * q2[i - 1] - q2[i] * i2[i - 1]) + 0.8 * im[i - 1]
        pv = 360.0 / np.degrees(np.arctan(im[i] / re[i])) if (im[i] != 0 and re[i] != 0) else per[i - 1]
        if per[i - 1] > 0:
            pv = min(max(pv, 0.67 * per[i - 1]), 1.5 * per[i - 1])
        pv = min(max(pv, 6.0), 50.0)
        per[i] = 0.2 * pv + 0.8 * per[i - 1]
        sper[i] = 0.33 * per[i] + 0.67 * sper[i - 1]
    return sper, sm


def hilbert_sinewave(price):
    """Ehlers Sine Wave: (sine, leadsine) from the dominant-cycle phase (DCPhase)."""
    sper, sm = dominant_cycle(price)
    N = len(price)
    sine = np.full(N, np.nan)
    lead = np.full(N, np.nan)
    for i in range(N):
        dc = int(sper[i] + 0.5)
        if dc < 1 or i < dc:
            continue
        rp = ip = 0.0
        for count in range(dc):
            ang = np.radians(360.0 * count / dc)
            rp += np.sin(ang) * sm[i - count]
            ip += np.cos(ang) * sm[i - count]
        dcphase = np.degrees(np.arctan(ip / rp)) if abs(rp) > 1e-3 else 90.0
        dcphase += 90.0
        if rp < 0:
            dcphase += 180.0
        if dcphase > 315.0:
            dcphase -= 360.0
        sine[i] = np.sin(np.radians(dcphase))
        lead[i] = np.sin(np.radians(dcphase + 45.0))
    return sine, lead
