"""The 882-release surprise ledger + causal forward returns.

The ledger is the COMMITTED artifact optimize/fundamentals/surprises_cache.csv -- the exact data behind the
pooled directional null (-0.004, n=882, 99% power), so conditional results are comparable to it directly.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

_LEDGER = Path(__file__).resolve().parents[1] / "optimize" / "fundamentals" / "surprises_cache.csv"


def load_ledger(path: Path | None = None) -> pd.DataFrame:
    """One row per release: Date, event, actual, expected, raw_surprise, surprise_z."""
    p = Path(path) if path is not None else _LEDGER
    if not p.exists():
        raise FileNotFoundError(f"surprise ledger not found: {p}")
    d = pd.read_csv(p, parse_dates=["Date"])
    need = {"Date", "event", "surprise_z"}
    missing = need - set(d.columns)
    if missing:
        raise ValueError(f"ledger missing columns: {sorted(missing)}")
    return d.sort_values("Date").reset_index(drop=True)


def attach_returns(sur: pd.DataFrame, df1: pd.DataFrame, horizons: Sequence[int]) -> pd.DataFrame:
    """Add ret_{h} = close[T+h] - close[T-1] in points, where T is the release minute.

    Anchored at close[T-1] (08:29) so the entire measured move is AFTER the print -- matches
    study_surprise.py's convention exactly. NaN when either the anchor or the horizon bar is absent.

    Vectorized via reindex rather than a per-row lookup: the price frame is 5.45M rows and a Python-level
    loop over it would dominate the runtime.
    """
    if not len(horizons):
        raise ValueError("horizons must be non-empty")
    px = df1.set_index("Date")["Close"]
    px = px[~px.index.duplicated(keep="last")]

    ts = pd.DatetimeIndex(sur["Date"])
    anchor = px.reindex(ts - pd.Timedelta(minutes=1)).to_numpy(dtype=float)

    out = sur.copy()
    for h in horizons:
        if h < 1:
            raise ValueError(f"horizon must be >= 1 minute, got {h}")
        fwd = px.reindex(ts + pd.Timedelta(minutes=h)).to_numpy(dtype=float)
        out[f"ret_{h}"] = fwd - anchor
    return out
