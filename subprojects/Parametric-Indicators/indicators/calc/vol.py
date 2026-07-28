"""Volatility primitives (pure, causal). Return float arrays; NaN during warm-up.

Most feed the magnitude-veto convention (value vs its own EMA); a few are bounded (choppiness, mass
index) or band-based (STARC/accel/projection)."""
from __future__ import annotations

import numpy as np

from .. import classic
from .._numba import HAVE_NUMBA as _HAVE_NUMBA, njit as _njit, pw_mean as _pw_mean, pw_sum as _pw_sum
from ..classic import _roll_max, _roll_min
from ..classic import atr as _atr
from ..classic import ema as _ema
from ..classic import sma as _sma
from ..classic import true_range as _tr
from .osc import roc as _roc, roll_sum_safe


def rolling_std(x, n):
    """Population rolling std (ddof=0); NaN for windows with any NaN (matches classic.bollinger)."""
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        win = np.lib.stride_tricks.sliding_window_view(x, n)
        out[n - 1:] = win.std(axis=1)
    return out


def _rolling_var(x, n, ddof=1):
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        win = np.lib.stride_tricks.sliding_window_view(x, n)
        out[n - 1:] = win.var(axis=1, ddof=ddof)
    return out


# --- positive-magnitude vols (magnitude-veto) ---
def atr_norm(high, low, close, n):
    return _atr(high, low, close, n) / np.asarray(close, float)


def stddev(close, n):
    return rolling_std(np.asarray(close, float), n)


def hist_vol(close, n, annual=252.0):
    c = np.asarray(close, float)
    lr = np.full(len(c), np.nan)
    lr[1:] = np.log(c[1:] / c[:-1])
    return rolling_std(lr, n) * np.sqrt(annual)


def parkinson(high, low, n):
    h, l = np.asarray(high, float), np.asarray(low, float)
    lr2 = np.log(h / l) ** 2
    return np.sqrt(roll_sum_safe(lr2, n) / (4.0 * n * np.log(2.0)))


def garman_klass(openp, high, low, close, n):
    o, h, l, c = map(lambda a: np.asarray(a, float), (openp, high, low, close))
    term = 0.5 * np.log(h / l) ** 2 - (2.0 * np.log(2.0) - 1.0) * np.log(c / o) ** 2
    return np.sqrt(np.maximum(roll_sum_safe(term, n) / n, 0.0))


def rogers_satchell(openp, high, low, close, n):
    o, h, l, c = map(lambda a: np.asarray(a, float), (openp, high, low, close))
    term = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    return np.sqrt(np.maximum(roll_sum_safe(term, n) / n, 0.0))


def yang_zhang(openp, high, low, close, n):
    o, h, l, c = map(lambda a: np.asarray(a, float), (openp, high, low, close))
    N = len(c)
    oc = np.log(c / o)
    on = np.full(N, np.nan)
    on[1:] = np.log(o[1:] / c[:-1])
    vo = _rolling_var(on, n)
    vc = _rolling_var(oc, n)
    rs_term = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    vrs = roll_sum_safe(rs_term, n) / n
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    return np.sqrt(np.maximum(vo + k * vc + (1.0 - k) * vrs, 0.0))


def ulcer_reference(close, n):
    """FROZEN reference for `ulcer` — the ORIGINAL per-bar window loop (issue #62)."""
    c = np.asarray(close, float)
    out = np.full(len(c), np.nan)
    for i in range(n - 1, len(c)):
        w = c[i - n + 1:i + 1]
        peak = np.maximum.accumulate(w)
        dd = 100.0 * (w - peak) / peak
        out[i] = np.sqrt(np.mean(dd ** 2))
    return out


@_njit(cache=True, nogil=True, fastmath=False)
def _ulcer_core(c, n):
    N = c.shape[0]
    out = np.full(N, np.nan)
    sq = np.empty(n)
    for i in range(n - 1, N):
        peak = c[i - n + 1]
        for k in range(n):
            v = c[i - n + 1 + k]
            # `np.maximum.accumulate` POISONS the running peak from a NaN onward — reproduce that,
            # rather than a bare `>` which would silently step over the NaN.
            if np.isnan(peak) or np.isnan(v):
                peak = np.nan
            elif v > peak:
                peak = v
            dd = 100.0 * (v - peak) / peak
            sq[k] = dd * dd
        out[i] = np.sqrt(_pw_sum(sq, 0, n) / n)
    return out


def ulcer(close, n):
    """Ulcer Index — RMS percentage drawdown from the running window peak.

    Numba-accelerated (issue #62), summing with `pw_sum` so the reduction matches numpy's pairwise
    order **bit-for-bit**. `ulcer_reference` is the oracle and is used verbatim when Numba is absent.
    """
    c = np.asarray(close, float)
    if not _HAVE_NUMBA or n <= 0:
        return ulcer_reference(c, n)
    return _ulcer_core(np.ascontiguousarray(c), int(n))


def vol_ratio(high, low, close, n_fast, n_slow):
    with np.errstate(invalid="ignore", divide="ignore"):
        return _atr(high, low, close, n_fast) / _atr(high, low, close, n_slow)


