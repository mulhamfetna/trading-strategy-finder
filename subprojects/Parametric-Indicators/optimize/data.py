"""H.3 — per-timeframe input loader.

Builds the (df_dec, df1, box, vf, n_split) bundle that core.backtest_metrics needs, for any of the
7 decision timeframes. Only the DECISION frame changes per timeframe; the 1-minute exit frame and
the box levels are shared (TASK.md §2, §4).

Sources:
  - decision frame: Full_Canldes_Data/<RAW_DIR>/NQ_<tf>.csv     (all-history, one file per TF)
  - 1-minute frame: Full_Canldes_Data/<RAW_DIR>/NQ_1m.csv       (shared exit resolution)
  - box levels:     data/full_data/NQ_full_data.csv             (shared, one row per market date)

n_split = number of decision bars in the first calendar year (config.YEARS[0], 2025); used to
freeze the gate threshold causally and to slice 2025/2026 windows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import os               # noqa: E402
import config            # noqa: E402
import roots                                 # the ONE resolver for repo/data roots (#94)
from loader import load_data  # noqa: E402
from volatility import vol_forecast  # noqa: E402
from optimize import timeframes as TF  # noqa: E402

# Base dir holding the raw timeframe CSVs (Full_Canldes_Data/...). Overridable for the server
# migration via WSH_DATA_ROOT / the legacy WSH_DATA_BASE. NEVER a hardcoded absolute path (#94):
# the old literal default was one machine's layout, so anywhere else this resolved to a tree that
# does not exist and the failure surfaced as "your code is broken".
_BASE = roots.DATA_ROOT
_RAW = _BASE / TF.RAW_DIR
_BOX_CSV = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"   # config.DATA_ROOT honours WSG_DATA_ROOT


def load_box(instrument: str = "NQ") -> pd.DataFrame:
    """Load the box-level frame, indexed by normalized Date (same shape as strategy.py). NQ uses the existing
    _BOX_CSV (byte-identical); other instruments resolve through the registry."""
    if instrument == "NQ":
        box_csv = str(_BOX_CSV)
    else:
        from optimize import instruments
        box_csv = instruments.resolve_paths(instrument, "4h")[2]
    c = pd.read_csv(box_csv)
    c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
    return c.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)


def load_inputs(tf_name: str, instrument: str = "NQ"):
    """Return (df_dec, df1, box, vf, n_split) for the given decision timeframe + instrument. NQ keeps the
    existing inline paths (golden-safe); other instruments resolve through optimize.instruments."""
    tf = TF.get(tf_name)
    if instrument == "NQ":
        dec_csv, min_csv = str(_RAW / f"NQ_{tf.name}.csv"), str(_RAW / "NQ_1m.csv")
    else:
        from optimize import instruments
        dec_csv, min_csv, _ = instruments.resolve_paths(instrument, tf.name)
    df_dec = load_data(dec_csv).sort_values("Date").reset_index(drop=True)
    df1 = load_data(min_csv).sort_values("Date").reset_index(drop=True)
    box = load_box(instrument)
    vf = vol_forecast(df_dec, df1, bar_minutes=tf.minutes)
    n_split = int((df_dec["Date"].dt.year == config.YEARS[0]).sum())
    return df_dec, df1, box, vf, n_split
