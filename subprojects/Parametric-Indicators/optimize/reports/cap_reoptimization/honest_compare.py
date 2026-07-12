"""Re-decide every slot on CORRECTED out-of-sample numbers.

WHY THIS EXISTS: every 2026 OOS figure we had was read from meta.summary, which came from
strategy.build_payload — and that path DROPPED the time-cap parameters. So OOS was computed with the cap
switched off, letting trades run past the deadline the strategy actually enforces. Every non-NQ champion
is capped, so essentially every OOS number in the project was inflated — for the incumbents AND the
challengers alike.

strategy.validate_params now preserves the caps and build_payload passes them to the engine (verified:
the headless path reproduces the UI to the dollar, and boxes == summary on the OOS window for the first
time). This script recomputes BOTH sides of every slot on that fixed engine and re-decides.

Emits progress after every champion (no silent waits).
"""
import json
import os
import sys
import time

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
sys.path.insert(0, PI)
os.chdir(PI)

import presets  # noqa: E402
from optimize.l2 import payload as L2  # noqa: E402

WSI = os.path.expanduser("~/Mulham/wsg-i")
BAK = f"{WSI}/deployed_champions_backup"
CAP = f"{WSI}/cap1_champions"
OUT = f"{WSI}/honest_compare.json"

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]


def run(inst, tf, entry):
    """Corrected on-screen P/L, drawdown and 2026 OOS for one champion."""
    p = presets._preset(tf, entry["box"], entry.get("indicators", {}))
    p["ind_1min"] = True
    lp = L2.validate_layer_params(p)
    full = L2.build_view_payload(dict(lp, window="full"), {}, tf, "l1",
                                 instrument=inst, l1_engine=lp)
    p26 = dict(lp); p26["window"] = "2026"
    oos = L2.build_view_payload(p26, {}, tf, "l1", instrument=inst, l1_engine=p26)
    b = full["meta"]["boxes"]
    return dict(pnl=b["pnl"], dd=b["max_dd"], win=b["win"], n=b["n_taken"],
                oos=oos["meta"]["boxes"]["pnl"],
                cap_mode=lp.get("cap_mode"), cap_1min=lp.get("cap_1min"))


rows = []
t0 = time.time()
total = len(INSTS) * len(TFS)

for inst in INSTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    old_ch = json.load(open(f"{BAK}/wsh4_champions_full{suf}.json"))
    new_ch = json.load(open(f"{CAP}/cap1_champions_{inst}.json"))

    for tf in TFS:
        i = len(rows) + 1
        rec = {"inst": inst, "tf": tf}
        try:
            rec["old"] = run(inst, tf, old_ch[tf]) if tf in old_ch else None
            rec["new"] = run(inst, tf, new_ch[tf]) if tf in new_ch else None
        except Exception as e:
            rec["err"] = str(e)[:140]
            print(f"ERROR [{i}/{total}] {inst} {tf}: {rec['err']}", flush=True)

        o, n = rec.get("old"), rec.get("new")
        if o and n:
            print(f"[{i:2d}/{total}] {inst:3} {tf:3}  "
                  f"OLD ${o['pnl']:>9,.0f} / oos ${o['oos']:>8,.0f}   "
                  f"NEW ${n['pnl']:>9,.0f} / oos ${n['oos']:>8,.0f}  "
                  f"(cap {n['cap_mode']}/{n['cap_1min']})", flush=True)
        rows.append(rec)
        json.dump(rows, open(OUT, "w"), indent=1)
        el = time.time() - t0
        print(f"PROGRESS {i}/{total} ({100*i//total}%) elapsed {el/60:.1f}m "
              f"ETA {(el/i)*(total-i)/60:.1f}m", flush=True)

print(f"\nCOMPARE_DONE -> {OUT}", flush=True)
