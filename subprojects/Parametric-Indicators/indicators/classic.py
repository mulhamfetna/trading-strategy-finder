"""Group A — classic technical-indicator math (numpy/pandas, causal, no look-ahead).

Each function takes 1-D float arrays of the decision-timeframe series and returns a 1-D float array
of the same length (NaN during the warm-up period). These are the raw indicator series; the
confirm/veto vote layer (indicators/confirm.py) is built on top. See docs/INDICATORS.md §3–16.

STUBS — implementations follow the TDD cycle (tests/test_classic.py). A stub returns all-NaN so the
hand-computed assertions fail for the right reason (wrong value), not an import/typo error.
"""
from __future__ import annotations

import numpy as np

from ._numba import HAVE_NUMBA as _HAVE_NUMBA, njit as _njit


def _nan_like(x) -> np.ndarray:
    return np.full(len(x), np.nan, dtype=float)


def sma(close: np.ndarray, n: int) -> np.ndarray:
    """Simple moving average over the last n closes. NaN for the first n-1 bars."""
    x = np.asarray(close, dtype=float)
    out = _nan_like(x)
    if n <= 0 or len(x) < n:
        return out
    csum = np.cumsum(x)
    out[n - 1] = csum[n - 1] / n
    out[n:] = (csum[n:] - csum[:-n]) / n
    return out


@_njit(cache=True, nogil=True, fastmath=False)
def _ema_core(x, a):
    N = x.shape[0]
    out = np.full(N, np.nan)
    out[0] = x[0]
    for t in range(1, N):
        out[t] = a * x[t] + (1.0 - a) * out[t - 1]
    return out


def ema(close: np.ndarray, n: int) -> np.ndarray:
    """Exponential MA, alpha = 2/(n+1), seeded with close[0].

    The recurrence is sequential, so the Numba kernel performs the SAME operations in the SAME order
    with `fastmath=False` — bit-identical, not merely close (issue #62). Reference: `_reference.ema_ref`.
    """
    x = np.asarray(close, dtype=float)
    if len(x) == 0:
        return _nan_like(x)
    a = 2.0 / (n + 1.0)
    if not _HAVE_NUMBA:
        from ._reference import ema_ref
        return ema_ref(x, n)
    return _ema_core(np.ascontiguousarray(x), a)


def rma(x: np.ndarray, n: int) -> np.ndarray:
    """Wilder's smoothing (RMA), alpha = 1/n, seeded at the first finite value.
    Leading NaNs stay NaN; a NaN after the seed holds the previous value (so a transient
    undefined input — e.g. ADX's 0/0 DX — does not poison the whole series). Used by RSI/ATR/ADX."""
    v = np.asarray(x, dtype=float)
    out = _nan_like(v)
    finite = np.where(~np.isnan(v))[0]
    if len(finite) == 0:
        return out
    a = 1.0 / n
    s = int(finite[0])
    if not _HAVE_NUMBA:
        from ._reference import rma_ref
        return rma_ref(v, n)
    return _rma_core(np.ascontiguousarray(v), a, s)


@_njit(cache=True, nogil=True, fastmath=False)
def _rma_core(v, a, s):
    """Sequential recurrence — same ops, same order, `fastmath=False` ⇒ bit-identical (issue #62)."""
    N = v.shape[0]
    out = np.full(N, np.nan)
    out[s] = v[s]
    for t in range(s + 1, N):
        if np.isnan(v[t]):
            out[t] = out[t - 1]
        else:
            out[t] = a * v[t] + (1.0 - a) * out[t - 1]
    return out


