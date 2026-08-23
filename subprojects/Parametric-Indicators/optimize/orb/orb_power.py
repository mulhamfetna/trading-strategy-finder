"""WS-ORB (#183) — verdicts per the pre-registration: POSITIVE / NEGATIVE / UNDERPOWERED / NULL, with the
power (MDE at 80% power, two-sided 5%) and the year-stability facts. Reads grid1/orb_summary.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

D = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("optimize/orb/data/grid1")
rows = json.load(open(D / "orb_summary.json"))
BONF_T = 2.5          # pre-registered
out = []
for r in rows:
    if r["n"] == 0:
        out.append(dict(cell=r["cell"], verdict="NO-TRADES")); continue
    c = r["confirmation"]["c25"]; e = r["exploration"]["c25"]
    n, mean, sd, t = c["n"], c["mean"], c["sd"], c["t"]
    mde = 2.8 * sd / np.sqrt(n) if n > 1 and sd else np.nan
    yrs = r["years_c25"]; ypos = sum(1 for v in yrs.values() if v[0] > 0); ny = len(yrs)
    tot = sum(v[0] for v in yrs.values()); maxshare = (max(v[0] for v in yrs.values()) / tot) if tot > 0 else np.nan
    loyo = min(tot - v[0] for v in yrs.values()) if ny else np.nan
    pos = (t is not None and t >= BONF_T and mean > 0 and e["mean"] is not None and e["mean"] > 0
           and ypos / ny >= 0.6 and maxshare <= 0.5 and loyo > 0)
    if pos:
        v = "POSITIVE-CANDIDATE (controls pending)"
    elif mean is not None and mean < 0 and t is not None and t <= -2.0 and mde <= 25.0:
        v = "NEGATIVE"
    elif mean is not None and mean < 0 and t is not None and t <= -2.0:
        v = "NEGATIVE (t) but UNDERPOWERED vs $25"
    elif mde > 25.0:
        v = "UNDERPOWERED"
    else:
        v = "NULL"
    out.append(dict(cell=r["cell"], tok=r["tok"], arm=r["arm"], N=r["N"], rule=r["rule"], n_conf=n, mean25=mean, t25=t,
                    mde=round(float(mde), 2) if np.isfinite(mde) else None, expl_mean25=e["mean"], yrs_pos=f"{ypos}/{ny}",
                    max_year_share=round(float(maxshare), 2) if np.isfinite(maxshare) else None, loyo_min=round(float(loyo), 0),
                    ticks=r["gross_edge_ticks"], verdict=v))
df = pd.DataFrame(out)
df.to_csv(D / "verdicts.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
print(df["verdict"].value_counts().to_string())
print("\nMDE distribution ($/trade):", df["mde"].describe().round(1).to_dict())
print("\ncells with t25 > 1 (best of the grid):")
print(df[df["t25"] > 1].sort_values("t25", ascending=False).to_string(index=False))
print("\nNEGATIVE by instrument:"); print(df[df.verdict == "NEGATIVE"].groupby("tok").size().to_string())
print("\nby rule / arm / N — share of cells NEGATIVE:")
for k in ("rule", "arm", "N"):
    print(df.groupby(k)["verdict"].apply(lambda s: round((s == "NEGATIVE").mean(), 2)).to_dict())
