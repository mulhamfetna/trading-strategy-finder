#!/usr/bin/env python3
"""Run TimesFM 2.5 over the 2024-2026 NQ 1h series and write the causal forecast band per bar.

Uses the vendored tfm harness (forecast_arrays -> disk cache). Real model, CPU. First call downloads
google/timesfm-2.5-200m-pytorch (~200MB) and compiles; then batched inference over ~14k bars.

Output: nq_2426_relband.csv  {datetime, rel_band}  where rel_band = (q90-q10)/decile_span/close,
the same stationary volatility band the teammate's gate uses. Cached forecasts -> re-runs are free.

Env: FUTURES_DATA_DIR must point at the dir holding NQ_1h.csv (the 2024-2026 slice).
Run (isolated venv):  python3 forecast_2426.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor-baseline"))
from tfm.data import load_tf                       # noqa: E402
from tfm.forecast_cache import forecast_arrays     # noqa: E402
from tfm.forecaster import get_forecaster          # noqa: E402
from tfm.strategy import _DECILE_SPAN_SIGMAS       # noqa: E402


def main():
    df = load_tf("NQ", "1h")
    close = df["close"].to_numpy(float)
    print(f"NQ 1h loaded: {len(df)} bars  {df['datetime'].min()} -> {df['datetime'].max()}", flush=True)
    print("running TimesFM 2.5 (first call downloads+compiles the model)...", flush=True)
    med, qlo, qhi = forecast_arrays(df, get_forecaster("timesfm"), 512, 24,
                                    cache_key="NQ_1h_2426_full", progress=True)
    rel = (qhi - qlo) / _DECILE_SPAN_SIGMAS / close
    out = pd.DataFrame({"datetime": df["datetime"].astype(str), "rel_band": rel})
    path = HERE / "nq_2426_relband.csv"
    out.to_csv(path, index=False)
    valid = int(np.isfinite(rel).sum())
    print(f"WROTE {path}  ({len(out)} bars, {valid} with a forecast)", flush=True)
    print("FORECAST_2426_DONE", flush=True)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
