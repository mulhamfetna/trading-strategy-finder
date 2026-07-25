"""Trend / directional primitives (pure, causal). Return float arrays (or tuples); NaN during warm-up.

Reuses classic.py leaves + the NaN-safe helpers in calc/osc.py."""
from __future__ import annotations

import numpy as np

from ..classic import _roll_max, _roll_min
from ..classic import atr as _atr
from ..classic import ema as _ema
from ..classic import rma as _rma
from ..classic import rsi as _rsi
from ..classic import sma as _sma
from ..classic import true_range as _tr
from .ma import wma as _wma
from .osc import _shift, nan_ema, nan_sma, roc as _roc, roll_sum_safe


def ppo(close, fast, slow):
    ef, es = _ema(close, fast), _ema(close, slow)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * (ef - es) / es


def apo(close, fast, slow):
    return _ema(close, fast) - _ema(close, slow)


def plus_minus_di(high, low, close, n):
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    N = len(c)
    up = np.zeros(N)
    dn = np.zeros(N)
    up[1:] = h[1:] - h[:-1]
    dn[1:] = l[:-1] - l[1:]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = _tr(h, l, c)
    atr = _rma(tr, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * _rma(pdm, n) / atr, 100.0 * _rma(mdm, n) / atr


def aroon(high, low, n):
    h, l = np.asarray(high, float), np.asarray(low, float)
    N = len(h)
    up = np.full(N, np.nan)
    dn = np.full(N, np.nan)
    for i in range(n, N):
        wh, wl = h[i - n:i + 1], l[i - n:i + 1]
        since_high = n - int(np.argmax(wh))    # bars since highest high (0 = current bar)
        since_low = n - int(np.argmin(wl))
        up[i] = 100.0 * (n - since_high) / n
        dn[i] = 100.0 * (n - since_low) / n
    return up, dn


def psar(high, low, step, maxstep):
    h, l = np.asarray(high, float), np.asarray(low, float)
    N = len(h)
    sar = np.full(N, np.nan)
    if N < 2:
        return sar
    trend = 1
    af = step
    ep = h[0]
    sar[0] = l[0]
    for i in range(1, N):
        prev = sar[i - 1]
        if trend == 1:
            cur = prev + af * (ep - prev)
            cur = min(cur, l[i - 1], l[i - 2] if i >= 2 else l[i - 1])
            if l[i] < cur:
                trend, cur, ep, af = -1, ep, l[i], step
            elif h[i] > ep:
                ep, af = h[i], min(af + step, maxstep)
        else:
            cur = prev + af * (ep - prev)
            cur = max(cur, h[i - 1], h[i - 2] if i >= 2 else h[i - 1])
            if h[i] > cur:
                trend, cur, ep, af = 1, ep, h[i], step
            elif l[i] < ep:
                ep, af = l[i], min(af + step, maxstep)
        sar[i] = cur
    return sar


def vortex(high, low, close, n):
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    tr = _tr(h, l, c)
    vmp = np.abs(h - _shift(l, 1))
    vmm = np.abs(l - _shift(h, 1))
    str_ = roll_sum_safe(tr, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return roll_sum_safe(vmp, n) / str_, roll_sum_safe(vmm, n) / str_


def supertrend(high, low, close, n, m):
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    atr = _atr(h, l, c, n)
    hl2 = (h + l) / 2.0
    upper, lower = hl2 + m * atr, hl2 - m * atr
    N = len(c)
    fu = np.full(N, np.nan)
    fl = np.full(N, np.nan)
    dirn = np.full(N, np.nan)
    fin = np.where(~np.isnan(atr))[0]
    if len(fin) == 0:
        return dirn
    s = int(fin[0])
    fu[s], fl[s], dirn[s] = upper[s], lower[s], 1.0
    for i in range(s + 1, N):
        fu[i] = upper[i] if (upper[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lower[i] if (lower[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if c[i] > fu[i - 1]:
            dirn[i] = 1.0
        elif c[i] < fl[i - 1]:
            dirn[i] = -1.0
        else:
            dirn[i] = dirn[i - 1]
    return dirn


def trix(close, n):
    e = _ema(_ema(_ema(close, n), n), n)
    out = np.full(len(e), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[1:] = (e[1:] / e[:-1] - 1.0) * 10000.0
    return out


def kst(close):
    k = (nan_sma(_roc(close, 10), 10) * 1 + nan_sma(_roc(close, 15), 10) * 2
         + nan_sma(_roc(close, 20), 10) * 3 + nan_sma(_roc(close, 30), 15) * 4)
    return k


def coppock(close):
    return _wma(_roc(close, 11) + _roc(close, 14), 10)


def dpo(close, n):
    c = np.asarray(close, float)
    return c - _shift(_sma(c, n), n // 2 + 1)


def trend_intensity(close, n):
    c = np.asarray(close, float)
    dev = c - _sma(c, n)
    half = max(1, n // 2)
    sp = roll_sum_safe(np.where(dev > 0, dev, 0.0), half)
    sn = roll_sum_safe(np.where(dev < 0, -dev, 0.0), half)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * sp / (sp + sn)


def linreg_slope(close, n):
    c = np.asarray(close, float)
    t = np.arange(n, dtype=float)
    tm = t.mean()
    ss = ((t - tm) ** 2).sum()
    out = np.full(len(c), np.nan)
    for i in range(n - 1, len(c)):
        y = c[i - n + 1:i + 1]
        out[i] = ((t - tm) * (y - y.mean())).sum() / ss
    return out


def linreg_dev(close, n):
    """(close − regression endpoint, rolling std of that residual over n) — for the channel veto."""
    c = np.asarray(close, float)
    t = np.arange(n, dtype=float)
    tm = t.mean()
    ss = ((t - tm) ** 2).sum()
    reg = np.full(len(c), np.nan)
    resid_std = np.full(len(c), np.nan)
    for i in range(n - 1, len(c)):
        y = c[i - n + 1:i + 1]
        b = ((t - tm) * (y - y.mean())).sum() / ss
        a = y.mean() - b * tm
        line = a + b * t
        reg[i] = line[-1]
        resid_std[i] = np.sqrt(np.mean((y - line) ** 2))
    return c - reg, resid_std


def chandelier(high, low, close, n, m):
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    atr = _atr(h, l, c, n)
    return _roll_max(h, n) - m * atr, _roll_min(l, n) + m * atr


def chande_kroll(high, low, close, n, m, p):
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    atr = _atr(h, l, c, n)
    first_hs = _roll_max(h, n) - m * atr
    first_ls = _roll_min(l, n) + m * atr
    return _roll_max(first_hs, p), _roll_min(first_ls, p)


def qqe(close, n, sf, f):
    """QQE trend line ∈ {+1,-1}: smoothed-RSI vs its ATR-of-RSI trailing bands."""
    rsi_ma = nan_ema(_rsi(close, n), sf)
    wilder = 2 * n - 1
    delta = np.abs(rsi_ma - _shift(rsi_ma, 1))
    dar = nan_ema(nan_ema(delta, wilder), wilder) * f
    N = len(rsi_ma)
    longb = np.full(N, np.nan)
    shortb = np.full(N, np.nan)
    trend = np.full(N, np.nan)
    fin = np.where(~np.isnan(rsi_ma) & ~np.isnan(dar))[0]
    if len(fin) == 0:
        return trend
    s = int(fin[0])
    longb[s], shortb[s], trend[s] = rsi_ma[s] - dar[s], rsi_ma[s] + dar[s], 1.0
    for i in range(s + 1, N):
        nl, ns = rsi_ma[i] - dar[i], rsi_ma[i] + dar[i]
        longb[i] = max(longb[i - 1], nl) if rsi_ma[i - 1] > longb[i - 1] else nl
        shortb[i] = min(shortb[i - 1], ns) if rsi_ma[i - 1] < shortb[i - 1] else ns
        if rsi_ma[i] > shortb[i - 1]:
            trend[i] = 1.0
        elif rsi_ma[i] < longb[i - 1]:
            trend[i] = -1.0
        else:
            trend[i] = trend[i - 1]
    return trend


def elder_ray(high, low, close, n):
    e = _ema(close, n)
    return np.asarray(high, float) - e, np.asarray(low, float) - e


def asi(openp, high, low, close, limit):
    o, h, l, c = map(lambda a: np.asarray(a, float), (openp, high, low, close))
    N = len(c)
    si = np.zeros(N)
    for i in range(1, N):
        cy, oy = c[i - 1], o[i - 1]
        k = max(abs(h[i] - cy), abs(l[i] - cy))
        a1, a2, a3 = abs(h[i] - cy), abs(l[i] - cy), abs(h[i] - l[i])
        if a1 >= a2 and a1 >= a3:
            r = a1 - 0.5 * a2 + 0.25 * abs(cy - oy)
        elif a2 >= a3:
            r = a2 - 0.5 * a1 + 0.25 * abs(cy - oy)
        else:
            r = a3 + 0.25 * abs(cy - oy)
        if r != 0 and limit != 0:
            si[i] = 50.0 * ((c[i] - cy) + 0.5 * (c[i] - o[i]) + 0.25 * (cy - oy)) / r * (k / limit)
    return np.cumsum(si)


def dma(close, f, s, m):
    ddd = _sma(close, f) - _sma(close, s)
    return ddd, nan_sma(ddd, m)


def bbi(close):
    return (_sma(close, 3) + _sma(close, 6) + _sma(close, 12) + _sma(close, 24)) / 4.0
