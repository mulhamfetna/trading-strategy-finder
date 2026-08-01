"""Legacy build_payload vs the causal on-screen engine — using the EXACT preset golden runs."""
import os
import sys

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
sys.path.insert(0, PI)
sys.path.insert(0, os.path.join(PI, "perf"))
os.chdir(PI)

import strategy  # noqa: E402
from optimize.l2 import payload as L2  # noqa: E402
from _common import champion_preset  # noqa: E402   (the preset golden uses)

for tf in ("4h", "2h", "1h", "15m", "5m", "2m"):
    p = dict(champion_preset(tf))
    p["window"] = "full"
    legacy = strategy.build_payload(*strategy.get_bundle(tf, "NQ"), p, instrument="NQ")
    lp = L2.validate_layer_params(p)
    causal = L2.build_view_payload(dict(lp, window="full"), {}, tf, "l1",
                                   instrument="NQ", l1_engine=lp)
    ls = legacy["meta"]["summary"]["pnl"]
    ln = legacy["meta"]["summary"]["n_taken"]
    cb = causal["meta"]["boxes"]["pnl"]
    cn = causal["meta"]["boxes"]["n_taken"]
    tag = "OK" if abs(ls - cb) < 1 else "*** DIVERGE ***"
    print(f"{tf:4} cap={str(p.get('cap_mode')):5}/{p.get('cap_1min', 0):>4}  "
          f"legacy=${ls:>10,.0f} (n={ln:>4})   causal=${cb:>10,.0f} (n={cn:>4})   {tag}", flush=True)
