"""VERIFY the 54 cold-start forced-EOD (eod1) champions with the CAUSAL engine, then run the
three-way head-to-head that decides what ships.

WHY THIS EXISTS. The optimizer's fast engine is an approximation. It has now lied FIVE times (HG 2m,
NG 15m twice, NG 2m) -- twice by the SIGN, claiming a profit on a strategy that actually loses money.
So NOTHING the campaign printed is trusted until the causal engine (the one the dashboard draws) has
re-run it. That is what this does.

THREE CANDIDATES PER SLOT, all measured the same way, decided on the HELD-OUT 2026 YEAR:
    deployed   -- today's champion (most hold overnight)          [already in honest_metrics.json]
    bolt-on    -- that same champion with EOD switched on, no re-tuning  [already in eod_forced.json]
    eod1       -- this campaign: cold-start, re-tuned WITH the EOD close forced   <-- measured here

The in-sample number is NOT the decider. Several eod1 champions look spectacular in-sample and were
found by a search that saw that data; 2026 is the year none of them have seen.
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
CHAMPS = f"{WSI}/eod1_champions"
OUT = f"{WSI}/eod1_verified.json"

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
KEYS = ("pnl", "max_dd", "win", "n_taken", "n_candidates", "exposure", "pf", "payoff", "n_locks")
SKEYS = ("avg_win", "avg_loss", "position_hold_total", "pnl_2025", "pnl_2026")


def metrics(inst, tf, lp):
    out = {}
    for key, win in (("full", "full"), ("oos2026", "2026")):
        p = dict(lp); p["window"] = win
        pay = L2.build_view_payload(p, {}, tf, "l1", instrument=inst, l1_engine=p)
        b, s = pay["meta"]["boxes"], pay["meta"]["summary"]
        m = {k: b.get(k) for k in KEYS}
        m.update({k: s.get(k) for k in SKEYS})
        out[key] = m
    return out


rows, t0 = [], time.time()
for inst in INSTS:
    champs = json.load(open(f"{CHAMPS}/eod1_champions_{inst}.json"))
    for tf in TFS:
        i = len(rows) + 1
        c = champs[tf]
        base = presets._preset(tf, c["box"], c.get("indicators", {}))
        base["ind_1min"] = True
        lp = L2.validate_layer_params(base)
        rec = {"inst": inst, "tf": tf,
               "cap_mode": lp.get("cap_mode", "none"),
               "cap_1min": int(lp.get("cap_1min") or 0),
               "claimed_full": c.get("full_pnl") or c.get("pnl")}
        try:
            m = metrics(inst, tf, lp)
            rec["eod1"] = m
            f, o = m["full"], m["oos2026"]
            # the fabrication guard: profit with no trades is the bug, not a champion
            for w, d in (("full", f), ("2026", o)):
                if (d.get("n_taken") or 0) == 0 and abs(d.get("pnl") or 0) > 1:
                    raise ValueError(f"{w}: ${d['pnl']:,.0f} across 0 trades")
            cl = rec["claimed_full"]
            drift = ("" if not cl else f"  optimizer said ${cl:,.0f}"
                     + ("  *** ENGINE DISAGREES ***" if abs(cl - f["pnl"]) > max(50, .02 * abs(cl)) else ""))
            print(f"[{i:2d}/54] {inst:3} {tf:3} {rec['cap_mode']:5} "
                  f"full ${f['pnl']:>9,.0f} DD ${f['max_dd']:>7,.0f} n={f['n_taken']:>5} | "
                  f"2026 ${o['pnl']:>8,.0f} DD ${o['max_dd']:>6,.0f} n={o['n_taken']:>4}{drift}", flush=True)
        except Exception as e:
            rec["err"] = str(e)[:160]
            print(f"[{i:2d}/54] {inst:3} {tf:3}  ERROR {rec['err']}", flush=True)
        rows.append(rec)
        json.dump(rows, open(OUT, "w"), indent=1)
        el = time.time() - t0
        print(f"PROGRESS {i}/54  elapsed {el/60:.1f}m  ETA {(el/i)*(54-i)/60:.1f}m", flush=True)

print("VERIFY_DONE", flush=True)
