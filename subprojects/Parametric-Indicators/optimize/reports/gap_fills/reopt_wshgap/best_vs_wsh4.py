"""HEAD-TO-HEAD: dev's best_ champions vs FA's wsh4-adopted champions, BOTH under the honest engine
(gap_fills=True), NQ+GC, full + 2026 OOS. Isolates 'which champion SELECTION is better' from the
optimistic-fill inflation that flattered best_'s original OOS number."""
import json, sys
from pathlib import Path
ROOT = "/home/dev/Mulham/code/.worktrees/fundamental/subprojects/Parametric-Indicators"
sys.path.insert(0, ROOT)
import presets
from optimize.l2 import payload as L2
RES = Path(ROOT) / "optimize" / "results"
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]

def score(inst, tf, entry):
    base = presets._preset(tf, entry["box"], entry.get("indicators", {}))
    base["ind_1min"] = True; base["gap_fills"] = True
    lp = L2.validate_layer_params(base)
    out = {}
    for key, win in (("full","full"), ("oos","2026")):
        p = dict(lp); p["window"] = win
        pay = L2.build_view_payload(p, {}, tf, "l1", instrument=inst, l1_engine=p)
        b = pay["meta"]["boxes"]
        out[key] = (round(b.get("pnl") or 0), round(b.get("max_dd") or 0))
    return out

# best_ extracted from origin/dev to /tmp; wsh4-adopted from the FA worktree
SETS = {"NQ": ("/tmp/best_NQ.json", RES/"wsh4_champions_full.json"),
        "GC": ("/tmp/best_GC.json", RES/"wsh4_champions_full_GC.json")}
tot = {"best_full":0,"wsh4_full":0,"best_oos":0,"wsh4_oos":0}
print(f"{'mkt tf':8} | {'best full':>10} {'wsh4 full':>10} {'Δfull':>9} | {'best oos':>9} {'wsh4 oos':>9} {'Δoos':>9}")
print("-"*76)
for inst,(bp,wp) in SETS.items():
    best = json.load(open(bp)); wsh4 = json.load(open(wp))
    for tf in TFS:
        if tf not in best or tf not in wsh4: continue
        bs = score(inst, tf, best[tf]); ws = score(inst, tf, wsh4[tf])
        tot["best_full"]+=bs["full"][0]; tot["wsh4_full"]+=ws["full"][0]
        tot["best_oos"]+=bs["oos"][0]; tot["wsh4_oos"]+=ws["oos"][0]
        adopted = " *" if (inst,tf) in {("NQ","1h"),("NQ","2h"),("GC","15m")} else "  "
        print(f"{inst} {tf:>3}{adopted}| {bs['full'][0]:>10,} {ws['full'][0]:>10,} {ws['full'][0]-bs['full'][0]:>+9,} "
              f"| {bs['oos'][0]:>9,} {ws['oos'][0]:>9,} {ws['oos'][0]-bs['oos'][0]:>+9,}", flush=True)
print("-"*76)
print(f"{'TOTAL':8} | {tot['best_full']:>10,} {tot['wsh4_full']:>10,} {tot['wsh4_full']-tot['best_full']:>+9,} "
      f"| {tot['best_oos']:>9,} {tot['wsh4_oos']:>9,} {tot['wsh4_oos']-tot['best_oos']:>+9,}")
print("\n(* = FA-adopted slot.  Δ = wsh4-adopted minus best_, both on the HONEST engine. + = wsh4 better.)")
