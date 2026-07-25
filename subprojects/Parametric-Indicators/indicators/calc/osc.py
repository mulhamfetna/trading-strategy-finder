"""Momentum / oscillator primitives (pure, causal). Return float arrays; NaN during warm-up.

Depends on numpy + leaf primitives in indicators/classic.py. `nan_ema` seeds at the first finite
value (classic.ema seeds at bar 0 and would poison a NaN-warmup input such as RSI)."""
from __future__ import annotations

import numpy as np

from ..classic import _roll_max, _roll_min
from ..classic import ema as _ema
from ..classic import rma as _rma
from ..classic import rsi as _rsi
from ..classic import sma as _sma
from ..classic import true_range as _tr
from .ma import _rolling_sum


def nan_ema(x: np.ndarray, n: int) -> np.ndarray:
    """EMA (alpha=2/(n+1)) that seeds at the first finite value and holds through interior NaNs.
    Use when the input carries a NaN warm-up (RSI, stochastic) — classic.ema would go all-NaN."""
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    fin = np.where(~np.isnan(x))[0]
    if len(fin) == 0:
        return out
    a = 2.0 / (n + 1.0)
    s = int(fin[0])
    out[s] = x[s]
    for t in range(s + 1, len(x)):
        out[t] = out[t - 1] if np.isnan(x[t]) else a * x[t] + (1.0 - a) * out[t - 1]
    return out


def roll_sum_safe(x: np.ndarray, n: int) -> np.ndarray:
    """Rolling sum tolerant of LEADING NaN (warm-up): result is NaN until the full window is finite,
    then the true sum. Avoids the cumsum-poisoning of classic.sma / calc.ma._rolling_sum."""
    x = np.asarray(x, dtype=float)
    N = len(x)
    s = np.full(N, np.nan)
    if N < n or n <= 0:
        return s
    xf = np.where(np.isnan(x), 0.0, x)
    c = np.cumsum(xf)
    s[n - 1] = c[n - 1]
    s[n:] = c[n:] - c[:-n]
    valid = (~np.isnan(x)).astype(float)
    vc = np.cumsum(valid)
    w = np.full(N, 0.0)
    w[n - 1] = vc[n - 1]
    w[n:] = vc[n:] - vc[:-n]
    s[w < n] = np.nan
    return s


def nan_sma(x: np.ndarray, n: int) -> np.ndarray:
    """SMA tolerant of leading NaN (see roll_sum_safe)."""
    return roll_sum_safe(x, n) / n


