#!/usr/bin/env python3
"""Write the TimesFM per-bar volatility-band files the reference engine reads to gate NQ entries.

For NQ 1h and 4h: forecast the full close series (cached), compute the stationary forecast band
rel_band[i] = (q90-q10)/decile_span/close at each decision bar, and write {datetime, rel_band} to
<reference_repo>/timesfm_gate/NQ_<tf>_relband.csv. The engine (l1_runner) turns this into an
allow/veto mask using an in-sample-prefix percentile threshold — NQ only, ES untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from tfm.data import DEFAULT_DATA_DIR, load_tf
from tfm.forecast_cache import forecast_arrays
from tfm.forecaster import get_forecaster
from tfm.strategy import _DECILE_SPAN_SIGMAS

OUT_DIR = DEFAULT_DATA_DIR / "timesfm_gate"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    OUT_DIR.mkdir(exist_ok=True)
    fc = get_forecaster("timesfm")  # loaded once; 1h hits cache, 4h forecasts fresh (~2 min)
    for tf in ("1h", "4h"):
        df = load_tf("NQ", tf)
        close = df["close"].to_numpy(float)
        med, qlo, qhi = forecast_arrays(df, fc, 512, 24, cache_key=f"NQ_{tf}_full", progress=True)
        rel = (qhi - qlo) / _DECILE_SPAN_SIGMAS / close
        out = pd.DataFrame({"datetime": df["datetime"].astype(str), "rel_band": rel})
        path = OUT_DIR / f"NQ_{tf}_relband.csv"
        out.to_csv(path, index=False)
        valid = int(np.isfinite(rel).sum())
        print(f"wrote {path}  ({len(out)} bars, {valid} with a forecast)")


if __name__ == "__main__":
    main()
