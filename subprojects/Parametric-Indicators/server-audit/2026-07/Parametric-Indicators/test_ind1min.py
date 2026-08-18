"""Isolate the ind_1min mismatch: run GC 4h champion through the dashboard engine with ind_1min True vs False,
compare to the optimizer target (full_pnl 97889 / full_dd 7360)."""
import json, sys
from optimize.l2 import payload as l2p

inst, tf = "GC", "4h"
for i1m in (True, False):
    l1 = dict(l2p.instrument_l1_default(inst, tf))
    l1["ind_1min"] = i1m
    body = dict(l1); body["timeframe"] = tf; body["instrument"] = inst
    l1lay = l2p._layer_from_strategy(body)
    out = l2p.build_view_payload(l1lay, {}, tf, "l1", instrument=inst, l1_engine=body)
    s = out["meta"]["summary"]
    print(f"ind_1min={i1m!s:5} -> pnl ${s['pnl']:>10,.0f} | max_dd ${s['max_dd']:>10,.0f} | "
          f"win {float(s['win']):.1f}% | n_taken {s['n_taken']}")
print("optimizer target (fast engine, ind_1min=False): full_pnl $97,889 | full_dd $7,360 | win(fold) 74%")
