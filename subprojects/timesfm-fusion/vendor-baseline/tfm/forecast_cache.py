"""Compute + disk-cache the expensive forecast arrays, so threshold sweeps are ~free.

For each decision bar i (i >= context_len-1, i < n-1) we store the TERMINAL forecast (median,
q_low, q_high at the horizon end) and the last close. Everything the strategy needs (direction,
edge, vol-adaptive SL/TP, vol gate) derives from those three numbers, so a full grid over
edge_k / min_edge / sl / tp / gate reuses one cached forecast pass.

Cache key = (instrument, tf, split, model, context_len, horizon, n_bars). Invalidated automatically
when the data length changes. Files live under FUTURES/.cache/*.npz.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .forecaster import Forecaster

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache"


def forecast_arrays(df: pd.DataFrame, forecaster: Forecaster, context_len: int, horizon: int,
                    cache_key: str | None = None, batch_size: int = 256,
                    progress: bool = False) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (median_end, q_low_end, q_high_end), each shape (n,), NaN where no forecast.

    median_end[i] etc. are the terminal-horizon forecast made from close[..i]; the strategy uses
    them to decide the entry at bar i+1. Cached to disk when `cache_key` is given.
    """
    n = len(df)
    if cache_key:
        CACHE_DIR.mkdir(exist_ok=True)
        path = CACHE_DIR / f"{cache_key}_{forecaster.name}_ctx{context_len}_h{horizon}_n{n}.npz"
        if path.exists():
            z = np.load(path)
            return z["med"], z["qlo"], z["qhi"]

    close = df["close"].to_numpy(dtype=float)
    med = np.full(n, np.nan)
    qlo = np.full(n, np.nan)
    qhi = np.full(n, np.nan)
    decision_idx = list(range(context_len - 1, n - 1))

    for start in range(0, len(decision_idx), batch_size):
        chunk = decision_idx[start:start + batch_size]
        contexts = [close[i - context_len + 1: i + 1] for i in chunk]
        for i, fc in zip(chunk, forecaster.forecast_batch(contexts, horizon)):
            med[i] = fc.median[-1]
            qlo[i] = fc.q_low[-1]
            qhi[i] = fc.q_high[-1]
        if progress and (start // batch_size) % 20 == 0:
            print(f"    forecast {start + len(chunk)}/{len(decision_idx)}", flush=True)

    if cache_key:
        np.savez_compressed(path, med=med, qlo=qlo, qhi=qhi)
    return med, qlo, qhi
