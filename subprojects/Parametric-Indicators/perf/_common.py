"""Shared helpers for the backtester speed-optimization safety net (task #210, Phase 0).

Loads a per-timeframe champion bundle (decision candles + 1-minute frame + box + HAR-RV forecast +
the full tuned preset) the SAME way strategy.build_payload consumes it, and exposes the indicator
wiring so we can capture per-decision-bar votes. Pure read-only — never mutates engine code or data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_PROJ = _HERE.parent
sys.path.insert(0, str(_PROJ))

import config                                  # noqa: E402
from loader import load_data                   # noqa: E402
from volatility import vol_forecast            # noqa: E402
from optimize import timeframes as TF          # noqa: E402
import presets                                 # noqa: E402

ROOT = config.DATA_ROOT.parent
RAW = ROOT / TF.RAW_DIR
BOX_CSV = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]    # the wsh4 champion set (1m excluded from that sweep)


def champion_preset(tf: str) -> dict:
    """The full dashboard preset for the 1-min-trained champion of this timeframe."""
    p = next(s["preset"] for s in presets.strategies() if s["id"] == f"wsi1m_{tf}")
    p = dict(p); p["window"] = "full"
    return p


def load_bundle(tf: str):
    """Return (df_dec, df1, box, vf, n2025, preset) for `tf` — exactly what build_payload expects."""
    df_dec = load_data(str(RAW / f"NQ_{tf}.csv"))
    df1 = load_data(str(RAW / "NQ_1m.csv"))
    box = pd.read_csv(BOX_CSV)
    box["Date"] = pd.to_datetime(box["Date"]).dt.normalize()
    box = box.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)
    bar_min = int(TF.get(tf).bar_td.total_seconds() // 60)
    vf = vol_forecast(df_dec, df1, bar_minutes=bar_min)
    n2025 = int((df_dec["Date"].dt.year == 2025).sum()) or len(df_dec)
    return df_dec, df1, box, vf, n2025, champion_preset(tf)


def compute_votes_named(tf: str, df_dec, df1, box, preset) -> dict:
    """Per-decision-bar vote array per ENABLED indicator (keyed by indicator .key), via the exact
    build_payload wiring (1-minute indicator source). This is the deepest golden signal — it catches
    any divergence at the indicator level even if the final trade set is unchanged."""
    from indicators import library, runner
    inds = library.from_specs(preset["indicators"])
    bar_td = TF.get(tf).bar_td
    t0 = df_dec["Date"].iloc[0]; t1 = df_dec["Date"].iloc[-1] + bar_td
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    src = runner.indicator_source_1min(df_dec, d1, bar_td)
    votes = runner.compute_votes(df_dec, box, inds, src=src)   # {id(ind): np.ndarray}
    out = {}
    for i in inds:
        v = votes.get(id(i))
        if v is not None and i.config.enabled:
            out[i.key] = np.asarray(v)
    return out
