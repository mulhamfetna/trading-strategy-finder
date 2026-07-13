"""STUDY-ONLY extended price frame: 2024 + 2025 + 2026.

WHY THIS EXISTS. Every fundamental-analysis result was capped at ~52-103 events by the length of our
price history (2025-01-01 -> 2026-05-19, sixteen and a half months). The power analysis showed we had
12% power — we needed 647 releases and had 52. The bottleneck was never the market and never the
calendar (FRED has decades, free). It was our own dataset.

data/2024_data/NQ_1m_2024.csv has been sitting UNUSED on disk: 355,014 bars, a complete year, with every
release minute present. Folding it in roughly DOUBLES the sample for free.

⚠️ WHY THIS IS A SEPARATE MODULE AND NOT A CHANGE TO optimize/data.py ⚠️

The golden gate (perf/check_golden.py) hashes the trade ledger produced from the EXACT paths that
optimize/data.py resolves. Silently lengthening the engine's price history would change every champion's
results and break the identity guarantee that the whole project rests on.

So this module is for RESEARCH ONLY. It never touches the engine. The engine's data loading is unchanged
and the golden 6/6 stay byte-identical.

Verified before writing this (2026-07-13):
  · identical columns and dtypes in both files
  · ZERO overlapping timestamps (2024 ends 2024-12-31 16:59, 2025 starts 2025-01-01 18:00)
  · clean price continuity across the seam (21234.25 -> 21269.00, a normal New Year gap)
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

_ROOT = Path(os.environ.get("WSH_DATA_BASE", "/mnt/data/projects/trading"))
_DATA = Path(os.environ.get("WSG_DATA_ROOT", str(_ROOT / "data")))

# The 2025+2026 frame the engine already uses (unchanged, untouched).
_MAIN = _ROOT / "Full_Canldes_Data" / "drive-download-20260602T124702Z-3-001" / "NQ_1m.csv"
# The 2024 frame that has been sitting unused.
_2024 = _DATA / "2024_data" / "NQ_1m_2024.csv"


def load_1m_extended(instrument: str = "NQ") -> pd.DataFrame:
    """1-minute bars for 2024 + 2025 + 2026, in the SAME shape the engine's loader produces:
    columns ['Date','Open','High','Low','Close','Volume'], tz-naive US-Eastern wall-clock,
    sorted ascending, RangeIndex.

    Only NQ has a 2024 file. For any other instrument we fall back to the standard loader, so callers
    can use this uniformly across the 9-market studies without special-casing.
    """
    if instrument != "NQ" or not _2024.exists():
        from optimize import data as _d
        _, df1, *_ = _d.load_inputs("4h", instrument=instrument)
        return df1

    frames = []
    for p in (_2024, _MAIN):
        d = pd.read_csv(p, parse_dates=["datetime"])
        d = d.rename(columns={"datetime": "Date", "open": "Open", "high": "High",
                              "low": "Low", "close": "Close", "volume": "Volume"})
        frames.append(d[["Date", "Open", "High", "Low", "Close", "Volume"]])

    df = pd.concat(frames, ignore_index=True).sort_values("Date").reset_index(drop=True)

    # A duplicate timestamp would silently double-count a bar and corrupt every return. Refuse.
    dup = int(df["Date"].duplicated().sum())
    if dup:
        raise ValueError(f"{dup} duplicate timestamps after concatenation — refusing to proceed")
    return df


def span(df: pd.DataFrame) -> str:
    return f"{df['Date'].iloc[0]} -> {df['Date'].iloc[-1]}  ({len(df):,} bars)"


if __name__ == "__main__":
    d = load_1m_extended()
    print("EXTENDED NQ 1-minute frame (study use only — the engine is untouched)")
    print(" ", span(d))
    print(f"  years present: {sorted(d['Date'].dt.year.unique())}")
    print(f"  bars at 08:30 (the release minute): {(d['Date'].dt.strftime('%H:%M') == '08:30').sum()}")