# --- 0-centred / bounded vols ---
def chaikin_vol(high, low, n, roc_n):
    e = _ema(np.asarray(high, float) - np.asarray(low, float), n)
    return _roc(e, roc_n)


def rvi_dorsey(close, n, stdlen=10):
    """Relative Volatility Index (Dorsey): RSI logic on rolling std, up-days vs down-days."""
    c = np.asarray(close, float)
    s = rolling_std(c, stdlen)
    d = np.full(len(c), np.nan)
    d[1:] = np.diff(c)
    u = np.where(d > 0, s, 0.0)
    dn = np.where(d < 0, s, 0.0)
    au, ad = classic.rma(u, n), classic.rma(dn, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * au / (au + ad)


def mass_index(high, low, n):
    rng = np.asarray(high, float) - np.asarray(low, float)
    e1 = _ema(rng, 9)
    e2 = _ema(e1, 9)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = e1 / e2
    return roll_sum_safe(ratio, n)


def choppiness(high, low, close, n):
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    s = roll_sum_safe(_tr(h, l, c), n)
    rng = _roll_max(h, n) - _roll_min(l, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * np.log10(s / rng) / np.log10(n)


def ttm_squeeze(high, low, close, n):
    """1.0 when Bollinger(n,2) sits INSIDE Keltner(n,1.5) (squeeze on), else 0.0."""
    _, bu, bl = classic.bollinger(np.asarray(close, float), n, 2.0)
    _, ku, kl = classic.keltner(high, low, close, n, 1.5)
    on = (bl > kl) & (bu < ku)
    return on.astype(float)


# --- bands (band-veto) ---
def starc(high, low, close, n, m):
    mid = _sma(np.asarray(close, float), n)
    a = _atr(high, low, close, n)
    return mid + m * a, mid - m * a


def accel_bands(high, low, close, n, f):
    h, l = np.asarray(high, float), np.asarray(low, float)
    hl = (h - l) / (h + l)
    return _sma(h * (1.0 + f * hl), n), _sma(l * (1.0 - f * hl), n)


def proj_bands_reference(high, low, n):
    """FROZEN reference for `proj_bands` — the ORIGINAL per-bar regression loop (issue #62)."""
    h, l = np.asarray(high, float), np.asarray(low, float)
    N = len(h)
    upper = np.full(N, np.nan)
    lower = np.full(N, np.nan)
    t = np.arange(n, dtype=float)
    tm = t.mean()
    ss = ((t - tm) ** 2).sum()
    for i in range(n - 1, N):
        wh, wl = h[i - n + 1:i + 1], l[i - n + 1:i + 1]
        sh = ((t - tm) * (wh - wh.mean())).sum() / ss
        sl = ((t - tm) * (wl - wl.mean())).sum() / ss
        fwd = n - 1 - t                                # bars forward to the current bar
        upper[i] = np.max(wh + sh * fwd)
        lower[i] = np.min(wl + sl * fwd)
    return upper, lower


@_njit(cache=True, nogil=True, fastmath=False)
def _proj_bands_core(h, l, n, t, tm, ss):
    N = h.shape[0]
    upper = np.full(N, np.nan)
    lower = np.full(N, np.nan)
    ph = np.empty(n); pl = np.empty(n)
    for i in range(n - 1, N):
        mh = _pw_mean(h, i - n + 1, n)
        ml = _pw_mean(l, i - n + 1, n)
        for k in range(n):
            w = t[k] - tm
            ph[k] = w * (h[i - n + 1 + k] - mh)
            pl[k] = w * (l[i - n + 1 + k] - ml)
        sh = _pw_sum(ph, 0, n) / ss
        sl = _pw_sum(pl, 0, n) / ss
        hi = -np.inf
        lo = np.inf
        bad = False
        for k in range(n):
            fwd = n - 1 - t[k]
            uv = h[i - n + 1 + k] + sh * fwd
            lv = l[i - n + 1 + k] + sl * fwd
            if np.isnan(uv) or np.isnan(lv):       # np.max/np.min propagate NaN; `>`/`<` do not
                bad = True
            if uv > hi:
                hi = uv
            if lv < lo:
                lo = lv
        upper[i] = np.nan if bad else hi
        lower[i] = np.nan if bad else lo
    return upper, lower


def proj_bands(high, low, n):
    """Mickey Jordan projection bands: each bar's high/low extended by its window regression slope.

    Numba-accelerated (issue #62), summing with `pw_sum` so every reduction matches numpy's pairwise
    order **bit-for-bit**, and propagating NaN through the window extremes the way `np.max`/`np.min`
    do. `proj_bands_reference` is the oracle and is used verbatim when Numba is absent.
    """
    h, l = np.asarray(high, float), np.asarray(low, float)
    if not _HAVE_NUMBA or n <= 0:
        return proj_bands_reference(h, l, n)
    t = np.arange(n, dtype=float)
    tm = t.mean()
    ss = ((t - tm) ** 2).sum()
    return _proj_bands_core(np.ascontiguousarray(h), np.ascontiguousarray(l), int(n), t, tm, ss)
