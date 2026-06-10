"""Build the COMBINED "+last-20-days" data set consumed by the dashboard, keeping every existing
file untouched (parity-locked windows stay byte-identical).

The system reads market data from TWO backends, so we extend BOTH:
  • 4h window  -> per-year files            data/2026_data/NQ_{4h,1m}_2026.csv + NQ_full_data_2026.csv
  • other TFs  -> all-history files         Full_Canldes_Data/<RAW>/NQ_<tf>.csv + NQ_1m.csv
                  shared box                data/full_data/NQ_full_data.csv

The recent drop lives at 2026_last_20_days_data/ (candles prefix NQ-5-6-2026, raw box). The system's
existing 2026 box is ALREADY in the −1-business-day-shifted convention (verified: sys[D] == raw20d
[D+1BDay]), so the 20-day box is shifted −1 BDay before merging (else a 1-day seam at the join).
Candles are merged by de-duplicating the datetime overlap (2026-05-18/19), keeping the existing rows.

Outputs (NEW files; nothing is overwritten):
  data/2026_data/NQ_4h_2026_with20d.csv, NQ_1m_2026_with20d.csv, NQ_full_data_2026_with20d.csv
  Full_Canldes_Data/<RAW>/NQ_<tf>_with20d.csv   for tf in {1m,2m,5m,15m,1h,2h,4h}
  data/full_data/NQ_full_data_with20d.csv

Usage:  python3 build_plus20d_data.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd

import config
from optimize import timeframes as TF

REPO = Path("/mnt/data/projects/trading")
DROP = REPO / "2026_last_20_days_data"
DROP_BOX = DROP / "NQ-2026-last-20-days-boxs" / "NQ-5-6-2026" / "NQ_full_data.csv"
DROP_CANDLES = DROP / "NQ-2026-last-20-days-candles" / "NQ-5-6-2026_Continuous_Data"
DROP_PREFIX = "NQ-5-6-2026"
TFS = ["1m", "2m", "5m", "15m", "1h", "2h", "4h"]
_BASE = Path(os.environ.get("WSH_DATA_BASE", str(REPO)))
_RAW = _BASE / TF.RAW_DIR


def _shifted_drop_box() -> pd.DataFrame:
    """The 20-day box, Date shifted −1 business day (matches the system's existing convention)."""
    b = pd.read_csv(DROP_BOX)
    old = pd.to_datetime(b["Date"]).dt.normalize()
    new = old - pd.offsets.BDay(1)
    assert new.dt.dayofweek.max() <= 4, "weekend after shift"
    assert not new.duplicated().any(), "collision after shift"
    assert (new < old).all(), "not all moved back"
    b = b.copy(); b["Date"] = new.dt.strftime("%Y-%m-%d")
    return b


def _merge_candles(base_csv: Path, add_csv: Path, out_csv: Path):
    base = pd.read_csv(base_csv); add = pd.read_csv(add_csv)
    add = add[base.columns]                                  # align schema/order to the base file
    m = (pd.concat([base, add], ignore_index=True)
         .drop_duplicates(subset=["datetime"], keep="first")  # keep existing rows on the overlap
         .sort_values("datetime", kind="mergesort").reset_index(drop=True))
    m.to_csv(out_csv, index=False)
    return len(base), len(add), len(m), m["datetime"].iloc[0], m["datetime"].iloc[-1]


def _merge_box(base_csv: Path, shifted_box: pd.DataFrame, out_csv: Path):
    base = pd.read_csv(base_csv)
    add = shifted_box[base.columns]                          # align to base column order
    bdt = pd.to_datetime(base["Date"]).dt.normalize()
    adt = pd.to_datetime(add["Date"]).dt.normalize()
    # overlap sanity: where dates coincide, the shifted-drop box must equal the existing box
    overlap = sorted(set(bdt) & set(adt))
    cmp_cols = [c for c in ("dOpen", "wOpen", "mOpen") if c in base.columns]
    mism = 0
    for d in overlap:
        bv = base[bdt == d][cmp_cols].iloc[0].to_dict()
        av = add[adt == d][cmp_cols].iloc[0].to_dict()
        if bv != av:
            mism += 1
    m = (pd.concat([base, add], ignore_index=True)
         .assign(_d=lambda x: pd.to_datetime(x["Date"]).dt.normalize())
         .drop_duplicates(subset=["_d"], keep="first").drop(columns="_d")
         .sort_values("Date", kind="mergesort").reset_index(drop=True))
    m.to_csv(out_csv, index=False)
    return len(base), len(add), len(m), len(overlap), mism


def main() -> int:
    sh = _shifted_drop_box()
    print(f"shifted 20d box: {len(sh)} rows  "
          f"{pd.to_datetime(sh['Date']).min().date()} .. {pd.to_datetime(sh['Date']).max().date()}")

    print("\n[4h per-year backend] data/2026_data/*_with20d.csv")
    d26 = config.DATA_ROOT / "2026_data"
    r = _merge_candles(d26/"NQ_4h_2026.csv", DROP_CANDLES/f"{DROP_PREFIX}_4h.csv", d26/"NQ_4h_2026_with20d.csv")
    print(f"  4h : {r[0]}+{r[1]} -> {r[2]} rows  {r[3]} .. {r[4]}")
    r = _merge_candles(d26/"NQ_1m_2026.csv", DROP_CANDLES/f"{DROP_PREFIX}_1m.csv", d26/"NQ_1m_2026_with20d.csv")
    print(f"  1m : {r[0]}+{r[1]} -> {r[2]} rows  {r[3]} .. {r[4]}")
    r = _merge_box(d26/"NQ_full_data_2026.csv", sh, d26/"NQ_full_data_2026_with20d.csv")
    print(f"  box: {r[0]}+{r[1]} -> {r[2]} rows  (overlap {r[3]}, mismatches {r[4]})")
    if r[4]:
        print("  !! box overlap mismatch — convention wrong; aborting", file=sys.stderr); return 1

    print(f"\n[all-history backend] {TF.RAW_DIR}/NQ_<tf>_with20d.csv")
    for tf in TFS:
        base = _RAW / f"NQ_{tf}.csv"
        add = DROP_CANDLES / f"{DROP_PREFIX}_{tf}.csv"
        if not base.exists():
            print(f"  SKIP {tf}: no all-history base {base}", file=sys.stderr); continue
        r = _merge_candles(base, add, _RAW / f"NQ_{tf}_with20d.csv")
        print(f"  {tf:3s}: {r[0]}+{r[1]} -> {r[2]} rows  {r[3]} .. {r[4]}")

    print("\n[all-history shared box] data/full_data/NQ_full_data_with20d.csv")
    r = _merge_box(config.DATA_ROOT/"full_data"/"NQ_full_data.csv", sh,
                   config.DATA_ROOT/"full_data"/"NQ_full_data_with20d.csv")
    print(f"  box: {r[0]}+{r[1]} -> {r[2]} rows  (overlap {r[3]}, mismatches {r[4]})")
    if r[4]:
        print("  !! shared box overlap mismatch — aborting", file=sys.stderr); return 1
    print("\nDONE — all combined files written; originals untouched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
