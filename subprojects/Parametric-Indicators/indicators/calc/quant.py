"""Statistical / quant primitives (pure, causal). Hurst & DFA are computed on the RETURN series so a
random walk gives ~0.5 (persistence >0.5 = trending, <0.5 = mean-reverting/chop)."""
from __future__ import annotations

import numpy as np

from ..classic import sma as _sma
from .osc import _shift, roll_sum_safe
from .vol import rolling_std


def zscore(close, n):
    c = np.asarray(close, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (c - _sma(c, n)) / rolling_std(c, n)


def hurst_exp(close, n):
    """Rolling R/S Hurst of the window's returns. H≈0.5 random, >0.5 persistent, <0.5 mean-reverting."""
    c = np.asarray(close, float)
    N = len(c)
    out = np.full(N, np.nan)
    for i in range(n - 1, N):
        r = np.diff(c[i - n + 1:i + 1])
        s = r.std()
        if s <= 0:
            continue
        y = np.cumsum(r - r.mean())
        rng = y.max() - y.min()
        if rng > 0:
            out[i] = np.log(rng / s) / np.log(len(r))
    return out


def dfa(close, n):
    """Rolling detrended-fluctuation exponent alpha of the window's returns (few log-spaced scales)."""
    c = np.asarray(close, float)
    N = len(c)
    out = np.full(N, np.nan)
    scales = sorted({s for s in (4, n // 8, n // 4, n // 2) if 4 <= s <= (n - 1) // 2})
    if len(scales) < 2:
        return out
    for i in range(n - 1, N):
        r = np.diff(c[i - n + 1:i + 1])
        y = np.cumsum(r - r.mean())
        fs, ls = [], []
        for s in scales:
            nb = len(y) // s
            if nb < 1:
                continue
            f2 = []
            t = np.arange(s)
            for b in range(nb):
                seg = y[b * s:(b + 1) * s]
                coef = np.polyfit(t, seg, 1)
                f2.append(np.mean((seg - np.polyval(coef, t)) ** 2))
            fs.append(np.sqrt(np.mean(f2)))
            ls.append(s)
        fs = np.asarray(fs)
        if len(fs) >= 2 and np.all(fs > 0):
            out[i] = np.polyfit(np.log(ls), np.log(fs), 1)[0]
    return out


def autocorr(close, n, lag=1):
    """Lag-`lag` autocorrelation of returns over the last n returns."""
    c = np.asarray(close, float)
    r = np.diff(c)
    N = len(c)
    out = np.full(N, np.nan)
    for i in range(n + 1, N):
        w = r[i - n:i]
        a, b = w[lag:], w[:-lag]
        if a.std() > 0 and b.std() > 0:
            out[i] = np.corrcoef(a, b)[0, 1]
    return out


def demarker(high, low, n):
    h, l = np.asarray(high, float), np.asarray(low, float)
    dh = h - _shift(h, 1)
    dl = _shift(l, 1) - l
    demax = np.where(dh > 0, dh, 0.0)
    demin = np.where(dl > 0, dl, 0.0)
    demax[~np.isfinite(demax)] = 0.0
    demin[~np.isfinite(demin)] = 0.0
    smax, smin = _sma(demax, n), _sma(demin, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return smax / (smax + smin)


def td_rei(high, low, n=5):
    """Simplified TD Range Expansion Index (−100..100): 2-bar high/low expansion, summed over n."""
    h, l = np.asarray(high, float), np.asarray(low, float)
    dh = h - _shift(h, 2)
    dl = l - _shift(l, 2)
    num = roll_sum_safe(dh + dl, n)
    den = roll_sum_safe(np.abs(dh) + np.abs(dl), n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * num / den


def linreg_r2(close, n):
    c = np.asarray(close, float)
    t = np.arange(n, dtype=float)
    tm = t.mean()
    tss = ((t - tm) ** 2).sum()
    out = np.full(len(c), np.nan)
    for i in range(n - 1, len(c)):
        y = c[i - n + 1:i + 1]
        ym = y.mean()
        b = ((t - tm) * (y - ym)).sum() / tss
        pred = (ym - b * tm) + b * t
        sst = ((y - ym) ** 2).sum()
        out[i] = 1.0 - ((y - pred) ** 2).sum() / sst if sst > 0 else 0.0
    return out


def efficiency_ratio(close, n):
    """Kaufman efficiency ratio (0..1): |net change| / sum(|bar changes|) over n."""
    c = np.asarray(close, float)
    absd = np.abs(np.diff(c))
    out = np.full(len(c), np.nan)
    for i in range(n, len(c)):
        vol = absd[i - n:i].sum()
        out[i] = abs(c[i] - c[i - n]) / vol if vol > 0 else 0.0
    return out
