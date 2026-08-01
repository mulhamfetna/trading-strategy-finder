"""Dump the FULL deeper-metric set per timeframe for an instrument's champions (deployed frame).
Usage: measure_deep.py <INST> <outfile.json>"""
import json, sys
from optimize import data as D, instruments as I, timeframes as TF, signals as sig_mod
from optimize.core import backtest_metrics
from optimize.fast_engine import signals_to_int
from optimize.l2 import payload as l2p

inst, out = sys.argv[1], sys.argv[2]
pv = float(I.point_value(inst))
res = {}
for tf in ["4h", "2h", "1h", "15m", "5m", "2m"]:
    try:
        dd, d1, box, vf, n = D.load_inputs(tf, inst)
        si = signals_to_int(sig_mod.decision_signals(dd, box)); bt = TF.get(tf).bar_td
        lp = dict(l2p.instrument_l1_default(inst, tf)); lp["window"] = "full"
        m = backtest_metrics(dd, d1, box, vf, n, lp, bt, sig_int=si, pv=pv)
        g = lambda k: m.get(k)
        res[tf] = {k: (float(g(k)) if isinstance(g(k), (int, float)) else g(k)) for k in
                   ("pnl", "pnl_2025", "pnl_2026", "max_dd", "win", "pf", "payoff", "exposure",
                    "avg_win", "avg_loss", "n_taken", "n_candidates", "n_skipped_breaker",
                    "noentry_streak_n", "noentry_streak_days") if k in m}
        res[tf]["sl_soft"] = lp.get("sl_soft"); res[tf]["tp"] = lp.get("tp"); res[tf]["gate_pct"] = lp.get("gate_pct")
        res[tf]["n_ind"] = sum(1 for i in lp.get("indicators", []) if isinstance(i, dict) and i.get("enabled"))
    except Exception as e:
        res[tf] = {"err": str(e)[:80]}
json.dump(res, open(out, "w"), default=str)
print(f"wrote {out}")
for tf, r in res.items():
    if "err" in r: print(f"  {tf}: ERR {r['err']}"); continue
    print(f"  {tf}: pnl ${r.get('pnl',0):,.0f} | 2026 ${r.get('pnl_2026',0):,.0f} | dd ${r.get('max_dd',0):,.0f} | "
          f"win {r.get('win')}% | pf {r.get('pf')} | payoff {r.get('payoff')} | exp {r.get('exposure')}% | tr {r.get('n_taken')}")
