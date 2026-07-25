"""Moving-average primitives (pure, vectorized/recursive, causal). Each returns a float array the
length of the input; NaN (or a soft seed) during warm-up. Depends only on numpy + the leaf
primitives in indicators/classic.py (ema/sma) — unit-testable against independent oracles."""
from __future__ import annotations

import numpy as np

from ..classic import ema as _ema


def _rolling_sum(x: np.ndarray, n: int) -> np.ndarray:
    """Sum of the last n values; NaN for the first n-1 bars."""
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    if n <= 0 or len(x) < n:
        return out
    c = np.cumsum(x)
    out[n - 1] = c[n - 1]
    out[n:] = c[n:] - c[:-n]
    return out


def wma(x: np.ndarray, n: int) -> np.ndarray:
    """Linearly-weighted MA: weights 1..n (most recent = n). NaN for the first n-1 bars."""
    x = np.asarray(x, dtype=float)
    w = np.arange(1, n + 1, dtype=float)
    denom = w.sum()
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = np.dot(x[i - n + 1:i + 1], w) / denom
    return out


def dema(x: np.ndarray, n: int) -> np.ndarray:
    """Double EMA: 2·EMA − EMA(EMA)."""
    e = _ema(x, n)
    return 2.0 * e - _ema(e, n)


def tema(x: np.ndarray, n: int) -> np.ndarray:
    """Triple EMA: 3e − 3·EMA(e) + EMA(EMA(e)), e=EMA(x)."""
    e = _ema(x, n)
    e2 = _ema(e, n)
    e3 = _ema(e2, n)
    return 3.0 * e - 3.0 * e2 + e3


def tma(x: np.ndarray, n: int) -> np.ndarray:
    """Triangular MA = SMA(⌈n/2⌉)∘SMA(⌊n/2⌋+1) (TA-Lib TRIMA convention). Implemented as the
    equivalent single triangular-kernel windowed average — SMA∘SMA via classic.sma would poison on
    the inner SMA's leading NaNs (cumsum). Kernel = boxcar(h)⊛boxcar(k), length h+k-1."""
    import math
    h = math.ceil(n / 2)
    k = n // 2 + 1
    w = np.convolve(np.ones(h), np.ones(k)) / (h * k)   # symmetric triangular weights
    L = len(w)
    x = np.asarray(x, dtype=float)
    out = np.full(len(x), np.nan)
    for i in range(L - 1, len(x)):
        out[i] = np.dot(x[i - L + 1:i + 1], w)
    return out


