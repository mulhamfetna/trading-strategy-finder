"""Measure the cost of FORCING the end-of-day close onto every deployed champion — and capture the FULL
metric set while we're at it (the playbooks were shipping fabricated placeholders).

For each of the 54 deployed champions, run BOTH:
    AS-DEPLOYED   — the exit rule the optimizer actually chose
    EOD-FORCED    — the same strategy with the end-of-day close switched on:
                        cap_mode none -> eod
                        cap_mode bars -> both   (keep the bar cap, add end-of-day)
                        eod / both    -> unchanged (already closes at end of day)

...over BOTH windows (full history + the held-out 2026 year), capturing every metric the playbooks print:
pnl, max_dd, win, n_taken, n_candidates, exposure, pf, payoff, avg_win, avg_loss, n_locks.

NOTE THE ASYMMETRY BEING TESTED: 41 of these champions were TUNED in a world where they could hold
overnight. Forcing them to close will cut trades short in ways their stops/targets were never optimized
for. A drop is the expected outcome, not a bug — the point is to see HOW MUCH.
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
RES = f"{PI}/optimize/results"
OUT = f"{WSI}/eod_forced.json"

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]

FORCE = {"none": "eod", "bars": "both", "eod": "eod", "both": "both"}
KEYS = ("pnl", "max_dd", "win", "n_taken", "n_candidates", "exposure", "pf", "payoff", "n_locks")
SKEYS = ("avg_win", "avg_loss")


def metrics(inst, tf, lp):
    """Full metric set, both windows, from the causal on-screen engine."""
    out = {}
    for key, win in (("full", "full"), ("oos2026", "2026")):
        p = dict(lp); p["window"] = win
        pay = L2.build_view_payload(p, {}, tf, "l1", instrument=inst, l1_engine=p)
        b, s = pay["meta"]["boxes"], pay["meta"]["summary"]
        m = {k: b.get(k) for k in KEYS}
        m.update({k: s.get(k) for k in SKEYS})
        out[key] = m
    return out


rows = []
t0 = time.time()
total = 54
for inst in INSTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    champs = json.load(open(f"{RES}/wsh4_champions_full{suf}.json"))
    for tf in TFS:
        i = len(rows) + 1
        c = champs[tf]
        base = presets._preset(tf, c["box"], c.get("indicators", {}))
        base["ind_1min"] = True
        lp = L2.validate_layer_params(base)

        cur_mode = lp.get("cap_mode", "none")
        forced = dict(lp)
        forced["cap_mode"] = FORCE[cur_mode]
        forced["eod_margin_min"] = int(forced.get("eod_margin_min") or 15)
        forced = L2.validate_layer_params(forced)

        rec = {"inst": inst, "tf": tf, "cap_mode": cur_mode,
               "cap_1min": int(lp.get("cap_1min") or 0),
               "forced_mode": forced["cap_mode"]}
        try:
            rec["as_deployed"] = metrics(inst, tf, lp)
            rec["eod_forced"] = (rec["as_deployed"] if cur_mode in ("eod", "both")
                                 else metrics(inst, tf, forced))
            a, b = rec["as_deployed"], rec["eod_forced"]
            d_full = b["full"]["pnl"] - a["full"]["pnl"]
            d_oos = b["oos2026"]["pnl"] - a["oos2026"]["pnl"]
            tag = "(already closes EOD)" if cur_mode in ("eod", "both") else ""
            print(f"[{i:2d}/{total}] {inst:3} {tf:3} {cur_mode:5}->{rec['forced_mode']:5}  "
                  f"full ${a['full']['pnl']:>9,.0f} -> ${b['full']['pnl']:>9,.0f} ({d_full:>+9,.0f})   "
                  f"oos ${a['oos2026']['pnl']:>8,.0f} -> ${b['oos2026']['pnl']:>8,.0f} ({d_oos:>+8,.0f}) {tag}",
                  flush=True)
        except Exception as e:
            rec["err"] = str(e)[:150]
            print(f"[{i:2d}/{total}] {inst} {tf}: ERROR {rec['err']}", flush=True)

        rows.append(rec)
        json.dump(rows, open(OUT, "w"), indent=1)
        el = time.time() - t0
        print(f"PROGRESS {i}/{total} elapsed {el/60:.1f}m ETA {(el/i)*(total-i)/60:.1f}m", flush=True)

print(f"\nEODFORCED_DONE -> {OUT}", flush=True)
