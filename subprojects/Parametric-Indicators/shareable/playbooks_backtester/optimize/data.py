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
from loader import load_data  # noqa: E402
from volatility import vol_forecast  # noqa: E402
from optimize import timeframes as TF  # noqa: E402

# Base dir holding the raw timeframe CSVs (Full_Canldes_Data/...). Overridable for the server
# migration via WSH_DATA_BASE; defaults to the local repo root.
_BASE = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))
_RAW = _BASE / TF.RAW_DIR
_BOX_CSV = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"   # config.DATA_ROOT honours WSG_DATA_ROOT
# Shareable bundle: every instrument CSV lives in one folder, named <INST>_<tf>.csv (decision frame),
# <INST>_1m.csv (1-minute frame), <INST>_box.csv (per-day box levels). Override the folder with WSH_BUNDLE_DATA.
_BUNDLE_DATA = Path(os.environ.get("WSH_BUNDLE_DATA", str(Path(__file__).resolve().parents[1] / "data")))


def load_box(instrument: str = "NQ") -> pd.DataFrame:
    """Load the box-level frame, indexed by normalized Date (same shape as strategy.py). NQ uses the existing
    _BOX_CSV (byte-identical); other instruments resolve through the registry."""
    box_csv = str(_BUNDLE_DATA / f"{instrument}_box.csv")
    c = pd.read_csv(box_csv)
    c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
    return c.drop_duplicates(subset=["Date"]).set_index("Date", drop=False)


def load_inputs(tf_name: str, instrument: str = "NQ"):
    """Return (df_dec, df1, box, vf, n_split) for the given decision timeframe + instrument. NQ keeps the
    existing inline paths (golden-safe); other instruments resolve through optimize.instruments."""
    tf = TF.get(tf_name)
    dec_csv = str(_BUNDLE_DATA / f"{instrument}_{tf.name}.csv")
    min_csv = str(_BUNDLE_DATA / f"{instrument}_1m.csv")
    df_dec = load_data(dec_csv).sort_values("Date").reset_index(drop=True)
    df1 = load_data(min_csv).sort_values("Date").reset_index(drop=True)
    box = load_box(instrument)
    vf = vol_forecast(df_dec, df1, bar_minutes=tf.minutes)
    n_split = int((df_dec["Date"].dt.year == config.YEARS[0]).sum())
    return df_dec, df1, box, vf, n_split
