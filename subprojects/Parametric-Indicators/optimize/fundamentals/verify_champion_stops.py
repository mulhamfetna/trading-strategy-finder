import sys
sys.path.insert(0, ".")
import numpy as np
from optimize import data, signals
from optimize.fast_engine import fast_backtest, signals_to_int
from perf._common import champion_preset

for tf in ("4h", "1h"):
    df, df1, box, vf, n = data.load_inputs(tf, instrument="NQ")
    p = champion_preset(tf)
    s = signals_to_int(signals.decision_signals(df, box))
    gate = vf <= float(np.percentile(vf[:n], float(p.get("gate_pct", 60))))
    MD = df1["Date"].to_numpy()
    HI = df1["High"].to_numpy(float); LO = df1["Low"].to_numpy(float); MC = df1["Close"].to_numpy(float)
    DD = df["Date"].to_numpy(); DC = df["Close"].to_numpy(float)

    def run(ss, sh, tp, flip, label):
        F = fast_backtest(DD, DC, s, gate, MD, HI, LO, MC, ss, sh, tp, flip, m_open=MO, gap_fills=False)
        pnl = np.array([float(t["pnl_points"]) for t in F])
        return F, pnl, label

    # (A) what the studies ACTUALLY ran: the silent defaults
    A = run(float(p.get("sl_soft_points", 30)), 40.0, float(p.get("tp_hard_points", 60)),
            bool(p.get("flip_entry_direction", False)), "STUDIES RAN (silent defaults 30/40/60)")
    # (B) the real champion parameters, under their true key names
    B = run(float(p["sl_soft"]), float(p["sl_hard"]), float(p["tp"]), bool(p.get("flip", False)),
            "REAL CHAMPION (%.1f/%.1f/%.1f)" % (p["sl_soft"], p["sl_hard"], p["tp"]))

    print("=" * 78)
    print(f"NQ {tf}")
    print("=" * 78)
    for F, pnl, label in (A, B):
        if len(pnl) == 0:
            print(f"  {label:52} no trades"); continue
        print(f"  {label:52}")
        print(f"      trades={len(pnl):5d}  mean={pnl.mean():+8.2f} pts  total={pnl.sum():+10.1f} pts")
        print(f"      min={pnl.min():+8.2f}  max={pnl.max():+8.2f}  win={100*np.mean(pnl>0):5.1f}%")
    print()
