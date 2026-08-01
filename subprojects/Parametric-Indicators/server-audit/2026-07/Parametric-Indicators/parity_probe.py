"""Feed the SAME champion params to the optimizer's fast engine (backtest_metrics) and the dashboard
(build_view_payload) for GC 4h. Localizes: same params -> which engine diverges + where (candidates vs exits)."""
import json
from optimize import data as D
from optimize import instruments as I
from optimize.core import backtest_metrics
from optimize import signals as sig_mod
from optimize.fast_engine import signals_to_int
from optimize import timeframes as TF
from optimize.l2 import payload as l2p

inst, tf = "GC", "4h"
df_dec, df1, box, vf, n_split = D.load_inputs(tf, inst)
pv = float(I.point_value(inst))
sig_int = signals_to_int(sig_mod.decision_signals(df_dec, box))
bar_td = TF.get(tf).bar_td

# shared param source = exactly what the dashboard serves (instrument_l1_default = champion JSON)
lp = dict(l2p.instrument_l1_default(inst, tf))
params = dict(lp); params["window"] = "full"

fast = backtest_metrics(df_dec, df1, box, vf, n_split, params, bar_td, sig_int=sig_int, pv=pv)
print(f"FAST  backtest_metrics : pnl ${fast['pnl']:>11,.0f} | max_dd ${fast['max_dd']:>10,.0f} | "
      f"n_taken {fast.get('n_taken')} | n_cand {fast.get('n_candidates')}")

body = dict(lp); body["timeframe"] = tf; body["instrument"] = inst
l1lay = l2p._layer_from_strategy(body)
out = l2p.build_view_payload(l1lay, {}, tf, "l1", instrument=inst, l1_engine=body)
s = out["meta"]["summary"]
print(f"DASH  build_view_payload: pnl ${s['pnl']:>11,.0f} | max_dd ${s['max_dd']:>10,.0f} | "
      f"n_taken {s.get('n_taken')} | n_cand {s.get('n_candidates')}")
print(f"optimizer recorded (pareto): full_pnl $97,889 | full_dd $7,360")
print(f"\nparams: sl_soft={params['sl_soft']} sl_hard={params['sl_hard']} tp={params['tp']} "
      f"gate_pct={params['gate_pct']} dd_limit={params['dd_limit']} k={params['k']} "
      f"cap_1min={params.get('cap_1min')} cap_mode={params.get('cap_mode')} ind_1min={params.get('ind_1min')} "
      f"n_ind_enabled={sum(1 for i in params.get('indicators',[]) if isinstance(i,dict) and i.get('enabled'))}")
