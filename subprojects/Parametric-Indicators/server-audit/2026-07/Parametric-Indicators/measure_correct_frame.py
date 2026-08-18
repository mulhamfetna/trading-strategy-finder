"""Measure every champion on its CORRECT frame (ind_1min=False, how it was optimized): full P/L, 2025 vs 2026
split, drawdown, win, trades. This is the verification that should have gated deployment."""
import json
from optimize import data as D, instruments as I, timeframes as TF, signals as sig_mod
from optimize.core import backtest_metrics
from optimize.fast_engine import signals_to_int
from optimize.l2 import payload as l2p

TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
rows = []
for inst in ("GC", "SI", "ES"):
    pv = float(I.point_value(inst))
    for tf in TFS:
        try:
            df_dec, df1, box, vf, n = D.load_inputs(tf, inst)
            si = signals_to_int(sig_mod.decision_signals(df_dec, box))
            bt = TF.get(tf).bar_td
            lp = dict(l2p.instrument_l1_default(inst, tf)); lp["window"] = "full"; lp["ind_1min"] = False
            m = backtest_metrics(df_dec, df1, box, vf, n, lp, bt, sig_int=si, pv=pv)
            rows.append(dict(inst=inst, tf=tf, pnl=m.get("pnl"), p25=m.get("pnl_2025"),
                             p26=m.get("pnl_2026"), dd=m.get("max_dd"), win=m.get("win"),
                             n=m.get("n_taken"), sl=lp.get("sl_soft"), tp=lp.get("tp")))
        except Exception as e:
            rows.append(dict(inst=inst, tf=tf, err=str(e)[:60]))
json.dump(rows, open("/tmp/correct_frame.json", "w"), default=str)
print(f"{'inst':4} {'tf':4} {'full_pnl':>11} {'2025':>10} {'2026':>10} {'max_dd':>10} {'win':>5} {'trades':>6}")
for r in rows:
    if r.get("err"): print(f"{r['inst']:4} {r['tf']:4}  ERR {r['err']}"); continue
    f = lambda x: f"${float(x):,.0f}" if x is not None else "-"
    print(f"{r['inst']:4} {r['tf']:4} {f(r['pnl']):>11} {f(r['p25']):>10} {f(r['p26']):>10} {f(r['dd']):>10} "
          f"{(f'{float(r['win']):.0f}%' if r.get('win') is not None else '-'):>5} {str(r.get('n')):>6}")
