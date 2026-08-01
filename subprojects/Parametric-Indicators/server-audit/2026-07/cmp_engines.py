"""Legacy build_payload vs the causal on-screen engine, on the 3 adopted NQ champions."""
import json
import os
import sys

sys.path.insert(0, os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators"))
os.chdir(os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators"))

import presets  # noqa: E402
import strategy  # noqa: E402
from optimize.l2 import payload as L2  # noqa: E402

champs = json.load(open("optimize/results/wsh4_champions_full.json"))

for tf in ("4h", "2h", "1h", "15m", "5m", "2m"):
    c = champs[tf]
    p = presets._preset(tf, c["box"], c.get("indicators", {}))
    p["ind_1min"] = True
    lp = L2.validate_layer_params(p)

    legacy = strategy.build_payload(*strategy.get_bundle(tf, "NQ"),
                                    dict(lp, window="full"), instrument="NQ")
    causal = L2.build_view_payload(dict(lp, window="full"), {}, tf, "l1",
                                   instrument="NQ", l1_engine=lp)

    ls = legacy["meta"]["summary"]["pnl"]
    ln = legacy["meta"]["summary"]["n_taken"]
    cb = causal["meta"]["boxes"]["pnl"]
    cn = causal["meta"]["boxes"]["n_taken"]
    tag = "OK" if abs(ls - cb) < 1 else "*** DIVERGE ***"
    print(f"{tf:4} cap={str(lp.get('cap_mode')):5}/{lp.get('cap_1min'):>4}  "
          f"legacy=${ls:>10,.0f} (n={ln:>4})   causal(on-screen)=${cb:>10,.0f} (n={cn:>4})   {tag}",
          flush=True)
