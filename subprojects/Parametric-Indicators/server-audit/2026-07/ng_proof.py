"""THE DECISIVE TEST.

The optimizer scored NG 5m at +$38,079. The causal engine, running the champion we EXTRACTED, said -$1,714
and we called the optimizer a liar for the sixth time.

But the extractor rounds sl/tp/dd to 4 decimals, and NG's are ~0.0008 — so we wrote out a strategy whose
stops differ from the scored one by 1-2%. Run the causal engine on the TRUE (unrounded) params. If it now
agrees with the optimizer, the fast engine was right all along and the bug is OURS.
"""
import json
import os
import sys

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
sys.path.insert(0, PI)
os.chdir(PI)

import presets  # noqa: E402
from optimize.l2 import payload as L2  # noqa: E402

BASE = os.path.expanduser("~/Mulham/wsg-i")
INST, TF = "NG", "5m"

# the TRUE params, straight from the winning trial in Postgres
TRUE = {"sl_soft": 0.0008091912403781283,
        "sl_hard": 0.0008091912403781283 + 0.00020807253887150654,
        "tp": 0.003925881552422834,
        "dd_limit": 0.0035520951848387813}

ch = json.load(open(f"optimize/results/eod1_champions_full_{INST}.json"))[TF]


def run(box, label):
    lp = presets._preset(TF, box, ch.get("indicators", {}))
    lp["ind_1min"] = True
    lp = L2.validate_layer_params(lp)
    out = {}
    for key, win in (("full", "full"), ("2026", "2026")):
        p = dict(lp); p["window"] = win
        pay = L2.build_view_payload(p, {}, TF, "l1", instrument=INST, l1_engine=p)
        out[key] = pay["meta"]["boxes"]
    f, o = out["full"], out["2026"]
    print(f"  {label:34} full ${f['pnl']:>10,.0f}  DD ${f['max_dd']:>8,.0f}  n={f['n_taken']:>5}   "
          f"2026 ${o['pnl']:>9,.0f}  n={o['n_taken']:>5}", flush=True)
    return f["pnl"]


print(f"NG 5m — the optimizer claimed  +$38,079\n")
rounded = run(dict(ch["box"]), "champion AS EXTRACTED (4-dp)")

box_true = dict(ch["box"])
box_true.update(TRUE)
exact = run(box_true, "same champion, TRUE precision")

print()
print(f"  rounding to 4 decimals moved the result by  ${exact - rounded:>+12,.0f}")
if exact > 0 and rounded < 0:
    print("\n  ⇒ THE ROUNDING FLIPPED THE SIGN. The optimizer was right; the extractor corrupted the champion.")
