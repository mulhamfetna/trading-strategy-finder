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

# The 2025+2026 frame the engine uses (unchanged, untouched — golden-locked).
_MAIN = _ROOT / "Full_Canldes_Data" / "drive-download-20260602T124702Z-3-001" / "NQ_1m.csv"
_2024 = _DATA / "2024_data" / "NQ_1m_2024.csv"

# ---------------------------------------------------------------------------------------------
# THE 16-YEAR FRAME (2010-06 -> 2026-07). 5,452,534 one-minute bars.
#
# Assembled by main_futures_seconds.py from Databento 1-second raw:
#   · spread contracts (NQH5-NQM5) dropped
#   · UTC -> America/New_York, then the tz label stripped => Eastern wall-clock, DST applied
#   · trading day = ts + 6h, so the 18:00 CME session maps to one date (matches our box rule)
#   · continuous contract = the HIGHEST-VOLUME contract per trading day
#
# ⚠️ NOT BACK-ADJUSTED. There is a price GAP at every contract roll. That is FINE for these studies —
# we measure returns inside +-60-minute windows around a release, and a roll happens at a DAY boundary,
# never inside such a window. It would NOT be fine for anything measuring returns ACROSS a roll.
#
# ✅ VALIDATED 2026-07-14: on the 486,969-bar overlap with the engine's file (2025-01-01 -> 2026-05-19)
#    it is 100.000% IDENTICAL on open/high/low/close/volume. Zero missing bars, zero extra, max abs
#    difference 0.0000. Same source, same conventions. Safe to build on.
_16Y = Path("/home/dev/Mulham/data_2010_1s/NQ_Continuous_Data/NQ_1m.csv")
_16Y_SECONDS = Path("/home/dev/Mulham/data_2010_1s/NQ_Continuous_Data/NQ_1s.csv")


def _read(p: Path) -> pd.DataFrame:
    d = pd.read_csv(p, parse_dates=["datetime"])
    d = d.rename(columns={"datetime": "Date", "open": "Open", "high": "High",
                          "low": "Low", "close": "Close", "volume": "Volume"})
    return d[["Date", "Open", "High", "Low", "Close", "Volume"]]


def load_1m_extended(instrument: str = "NQ") -> pd.DataFrame:
    """The longest 1-minute NQ history available, in the SAME shape the engine's loader produces:
    columns ['Date','Open','High','Low','Close','Volume'], tz-naive US-Eastern wall-clock, sorted.

    Prefers the 16-year frame (2010->2026). Falls back to 2024+2025+2026 if it is absent, and to the
    engine's own loader for any non-NQ instrument.

    ⚠️ THE ENGINE MUST NEVER USE THIS. Lengthening the engine's price history would change n_split and
    the volatility-percentile gate, and therefore EVERY champion. optimize/data.py stays untouched and
    the golden 6/6 stay byte-identical. This is research only.
    """
    if instrument != "NQ":
        from optimize import data as _d
        _, df1, *_ = _d.load_inputs("4h", instrument=instrument)
        return df1

    if _16Y.exists():
        df = _read(_16Y)
    else:
        frames = [_read(p) for p in (_2024, _MAIN) if p.exists()]
        if not frames:
            from optimize import data as _d
            _, df1, *_ = _d.load_inputs("4h", instrument="NQ")
            return df1
        df = pd.concat(frames, ignore_index=True)

    df = df.sort_values("Date").reset_index(drop=True)

    # A duplicate timestamp would silently double-count a bar and corrupt every return. Refuse.
    dup = int(df["Date"].duplicated().sum())
    if dup:
        raise ValueError(f"{dup} duplicate timestamps — refusing to proceed")
    return df


def load_1s(start=None, end=None) -> pd.DataFrame:
    """1-SECOND NQ bars (7.8 GB file — ALWAYS pass a window, never load it whole).

    This is what answers Task #6: the 2025-03-07 payrolls bar went DOWN 46 points and UP 141 points
    inside the same minute, and a 1-minute OHLC candle cannot tell you the ORDER. Seconds can.
    """
    if not _16Y_SECONDS.exists():
        raise FileNotFoundError(f"1-second file not found: {_16Y_SECONDS}")
    it = pd.read_csv(_16Y_SECONDS, parse_dates=["datetime"], chunksize=2_000_000)
    keep = []
    for ch in it:
        if start is not None:
            ch = ch[ch["datetime"] >= start]
        if end is not None:
            ch = ch[ch["datetime"] <= end]
        if len(ch):
            keep.append(ch)
    if not keep:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    d = pd.concat(keep, ignore_index=True)
    d = d.rename(columns={"datetime": "Date", "open": "Open", "high": "High",
                          "low": "Low", "close": "Close", "volume": "Volume"})
    return d[["Date", "Open", "High", "Low", "Close", "Volume"]].sort_values("Date").reset_index(drop=True)


def span(df: pd.DataFrame) -> str:
    return f"{df['Date'].iloc[0]} -> {df['Date'].iloc[-1]}  ({len(df):,} bars)"


if __name__ == "__main__":
    d = load_1m_extended()
    print("EXTENDED NQ 1-minute frame (study use only — the engine is untouched)")
    print(" ", span(d))
    print(f"  years present: {sorted(d['Date'].dt.year.unique())}")
    print(f"  bars at 08:30 (the release minute): {(d['Date'].dt.strftime('%H:%M') == '08:30').sum()}")
