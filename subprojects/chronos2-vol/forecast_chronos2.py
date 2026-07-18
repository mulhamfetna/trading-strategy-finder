#!/usr/bin/env python3
"""Chronos-2 forecast band over 2024-26 NQ 1h — same context(512)/horizon(24) as the TimesFM test,
so the vol-gate A/B is apples-to-apples. Writes nq_2426_relband_chronos.csv {datetime, rel_band}
with rel_band = (q0.9 - q0.1)/close at the terminal horizon (the forward vol band). CPU.

Run:  python3 forecast_chronos2.py <NQ_1h.csv>
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from chronos import Chronos2Pipeline

CTX, HORIZON, BATCH = 512, 24, 256
QLEVELS = [0.1, 0.5, 0.9]
HERE = Path(__file__).resolve().parent


def main():
    nq_csv = sys.argv[1]
    df = pd.read_csv(nq_csv)
    df.columns = [c.strip().lower() for c in df.columns]
    df["dt"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("dt").drop_duplicates("dt").reset_index(drop=True)
    close = df["close"].to_numpy(float)
    n = len(close)
    print(f"NQ 1h: {n} bars {df['dt'].min()} -> {df['dt'].max()}", flush=True)

    pipe = Chronos2Pipeline.from_pretrained("amazon/chronos-2", device_map="cpu")
    print("chronos-2 loaded (cpu); forecasting...", flush=True)

    dec = list(range(CTX - 1, n - 1))                    # decision bars (same as TimesFM harness)
    rel = np.full(n, np.nan)
    for s in range(0, len(dec), BATCH):
        chunk = dec[s:s + BATCH]
        ctxs = [close[i - CTX + 1:i + 1].astype(np.float32) for i in chunk]
        qf, _mean = pipe.predict_quantiles(ctxs, prediction_length=HORIZON, quantile_levels=QLEVELS)
        for i, q in zip(chunk, qf):
            q = np.asarray(q)
            if q.ndim == 3:                              # (n_targets=1, H, n_quantiles) -> (H, n_quantiles)
                q = q[0]
            qlo, qhi = q[-1, 0], q[-1, -1]               # terminal q0.1, q0.9
            rel[i] = (qhi - qlo) / close[i]
        if (s // BATCH) % 10 == 0:
            print(f"    forecast {s + len(chunk)}/{len(dec)}", flush=True)

    out = pd.DataFrame({"datetime": df["dt"].astype(str), "rel_band": rel})
    path = HERE / "nq_2426_relband_chronos.csv"
    out.to_csv(path, index=False)
    print(f"WROTE {path} ({n} bars, {int(np.isfinite(rel).sum())} with a forecast)", flush=True)
    print("FORECAST_CHRONOS_DONE", flush=True)


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
