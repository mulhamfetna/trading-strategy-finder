"""Stage 1 · S1.1 — the 29-month bundle for the SL/TP sub-optimizer.

Concatenates the per-year 4h + 1-minute + box files for **2024 + 2025 + 2026** into one continuous bundle,
mirroring `strategy.load_inputs` (which only spans 2025+2026) but extended to the full sub-optimizer span.
HAR-RV `vf` is computed once over the FULL series (causal, 4h `bar_minutes=240`), and a per-decision-bar
month label (`YYYY-MM`) is returned so the rolling-window indexer can slice by calendar month.

Box note: uses the SHIFTED `NQ_full_data_<yr>.csv` for every year (the −1 BDay shift is already applied;
NOT the `.preshift.csv`), matching the parity-locked box behaviour.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parents[1]                      # Parametric-Indicators root
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import config                                # noqa: E402
from loader import load_data                # noqa: E402
from volatility import vol_forecast          # noqa: E402

YEARS = (2024, 2025, 2026)


def load_bundle(years=YEARS):
    """Return (df4, df1, box, vf, months) for the concatenated per-year files.
      df4    : 4h decision frame (Date-sorted, reset index), with a '_year' column
      df1    : shared 1-minute frame (Date-sorted)
      box    : box-levels frame indexed by normalized Date (deduped)
      vf     : HAR-RV forecast aligned 1:1 with df4 (computed over the full series)
      months : np.ndarray[str] 'YYYY-MM' aligned 1:1 with df4 rows
    """
    f4, f1, fb = [], [], []
    for yr in years:
        d = config.DATA_ROOT / f"{yr}_data"
        a = load_data(str(d / f"NQ_4h_{yr}.csv")); a["_year"] = yr
        b = load_data(str(d / f"NQ_1m_{yr}.csv"))
        c = pd.read_csv(d / f"NQ_full_data_{yr}.csv")
        c["Date"] = pd.to_datetime(c["Date"]).dt.normalize()
        f4.append(a); f1.append(b); fb.append(c)
    df4 = pd.concat(f4).sort_values("Date").reset_index(drop=True)
    df1 = pd.concat(f1).sort_values("Date").reset_index(drop=True)
    box = pd.concat(fb).drop_duplicates(subset=["Date"]).set_index("Date", drop=False)
    vf = vol_forecast(df4, df1)                          # 4h default (bar_minutes=240), full-series causal
    months = pd.to_datetime(df4["Date"]).dt.strftime("%Y-%m").to_numpy()
    return df4, df1, box, vf, months


if __name__ == "__main__":
    df4, df1, box, vf, months = load_bundle()
    uniq, counts = np.unique(months, return_counts=True)
    print(f"df4={len(df4)} bars  df1={len(df1)} bars  box={len(box)} dates  vf={len(vf)}")
    print(f"4h span: {df4['Date'].iloc[0]} → {df4['Date'].iloc[-1]}")
    print(f"1m span: {df1['Date'].iloc[0]} → {df1['Date'].iloc[-1]}")
    print(f"months: {len(uniq)}  ({uniq[0]} … {uniq[-1]})")
    # continuity check: no year-join gap > 5 days in the 4h frame
    gaps = pd.to_datetime(df4["Date"]).diff().dropna()
    big = gaps[gaps > pd.Timedelta(days=5)]
    print(f"4h gaps >5d: {len(big)}")
    print("per-month 4h bar counts:")
    for m, n in zip(uniq, counts):
        print(f"  {m}: {n}")
