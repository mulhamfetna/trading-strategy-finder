"""#88 A/B — does bucketing the indicator axis restore SELECTION in the MAP-Elites archive?

THE CLAIM UNDER TEST. The archive keeps the best solution per niche, which only means anything if each
niche is visited more than once. With the raw indicator count as the second axis the archive is 9 x 166
= 1,494 niches against 400 evaluations (0.27 visits each), so nearly every niche is filled by the FIRST
genome to land in it and never challenged. Bucketing the axis gives 9 x 9 = 81 niches (~4.9 visits).

WHY THIS SCRIPT EXISTS RATHER THAN AN ARGUMENT. The niche arithmetic is arithmetic — it cannot fail, and
that is exactly what makes it untrustworthy as evidence. The falsification criterion was written down
BEFORE the run (docs/reports-2026-08-01/ISSUE-88-explained-visually.md §7):

    if the IMPROVEMENT count does not rise materially, the fix did not work.

An improvement means a newcomer beat a sitting elite. A first-fill means the niche was empty and
anything was accepted — no comparison took place. The old code summed the two into one "improvements"
number, which is why the degraded regime never showed up in a log.

THE CONTROL. The control arm is not a re-run of old code from git; it is THIS code with `ind_bucket`
replaced by the identity function, which is precisely what the second axis used to be. Same seed, same
data, same evaluator, same everything else — the axis is the only difference. Both arms are run in one
process so a machine difference cannot explain the result.

WHAT A PASS DOES NOT MEAN. It does not validate any earlier MAP-Elites result (those came from the
broken shape — that is #90), and it does not claim MAP-Elites beats the ordinary search. Nothing here
compares the two.

Usage:  python3 -m optimize.perf.bench_mapelites_niches 4h --evals 400 [--seed 1]
        (1-minute indicator frame is the default; --tf-indicators switches to the decision frame)
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
from indicators import library


def _arm(name, tf, evals, ind_1min, seed, raw_axis, warm_start):
    """Run one arm. `raw_axis=True` restores the pre-#88 behaviour: niche column = the raw count."""
    original, original_n = ME.ind_bucket, ME.N_NICHES
    if raw_axis:
        ME.ind_bucket = lambda n: int(n)                       # the old axis, exactly
        # N_NICHES too, or the control's own log would claim 81 niches while its axis has 166 columns —
        # a control that misreports itself is worse than no control.
        ME.N_NICHES = (ME.DD_BIN_CAP + 1) * (len(library.REGISTRY) + 1)
    try:
        t0 = time.time()
        print(f"\n{'=' * 92}\nARM: {name}  (indicator axis = "
              f"{'RAW COUNT — pre-#88' if raw_axis else 'BUCKETED — post-#88'})\n{'=' * 92}", flush=True)
        r = ME.run(tf, n_evals=evals, ind_1min=ind_1min, seed=seed, warm_start=warm_start, save=False)
        r["arm"] = name
        r["wall_s"] = round(time.time() - t0, 1)
        # the control's niche total is not ME.N_NICHES — its axis is the registry, so recompute honestly
        r["true_niches"] = ME.N_NICHES
        r["true_evals_per_niche"] = round(evals / r["true_niches"], 3)
        r["quality"] = _quality(r)
        return r
    finally:
        ME.ind_bucket, ME.N_NICHES = original, original_n


# Deployed champions use 3–10 indicators. An archive is not judged by how busy it was but by what is
# IN it, and specifically by what is in the region anything would actually be deployed from.
CHAMPION_ZONE = (3, 10)


