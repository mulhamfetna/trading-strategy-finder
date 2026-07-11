"""NQ 4h is the one slot the dashboard CANNOT serve from the champion file.

payload.l1_default_params() hardcodes tf=="4h" to the frozen lean anchor champion, so selecting NQ+4h in
the UI always loads the incumbent — my UI pass "verified" the old champion, not the new one.

So verify it by running the champion preset through the SAME causal code path the dashboard's L1 view
uses (payload.build_view_payload), which is exactly what the shareable bundle does — and that bundle
reproduces all 55 shipped champions to the dollar. Same engine, same numbers, just bypassing the
hardcoded default.
"""
import json
import os
import sys

PI = os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators")
sys.path.insert(0, PI)
os.chdir(PI)

import presets  # noqa: E402
from optimize.l2 import payload as L2  # noqa: E402

CH = os.path.expanduser("~/Mulham/wsg-i/cap1_champions/cap1_champions_NQ.json")
champs = json.load(open(CH))
entry = champs["4h"]

lp = presets._preset("4h", entry["box"], entry.get("indicators", {}))
lp["ind_1min"] = True
lp = L2.validate_layer_params(lp)

print(f"cap_mode = {lp.get('cap_mode')}   cap_1min = {lp.get('cap_1min')}   "
      f"k = {lp.get('k')}   flip = {lp.get('flip')}", flush=True)
print(f"optimizer claimed: full ${entry['full_pnl']:,.0f}  DD ${entry['full_dd']:,.0f}", flush=True)
print("running the causal engine (the dashboard's L1 path) ...", flush=True)

out = L2.build_view_payload(dict(lp, window="full"), {}, "4h", "l1", instrument="NQ", l1_engine=lp)
b = out["meta"]["boxes"]

p26 = dict(lp); p26["window"] = "2026"
oos = L2.build_view_payload(p26, {}, "4h", "l1", instrument="NQ",
                            l1_engine=p26)["meta"]["summary"]["pnl"]

print("\n" + "=" * 70)
print(f"  NQ 4h  (cap1 challenger)")
print(f"  on-screen P/L : ${b['pnl']:,.0f}")
print(f"  max drawdown  : ${b['max_dd']:,.0f}")
print(f"  win rate      : {b['win']}%   trades: {b['n_taken']}")
print(f"  2026 OOS      : ${oos:,.0f}")
print("=" * 70)
print(f"\n  INCUMBENT (deployed): $149,989 / DD $15,491 / OOS +$58,029")
print(f"  VERDICT: {'NEW wins' if oos > 58029 * 1.05 else 'OLD holds'}  (decided on 2026 out-of-sample)")
json.dump({"inst": "NQ", "tf": "4h", "pnl": b["pnl"], "dd": b["max_dd"],
           "win": b["win"], "n": b["n_taken"], "oos": oos,
           "cap_mode": lp.get("cap_mode"), "cap_1min": lp.get("cap_1min")},
          open(os.path.expanduser("~/Mulham/wsg-i/nq4h_verify.json"), "w"), indent=1)
print("NQ4H_DONE", flush=True)
