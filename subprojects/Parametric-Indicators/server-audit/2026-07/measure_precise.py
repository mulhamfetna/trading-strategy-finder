"""Re-measure ALL THREE candidates per slot from the PRECISION-CORRECTED champions.

Everything measured before this point was measured on champions whose stops had been rounded to four
decimal places — which is a 1-2% distortion in the four lowest-priced markets and flipped NG 5m's sign.
So every number in honest_metrics.json / eod_forced.json / eod1_verified.json is suspect for SI/HG/CL/NG,
and every gate_pct was written at 2 dp when the optimizer scored ~10 significant digits. Re-measure all of
it rather than try to reason about which slots "probably" didn't move.

    deployed  cap1p champion, exactly as the optimizer chose it
    bolt-on   that champion with the end-of-day close switched on, nothing re-tuned
    eod1      eod1p champion — cold start, re-tuned WITH the bell close forced

Causal engine, both windows, on-screen truth (meta.boxes).
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

BASE = os.path.expanduser("~/Mulham/wsg-i")
RES = f"{PI}/optimize/results"
OUT = f"{BASE}/precise_metrics.json"

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
FORCE = {"none": "eod", "bars": "both", "eod": "eod", "both": "both"}
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


def layer(tf, entry):
    lp = presets._preset(tf, entry["box"], entry.get("indicators", {}))
    lp["ind_1min"] = True
    return L2.validate_layer_params(lp)


rows, t0 = [], time.time()
for inst in INSTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    dep = json.load(open(f"{RES}/cap1p_champions_full{suf}.json"))
    new = json.load(open(f"{RES}/eod1p_champions_full{suf}.json"))
    for tf in TFS:
        i = len(rows) + 1
        rec = {"inst": inst, "tf": tf}
        try:
            dlp = layer(tf, dep[tf])
            cur = dlp.get("cap_mode", "none")
            blp = L2.validate_layer_params(dict(dlp, cap_mode=FORCE[cur],
                                                eod_margin_min=int(dlp.get("eod_margin_min") or 15)))
            nlp = layer(tf, new[tf])

            rec["deployed"] = metrics(inst, tf, dlp)
            rec["bolt-on"] = rec["deployed"] if cur in ("eod", "both") else metrics(inst, tf, blp)
            rec["eod1"] = metrics(inst, tf, nlp)
            rec["cap_deployed"] = f"{cur}/{int(dlp.get('cap_1min') or 0)}"
            rec["cap_eod1"] = f"{nlp.get('cap_mode')}/{int(nlp.get('cap_1min') or 0)}"

            for name in ("deployed", "bolt-on", "eod1"):
                for w in ("full", "oos2026"):
                    d = rec[name][w]
                    if (d.get("n_taken") or 0) == 0 and abs(d.get("pnl") or 0) > 1:
                        raise ValueError(f"{name}/{w}: ${d['pnl']:,.0f} across 0 trades")

            D, B, N = rec["deployed"], rec["bolt-on"], rec["eod1"]
            print(f"[{i:2d}/54] {inst:3} {tf:3} | dep ${D['full']['pnl']:>9,.0f}/2026 ${D['oos2026']['pnl']:>8,.0f} "
                  f"| bolt ${B['full']['pnl']:>9,.0f}/${B['oos2026']['pnl']:>8,.0f} "
                  f"| eod1 ${N['full']['pnl']:>9,.0f}/${N['oos2026']['pnl']:>8,.0f}", flush=True)
        except Exception as e:
            rec["err"] = str(e)[:150]
            print(f"[{i:2d}/54] {inst:3} {tf:3}  ERROR {rec['err']}", flush=True)
        rows.append(rec)
        json.dump(rows, open(OUT, "w"), indent=1)
        el = time.time() - t0
        print(f"PROGRESS {i}/54  elapsed {el/60:.1f}m  ETA {(el/i)*(54-i)/60:.1f}m", flush=True)

print("MEASURE_DONE", flush=True)
