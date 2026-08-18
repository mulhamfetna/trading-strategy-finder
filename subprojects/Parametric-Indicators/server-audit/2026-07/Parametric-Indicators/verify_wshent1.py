import sys, json
from pathlib import Path
PI = Path("/home/dev/Mulham/wsg-i/Parametric-Indicators")
sys.path.insert(0, str(PI))
from indicators import library                    # noqa: E402
from optimize.l2 import payload                   # noqa: E402

CAST = {key: {p["name"]: type(p["default"]) for p in library.SCHEMA[key].get("params", [])}
        for key in library.REGISTRY}


def recipe(np):
    box = dict(sl_soft=round(np["sl_soft"], 2), sl_hard=round(np["sl_soft"] + np["sl_hard_delta"], 2),
               tp=round(np["tp"], 2), gate_pct=round(np["gate_pct"], 2), dd_limit=round(np["dd_limit"], 2),
               cooldown=int(np["cooldown"]), flip=bool(int(np["flip"])), k=int(np["k"]),
               cap_1min=int(np.get("cap_1min", 0) or 0))
    inds = {}
    for key in library.REGISTRY:
        if int(np.get("en_" + key, 0)) == 1:
            params = {pn: c(np[f"{key}_{pn}"]) for pn, c in CAST.get(key, {}).items() if np.get(f"{key}_{pn}") is not None}
            inds[key] = params
    return {"box": box, "indicators": inds}


summ = json.load(open(PI / "optimize/results/wshent1_4h_summary.json"))
for key, label in [("champion_max_full_pnl", "max-P/L"), ("champion_max_entries", "max-entries"),
                   ("champion_max_median_pnl", "max-med-P/L")]:
    ch = summ[key]
    preset = payload._champion_layer_params("4h", recipe(ch["params"]))
    res = payload.run_l1_cached("4h", params=preset, instrument="NQ")
    pnl = sum(t["pnl"] for t in res.ledger)
    n = len(res.ledger)
    diff = 100.0 * (pnl - ch["full_pnl"]) / ch["full_pnl"]
    print(f"{label:12} dashboard-L1 = ${pnl:>10,.0f}  ({n} entries)   study full_pnl = ${ch['full_pnl']:>10,.0f}   diff {diff:+.1f}%")
