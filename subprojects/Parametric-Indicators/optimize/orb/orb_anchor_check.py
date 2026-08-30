"""WS-ORB (#183) pre-run data check: does the 1-minute volume profile step at the declared cash anchor?
For each instrument: median volume per minute-of-day over the confirmation window (2018-2024), the minute
with the largest positive jump (vol[m] / mean(vol[m-5..m-1])) inside 07:00-10:30 ET, and the declared anchor.
Writes optimize/orb/data/anchor_check.json. Anchors are NEVER chosen on P/L."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WSH_16Y_ROOT", ""))   # server tape root: $WSH_16Y_ROOT
if not str(ROOT):
    raise SystemExit("usage: orb_anchor_check.py <tape_root> [out.json]  (or set $WSH_16Y_ROOT)")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("optimize/orb/data/anchor_check.json")
DECL = {"NQ": "09:30", "ES": "09:30", "RTY": "09:30", "YM": "09:30", "GC": "08:20", "SI": "08:20", "HG": "08:20", "CL": "09:00", "NG": "09:00"}
res = {}
for tok, decl in DECL.items():
    df = pd.read_csv(ROOT / f"{tok}_Continuous_Data" / f"{tok}_1m.csv", usecols=["datetime", "volume"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df[(df["datetime"] >= "2018-01-01") & (df["datetime"] < "2025-01-01")]
    mod = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute
    prof = df.groupby(mod)["volume"].median()
    prof = prof.reindex(range(0, 24 * 60)).fillna(0)
    jump = {}
    for m in range(7 * 60, 10 * 60 + 31):
        prev = prof.iloc[m - 5:m].mean()
        jump[m] = prof.iloc[m] / prev if prev > 0 else np.nan
    j = pd.Series(jump).dropna()
    best = int(j.idxmax())
    dm = int(decl[:2]) * 60 + int(decl[3:])
    res[tok] = {"declared": decl, "declared_jump": round(float(j.get(dm, np.nan)), 2),
                "best_minute": f"{best // 60:02d}:{best % 60:02d}", "best_jump": round(float(j.max()), 2),
                "top5": [(f"{int(m) // 60:02d}:{int(m) % 60:02d}", round(float(v), 2)) for m, v in j.nlargest(5).items()],
                "median_vol_at_declared": float(prof.iloc[dm]), "pass": abs(best - dm) <= 1}
    print(tok, res[tok], flush=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, indent=1))
print("->", OUT)
