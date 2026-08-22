"""WS-FWD Gate D (#176) — integrate the owner's NQ `with20d` drop into the FWD root.

Production holds an owner-supplied NQ extension (candles + SCRAPED box rows through
2026-06-09, merged by the proven build_plus20d_data.py) that was never swapped into the live
files. The box rows are genuine scrapes — usable. Candles are superseded by the Phase-0.5
extension, so Gate D demands: the with20d 1m rows must EXACTLY match the extended 1m on
their whole overlap (OHLCV). Pass ==> the FWD root adopts the with20d NQ box (full + per-year)
and gains 12 days of real NQ entry coverage; fail ==> report and stop.

Also builds the dashboard's per-year NQ backend in the FWD root:
  data/2025_data -> symlink to prod (2025 unchanged)
  data/2026_data/NQ_4h_2026.csv, NQ_1m_2026.csv  = year-2026 slice of the EXTENDED frames
  data/2026_data/NQ_full_data_2026.csv           = the with20d per-year box (prod file)
  data/full_data (was a symlink) -> real dir: every prod file symlinked EXCEPT
  NQ_full_data.csv := prod NQ_full_data_with20d.csv (copied)
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pandas as pd

PROD = Path("/home/dev/Mulham/wsg-i")
FWD = Path("/home/dev/Mulham/wsg-i/FWD_EXTENDED")
RAW = "Full_Canldes_Data/drive-download-20260602T124702Z-3-001"


def _read(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.sort_values("datetime").reset_index(drop=True)


def main() -> None:
    ext = _read(FWD / RAW / "NQ_1m.csv")
    w20 = _read(PROD / RAW / "NQ_1m_with20d.csv")
    cut = pd.Timestamp("2026-05-19 19:59:00")
    w = w20[w20["datetime"] > cut].set_index("datetime")
    e = ext[(ext["datetime"] > cut) & (ext["datetime"] <= w.index.max())].set_index("datetime")
    common = w.index.intersection(e.index)
    only_w = w.index.difference(e.index)
    only_e = e.index.difference(w.index)
    mism = {c: int((w.loc[common, c].to_numpy() != e.loc[common, c].to_numpy()).sum())
            for c in ("open", "high", "low", "close", "volume")}
    print(f"gate D: overlap rows w20={len(w)} ext={len(e)} common={len(common)} "
          f"w20_only={len(only_w)} ext_only={len(only_e)} mism={mism}")
    ok = len(only_w) == 0 and len(only_e) == 0 and all(v == 0 for v in mism.values())
    print(f"gate D pass={ok}")
    if not ok:
        raise SystemExit("GATE D FAILED — with20d candles disagree with the extension; not wiring the box")

    # full_data: symlink dir -> real dir with the with20d box as the live NQ box
    fd = FWD / "data" / "full_data"
    if fd.is_symlink():
        fd.unlink()
    fd.mkdir(parents=True, exist_ok=True)
    for f in (PROD / "data" / "full_data").iterdir():
        if f.name == "NQ_full_data.csv":
            continue
        dst = fd / f.name
        if not dst.exists():
            dst.symlink_to(f)
    shutil.copy2(PROD / "data" / "full_data" / "NQ_full_data_with20d.csv", fd / "NQ_full_data.csv")
    b = pd.read_csv(fd / "NQ_full_data.csv")
    print(f"FWD NQ box rows={len(b)} last Date={b['Date'].iloc[-1]}")

    # per-year backend
    dd = FWD / "data"
    y25 = dd / "2025_data"
    if not y25.exists():
        y25.symlink_to(PROD / "data" / "2025_data")
    y26 = dd / "2026_data"
    y26.mkdir(exist_ok=True)
    for tfname in ("4h", "1m"):
        src = _read(FWD / RAW / f"NQ_{tfname}.csv")
        sl = src[src["datetime"].dt.year == 2026]
        sl.to_csv(y26 / f"NQ_{tfname}_2026.csv", index=False)
        print(f"2026_data/NQ_{tfname}_2026.csv rows={len(sl)} last={sl['datetime'].iloc[-1]}")
    shutil.copy2(PROD / "data" / "2026_data" / "NQ_full_data_2026_with20d.csv",
                 y26 / "NQ_full_data_2026.csv")
    # 2024 backend dir, if the server code ever asks for it
    y24 = dd / "2024_data"
    if (PROD / "data" / "2024_data").exists() and not y24.exists():
        y24.symlink_to(PROD / "data" / "2024_data")
    print("WIRED")


if __name__ == "__main__":
    main()
