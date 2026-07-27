"""CPU cold-miss accelerators for the pathological indicators (issue #54, Task 3).

The baseline (optimize/perf/results/baseline_NQ_4h_smoke3.json) showed ONE indicator, `dfa`, is ~81% of
all cold-compute time (~83 s per compute) — a triple-nested Python loop calling `np.polyfit` per segment
over ~486,970 one-minute bars (`indicators/calc/quant.py:dfa`). This module provides a vectorized /
Numba-JIT replacement.

**Parity contract.** `np.polyfit` solves via LAPACK lstsq (SVD), so a closed-form fit is NOT bit-identical
at the float level. What must not change is the downstream VOTE: `DFA.directions` emits
`both_veto(isfinite(alpha) & (alpha < threshold))` for `threshold ∈ [0.30, 0.70]` step 0.01. So the
accelerated `alpha` must reproduce that boolean EXACTLY on the real series, across the whole threshold
grid. `test_cold_accel_parity.py` asserts float-closeness AND exact vote-boolean equality; the server
harness re-checks it on the true 1-minute frame before this is trusted. Default-OFF at the call sites.
"""
from __future__ import annotations

import numpy as np

try:
    from numba import njit
except Exception:  # pragma: no cover - numba is present on the server venv; fallback runs pure-Python
    def njit(*args, **kwargs):  # identity decorator so _dfa_core still runs (slowly) without numba
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        def deco(f):
            return f
        return deco


def _scales_for(n: int) -> list[int]:
    """The reference's scale set (depends only on n): sorted unique {4, n//8, n//4, n//2} within
    [4, (n-1)//2]. Kept byte-identical to calc/quant.py:dfa so both see the same scales."""
    return sorted({s for s in (4, n // 8, n // 4, n // 2) if 4 <= s <= (n - 1) // 2})


@njit(cache=True, fastmath=False)
def _dfa_core(c, n, scales):
    """Rolling DFA-alpha, closed-form linear detrend (no polyfit), one pass. Mirrors the reference's
    arithmetic order (r - mean(r); cumsum; per-segment OLS residual mean-square; sqrt(mean(F2));
    log-log slope) but in scalar float64 so Numba reproduces it deterministically. fastmath=False keeps
    IEEE semantics (no reassociation) — essential for reproducing the vote threshold."""
    N = c.shape[0]
    out = np.full(N, np.nan)
    ns = scales.shape[0]
    if ns < 2:
        return out
    m = n - 1                                   # length of the returns/profile window
    # precompute per-scale t-centering constants (t = 0..s-1)
    for i in range(n - 1, N):
        # returns r[k] = c[i-n+2+k] - c[i-n+1+k], k=0..m-1
        rmean = 0.0
        for k in range(m):
            rmean += c[i - n + 2 + k] - c[i - n + 1 + k]
        rmean /= m
        # detrended profile y = cumsum(r - rmean)
        y = np.empty(m)
        acc = 0.0
        for k in range(m):
            acc += (c[i - n + 2 + k] - c[i - n + 1 + k]) - rmean
            y[k] = acc
        valid = 0
        sum_log_l = 0.0
        sum_log_f = 0.0
        sum_log_ll = 0.0
        sum_log_lf = 0.0
        all_pos = True
        for si in range(ns):
            s = scales[si]
            nb = m // s
            if nb < 1:
                continue
            # t stats for t = 0..s-1 (fixed per scale)
            tbar = (s - 1) / 2.0
            sxx = 0.0
            for tt in range(s):
                d = tt - tbar
                sxx += d * d
            f2sum = 0.0
            for b in range(nb):
                base = b * s
                # segment mean
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
                # residual mean-square = (Sdd - b^2 * Sxx) / s  (closed form of mean((seg - a - b t)^2))
                f2 = (sdd - bslope * bslope * sxx) / s
                if f2 < 0.0:
                    f2 = 0.0
                f2sum += f2
            fs_val = np.sqrt(f2sum / nb)
            if fs_val <= 0.0:
                all_pos = False
                break
            ll = np.log(float(s))
            lf = np.log(fs_val)
            sum_log_l += ll
            sum_log_f += lf
            sum_log_ll += ll * ll
            sum_log_lf += ll * lf
            valid += 1
        if valid >= 2 and all_pos:
            denom = valid * sum_log_ll - sum_log_l * sum_log_l
            if denom != 0.0:
                out[i] = (valid * sum_log_lf - sum_log_l * sum_log_f) / denom
    return out


def dfa_fast(close, n: int) -> np.ndarray:
    """Vectorized/Numba drop-in for calc.quant.dfa — same shape/NaN warm-up, closed-form detrend."""
    c = np.asarray(close, dtype=np.float64)
    scales = np.asarray(_scales_for(int(n)), dtype=np.int64)
    if scales.shape[0] < 2:
        return np.full(c.shape[0], np.nan)
    return _dfa_core(c, int(n), scales)