def _shift(x: np.ndarray, k: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if 0 < k < len(x):
        out[k:] = x[:-k]
    elif k == 0:
        out[:] = x
    return out


# --- simple momentum ---
def momentum(close, n):
    c = np.asarray(close, dtype=float)
    return c - _shift(c, n)


def roc(close, n):
    c = np.asarray(close, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * (c / _shift(c, n) - 1.0)


def disparity(close, n):
    c = np.asarray(close, dtype=float)
    m = _sma(c, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * (c / m - 1.0)


def bias(close, n):
    c = np.asarray(close, dtype=float)
    m = _sma(c, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * (c - m) / m


def williams_r(high, low, close, n):
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    hh, ll = _roll_max(h, n), _roll_min(l, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return -100.0 * (hh - c) / (hh - ll)


def cmo(close, n):
    c = np.asarray(close, dtype=float)
    d = np.diff(c)
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    su, sd = _rolling_sum(up, n), _rolling_sum(dn, n)
    out = np.full(len(c), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[1:] = 100.0 * (su - sd) / (su + sd)
    return out


def psy(close, n):
    c = np.asarray(close, dtype=float)
    up = (np.diff(c) > 0).astype(float)
    out = np.full(len(c), np.nan)
    out[1:] = 100.0 * _rolling_sum(up, n) / n
    return out


def balance_of_power(openp, high, low, close, n):
    o, h, l, c = map(lambda a: np.asarray(a, float), (openp, high, low, close))
    with np.errstate(invalid="ignore", divide="ignore"):
        bop = (c - o) / (h - l)
    return _sma(bop, n)


# --- RSI variants ---
def rsi_cutler(close, n):
    """Cutler's RSI — SMA smoothing of gains/losses (vs Wilder's RMA)."""
    c = np.asarray(close, dtype=float)
    d = np.diff(c)
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    ag, al = _rolling_sum(up, n) / n, _rolling_sum(dn, n) / n
    out = np.full(len(c), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        rs = ag / al
        out[1:] = 100.0 - 100.0 / (1.0 + rs)
        out[1:][al == 0] = 100.0
    return out


def connors_rsi(close, rsi_n=3, streak_n=2, rank_n=100):
    """Connors RSI = mean(RSI(close,rsi_n), RSI(streak,streak_n), PercentRank(ROC1,rank_n))."""
    c = np.asarray(close, dtype=float)
    N = len(c)
    r1 = _rsi(c, rsi_n)
    # streak: consecutive up/down count
    streak = np.zeros(N)
    for i in range(1, N):
        if c[i] > c[i - 1]:
            streak[i] = streak[i - 1] + 1 if streak[i - 1] > 0 else 1
        elif c[i] < c[i - 1]:
            streak[i] = streak[i - 1] - 1 if streak[i - 1] < 0 else -1
        else:
            streak[i] = 0
    r2 = _rsi(streak, streak_n)
    roc1 = np.full(N, np.nan)
    roc1[1:] = (c[1:] / c[:-1] - 1.0) * 100.0
    pr = np.full(N, np.nan)
    for i in range(rank_n, N):
        win = roc1[i - rank_n:i]
        pr[i] = 100.0 * np.mean(win < roc1[i])
    return (r1 + r2 + pr) / 3.0


def rmi(close, n, m):
    """Relative Momentum Index — RSI of the m-bar momentum, Wilder-smoothed over n."""
    c = np.asarray(close, dtype=float)
    N = len(c)
    mom = np.full(N, np.nan)
    mom[m:] = c[m:] - c[:-m]
    up = np.where(mom > 0, mom, 0.0)
    dn = np.where(mom < 0, -mom, 0.0)
    au, ad = _rma(up, n), _rma(dn, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 - 100.0 / (1.0 + au / ad)


def dynamic_dmi(close, n):
    """Chande Dynamic Momentum Index — RSI whose period shrinks when volatility rises.
    td = n / (std5 / SMA10(std5)), clamped to [3, 2n]; then Wilder RSI over td (per-bar period)."""
    c = np.asarray(close, dtype=float)
    N = len(c)
    std5 = np.full(N, np.nan)
    for i in range(4, N):
        std5[i] = c[i - 4:i + 1].std()
    vi = std5 / nan_sma(std5, 10)
    out = np.full(N, np.nan)
    d = np.diff(c)
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    for i in range(1, N):
        if np.isnan(vi[i]) or vi[i] <= 0:
            continue
        td = int(round(n / vi[i]))
        td = max(3, min(td, 2 * n))
        if i < td:
            continue
        au = up[i - td:i].mean()
        ad = dn[i - td:i].mean()
        out[i] = 100.0 if ad == 0 else 100.0 - 100.0 / (1.0 + au / ad)
    return out


# --- stochastic family ---
def stoch_rsi(close, n, k, d):
    """Stochastic of RSI(n) over k, %D = SMA(%K, d). Returns %K (0..100)."""
    r = _rsi(close, n)
    hh, ll = _roll_max(r, k), _roll_min(r, k)
    with np.errstate(invalid="ignore", divide="ignore"):
        kk = 100.0 * (r - ll) / (hh - ll)
    return kk


def kdj_k(high, low, close, n):
    """KDJ %K line: K = (2/3)K_prev + (1/3)RSV, RSV = 100·(close−LLn)/(HHn−LLn)."""
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    hh, ll = _roll_max(h, n), _roll_min(l, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        rsv = 100.0 * (c - ll) / (hh - ll)
    out = np.full(len(c), np.nan)
    fin = np.where(~np.isnan(rsv))[0]
    if len(fin) == 0:
        return out
    s = int(fin[0])
    out[s] = rsv[s]
    for i in range(s + 1, len(c)):
        out[i] = (2.0 / 3.0) * out[i - 1] + (1.0 / 3.0) * (rsv[i] if not np.isnan(rsv[i]) else out[i - 1])
    return out


def smi(high, low, close, n, smooth):
    """Blau Stochastic Momentum Index (−100..100): double-EMA of (close − midpoint) over range/2."""
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    hh, ll = _roll_max(h, n), _roll_min(l, n)
    mid = (hh + ll) / 2.0
    diff = c - mid
    rng = hh - ll
    ds = nan_ema(nan_ema(diff, smooth), smooth)
    rs = nan_ema(nan_ema(rng, smooth), smooth)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * ds / (0.5 * rs)


# --- double-smoothed momentum ---
def tsi(close, r, s):
    """True Strength Index (−100..100): 100·EMA_s(EMA_r(Δc)) / EMA_s(EMA_r(|Δc|))."""
    c = np.asarray(close, dtype=float)
    pc = np.zeros(len(c))
    pc[1:] = np.diff(c)
    num = _ema(_ema(pc, r), s)
    den = _ema(_ema(np.abs(pc), r), s)
    with np.errstate(invalid="ignore", divide="ignore"):
        out = 100.0 * num / den
    out[0] = np.nan
    return out


def rvgi(openp, high, low, close, n):
    """Relative Vigor Index: SWMA(close−open) / SWMA(high−low), summed over n. Weights (1,2,2,1)/6."""
    o, h, l, c = map(lambda a: np.asarray(a, float), (openp, high, low, close))
    def swma(x):
        out = np.full(len(x), np.nan)
        for i in range(3, len(x)):
            out[i] = (x[i] + 2 * x[i - 1] + 2 * x[i - 2] + x[i - 3]) / 6.0
        return out
    num = roll_sum_safe(swma(c - o), n)
    den = roll_sum_safe(swma(h - l), n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / den


def rvgi_signal(rvi):
    """4-period symmetric-weighted signal of the RVI line."""
    out = np.full(len(rvi), np.nan)
    for i in range(3, len(rvi)):
        seg = rvi[i - 3:i + 1]
        if np.isnan(seg).any():
            continue
        out[i] = (seg[3] + 2 * seg[2] + 2 * seg[1] + seg[0]) / 6.0
    return out


def ultimate_osc(high, low, close, s1=7, s2=14, s3=28):
    """Williams Ultimate Oscillator (0..100), weighted 4/2/1 across three look-backs."""
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    pc = _shift(c, 1)
    bp = c - np.minimum(l, pc)
    tr = np.maximum(h, pc) - np.minimum(l, pc)
    def avg(k):
        return roll_sum_safe(bp, k) / roll_sum_safe(tr, k)
    with np.errstate(invalid="ignore", divide="ignore"):
        return 100.0 * (4 * avg(s1) + 2 * avg(s2) + avg(s3)) / 7.0


def wavetrend(high, low, close, n1, n2):
    """LazyBear WaveTrend line wt1 = EMA(ci, n2), ci = (ap−esa)/(0.015·d)."""
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    ap = (h + l + c) / 3.0
    esa = _ema(ap, n1)
    d = _ema(np.abs(ap - esa), n1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ci = np.where(d > 0, (ap - esa) / (0.015 * d), 0.0)
    return nan_ema(ci, n2)


def fisher(high, low, n):
    """Ehlers Fisher Transform of the normalized median price. Returns the fisher line."""
    h, l = np.asarray(high, float), np.asarray(low, float)
    mp = (h + l) / 2.0
    hh, ll = _roll_max(mp, n), _roll_min(mp, n)
    N = len(mp)
    val = np.zeros(N)
    fish = np.full(N, np.nan)
    prev_v, prev_f = 0.0, 0.0
    for i in range(N):
        if np.isnan(hh[i]) or hh[i] == ll[i]:
            continue
        raw = 2.0 * (mp[i] - ll[i]) / (hh[i] - ll[i]) - 1.0
        v = 0.33 * raw + 0.67 * prev_v
        v = min(max(v, -0.999), 0.999)
        f = 0.5 * np.log((1 + v) / (1 - v)) + 0.5 * prev_f
        fish[i] = f
        prev_v, prev_f = v, f
    return fish


def derivative_osc(close, rsi_n, s1, s2, signal):
    """DiNapoli Derivative Oscillator: double-smoothed RSI minus its SMA signal."""
    r = _rsi(close, rsi_n)
    smoothed = nan_ema(nan_ema(r, s1), s2)
    return smoothed - nan_sma(smoothed, signal)


def ergodic(close, r, s, signal):
    """Blau Ergodic = TSI line minus its EMA signal."""
    t = tsi(close, r, s)
    return t - nan_ema(t, signal)


def pgo(high, low, close, n):
    """Pretty Good Oscillator: (close − SMA(close,n)) / EMA(TR, n)."""
    h, l, c = map(lambda a: np.asarray(a, float), (high, low, close))
    tr = _tr(h, l, c)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (c - _sma(c, n)) / _ema(tr, n)
