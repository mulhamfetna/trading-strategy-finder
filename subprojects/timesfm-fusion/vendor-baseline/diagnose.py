#!/usr/bin/env python3
"""Cheap, decisive diagnostic: does TimesFM carry ANY directional edge on price, and is its
volatility band calibrated? One forecast pass over the full series (cached), then pure numpy.

    python diagnose.py ES 1h 24
    python diagnose.py NQ 1h 24

Reports:
  - directional hit rate: sign(median-last) vs sign(realized move over horizon)
  - correlation of expected vs realized move
  - band calibration: fraction of realized terminal prices inside [q10,q90] (target ~0.80)
  - a naive threshold trade count, to see how often 'standalone direction' would even fire
"""
from __future__ import annotations

import sys

import numpy as np

from tfm.data import INSTRUMENTS, load_tf
from tfm.forecast_cache import forecast_arrays
from tfm.forecaster import get_forecaster
from tfm.strategy import _DECILE_SPAN_SIGMAS


def diagnose(instrument: str, tf: str, horizon: int, context_len: int = 512, fc=None):
    inst = INSTRUMENTS[instrument]
    df = load_tf(instrument, tf)
    close = df["close"].to_numpy(float)
    n = len(close)
    fc = fc or get_forecaster("timesfm")

    print(f"[{instrument} {tf}] bars={n} horizon={horizon} ctx={context_len} — forecasting "
          f"(one cached pass)...", flush=True)
    med, qlo, qhi = forecast_arrays(df, fc, context_len, horizon,
                                    cache_key=f"{instrument}_{tf}_full", progress=True)

    # decision bar i forecasts terminal price at i+horizon; realized = close[i+horizon]
    idx = np.arange(n)
    valid = ~np.isnan(med) & (idx + horizon < n)
    i = idx[valid]
    exp_move = med[i] - close[i]
    realized = close[i + horizon] - close[i]
    sigma = (qhi[i] - qlo[i]) / _DECILE_SPAN_SIGMAS

    # directional edge
    nz = np.abs(exp_move) > 1e-9
    hit = (np.sign(exp_move[nz]) == np.sign(realized[nz])).mean() if nz.any() else float("nan")
    corr = np.corrcoef(exp_move, realized)[0, 1] if len(i) > 2 else float("nan")

    # band calibration: is realized terminal price within [q10,q90] ~80% of the time?
    realized_price = close[i + horizon]
    inside = ((realized_price >= qlo[i]) & (realized_price <= qhi[i])).mean()

    # how big is the median drift vs the band (why standalone rarely fires)
    med_drift_pts = np.abs(exp_move).mean()
    band_pts = (qhi[i] - qlo[i]).mean()

    # naive fire rate at a couple of edge thresholds
    for k in (0.15, 0.25, 0.4):
        fires = (np.abs(exp_move) > k * sigma).mean()
        print(f"  fire-rate @ edge_k={k:>4}: {100*fires:5.1f}% of bars")

    print(f"\n  directional hit rate      : {100*hit:5.1f}%   (50% = no edge)")
    print(f"  corr(expected, realized)  : {corr:+.3f}      (~0 = no edge)")
    print(f"  band calibration inside   : {100*inside:5.1f}%   (target ~80%)")
    print(f"  mean |median drift|       : {med_drift_pts:8.2f} pts")
    print(f"  mean band (q90-q10)       : {band_pts:8.2f} pts")
    print(f"  drift / band ratio        : {med_drift_pts/band_pts:6.3f}   "
          f"(tiny => flat median => few standalone trades)")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    inst = sys.argv[1] if len(sys.argv) > 1 else "ES"
    tf = sys.argv[2] if len(sys.argv) > 2 else "1h"
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    diagnose(inst, tf, h)