def _quality(r: dict) -> dict:
    """What the archive CONTAINS, which is the only thing a portfolio of elites is for.

    Round 1 and round 2 both measured the archive's process (how many improvements, how many
    comparisons) and both criteria failed — the second in the OPPOSITE direction, because an archive
    full of weak first arrivals is EASY to improve and therefore scores well on an improvement count.
    The counter is anti-correlated with the quality it was standing in for. So: measure the contents."""
    ents = [e for e in r["archive"].values() if e]
    zone = [e for e in ents if CHAMPION_ZONE[0] <= e["n_ind"] <= CHAMPION_ZONE[1]]
    best = lambda xs, k: max((e[k] for e in xs), default=None)
    return {
        "entries": len(ents),
        "best_median_pnl": best(ents, "median_pnl"),
        "best_full_pnl": best(ents, "full_pnl"),
        "zone_entries": len(zone),
        "zone_best_median_pnl": best(zone, "median_pnl"),
        "zone_best_full_pnl": best(zone, "full_pnl"),
        # sum of elite fitness over the champion zone: rewards an archive that is good ACROSS the
        # region, not one that got a single lucky point
        "zone_total_median_pnl": sum(e["median_pnl"] for e in zone) if zone else 0.0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="#88 A/B: raw indicator axis vs bucketed")
    ap.add_argument("timeframe")
    ap.add_argument("--evals", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1)
    OPT.add_indicator_frame_args(ap)
    OPT.add_warm_start_args(ap)
    ap.add_argument("--out", default=None, help="write the JSON verdict here")
    a = ap.parse_args()

    print(f"#88 A/B · {a.timeframe} · {a.evals} evals/arm · seed {a.seed} · "
          f"registry {len(library.REGISTRY)} indicators", flush=True)

    # control FIRST, so a crash in the treatment cannot be mistaken for a control that never ran
    ctl = _arm("control_raw_axis", a.timeframe, a.evals, a.ind_1min, a.seed, True, a.warm_start)
    trt = _arm("treatment_bucketed", a.timeframe, a.evals, a.ind_1min, a.seed, False, a.warm_start)

    c, t = ctl["selection"], trt["selection"]
    c_placed, t_placed = c["first_fill"] + c["improvement"], t["first_fill"] + t["improvement"]
    verdict = {
        "timeframe": a.timeframe, "evals": a.evals, "seed": a.seed, "warm_start": a.warm_start,
        "registry": len(library.REGISTRY),
        "control": {"niches": ctl["true_niches"], "evals_per_niche": ctl["true_evals_per_niche"],
                    "filled": ctl["coverage"], **c, "wall_s": ctl["wall_s"], **ctl["quality"]},
        "treatment": {"niches": trt["true_niches"], "evals_per_niche": trt["true_evals_per_niche"],
                      "filled": trt["coverage"], **t, "wall_s": trt["wall_s"], **trt["quality"]},
        "improvement_ratio": round(t["improvement"] / max(1, c["improvement"]), 2),
        # the pre-registered criterion, evaluated here rather than in prose afterwards
        "criterion": "improvements must rise materially (>=2x) over the control",
        "passes": t["improvement"] >= 2 * max(1, c["improvement"]),
    }

    print(f"\n{'=' * 92}\n#88 VERDICT\n{'=' * 92}")
    print(f"{'':22s} {'CONTROL (raw)':>18s} {'TREATMENT (bucketed)':>22s}")
    for lbl, k in (("niches", "niches"), ("evals per niche", "evals_per_niche"),
                   ("niches filled", "filled"), ("first-fills", "first_fill"),
                   ("IMPROVEMENTS", "improvement"), ("rejected", "rejected"),
                   ("infeasible", "infeasible"), ("wall seconds", "wall_s"),
                   # what the archive CONTAINS — the counters above describe its process, and #88
                   # rounds 1 and 2 showed the process counters answer the wrong question
                   ("archive entries", "entries"), ("best median P/L", "best_median_pnl"),
                   ("3-10 ind entries", "zone_entries"),
                   ("3-10 best median P/L", "zone_best_median_pnl"),
                   ("3-10 total median P/L", "zone_total_median_pnl")):
        cv, tv = verdict['control'][k], verdict['treatment'][k]
        fmt = lambda v: f"{v:,.0f}" if isinstance(v, float) else str(v)
        print(f"{lbl:22s} {fmt(cv):>18s} {fmt(tv):>22s}")
    print(f"{'real choices':22s} {100 * c['improvement'] / max(1, c_placed):17.0f}% "
          f"{100 * t['improvement'] / max(1, t_placed):21.0f}%")
    print(f"\nimprovement ratio: {verdict['improvement_ratio']}x  →  "
          f"{'PASS — selection restored' if verdict['passes'] else 'FAIL — the fix did not work'}",
          flush=True)

    if a.out:
        Path(a.out).write_text(json.dumps(verdict, indent=2))
        print(f"wrote {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
