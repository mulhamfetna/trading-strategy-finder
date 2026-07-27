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


def dfa_reference(close, n):
    """REFERENCE (slow) rolling DFA exponent — kept verbatim as the parity oracle for `dfa` below.

    Measured at ~248 s over the 486,969-bar 1-minute frame (n=100): a triple-nested Python loop calling
    np.polyfit per segment. `dfa()` dispatches to a Numba closed-form equivalent that is ~1,400× faster
    and vote-identical; this stays as the thing that equivalence is proven AGAINST (issue #54).
    """
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


# --- fast DFA (issue #54) ---------------------------------------------------------------------------
# The reference above dominated optimizer cold-compute (~81% of it). This replaces the per-segment
# np.polyfit with the closed-form OLS slope + residual mean-square, in a single Numba pass.
# fastmath=False keeps IEEE semantics (no reassociation) so the result is reproducible.
# NOTE ON PARITY: np.polyfit solves via LAPACK lstsq, so the two paths are NOT bit-identical in float;
# what is proven (optimize/perf/test_cold_accel_parity.py + bench_dfa.py on the real 1-minute frame) is
# that the DOWNSTREAM VETO VOTE — both_veto(isfinite(alpha) & (alpha < threshold)) — is IDENTICAL across
# the entire threshold grid [0.30, 0.70]. Without numba we fall back to the reference (slow but correct),
# so a missing optional dependency can never change a result.
try:                                                        # pragma: no cover - trivial import guard
    from numba import njit as _njit
    _HAVE_NUMBA = True
except Exception:                                           # pragma: no cover
    _HAVE_NUMBA = False

    def _njit(*args, **kwargs):
        def deco(f):
            return f
        return deco


@_njit(cache=True, fastmath=False)
def _dfa_core(c, n, scales):
    N = c.shape[0]
    out = np.full(N, np.nan)
    ns = scales.shape[0]
    if ns < 2:
        return out
    m = n - 1                                               # number of returns in the window
    for i in range(n - 1, N):
        rmean = 0.0
        for k in range(m):
            rmean += c[i - n + 2 + k] - c[i - n + 1 + k]
        rmean /= m
        y = np.empty(m)                                     # detrended profile = cumsum(r - mean(r))
        acc = 0.0
        for k in range(m):
            acc += (c[i - n + 2 + k] - c[i - n + 1 + k]) - rmean
            y[k] = acc
        valid = 0
        s_l = 0.0
        s_f = 0.0
        s_ll = 0.0
        s_lf = 0.0
        all_pos = True
        for si in range(ns):
            s = scales[si]
            nb = m // s
            if nb < 1:
                continue
            tbar = (s - 1) / 2.0
            sxx = 0.0
            for tt in range(s):
                d = tt - tbar
                sxx += d * d
            f2sum = 0.0
            for b in range(nb):
                base = b * s
                segbar = 0.0
                for tt in range(s):
                    segbar += y[base + tt]
                segbar /= s
                sdt = 0.0
                sdd = 0.0
                for tt in range(s):
                    dd = y[base + tt] - segbar
                    sdt += dd * (tt - tbar)
                    sdd += dd * dd
                bslope = sdt / sxx
                f2 = (sdd - bslope * bslope * sxx) / s      # closed-form residual mean-square
                if f2 < 0.0:
                    f2 = 0.0
                f2sum += f2
            fs_val = np.sqrt(f2sum / nb)
            if fs_val <= 0.0:
                all_pos = False
                break
            ll = np.log(float(s))
            lf = np.log(fs_val)
            s_l += ll
            s_f += lf
            s_ll += ll * ll
            s_lf += ll * lf
            valid += 1
        if valid >= 2 and all_pos:
            denom = valid * s_ll - s_l * s_l
            if denom != 0.0:
                out[i] = (valid * s_lf - s_l * s_f) / denom
    return out


def dfa(close, n):
    """Rolling detrended-fluctuation exponent alpha of the window's returns (few log-spaced scales).

    Fast path (numba) when available; otherwise the verbatim `dfa_reference`. Vote-identical to the
    reference — see the parity note above.
    """
    if not _HAVE_NUMBA:
        return dfa_reference(close, n)
    c = np.asarray(close, dtype=np.float64)
    scales = np.asarray(
        sorted({s for s in (4, n // 8, n // 4, n // 2) if 4 <= s <= (n - 1) // 2}), dtype=np.int64)
    if scales.shape[0] < 2:
        return np.full(c.shape[0], np.nan)
    return _dfa_core(c, int(n), scales)


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
