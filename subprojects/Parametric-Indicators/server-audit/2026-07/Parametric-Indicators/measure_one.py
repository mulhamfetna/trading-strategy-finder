"""Measure an instrument's champions on the DEPLOYED frame (ind_1min as instrument_l1_default sets it = True),
full + 2025/2026 split. Usage: measure_one.py <INST>"""
import sys
from optimize import data as D, instruments as I, timeframes as TF, signals as sig_mod
from optimize.core import backtest_metrics
from optimize.fast_engine import signals_to_int
from optimize.l2 import payload as l2p

inst = sys.argv[1]
pv = float(I.point_value(inst))
print(f"{'tf':4} {'full':>11} {'2025':>10} {'2026':>10} {'max_dd':>10} {'win':>4} {'tr':>5}  sl/tp/gate")
for tf in ["4h", "2h", "1h", "15m", "5m", "2m"]:
    dd, d1, box, vf, n = D.load_inputs(tf, inst)
    si = signals_to_int(sig_mod.decision_signals(dd, box))
    bt = TF.get(tf).bar_td
    lp = dict(l2p.instrument_l1_default(inst, tf)); lp["window"] = "full"   # ind_1min = deployed (True)
    m = backtest_metrics(dd, d1, box, vf, n, lp, bt, sig_int=si, pv=pv)
    f = lambda x: (f"${float(x):,.0f}" if x is not None else "-")
    w = str(round(float(m["win"]))) if m.get("win") is not None else "-"
    print(f"{tf:4} {f(m['pnl']):>11} {f(m.get('pnl_2025')):>10} {f(m.get('pnl_2026')):>10} "
          f"{f(m['max_dd']):>10} {w:>4} {str(m.get('n_taken')):>5}  {lp['sl_soft']:.1f}/{lp['tp']:.1f}/{lp.get('gate_pct',0):.0f}")
