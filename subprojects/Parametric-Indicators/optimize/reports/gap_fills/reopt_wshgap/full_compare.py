"""Full-metrics before/after: DEPLOYED (wsh4) vs RE-OPTIMIZED (wshgap) champions, BOTH under gap-aware
fills, all 12 slots, full + 2026 OOS windows. Emits JSON for the report."""
import json, sys
from pathlib import Path
ROOT = "/home/dev/Mulham/code/.worktrees/fundamental/subprojects/Parametric-Indicators"
sys.path.insert(0, ROOT)
import presets
from optimize.l2 import payload as L2
RES = Path(ROOT) / "optimize" / "results"
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]

def m(inst, tf, entry):
    base = presets._preset(tf, entry["box"], entry.get("indicators", {}))
    base["ind_1min"] = True; base["gap_fills"] = True
    lp = L2.validate_layer_params(base)
    out = {}
    for key, win in (("full", "full"), ("oos", "2026")):
        p = dict(lp); p["window"] = win
        pay = L2.build_view_payload(p, {}, tf, "l1", instrument=inst, l1_engine=p)
        b, s = pay["meta"]["boxes"], pay["meta"]["summary"]
        out[key] = {"pnl": round(b.get("pnl") or 0), "dd": round(b.get("max_dd") or 0),
                    "n": s.get("n_taken"), "win": round((s.get("win") or 0), 2)}
    out["box"] = {k: entry["box"].get(k) for k in ("sl_soft","sl_hard","tp","cap_mode","cap_1min","gate_pct","dd_limit","flip")}
    return out

report = {}
for inst in ("NQ", "GC"):
    suf = "" if inst == "NQ" else f"_{inst}"
    dep = json.load(open(RES / f"wsh4_champions_full{suf}.json"))
    new = json.load(open(RES / f"wshgap_champions_full{suf}.json"))
    for tf in TFS:
        if tf not in dep or tf not in new: continue
        d = dict(dep[tf]); n = dict(new[tf])
        report[f"{inst}_{tf}"] = {"dep": m(inst, tf, d), "reopt": m(inst, tf, n)}
        print(f"done {inst} {tf}", flush=True)
Path("/home/dev/Mulham/fa-m1/full_compare.json").write_text(json.dumps(report, indent=1))
print("WROTE /home/dev/Mulham/fa-m1/full_compare.json")
