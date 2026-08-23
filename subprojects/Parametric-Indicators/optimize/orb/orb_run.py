"""WS-ORB (#183) Phase 3 — run the pre-registered grid on the 16-year 1-minute tape (server).

    python3 optimize/orb/orb_run.py --root /home/dev/Mulham/data_2010_1s --out <dir> [--tokens NQ,ES] [--jobs 9]

Per instrument: 2 arms x 4 windows x 3 rules = 24 cells (+ C1 comparator). Each cell -> trade book CSV
(orb_book_<TOK>_<arm>_<N>_<rule>.csv) and a summary row with raw / $10 / $25 per-trade stats on the three
pre-registered windows (exploration 2010-06..2017, confirmation 2018..2024, fresh 2025..2026-08-07) plus a
per-calendar-year table on the confirmation window. No parameter is chosen here; this is a grid, not a search.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
from optimize.orb.orb_reference import RULES, WINDOWS, run_c1, run_cell  # noqa: E402

PV = {"NQ": 20.0, "ES": 50.0, "GC": 100.0, "SI": 5000.0, "HG": 25000.0, "CL": 1000.0, "NG": 10000.0, "RTY": 50.0, "YM": 5.0}
TICK = {"NQ": 0.25, "ES": 0.25, "GC": 0.1, "SI": 0.005, "HG": 0.0005, "CL": 0.01, "NG": 0.001, "RTY": 0.1, "YM": 1.0}
WIN = {"exploration": ("2010-06-06", "2017-12-31"), "confirmation": ("2018-01-01", "2024-12-31"), "fresh": ("2025-01-01", "2026-08-07")}
COSTS = (0.0, 10.0, 25.0)


def stats(b: pd.DataFrame) -> dict:
    out = {}
    n = len(b)
    for c in COSTS:
        p = b["pnl"] - c
        k = f"c{int(c)}"
        out[k] = {"n": n, "pnl": round(float(p.sum()), 2), "mean": round(float(p.mean()), 2) if n else None,
                  "sd": round(float(p.std(ddof=1)), 2) if n > 1 else None,
                  "t": round(float(p.mean() / (p.std(ddof=1) / np.sqrt(n))), 3) if n > 1 and p.std(ddof=1) > 0 else None,
                  "win": round(float((p > 0).mean()), 4) if n else None}
    return out


def run_token(tok: str, root: Path, out: Path) -> list[dict]:
    df = pd.read_csv(root / f"{tok}_Continuous_Data" / f"{tok}_1m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    rows = []
    cells = [(arm, N, rule) for arm in ("cash", "globex") for N in WINDOWS for rule in RULES] + [("cash", 0, "C1")]
    for arm, N, rule in cells:
        b = run_c1(df, tok, PV[tok]) if rule == "C1" else run_cell(df, arm, tok, N, rule, PV[tok])
        key = f"{tok}_{arm}_{N}_{rule}"
        if len(b) == 0:
            rows.append({"cell": key, "tok": tok, "arm": arm, "N": N, "rule": rule, "n": 0})
            print(key, "no trades", flush=True)
            continue
        b.to_csv(out / f"orb_book_{key}.csv", index=False)
        b["entry_time"] = pd.to_datetime(b["entry_time"])
        r = {"cell": key, "tok": tok, "arm": arm, "N": N, "rule": rule, "n": len(b),
             "gross_edge_ticks": round(float(b["points"].mean() / TICK[tok]), 2),
             "exit_reasons": b["exit_reason"].value_counts().to_dict()}
        for w, (a, z) in WIN.items():
            s = b[(b["entry_time"] >= a) & (b["entry_time"] <= f"{z} 23:59:59")]
            r[w] = stats(s)
        conf = b[(b["entry_time"] >= WIN["confirmation"][0]) & (b["entry_time"] <= WIN["confirmation"][1] + " 23:59:59")]
        yr = (conf["pnl"] - 25.0).groupby(conf["entry_time"].dt.year).agg(["sum", "count"])
        r["years_c25"] = {int(y): [round(float(v["sum"]), 2), int(v["count"])] for y, v in yr.iterrows()}
        rows.append(r)
        c = r["confirmation"]["c25"]
        print(f"{key:22s} n={len(b):5d} conf@25 pnl={c['pnl']:>12,.0f} mean={c['mean']} t={c['t']} ticks={r['gross_edge_ticks']}", flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/home/dev/Mulham/data_2010_1s")
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokens", default="NQ,ES,GC,SI,HG,CL,NG,RTY,YM")
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    toks = a.tokens.split(",")
    if a.jobs > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(a.jobs) as pool:
            res = pool.starmap(run_token, [(t, Path(a.root), out) for t in toks])
    else:
        res = [run_token(t, Path(a.root), out) for t in toks]
    rows = [r for rr in res for r in rr]
    (out / "orb_summary.json").write_text(json.dumps(rows, indent=1, default=str))
    print(f"DONE cells={len(rows)} -> {out / 'orb_summary.json'}", flush=True)


if __name__ == "__main__":
    main()