def hma(x: np.ndarray, n: int) -> np.ndarray:
    """Hull MA: WMA(2·WMA(n/2) − WMA(n), √n). Very low lag."""
    half = int(n // 2)
    sq = int(np.sqrt(n))
    return wma(2.0 * wma(x, half) - wma(x, n), sq)


def zlema(x: np.ndarray, n: int) -> np.ndarray:
    """Zero-lag EMA: EMA of the de-lagged series d[i]=2x[i]−x[i−lag], lag=(n−1)//2."""
    x = np.asarray(x, dtype=float)
    lag = (n - 1) // 2
    d = x.copy()
    if lag > 0:
        d[lag:] = 2.0 * x[lag:] - x[:-lag]
    return _ema(d, n)


def sine_wma(x: np.ndarray, n: int) -> np.ndarray:
    """Sine-weighted MA: weights sin(π(k+1)/(n+1)), k=0..n−1 (symmetric bell)."""
    x = np.asarray(x, dtype=float)
    k = np.arange(n)
    w = np.sin(np.pi * (k + 1) / (n + 1))
    w /= w.sum()
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = np.dot(x[i - n + 1:i + 1], w)
    return out


def vwma(x: np.ndarray, vol: np.ndarray, n: int) -> np.ndarray:
    """Volume-weighted MA: Σ(x·vol,n)/Σ(vol,n)."""
    x = np.asarray(x, dtype=float)
    v = np.asarray(vol, dtype=float)
    num = _rolling_sum(x * v, n)
    den = _rolling_sum(v, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / den


def lsma(x: np.ndarray, n: int) -> np.ndarray:
    """Least-squares MA: value of the OLS line (y~t) at the window's last point."""
    x = np.asarray(x, dtype=float)
    t = np.arange(n, dtype=float)
    tm = t.mean()
    ss = ((t - tm) ** 2).sum()
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        y = x[i - n + 1:i + 1]
        ym = y.mean()
        b = ((t - tm) * (y - ym)).sum() / ss
        a = ym - b * tm
        out[i] = a + b * (n - 1)
    return out


def kama(x: np.ndarray, n: int, fast: int, slow: int) -> np.ndarray:
    """Kaufman Adaptive MA. ER=|Δn|/Σ|Δ1|; smoothing sc=(ER·(fsc−ssc)+ssc)²; seeded at bar n."""
    x = np.asarray(x, dtype=float)
    N = len(x)
    out = np.full(N, np.nan)
    if N <= n:
        return out
    fsc = 2.0 / (fast + 1.0)
    ssc = 2.0 / (slow + 1.0)
    absd = np.abs(np.diff(x))                       # |Δ1|, length N-1
    out[n] = x[n]
    for i in range(n + 1, N):
        change = abs(x[i] - x[i - n])
        vol = absd[i - n:i].sum()
        er = change / vol if vol > 0 else 0.0
        sc = (er * (fsc - ssc) + ssc) ** 2
        out[i] = out[i - 1] + sc * (x[i] - out[i - 1])
    return out


def vidya(x: np.ndarray, n: int) -> np.ndarray:
    """Variable Index Dynamic Average (Chande): EMA whose gain scales with |CMO(n)|."""
    x = np.asarray(x, dtype=float)
    N = len(x)
    out = np.full(N, np.nan)
    if N <= n:
        return out
    d = np.diff(x)
    up = np.where(d > 0, d, 0.0)
    dn = np.where(d < 0, -d, 0.0)
    alpha = 2.0 / (n + 1.0)
    out[n] = x[n]
    for i in range(n + 1, N):
        su = up[i - n:i].sum()
        sd = dn[i - n:i].sum()
        k = abs(su - sd) / (su + sd) if (su + sd) > 0 else 0.0
        out[i] = alpha * k * x[i] + (1.0 - alpha * k) * out[i - 1]
    return out


def alma(x: np.ndarray, n: int, offset: float, sigma: float) -> np.ndarray:
    """Arnaud Legoux MA: Gaussian window centred at offset·(n−1), width n/sigma."""
    x = np.asarray(x, dtype=float)
    m = offset * (n - 1)
    s = n / sigma
    k = np.arange(n)
    w = np.exp(-((k - m) ** 2) / (2.0 * s * s))
    w /= w.sum()
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = np.dot(x[i - n + 1:i + 1], w)
    return out


def t3(x: np.ndarray, n: int, v: float) -> np.ndarray:
    """Tillson T3: six cascaded EMAs blended with volume-factor v."""
    e1 = _ema(x, n)
    e2 = _ema(e1, n)
    e3 = _ema(e2, n)
    e4 = _ema(e3, n)
    e5 = _ema(e4, n)
    e6 = _ema(e5, n)
    c1 = -v ** 3
    c2 = 3.0 * v ** 2 + 3.0 * v ** 3
    c3 = -6.0 * v ** 2 - 3.0 * v - 3.0 * v ** 3
    c4 = 1.0 + 3.0 * v + v ** 3 + 3.0 * v ** 2
    return c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3


def mcginley(x: np.ndarray, n: int) -> np.ndarray:
    """McGinley Dynamic: self-adjusting MA, md += (x−md)/(0.6·n·(x/md)^4). Seeded at bar 0."""
    x = np.asarray(x, dtype=float)
    N = len(x)
    out = np.full(N, np.nan)
    if N == 0:
        return out
    out[0] = x[0]
    for i in range(1, N):
        prev = out[i - 1]
        if prev == 0 or np.isnan(prev):
            out[i] = x[i]
            continue
        out[i] = prev + (x[i] - prev) / (0.6 * n * (x[i] / prev) ** 4)
    return out


def evwma(x: np.ndarray, vol: np.ndarray, n: int) -> np.ndarray:
    """Elastic Volume-Weighted MA: e = e·(V−vol)/V + x·vol/V, V=Σ(vol,n). Seeded at bar n−1."""
    x = np.asarray(x, dtype=float)
    vv = np.asarray(vol, dtype=float)
    N = len(x)
    out = np.full(N, np.nan)
    V = _rolling_sum(vv, n)
    if N < n:
        return out
    out[n - 1] = x[n - 1]
    for i in range(n, N):
        Vi = V[i]
        if Vi <= 0 or np.isnan(Vi):
            out[i] = out[i - 1]
            continue
        out[i] = out[i - 1] * (Vi - vv[i]) / Vi + x[i] * vv[i] / Vi
    return out