def rsi(close: np.ndarray, n: int) -> np.ndarray:
    """Wilder RSI. avg gain/loss seeded as SMA of the first n deltas, then RMA-smoothed.
    NaN for the first n bars."""
    c = np.asarray(close, dtype=float)
    out = _nan_like(c)
    if len(c) <= n:
        return out
    delta = np.diff(c)                       # length len-1, delta[i] = c[i+1]-c[i]
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    # SMA seed over the first n deltas (indices 0..n-1 of delta -> bar n).
    ag = gain[:n].mean()
    al = loss[:n].mean()
    for t in range(n, len(c)):
        if t > n:
            g = gain[t - 1]
            l = loss[t - 1]
            ag = (ag * (n - 1) + g) / n
            al = (al * (n - 1) + l) / n
        rs = np.inf if al == 0 else ag / al
        out[t] = 100.0 - 100.0 / (1.0 + rs)
    return out


def true_range(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """True range. TR[0]=high[0]-low[0]; TR[t]=max(H-L,|H-prevC|,|L-prevC|)."""
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    c = np.asarray(close, dtype=float)
    out = np.empty(len(c), dtype=float)
    out[0] = h[0] - l[0]
    if len(c) > 1:
        pc = c[:-1]
        out[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - pc), np.abs(l[1:] - pc)])
    return out


def atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    """Average true range = RMA(true_range, n), seeded at TR[0]."""
    return rma(true_range(high, low, close), n)


