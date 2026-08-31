"""#198 — vol-gate recalibration cadence: replay the 54 `best` slots under the pre-registered arms.

    python3 optimize/gatecal/gatecal_run.py --out <dir> --arm A0|A1|A2|C [--jobs 8]

Arms (docs/WS-GATECAL-PREREGISTRATION.md §2): A0 frozen (hook off — must equal the round-2 books),
A1 quarterly (gate_recal_months=3), A2 monthly (=1), C monthly with a random percentile per boundary
(gate_recal_random_pct_seed = 198 + slot index in sorted (TOKENS x TFS) order — deterministic per slot).
Same causal path as the round-2 books (build_view_payload, l1 view, scaled-permissive L2 stub).
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PI = HERE.parents[2]
sys.path.insert(0, str(PI))

TFS = ("4h", "2h", "1h", "15m", "5m", "2m")
TOKENS = ("NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM")
ARM = os.environ.get("WSH_GATECAL_ARM", "A0")
ARMS = {"A0": dict(), "A1": dict(gate_recal_months=3), "A2": dict(gate_recal_months=1)}


def run_slot(job: tuple[str, str, str]) -> dict:
    tok, tf, outdir = job
    from optimize.l2 import payload as P
    out = {"instrument": tok, "tf": tf, "arm": ARM}
    try:
        champs = json.loads(P._instrument_champions_path(tok, "best").read_text())
        if tf not in champs:
            out["status"] = "no_champion"
            return out
        l1p = P._champion_layer_params(tf, champs[tf])
        if ARM in ("A1", "A2"):
            l1p.update(ARMS[ARM])
        elif ARM == "C":
            idx = [f"{t}_{f}" for t in TOKENS for f in TFS].index(f"{tok}_{tf}")
            l1p.update(gate_recal_months=1, gate_recal_random_pct_seed=198 + idx)
        view = P.build_view_payload(l1p, P._scaled_permissive(tok), tf, "l1", instrument=tok)
        trades = view["trades"]
        pnl = sum(t["pnl"] for t in trades)
        out.update(status="ok", n_trades=len(trades), pnl=round(pnl, 2))
        book = Path(outdir) / f"gc_book_{ARM}_{tok}_{tf}.csv"
        cols = ["layer", "entry_time", "exit_time", "direction", "entry_price", "exit_price",
                "exit_reason", "pnl"]
        with open(book, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for t in sorted(trades, key=lambda r: r["entry_time"]):
                w.writerow(t)
        out["book"] = str(book)
    except Exception as e:  # noqa: BLE001
        import traceback
        out["status"] = f"ERROR: {type(e).__name__}: {e}"
        out["trace"] = traceback.format_exc()[-1500:]
    return out


def main() -> None:
    global ARM
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--arm", required=True, choices=["A0", "A1", "A2", "C"])
    ap.add_argument("--jobs", type=int, default=1)
    a = ap.parse_args()
    ARM = a.arm
    os.environ["WSH_GATECAL_ARM"] = a.arm            # spawn workers re-read it
    outdir = Path(a.out).expanduser()
    outdir.mkdir(parents=True, exist_ok=True)
    jobs = [(tok, tf, str(outdir)) for tok in TOKENS for tf in TFS]
    print(f"# gatecal arm={a.arm} slots={len(jobs)} jobs={a.jobs} "
          f"WSH_DATA_BASE={os.environ.get('WSH_DATA_BASE')!r}", flush=True)
    results = []
    if a.jobs > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(a.jobs) as pool:
            for r in pool.imap_unordered(run_slot, jobs):
                results.append(r)
                print(f"[{r['instrument']} {r['tf']}] {r.get('status')} pnl={r.get('pnl')} n={r.get('n_trades')}", flush=True)
    else:
        for j in jobs:
            r = run_slot(j)
            results.append(r)
            print(f"[{r['instrument']} {r['tf']}] {r.get('status')} pnl={r.get('pnl')} n={r.get('n_trades')}", flush=True)
    (outdir / f"gatecal_summary_{a.arm}.json").write_text(json.dumps(results, indent=1))
    ok = sum(1 for r in results if r.get("status") == "ok")
    print(f"DONE arm={a.arm} ok={ok}/{len(jobs)}", flush=True)


if __name__ == "__main__":
    main()
