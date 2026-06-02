"""Self-contained realized-volatility + HAR forecast (no repo imports).

Reproduces the meta-prophet computation exactly:
  per 4h bar:  rv_pts = sqrt( sum of 1-min squared log-returns within the bar ) * bar_close
  HAR forecast (causal):  vf[i] = 0.5*rv[i-1] + 0.3*mean(rv[i-6:i]) + 0.2*mean(rv[i-30:i])

The HAR forecast `vf` drives the volatility GATE (skip bars whose vf is above a percentile).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rv_pts(df4: pd.DataFrame, df1: pd.DataFrame) -> np.ndarray:
    """Per-4h-bar realized volatility in points, from the 1-min closes."""
    m = df1[["Date", "Close"]].copy()
    m["lr"] = np.log(m["Close"] / m["Close"].shift(1))
    mt = m["Date"].to_numpy()
    lr = m["lr"].to_numpy()
    starts = df4["Date"].to_numpy()
    closes = df4["Close"].to_numpy(float)
    rv = np.full(len(df4), np.nan)
    for i, T in enumerate(starts):
        end = T + np.timedelta64(4, "h")
        seg = lr[(mt >= T) & (mt < end)]
        seg = seg[~np.isnan(seg)]
        if len(seg) > 1:
            rv[i] = np.sqrt(np.sum(seg ** 2)) * closes[i]
    return rv


def har_forecast(rv: np.ndarray) -> np.ndarray:
    """Causal HAR-RV forecast (uses only past bars). Warmup filled with the median."""
    rv = pd.Series(rv).ffill().bfill().to_numpy()
    n = len(rv)
    vf = np.full(n, np.nan)
    for i in range(n):
        if i >= 30:
            vf[i] = 0.5 * rv[i - 1] + 0.3 * rv[i - 6:i].mean() + 0.2 * rv[i - 30:i].mean()
    return np.where(np.isfinite(vf), vf, np.nanmedian(vf))


def vol_forecast(df4: pd.DataFrame, df1: pd.DataFrame) -> np.ndarray:
    return har_forecast(compute_rv_pts(df4, df1))