def macd(close: np.ndarray, fast: int, slow: int, signal: int):
    """Returns (macd_line, signal_line, hist).
    macd_line = ema(close,fast)-ema(close,slow); signal_line = ema(macd_line,signal);
    hist = macd_line - signal_line."""
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def obv(close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """On-Balance Volume. OBV[0] = 0; then += sign(close[t]-close[t-1]) * volume[t].

    Vectorized prefix-sum (task #210): OBV[1:] = cumsum(sign(diff(close)) * volume[1:]). Mathematically
    identical to the original per-bar loop — np.sign matches (sign(0)=0) and NaN propagates the same way
    (a NaN diff makes that term NaN, and cumsum carries it forward exactly as the loop's running add did).
    Frozen reference: indicators/_reference.obv_ref; equivalence: tests/test_speedopt_equiv.py.
    """
    c = np.asarray(close, dtype=float)
    vol = np.asarray(volume, dtype=float)
    out = np.zeros(len(c), dtype=float)
    if len(c) > 1:
        out[1:] = np.cumsum(np.sign(np.diff(c)) * vol[1:])
    return out


@_njit(cache=True, nogil=True, fastmath=False)
def _roll_extreme_core(x, n, want_max):
    """O(N) monotonic-deque rolling extreme. EXACT, not approximate: max/min select an existing element,
    so there is no floating-point reassociation — the result is bit-identical to the per-bar `np.max`
    loop it replaces. NaN is handled by an explicit in-window counter (numpy propagates NaN through
    max/min, and NaN never enters the deque), so the NaN pattern matches exactly too."""
    N = x.shape[0]
    out = np.full(N, np.nan)
    dq = np.empty(N, dtype=np.int64)          # indices, values monotonically decreasing (max) / increasing (min)
    head = 0
    tail = 0                                  # deque occupies dq[head:tail]
    nan_count = 0
    for i in range(N):
        v = x[i]
        if np.isnan(v):
            nan_count += 1
        else:
            while tail > head and not (x[dq[tail - 1]] > v if want_max else x[dq[tail - 1]] < v):
                tail -= 1
            dq[tail] = i
            tail += 1
        drop = i - n                          # index leaving the window this bar
        if drop >= 0:
            if np.isnan(x[drop]):
                nan_count -= 1
            elif tail > head and dq[head] == drop:
                head += 1
        if i >= n - 1:
            out[i] = np.nan if nan_count > 0 else x[dq[head]]
    return out


def _roll_max(x, n):
    """Rolling maximum over the last n values (NaN until the window fills, NaN if the window holds one).

    PERFORMANCE (issue #62): this is the single most-shared primitive in the indicator library — 19 call
    sites feeding ichimoku, smi, chande_kroll, chandelier, stochastic, frama, schaff and more. The original
    per-bar `np.max(x[t-n+1:t+1])` loop paid Python interpreter overhead **once per bar**, which alone put
    four indicators over the 2 s full-frame budget (`ichimoku_cloud` 3.43 s at DEFAULT parameters). The
    monotonic-deque kernel is O(N) regardless of `n` and bit-identical — see `_roll_extreme_core`.
    Frozen reference: `indicators/_reference.roll_max_ref`; gate: `tests/test_speedopt_equiv.py`.
    """
    if not _HAVE_NUMBA or n <= 0:            # a missing optional dep must never change a number
        return _reference_roll("max", x, n)
    return _roll_extreme_core(np.ascontiguousarray(np.asarray(x, dtype=float)), int(n), True)


def _roll_min(x, n):
    """Rolling minimum over the last n values. See `_roll_max` for the performance note."""
    if not _HAVE_NUMBA or n <= 0:
        return _reference_roll("min", x, n)
    return _roll_extreme_core(np.ascontiguousarray(np.asarray(x, dtype=float)), int(n), False)


def _reference_roll(which, x, n):
    from ._reference import roll_max_ref, roll_min_ref
    return (roll_max_ref if which == "max" else roll_min_ref)(np.asarray(x, dtype=float), n)


def stochastic(high, low, close, n: int, d: int):
    """Returns (%K, %D). %K = 100*(C - minLow_n)/(maxHigh_n - minLow_n); %D = SMA(%K, d)."""
    h = np.asarray(high, float); l = np.asarray(low, float); c = np.asarray(close, float)
    hh = _roll_max(h, n); ll = _roll_min(l, n)
    rng = hh - ll
    k = _nan_like(c)
    valid = ~np.isnan(rng) & (rng != 0)
    k[valid] = 100.0 * (c[valid] - ll[valid]) / rng[valid]
    # %D = SMA(%K, d). Vectorised with a sliding window so each window's mean is computed with the
    # SAME float ops as the old per-bar loop (mean of a window containing a NaN is NaN — matches the
    # loop's "only when no NaN in window"). Bitwise-identical to the loop.
    dline = _nan_like(c)
    if len(c) >= d:
        dline[d - 1:] = np.lib.stride_tricks.sliding_window_view(k, d).mean(axis=1)
    return k, dline


def cci(high, low, close, n: int) -> np.ndarray:
    """Commodity Channel Index over typical price TP=(H+L+C)/3, factor 0.015, mean abs deviation.

    Vectorized (task #210): rolling mean-abs-deviation via a sliding window — |win - SMA|.mean(axis=1) —
    the SAME per-window reduction the loop ran. The mad==0 → 0 guard and edge convention (NaN for t<n-1,
    NaN windows) are preserved exactly. Frozen reference: indicators/_reference.cci_ref; equivalence:
    tests/test_speedopt_equiv.py (incl. a constant-price mad==0 case; vote-hash must stay byte-identical).
    """
    h = np.asarray(high, float); l = np.asarray(low, float); c = np.asarray(close, float)
    tp = (h + l + c) / 3.0
    m = sma(tp, n)
    out = _nan_like(c)
    if len(c) >= n:
        win = np.lib.stride_tricks.sliding_window_view(tp, n)        # (len-n+1, n)
        mad = np.abs(win - m[n - 1:, None]).mean(axis=1)             # mean abs deviation per window
        num = tp[n - 1:] - m[n - 1:]
        with np.errstate(divide="ignore", invalid="ignore"):
            res = num / (0.015 * mad)
        out[n - 1:] = np.where(mad == 0, 0.0, res)                  # mad==0 -> 0 (matches the loop guard)
    return out


def bollinger(close, n: int, k: float):
    """Returns (mid, upper, lower). mid=SMA(n); band = mid ± k*rolling_std (population, ddof=0).

    Vectorized rolling std (task #210): a sliding window of width n, std over axis 1 (population,
    ddof=0) — the SAME per-window reduction the loop ran, in one batched pass. Edge convention preserved
    (std is NaN for t<n-1, and NaN for any window containing a NaN). Frozen reference:
    indicators/_reference.bollinger_ref; equivalence: tests/test_speedopt_equiv.py (tight tolerance, and
    the per-decision-bar vote-hash must stay byte-identical — checked by perf/check_golden.py).
    """
    c = np.asarray(close, float)
    mid = sma(c, n)
    std = _nan_like(c)
    if len(c) >= n:
        win = np.lib.stride_tricks.sliding_window_view(c, n)   # shape (len-n+1, n)
        std[n - 1:] = win.std(axis=1)                          # ddof=0 population std per window
    return mid, mid + k * std, mid - k * std


def keltner(high, low, close, n: int, m: float):
    """Returns (mid, upper, lower). mid=EMA(n); band = mid ± m*ATR(n)."""
    mid = ema(close, n)
    a = atr(high, low, close, n)
    return mid, mid + m * a, mid - m * a


def vwap(high, low, close, volume, session_id: np.ndarray) -> np.ndarray:
    """Session-anchored VWAP: cumulative(typical*vol)/cumulative(vol), reset when session_id changes.
    typical = (H+L+C)/3."""
    h = np.asarray(high, float); l = np.asarray(low, float); c = np.asarray(close, float)
    vol = np.asarray(volume, float); sess = np.asarray(session_id)
    tp = (h + l + c) / 3.0
    out = _nan_like(c)
    cpv = cv = 0.0; cur = None
    for t in range(len(c)):
        if cur is None or sess[t] != cur:
            cur = sess[t]; cpv = cv = 0.0
        cpv += tp[t] * vol[t]; cv += vol[t]
        out[t] = cpv / cv if cv != 0 else np.nan
    return out


def mfi(high, low, close, volume, n: int) -> np.ndarray:
    """Money Flow Index over n. raw flow = typical*vol, split by typical-price change; NaN first n."""
    h = np.asarray(high, float); l = np.asarray(low, float); c = np.asarray(close, float)
    vol = np.asarray(volume, float)
    tp = (h + l + c) / 3.0
    flow = tp * vol
    pos = np.zeros(len(tp)); neg = np.zeros(len(tp))
    for t in range(1, len(tp)):
        if tp[t] > tp[t - 1]:
            pos[t] = flow[t]
        elif tp[t] < tp[t - 1]:
            neg[t] = flow[t]
    out = _nan_like(c)
    if len(tp) > n:                                       # rolling sums via sliding window (exact)
        ps = np.lib.stride_tricks.sliding_window_view(pos, n).sum(axis=1)   # window-end idx n-1..
        qs = np.lib.stride_tricks.sliding_window_view(neg, n).sum(axis=1)
        ratio = np.where(qs == 0, np.inf, ps / np.where(qs == 0, 1.0, qs))
        mfi_end = 100.0 - 100.0 / (1.0 + ratio)
        out[n:] = mfi_end[1:]                             # original starts at t=n (skips t=n-1)
    return out


def adx(high, low, close, n: int):
    """Returns (adx, +DI, -DI) via Wilder DM/TR smoothing (RMA)."""
    h = np.asarray(high, float); l = np.asarray(low, float); c = np.asarray(close, float)
    pdm = np.zeros(len(c)); ndm = np.zeros(len(c))
    for t in range(1, len(c)):
        up = h[t] - h[t - 1]
        dn = l[t - 1] - l[t]
        pdm[t] = up if (up > dn and up > 0) else 0.0
        ndm[t] = dn if (dn > up and dn > 0) else 0.0
    atr_ = rma(true_range(h, l, c), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100.0 * rma(pdm, n) / atr_
        mdi = 100.0 * rma(ndm, n) / atr_
        dx = 100.0 * np.abs(pdi - mdi) / (pdi + mdi)
    return rma(dx, n), pdi, mdi
