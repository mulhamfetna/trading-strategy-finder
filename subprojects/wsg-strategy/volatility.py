"""Self-contained realized-volatility + HAR forecast (no repo imports).

Reproduces the meta-prophet computation exactly for the default 4h bar:
  per decision bar:  rv_pts = sqrt( sum of 1-min squared log-returns within the bar ) * bar_close
  HAR forecast (causal):  vf[i] = 0.5*rv[i-1] + 0.3*mean(rv[i-6:i]) + 0.2*mean(rv[i-30:i])

The HAR forecast `vf` drives the volatility GATE (skip bars whose vf is above a percentile).

WS-H.2 — timeframe generalisation: the realized-vol WINDOW is now the decision-bar duration
(`bar_minutes`, default 240 = 4h), so the same RV-from-1m-closes computation works for any entry
timeframe. The HAR lookback stays in *decision-bar units* (1 / 6 / 30 bars) by design (TASK.md §5.2):
the gate only needs a monotone, causal vol proxy, and keeping bar-count windows makes the gate
self-consistent per timeframe. Default args reproduce the verified 4h forecast exactly (parity-locked).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_rv_pts(df4: pd.DataFrame, df1: pd.DataFrame, bar_minutes: int = 240) -> np.ndarray:
    """Per-decision-bar realized volatility in points, from the 1-min closes.

    bar_minutes: decision-bar duration in minutes (240 = 4h, the default/verified case).
    """
    m = df1[["Date", "Close"]].copy()
    m["lr"] = np.log(m["Close"] / m["Close"].shift(1))
    mt = m["Date"].to_numpy()
    lr = m["lr"].to_numpy()
    starts = df4["Date"].to_numpy()
    closes = df4["Close"].to_numpy(float)
    dur = np.timedelta64(int(bar_minutes), "m")
    rv = np.full(len(df4), np.nan)
    for i, T in enumerate(starts):
        end = T + dur
        seg = lr[(mt >= T) & (mt < end)]
        seg = seg[~np.isnan(seg)]
        if len(seg) > 1:
            rv[i] = np.sqrt(np.sum(seg ** 2)) * closes[i]
    return rv


def har_forecast(rv: np.ndarray) -> np.ndarray:
    """Causal HAR-RV forecast (uses only past bars). Warmup filled with the median.
    Lookback windows are in decision-bar units (1 / 6 / 30 bars) — see module docstring."""
    rv = pd.Series(rv).ffill().bfill().to_numpy()
    n = len(rv)
    vf = np.full(n, np.nan)
    for i in range(n):
        if i >= 30:
            vf[i] = 0.5 * rv[i - 1] + 0.3 * rv[i - 6:i].mean() + 0.2 * rv[i - 30:i].mean()
    return np.where(np.isfinite(vf), vf, np.nanmedian(vf))


def vol_forecast(df4: pd.DataFrame, df1: pd.DataFrame, bar_minutes: int = 240) -> np.ndarray:
    """HAR-RV forecast for an arbitrary decision timeframe (bar_minutes); default 4h."""
    return har_forecast(compute_rv_pts(df4, df1, bar_minutes=bar_minutes))
