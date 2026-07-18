#!/usr/bin/env python3
"""Assemble a self-contained 2024-2026 NQ data tree for the extended robustness run.

Slices the 2010-2026 candle history down to 2024-01-01 .. 2026-05-20 (matching the box coverage) and
concatenates the per-year box-level files into the single full_data/NQ_full_data.csv the fusion loader
reads. Output tree mirrors exactly what optimize/data.py expects:

    <DEST>/Full_Canldes_Data/drive-download-20260602T124702Z-3-001/NQ_{1h,4h,1m}.csv   (candles)
    <DEST>/data/full_data/NQ_full_data.csv                                             (box, all yrs)
    <DEST>/data/<year>_data/NQ_full_data_<year>.csv                                    (per-year copies)

Run:  python3 build_2426_tree.py <DEST>
"""
from __future__ import annotations
import shutil, sys
from pathlib import Path
import pandas as pd

SRC_CANDLES = Path("/home/dev/Mulham/data_2010_1s/NQ_Continuous_Data")
SRC_BOX_YEARS = Path("/home/dev/Mulham/wsg-i/data")
RAW_REL = "Full_Canldes_Data/drive-download-20260602T124702Z-3-001"
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2026-05-20")
YEARS = [2024, 2025, 2026]


def slice_candles(dest_raw: Path):
    dest_raw.mkdir(parents=True, exist_ok=True)
    for tf in ("1h", "4h", "1m"):
        df = pd.read_csv(SRC_CANDLES / f"NQ_{tf}.csv")
        df.columns = [c.strip() for c in df.columns]
        dtcol = "datetime" if "datetime" in df.columns else df.columns[0]
        dt = pd.to_datetime(df[dtcol])
        m = (dt >= START) & (dt < END)
        out = df.loc[m].reset_index(drop=True)
        out.to_csv(dest_raw / f"NQ_{tf}.csv", index=False)
        print(f"  NQ_{tf}: {len(out):>8} rows  {pd.to_datetime(out[dtcol]).min()} -> {pd.to_datetime(out[dtcol]).max()}")


def build_box(dest_data: Path):
    (dest_data / "full_data").mkdir(parents=True, exist_ok=True)
    frames = []
    for y in YEARS:
        yd = dest_data / f"{y}_data"; yd.mkdir(parents=True, exist_ok=True)
        src = SRC_BOX_YEARS / f"{y}_data" / f"NQ_full_data_{y}.csv"
        df = pd.read_csv(src)
        shutil.copy(src, yd / f"NQ_full_data_{y}.csv")
        frames.append(df)
        print(f"  box {y}: {len(df)} rows  ({df['Date'].min()} -> {df['Date'].max()})")
    box = pd.concat(frames, ignore_index=True)
    box["Date"] = pd.to_datetime(box["Date"])
    box = box.sort_values("Date").drop_duplicates(subset=["Date"]).reset_index(drop=True)
    box.to_csv(dest_data / "full_data" / "NQ_full_data.csv", index=False)
    print(f"  COMBINED box: {len(box)} rows  {box['Date'].min().date()} -> {box['Date'].max().date()}")


def main():
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Mulham/tfm-repro/data2426"
    print(f"building 2024-2026 tree at {dest}\n== candles ==")
    slice_candles(dest / RAW_REL)
    print("== box ==")
    build_box(dest / "data")
    print("\nDONE")


if __name__ == "__main__":
    main()
