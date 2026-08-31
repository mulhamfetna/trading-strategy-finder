"""#198 — the pre-registered judgement (docs/WS-GATECAL-PREREGISTRATION.md §3).

    python3 optimize/gatecal/gatecal_verdict.py --books <dir> --out <json>

Reads gc_book_{A0,A1,A2,C}_<slot>.csv, cuts each to the fresh window (entries after the per-instrument
pre-extension end, as #179), and reports per arm: fleet fresh net at $0/$10/$25, the arm-vs-A0 difference
with a session-block bootstrap CI (1,000 resamples, seed 198), the churn floor (C-vs-A0), and the
dark-slot entry counts. The VERDICT line applies §3 verbatim.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

PRE = {"NQ": "2026-05-19 19:59:00", "ES": "2026-05-19 19:59:00", "GC": "2026-07-02 19:59:00",
       "SI": "2026-07-02 19:59:00", "HG": "2026-07-07 19:59:00", "CL": "2026-07-08 19:59:00",
       "NG": "2026-07-08 19:59:00", "RTY": "2026-07-05 19:59:00", "YM": "2026-07-05 19:59:00"}
DARK = ("NQ_5m", "NQ_2m", "NQ_1h", "RTY_15m", "ES_2m")
COST = 25.0
ARMS = ("A0", "A1", "A2", "C")


def load_arm(d: Path, arm: str) -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob(str(d / f"gc_book_{arm}_*.csv"))):
        slot = Path(f).stem[len(f"gc_book_{arm}_"):]
        b = pd.read_csv(f)
        if not len(b):
            continue
        b["slot"] = slot
        b["tok"] = slot.split("_")[0]
        rows.append(b)
    t = pd.concat(rows, ignore_index=True)
    t["et"] = pd.to_datetime(pd.to_numeric(t["entry_time"]), unit="s")
    t["fresh"] = t["et"] > t["tok"].map(lambda k: pd.Timestamp(PRE[k]))
    t["session"] = t["et"].dt.normalize()
    return t


def fleet(t: pd.DataFrame, cost: float) -> float:
    f = t[t["fresh"]]
    return round(float((f["pnl"] - cost).sum()), 2)


def boot_diff(a: pd.DataFrame, b: pd.DataFrame, cost: float, n_boot: int = 1000, seed: int = 198):
    """Session-block bootstrap of the fleet fresh (arm - base) net difference."""
    fa = a[a["fresh"]].groupby("session")["pnl"].agg(["sum", "count"])
    fb = b[b["fresh"]].groupby("session")["pnl"].agg(["sum", "count"])
    days = sorted(set(fa.index) | set(fb.index))
    da = np.array([(fa["sum"].get(d, 0.0) - cost * fa["count"].get(d, 0)) for d in days])
    db = np.array([(fb["sum"].get(d, 0.0) - cost * fb["count"].get(d, 0)) for d in days])
    diff = da - db
    rng = np.random.default_rng(seed)
    n = len(diff)
    sims = np.array([diff[rng.integers(0, n, n)].sum() for _ in range(n_boot)])
    return {"point": round(float(diff.sum()), 2), "ci95": [round(float(np.percentile(sims, 2.5)), 2),
                                                           round(float(np.percentile(sims, 97.5)), 2)],
            "n_sessions": n}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = Path(a.books)
    arms = {arm: load_arm(d, arm) for arm in ARMS}
    out = {"preregistration": "docs/WS-GATECAL-PREREGISTRATION.md", "issue": "#198", "cost_rt": COST}
    for arm, t in arms.items():
        f = t[t["fresh"]]
        out[arm] = {"full_n": int(len(t)), "fresh_n": int(len(f)),
                    "fresh_raw": round(float(f["pnl"].sum()), 2),
                    "fresh_net10": fleet(t, 10.0), "fresh_net25": fleet(t, COST),
                    "dark_slots_fresh_entries": {s: int((f["slot"] == s).sum()) for s in DARK}}
    for arm in ("A1", "A2", "C"):
        out[f"{arm}_vs_A0"] = boot_diff(arms[arm], arms["A0"], COST)
    churn = out["C_vs_A0"]["point"]
    verdict = {}
    for arm in ("A1", "A2"):
        dv = out[f"{arm}_vs_A0"]
        verdict[arm] = ("POSITIVE" if dv["point"] > churn and dv["ci95"][0] > 0
                        else "NEGATIVE" if dv["ci95"][1] < 0 else "NULL")
    out["churn_floor_C_vs_A0"] = churn
    out["verdict"] = verdict
    Path(a.out).write_text(json.dumps(out, indent=1))
    for arm in ARMS:
        o = out[arm]
        print(f"{arm}: fresh n={o['fresh_n']} raw={o['fresh_raw']:,.0f} net25={o['fresh_net25']:,.0f} dark={o['dark_slots_fresh_entries']}")
    for arm in ("A1", "A2", "C"):
        dv = out[f"{arm}_vs_A0"]
        print(f"{arm} vs A0 @25: {dv['point']:+,.0f}  CI95 {dv['ci95']}  sessions {dv['n_sessions']}")
    print("churn floor (C vs A0):", churn, "| VERDICT:", verdict)
    print("->", a.out)


if __name__ == "__main__":
    main()
