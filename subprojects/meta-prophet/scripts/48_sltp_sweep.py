"""WS-G — fine SL/TP sweep to find a better drawdown-capped winner.

Grid the stop/target distances (with the vol gate + drawdown breaker) and report the best
config with maxDD <= $5,000, maximising P/L. Single-contract cloned engine; breaker is the
causal overlay from script 46. Goal: beat vSL_G60+breaker (+$20,345 P/L, $3,695 maxDD).
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

PROJ = Path("/mnt/data/projects/trading"); ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ)); sys.path.insert(0, str(ROOT))
import importlib.util
spec = importlib.util.spec_from_file_location("bm", ROOT / "scripts" / "17_backtest_matrix.py")
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)

NQ_PV = 20.0; DD_CAP = 5000.0


def run_engine(df4, df1, box, ss, sh, tp, gate):
    p = bm.SimpleStrategyParams(sl_soft_points=ss, sl_hard_points=sh, tp_soft_points=tp,
                                tp_hard_points=tp, data_path_4h="", data_path_1min="",
                                box_data_path="", flip_entry_direction=False)
    tr, _ = bm.SimpleStrategy(p).backtest(df4, df1, box, entry_gate=gate)
    cl = [t for t in tr if t.get("exit_reason") not in (None, "OPEN")]
    cl.sort(key=lambda t: pd.Timestamp(t["entry_time"]))
    pnl = np.array([float(t["pnl_points"]) * NQ_PV for t in cl])
    yr = np.array([pd.Timestamp(t["exit_time"]).year for t in cl])
    return pnl, yr


def breaker(pnl, L, K):
    peak = eq = 0.0; locked = False; cd = 0; keep = np.zeros(len(pnl), bool)
    for i, x in enumerate(pnl):
        if locked:
            cd -= 1
            if cd <= 0: locked = False; peak = eq
            else: continue
        eq += x; keep[i] = True; peak = max(peak, eq)
        if peak - eq >= L: locked = True; cd = K
    return keep


def metr(pnl, yr, keep):
    p = pnl[keep]; y = yr[keep]
    if not len(p): return None
    eq = np.cumsum(p); dd = float((np.maximum.accumulate(eq) - eq).max())
    return dict(pnl=float(p.sum()), p25=float(p[y == 2025].sum()), p26=float(p[y == 2026].sum()),
                n=int(len(p)), win=float((p > 0).mean() * 100), dd=dd)


def main():
    df4, df1, box = bm.load_all()
    n2025 = int((df4["_year"] == 2025).sum()); vf = bm.har_rv_forecast(df4)
    gates = {g: (vf <= np.percentile(vf[:n2025], g)) for g in (60, 70)}

    SL_HARD = [20, 25, 30, 40]
    TP = [30, 40, 50, 60]
    SOFT_OFF = [5, 10]                      # sl_soft = sl_hard - off
    BRK = [(2000, 15), (2000, 20), (2500, 15), (2500, 20), (2500, 30), (3000, 20)]

    rows = []
    for g, garr in gates.items():
        for sh in SL_HARD:
            for off in SOFT_OFF:
                ss = max(5, sh - off)
                for tp in TP:
                    pnl, yr = run_engine(df4, df1, box, ss, sh, tp, garr)
                    for (L, K) in BRK:
                        m = metr(pnl, yr, breaker(pnl, L, K))
                        if m is None: continue
                        m.update(g=g, ss=ss, sh=sh, tp=tp, L=L, K=K,
                                 feasible=(m["pnl"] > 0 and m["dd"] <= DD_CAP),
                                 ddpct=(m["dd"] / m["pnl"] * 100 if m["pnl"] > 0 else 9e9))
                        rows.append(m)

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "outputs" / "sltp_sweep.csv", index=False)
    cols = ["g", "ss", "sh", "tp", "L", "K", "pnl", "p25", "p26", "n", "win", "dd", "ddpct", "feasible"]
    feas = df[df.feasible].sort_values("pnl", ascending=False)
    pd.set_option("display.width", 170)
    print(f"swept {len(df)} configs ({df[['g','ss','sh','tp']].drop_duplicates().shape[0]} engine runs)")
    print(f"\n=== BEST under $5k maxDD cap (top 15 by P/L) ===")
    print(feas[cols].head(15).to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    print(f"\n=== prior winner for reference (sh25/tp40/g60/L2500/K20) ===")
    ref = df[(df.sh == 25) & (df.tp == 40) & (df.g == 60) & (df.L == 2500) & (df.K == 20)]
    print(ref[cols].to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    print(f"\n=== best DD%-of-P/L among feasible with P/L>=15k ===")
    big = feas[feas.pnl >= 15000].sort_values("ddpct")
    print(big[cols].head(8).to_string(index=False, float_format=lambda v: f"{v:,.1f}"))


if __name__ == "__main__":
    main()
