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
import time as _time
from pathlib import Path

import numpy as np
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
# GC landed 2026-07-19, assembled by the SAME main_futures_seconds.py from the same Databento source.
#   · GC_1m: 2010-06-06 -> 2026-07-17, 5,658,124 bars, ~350k/year with no holes
#   · identical schema and conventions to NQ (same assembler, same roll rule, same tz handling)
#   · likewise NOT back-adjusted — same roll-gap caveat as above
# Any instrument assembled into <ROOT>/<INST>_Continuous_Data/<INST>_<tf>.csv resolves automatically.
_16Y_ROOT = Path("/home/dev/Mulham/data_2010_1s")


def sixteen_year_path(instrument: str = "NQ", tf: str = "1m") -> Path:
    """Path to the assembled long-history frame for an instrument, or a non-existent path if absent."""
    return _16Y_ROOT / f"{instrument}_Continuous_Data" / f"{instrument}_{tf}.csv"


_16Y = sixteen_year_path("NQ", "1m")
_16Y_SECONDS = sixteen_year_path("NQ", "1s")


def _read(p: Path) -> pd.DataFrame:
    d = pd.read_csv(p, parse_dates=["datetime"])
    d = d.rename(columns={"datetime": "Date", "open": "Open", "high": "High",
                          "low": "Low", "close": "Close", "volume": "Volume"})
    return d[["Date", "Open", "High", "Low", "Close", "Volume"]]


def load_1m_extended(instrument: str = "NQ") -> pd.DataFrame:
    """The longest 1-minute NQ history available, in the SAME shape the engine's loader produces:
    columns ['Date','Open','High','Low','Close','Volume'], tz-naive US-Eastern wall-clock, sorted.

    Prefers the assembled 16-year frame (2010->2026) for ANY instrument that has one — NQ since
    2026-07-13, GC since 2026-07-19. Falls back to the 2024+2025+2026 stitch (NQ only, which is the
    only instrument those legacy files exist for), then to the engine's own loader.

    ⚠️ THE ENGINE MUST NEVER USE THIS. Lengthening the engine's price history would change n_split and
    the volatility-percentile gate, and therefore EVERY champion. optimize/data.py stays untouched and
    the golden 6/6 stay byte-identical. This is research only.
    """
    long_frame = sixteen_year_path(instrument, "1m")

    if long_frame.exists():
        df = _read(long_frame)
    elif instrument == "NQ":
        # The legacy 2024+2025+2026 stitch exists for NQ only.
        frames = [_read(p) for p in (_2024, _MAIN) if p.exists()]
        if not frames:
            from optimize import data as _d
            _, df1, *_ = _d.load_inputs("4h", instrument="NQ")
            return df1
        df = pd.concat(frames, ignore_index=True)
    else:
        from optimize import data as _d
        _, df1, *_ = _d.load_inputs("4h", instrument=instrument)
        return df1

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


_SEEK_SAFETY = 1 << 20          # 1 MB rewind — see the note at the end of _seek_to_timestamp


def _seek_to_timestamp(path: Path, target: str) -> int:
    """Byte offset of the first COMPLETE line whose timestamp >= `target`. Binary search over the file.

    The 1-second file is 7.3 GB and sorted by time. Task #11 only wants 2025-2026 — about the last 15%.
    Streaming the 2010-2024 prefix just to discard it is ~120M rows of pure waste. Since ISO-8601 sorts
    lexicographically, we can binary-search the raw BYTES and seek straight to the data we want.

    Returns 0 if the target precedes the whole file.
    """
    size = path.stat().st_size
    with path.open("rb") as f:
        f.readline()                                   # header
        lo, hi = f.tell(), size
        while lo < hi:
            mid = (lo + hi) // 2
            f.seek(mid)
            f.readline()                               # discard the partial line we landed inside
            pos = f.tell()
            line = f.readline()
            if not line:                               # ran off the end
                hi = mid
                continue
            ts = line.split(b",", 1)[0].decode()
            if ts < target:
                lo = pos + len(line)
            else:
                hi = mid

        # BACK OFF, ON PURPOSE. The search can land one line LATE (it converges on a byte, and the line
        # boundary nearest that byte may be past the target). Landing late SILENTLY DROPS BARS, and the
        # obvious assert (`first_ts >= target`) is satisfied by exactly that failure — so it would ship.
        #
        # Landing EARLY is free: the window mask discards anything before the first window anyway. So we
        # rewind a safe margin and re-align to the next complete line. Wrong-but-early beats right-but-
        # fragile.
        f.seek(max(0, lo - _SEEK_SAFETY))
        if lo > _SEEK_SAFETY:
            f.readline()                               # re-align to a complete line
        return f.tell()


