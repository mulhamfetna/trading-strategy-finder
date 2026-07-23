"""The 2024-2026 frame used ONLY by M3.

M1/M2 must run on the champion frame (2,119 bars, 2025-2026) because they depend on champion gate arrays.
M3 depends on no champion, so it takes the extra year of data for statistical power. The two windows are
reported separately and never mixed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

import config
from loader import load_data
from optimize.data import _RAW      # production decision-candle dir ($WSH_DATA_BASE/<RAW_DIR>)

_CANDLE_2024 = "NQ_{tf}_2024.csv"
_BOX_2024 = "NQ_full_data_2024.csv"


def _concat_checked(older: pd.DataFrame, newer: pd.DataFrame, label: str) -> pd.DataFrame:
    """Concatenate two date-keyed frames, refusing anything that would silently corrupt the study."""
    if set(older.columns) != set(newer.columns):
        only_a = sorted(set(older.columns) - set(newer.columns))
        only_b = sorted(set(newer.columns) - set(older.columns))
        raise ValueError(f"{label}: schema mismatch; only-in-older={only_a} only-in-newer={only_b}")
    out = pd.concat([older, newer[older.columns]], ignore_index=True)
    dupes = out["Date"].duplicated().sum()
    if dupes:
        raise ValueError(f"{label}: {dupes} duplicate Date rows after concat")
    return out.sort_values("Date").reset_index(drop=True)


def _read_candles(path: Path) -> pd.DataFrame:
    """Reuse the PRODUCTION loader so the study's frame is built exactly like the champion's.

    loader.load_data handles the datetime->Date and open/high/low/close->Title-case renaming, column
    stripping and Date parsing. Hand-rolling that here would risk silently diverging from production.
    """
    df = load_data(str(path)).sort_values("Date").reset_index(drop=True)
    return df[["Date", "Open", "High", "Low", "Close"]]


def load_extended(tf_name: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (df_dec, box) spanning 2024-01-01 -> 2026-05-19 for the given decision timeframe.

    Path resolution deliberately mirrors optimize/data.py, which uses TWO different roots:
      - decision candles: $WSH_DATA_BASE/<RAW_DIR>/NQ_<tf>.csv   (imported as _RAW)
      - box levels:       $WSG_DATA_ROOT/full_data/NQ_full_data.csv
    The 2024 add-on files live under $WSG_DATA_ROOT/2024_data/.
    """
    root = Path(config.DATA_ROOT)
    c_2024 = root / "2024_data" / _CANDLE_2024.format(tf=tf_name)
    c_main = Path(_RAW) / f"NQ_{tf_name}.csv"
    b_2024 = root / "2024_data" / _BOX_2024
    b_main = root / "full_data" / "NQ_full_data.csv"
    for p in (c_2024, c_main, b_2024, b_main):
        if not p.exists():
            raise FileNotFoundError(p)

    df_dec = _concat_checked(_read_candles(c_2024), _read_candles(c_main), "candles")

    box_a = pd.read_csv(b_2024)
    box_b = pd.read_csv(b_main)
    for b in (box_a, box_b):
        b["Date"] = pd.to_datetime(b["Date"]).dt.normalize()
    common = [c for c in box_a.columns if c in set(box_b.columns)]
    box = _concat_checked(box_a[common].drop_duplicates(subset=["Date"]),
                          box_b[common].drop_duplicates(subset=["Date"]), "box")
    return df_dec, box.set_index("Date", drop=False)
