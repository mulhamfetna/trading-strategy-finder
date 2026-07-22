import sys
sys.path.insert(0, ".")
import numpy as np
from optimize import data, signals
from optimize.fast_engine import fast_backtest, signals_to_int
from optimize.fundamentals.champion_params import champion_stops
from perf._common import champion_preset

tf = "4h"
df, df1, box, vf, n = data.load_inputs(tf, instrument="NQ")
p = champion_preset(tf)
ss, sh, tp, flip = champion_stops(p, tf)
sig = signals_to_int(signals.decision_signals(df, box))
gate = vf <= float(np.percentile(vf[:n], float(p["gate_pct"])))
MD = df1["Date"].to_numpy(); MO = df1["Open"].to_numpy(float)
MH = df1["High"].to_numpy(float); ML = df1["Low"].to_numpy(float); MC = df1["Close"].to_numpy(float)
F = fast_backtest(df["Date"].to_numpy(), df["Close"].to_numpy(float), sig, gate,
                  MD, MH, ML, MC, ss, sh, tp, flip, m_open=MO, gap_fills=False)

print(f"champion {tf}: sl_hard={sh}")
shown = 0
for t in F:
    if t["exit_reason"] != "STOP_LOSS_HARD":
        continue
    k = int(np.searchsorted(MD, np.datetime64(t["exit_time"]), side="left"))
    exact = (k < len(MD)) and (MD[k] == np.datetime64(t["exit_time"]))
    o, line = float(MO[k]), float(t["exit_price"])
    d = t["direction"]
    gapped = (o < line) if d in ("long", 1) else (o > line)
    if not gapped:
        continue
    shown += 1
    if shown > 6:
        break
    print(f"\n--- gap #{shown}  dir={d} ---")
    print(f"  exit_time      {t['exit_time']}   bar timestamp match EXACT? {exact}")
    print(f"  entry_price    {t['entry_price']:.2f}")
    print(f"  stop LINE      {line:.2f}      <- what the backtest booked")
    print(f"  bar OPEN       {o:.2f}      <- realistic fill")
    print(f"  bar H/L/C      {MH[k]:.2f} / {ML[k]:.2f} / {MC[k]:.2f}")
    print(f"  PREV bar close {MC[k-1]:.2f}   (prev bar time {MD[k-1]})")
    print(f"  gap prev_close->open  {o - float(MC[k-1]):+.2f} pts")
    print(f"  slip vs line          {abs(line - o):.2f} pts  (= ${abs(line-o)*20:,.0f})")
    print(f"  booked pnl     {t['pnl_points']:+.2f} pts   realistic {(o - t['entry_price']) if d in ('long',1) else (t['entry_price'] - o):+.2f} pts")