def load_1s_windows(windows, chunksize: int = 4_000_000, verbose: bool = True) -> pd.DataFrame:
    """Many small 1-second windows, in ONE pass over the 7.3 GB / 142M-row file.

    `windows` = iterable of (start, end) timestamps, inclusive. Returns every 1-second bar falling in
    ANY of them, deduplicated and sorted.

    WHY THIS EXISTS. load_1s() re-scans the entire file per call. Task #11 needs a window around EVERY
    stopped trade — hundreds of them — and hundreds of full 7.3 GB scans is not a study, it's a heater.
    This does one pass, no matter how many windows.

    THE TRICK: the `datetime` column is ISO-8601, and ISO-8601 sorts LEXICOGRAPHICALLY the same way it
    sorts chronologically. So we can locate window boundaries with a string searchsorted and never parse
    the 142M timestamps we are going to throw away — we parse only the few thousand rows we keep.
    """
    if not _16Y_SECONDS.exists():
        raise FileNotFoundError(f"1-second file not found: {_16Y_SECONDS}")

    w = sorted((pd.Timestamp(s), pd.Timestamp(e)) for s, e in windows)
    if not w:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    s_str = np.array([s.strftime("%Y-%m-%d %H:%M:%S") for s, _ in w])
    e_str = np.array([e.strftime("%Y-%m-%d %H:%M:%S") for _, e in w])
    lo, hi = min(s_str), max(e_str)                     # numpy's max() has no loop for <U19 dtype

    keep, seen, t0 = [], 0, _time.time()
    off = _seek_to_timestamp(_16Y_SECONDS, lo)
    if verbose:
        pct = 100 * off / _16Y_SECONDS.stat().st_size
        print(f"    [1s] seeking to {lo} -> byte {off:,} ({pct:.1f}% into the file); "
              f"skipping the {pct:.0f}% before it entirely", flush=True)

    fh = _16Y_SECONDS.open("r")
    fh.seek(off)
    reader = pd.read_csv(fh, chunksize=chunksize, dtype={"datetime": str},
                         names=["datetime", "open", "high", "low", "close", "volume"], header=None)
    for i, ch in enumerate(reader):
        t = ch["datetime"].to_numpy()
        seen += len(t)
        if t[-1] < lo:                                  # entirely before the first window
            continue
        if t[0] > hi:                                   # past the last window — the file is sorted, stop
            break
        a = np.searchsorted(t, s_str, side="left")
        b = np.searchsorted(t, e_str, side="right")
        mask = np.zeros(len(t), dtype=bool)
        for x, y in zip(a, b):
            if y > x:
                mask[x:y] = True
        if mask.any():
            keep.append(ch[mask])
        if verbose and i % 5 == 0:
            el = _time.time() - t0
            print(f"    [1s] scanned {seen/1e6:>6.1f}M rows  kept {sum(len(k) for k in keep):>7,}  "
                  f"{el:>5.0f}s", flush=True)
    fh.close()

    if not keep:
        return pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"])
    d = pd.concat(keep, ignore_index=True)
    d["datetime"] = pd.to_datetime(d["datetime"])       # parse ONLY the rows we kept
    d = d.rename(columns={"datetime": "Date", "open": "Open", "high": "High",
                          "low": "Low", "close": "Close", "volume": "Volume"})
    d = d[["Date", "Open", "High", "Low", "Close", "Volume"]]
    d = d.drop_duplicates(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    if verbose:
        print(f"    [1s] done: {len(d):,} bars across {len(w)} windows "
              f"in {_time.time()-t0:.0f}s (one pass)", flush=True)
    return d


def span(df: pd.DataFrame) -> str:
    return f"{df['Date'].iloc[0]} -> {df['Date'].iloc[-1]}  ({len(df):,} bars)"


if __name__ == "__main__":
    d = load_1m_extended()
    print("EXTENDED NQ 1-minute frame (study use only — the engine is untouched)")
    print(" ", span(d))
    print(f"  years present: {sorted(d['Date'].dt.year.unique())}")
    print(f"  bars at 08:30 (the release minute): {(d['Date'].dt.strftime('%H:%M') == '08:30').sum()}")
