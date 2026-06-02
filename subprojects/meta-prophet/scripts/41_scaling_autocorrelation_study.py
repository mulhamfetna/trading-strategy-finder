"""Workstream C — scaling/transform vs autocorrelation study (1-min direction problem).

Question: 1-min price changes are tiny. Does transforming the target — e.g. exp(change),
sign*magnitude, standardization, vol-scaling, etc. — make the DIRECTION predictable? The only
thing that matters is whether a transform raises the **autocorrelation** (the echo the model
could learn). A monotone/affine rescale cannot add information; only switching to a different
quantity (|r|, r^2, range = volatility) changes the predictable structure.

We measure ACF(1) (and a few lags) of ~20 transforms on real NQ 1-min closes and print a table.
Pure numpy/pandas; runs locally in seconds.
"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd

CSV = sys.argv[1] if len(sys.argv) > 1 else \
    "Full_Canldes_Data/drive-download-20260602T124702Z-3-001/NQ_1m.csv"

try:
    from scipy.stats import yeojohnson
    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False


def acf(x: np.ndarray, lag: int = 1) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) <= lag + 2:
        return float("nan")
    x = x - x.mean()
    denom = (x * x).sum()
    if denom == 0:
        return float("nan")
    return float((x[:-lag] * x[lag:]).sum() / denom)


def gaussian_rank(x: np.ndarray) -> np.ndarray:
    # rank -> uniform -> normal quantile (monotone)
    from numpy import argsort
    n = len(x)
    r = np.empty(n); r[argsort(argsort(x))] = np.arange(1, n + 1)
    u = (r - 0.5) / n
    # inverse normal CDF via erfinv
    from math import sqrt
    try:
        from scipy.special import ndtri
        return ndtri(u)
    except Exception:
        return np.sqrt(2) * np.vectorize(lambda v: _erfinv(2 * v - 1))(u)


def _erfinv(y):
    # crude fallback; scipy path used when available
    a = 0.147
    ln = np.log(1 - y * y)
    t = 2 / (np.pi * a) + ln / 2
    return np.sign(y) * np.sqrt(np.sqrt(t * t - ln / a) - t)


def main() -> int:
    df = pd.read_csv(CSV, usecols=["close", "high", "low"])
    c = df["close"].astype(float).to_numpy()
    hi = df["high"].astype(float).to_numpy()
    lo = df["low"].astype(float).to_numpy()

    r = np.diff(np.log(c))                 # log return  (the "change")
    s = np.diff(c) / c[:-1]                # simple return
    rng = ((hi - lo) / c)[1:]              # bar range / close (volatility proxy), aligned to r
    n = len(r)
    band = 1.96 / np.sqrt(n)
    print(f"1-min bars: {n:,}   white-noise band: +/-{band:.4f}\n")

    roll_sd = pd.Series(r).rolling(60, min_periods=20).std().to_numpy()
    k = 1.0 / (np.std(r) + 1e-12)          # scale so tanh/arcsinh spread the tiny returns

    # --- DIRECTION-BEARING transforms (monotone or sign-preserving) ---
    transforms = {
        "r  (log return) [BASE]":      r,
        "s  (simple return)":          s,
        "exp(r)  (gross return)":      np.exp(r),
        "exp(s)":                      np.exp(s),
        "YOUR sign*(exp|r|-1)":        np.sign(r) * (np.exp(np.abs(r)) - 1),
        "YOUR sign*exp|r| (disc.)":    np.sign(r) * np.exp(np.abs(r)),
        "zscore(r)":                   (r - r.mean()) / r.std(),
        "minmax(r)":                   (r - r.min()) / (r.max() - r.min()),
        "vol-scaled r/std60":          r / roll_sd,
        "tanh(k*r)":                   np.tanh(k * r),
        "arcsinh(k*r)":                np.arcsinh(k * r),
        "sign*sqrt|r|":                np.sign(r) * np.sqrt(np.abs(r)),
        "sign*log1p(k|r|)":            np.sign(r) * np.log1p(k * np.abs(r)),
        "gaussian-rank(r)":            gaussian_rank(r),
        "diff(r)":                     np.diff(r),
        "sign(r) only":                np.sign(r),
    }
    if HAVE_SCIPY:
        try:
            transforms["yeo-johnson(r)"] = yeojohnson(r)[0]
        except Exception:
            pass

    # --- DIFFERENT-QUANTITY transforms (even / volatility) for contrast ---
    vol_transforms = {
        "|r|  (abs return)":  np.abs(r),
        "r^2 (squared)":      r * r,
        "range (hi-lo)/c":    rng,
        "log|r|":             np.log(np.abs(r) + 1e-9),
    }

    def row(name, x):
        a1 = acf(x, 1)
        flag = "  <-- predictable" if abs(a1) > 5 * band else ""
        return f"  {name:<26} ACF(1)={a1:+.4f}{flag}"

    print("== DIRECTION-BEARING transforms (can a rescale make direction predictable?) ==")
    for name, x in transforms.items():
        print(row(name, x))

    print("\n== DIFFERENT QUANTITY: volatility/even transforms (the real signal) ==")
    for name, x in vol_transforms.items():
        print(row(name, x))

    print("\n== multi-lag ACF for the key series ==")
    for name, x in [("r (direction)", r),
                    ("YOUR sign*(exp|r|-1)", np.sign(r) * (np.exp(np.abs(r)) - 1)),
                    ("|r| (volatility)", np.abs(r)),
                    ("range (volatility)", rng)]:
        lags = [acf(x, L) for L in (1, 2, 3, 5, 10)]
        print(f"  {name:<26} " + " ".join(f"L{L}={v:+.3f}" for L, v in zip((1,2,3,5,10), lags)))

    # direction-of-next-bar predictability: does sign echo?
    sgn = np.sign(r)
    print(f"\n  sign autocorrelation ACF(1) = {acf(sgn,1):+.4f}  "
          f"(prob next move same dir as last ~ {(np.mean(sgn[:-1]==sgn[1:]))*100:.2f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
