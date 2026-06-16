"""P3 full proof on 4h vs wsh4 (ind_1min=True, the champion's frame). Shares ONE Stage A across both
Stage-B engines (cmaes, gp). Dumps JSON to /tmp/p3_proof.json. Throwaway harness (not committed-critical)."""
import json, time, warnings
warnings.filterwarnings("ignore")
from optimize import two_stage as TS

WSH4_MEDIAN = 33587.0   # warm-start champion median fold P/L (golden full P/L $142,203)

ctx = TS._Ctx("4h", split_sltp=False, ind_1min=True, folds=5, min_trades=5, warm_start=True)
shortlist = TS.run_stage_a(ctx, n_trials=14, top_k=2, seed=1)
out = {"wsh4_median": WSH4_MEDIAN, "has_champion": ctx.has_champion, "engines": {}}
for eng in ("cmaes", "gp"):
    t0 = time.time()
    results = []
    for i, ef in enumerate(shortlist):
        b = TS.run_stage_b(ctx, ef, eng, n_trials=10, seed=1)
        if b:
            results.append(b)
            print(f"[{eng}] subset {'champion' if i==0 else f'#{i}'}: med ${b['median_pnl']:,.0f} "
                  f"full ${b['full_pnl']:,.0f} DD ${b['full_dd']:,.0f} +{b['n_ind']}ind", flush=True)
    champ = max(results, key=lambda r: r["median_pnl"]) if results else None
    out["engines"][eng] = {
        "dur_s": time.time() - t0,
        "n_feasible_subsets": len(results),
        "champion": None if not champ else {
            "median_pnl": champ["median_pnl"], "worst_dd": champ["worst_dd"],
            "median_win": champ["median_win"], "full_pnl": champ["full_pnl"],
            "full_dd": champ["full_dd"], "n_ind": champ["n_ind"], "flip": champ["en_flip"]["flip"]},
        "beats_or_matches_wsh4": bool(champ and champ["median_pnl"] >= WSH4_MEDIAN - 1.0),
    }
    print(f"[{eng}] DONE: champion median ${champ['median_pnl']:,.0f}  "
          f">= wsh4 ${WSH4_MEDIAN:,.0f}? {out['engines'][eng]['beats_or_matches_wsh4']}", flush=True)

json.dump(out, open("/tmp/p3_proof.json", "w"), indent=2)
print("WROTE /tmp/p3_proof.json", flush=True)
