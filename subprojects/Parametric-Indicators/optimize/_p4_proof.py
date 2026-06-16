"""P4 full proof on 4h (ind_1min=True). Confirms: champion-seeded ⇒ archive holds a ≥-champion elite;
the archive fills MULTIPLE niches (diversity/portfolio); coverage > 1. Dumps /tmp/p4_proof.json. Throwaway."""
import json, warnings
warnings.filterwarnings("ignore")
from optimize import map_elites as ME

WSH4_MEDIAN = 33587.0
r = ME.run("4h", n_evals=60, ind_1min=True, warm_start=True, seed=1, save=False)
best = r["best_overall"] or {}
out = {"coverage": r["coverage"], "dur_s": r["dur_s"],
       "best_overall": best, "safest": r["safest"], "simplest": r["simplest"],
       "champion_floor_met": bool(best and best["median_pnl"] >= WSH4_MEDIAN - 1.0),
       "is_portfolio": r["coverage"] > 1}
json.dump(out, open("/tmp/p4_proof.json", "w"), indent=2)
print("WROTE /tmp/p4_proof.json", flush=True)
