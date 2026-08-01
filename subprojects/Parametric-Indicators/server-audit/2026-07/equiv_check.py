"""Does the headless causal path now match the UI, post-fix?

The UI (final_verify, running now) reported NQ 4h: on-screen $148,670, 2026 OOS $64,877.
Before the strategy.py cap fix, the same headless call returned OOS $80,424 (cap-blind summary).
If headless now returns $64,877, the two agree and we can safely compute the 108-champion comparison
headlessly instead of driving 216 browser runs.
"""
import json
import os
import sys

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
sys.path.insert(0, PI)
os.chdir(PI)

import presets  # noqa: E402
from optimize.l2 import payload as L2  # noqa: E402

champs = json.load(open("optimize/results/wsh4_champions_full.json"))
c = champs["4h"]
p = presets._preset("4h", c["box"], c.get("indicators", {}))
p["ind_1min"] = True
lp = L2.validate_layer_params(p)

full = L2.build_view_payload(dict(lp, window="full"), {}, "4h", "l1", instrument="NQ", l1_engine=lp)
p26 = dict(lp); p26["window"] = "2026"
oos = L2.build_view_payload(p26, {}, "4h", "l1", instrument="NQ", l1_engine=p26)

print(f"  headless on-screen (boxes) : ${full['meta']['boxes']['pnl']:,.0f}   (UI said $148,670)")
print(f"  headless 2026 OOS (summary): ${oos['meta']['summary']['pnl']:,.0f}   (UI said $64,877)")
print(f"  headless 2026 OOS (boxes)  : ${oos['meta']['boxes']['pnl']:,.0f}")
