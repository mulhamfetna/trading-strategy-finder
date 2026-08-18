"""#101 A/B — does widening the mutation parent pool with stepping stones help?

THE FINDING THIS TESTS. MAP-Elites draws every parent from the archive, and the archive only holds
FEASIBLE solutions. Measured across 32 runs: ~70-75% of evaluations are discarded, so a 4,000-evaluation
run mutates a pool of about THIRTY genomes. A method whose purpose is to resist collapsing into one
basin is running with a population of thirty.

THE CHANGE. Scored-but-infeasible genomes are kept in a separate archive ranked by how badly they miss
the constraint, and mutation may use them as parents. They NEVER enter the result archive — only the
parent pool widens.

Both arms use the bucketed axis (#88) and cold start (#102). `--stepping-stones` is the only difference,
and both arms run in one process so a machine difference cannot explain the result.

Criterion pre-registered in docs/reports-2026-08-03/ISSUE-101-diagnosis-and-prereg.md.

Usage:  python3 -m optimize.perf.bench_stepping_stones 4h --evals 4000 --seed 1 --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from optimize import map_elites as ME
from optimize import optimizer as OPT
from optimize.perf.bench_mapelites_niches import _quality


def _arm(name, tf, evals, ind_1min, seed, warm_start, stepping):
    t0 = time.time()
    print(f"\n{'=' * 92}\nARM: {name}  (stepping stones {'ON' if stepping else 'OFF'})\n{'=' * 92}",
          flush=True)
    r = ME.run(tf, n_evals=evals, ind_1min=ind_1min, seed=seed, warm_start=warm_start, save=False,
               stepping_stones=stepping)
    r["wall_s"] = round(time.time() - t0, 1)
    r["quality"] = _quality(r)
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="#101 A/B: stepping-stone parent pool")
    ap.add_argument("timeframe")
    ap.add_argument("--evals", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=1)
    OPT.add_indicator_frame_args(ap)
    OPT.add_warm_start_args(ap)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    # control FIRST, so a crash in the treatment cannot be mistaken for a control that never ran
    off = _arm("control_feasible_only", a.timeframe, a.evals, a.ind_1min, a.seed, a.warm_start, False)
    on = _arm("treatment_stepping", a.timeframe, a.evals, a.ind_1min, a.seed, a.warm_start, True)

    pick = lambda r: {**r["selection"], "filled": r["coverage"], "wall_s": r["wall_s"],
                      "parent_pool": r.get("parent_pool"), **r["quality"]}
    c, t = pick(off), pick(on)
    verdict = {"timeframe": a.timeframe, "evals": a.evals, "seed": a.seed,
               "warm_start": a.warm_start, "control": c, "treatment": t,
               "criterion": "best_median_pnl (ON) > (OFF), >=6/8 seeds",
               "treatment_wins": (t["best_median_pnl"] or 0) > (c["best_median_pnl"] or 0)}

    print(f"\n{'=' * 92}\n#101 VERDICT (seed {a.seed})\n{'=' * 92}")
    print(f"{'':24s} {'OFF (feasible only)':>20s} {'ON (stepping)':>18s}")
    for lbl, k in (("parent pool", "parent_pool"), ("niches filled", "filled"),
                   ("stepping stones kept", "stepping"),
                   ("BEST median P/L", "best_median_pnl"),
                   ("3-10 best median P/L", "zone_best_median_pnl"),
                   ("3-10 entries", "zone_entries"),
                   ("improvements", "improvement"), ("discarded", "infeasible"),
                   ("wall seconds", "wall_s")):
        f = lambda v: f"{v:,.0f}" if isinstance(v, float) else str(v)
        print(f"{lbl:24s} {f(c.get(k)):>20s} {f(t.get(k)):>18s}")
    print(f"\ntreatment wins this seed: {verdict['treatment_wins']}", flush=True)

    if a.out:
        Path(a.out).write_text(json.dumps(verdict, indent=2))
        print(f"wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
