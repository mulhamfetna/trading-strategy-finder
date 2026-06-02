"""Workstream G (cont.) — maximise P/L subject to a HARD max-drawdown cap.

Target: largest total P/L with maxDD <= min($5,000, 10% of total P/L).

Tools (all single-contract, on the verified clone; NO engine edit — the drawdown breaker is a
causal post-processing overlay on the chronological trade stream):
  1. base SL/TP params (optionally a tighter hard SL to cap per-trade loss),
  2. volatility GATE (skip the most-volatile bars; entry_gate lever),
  3. adaptive SL/TP multiplier (sl_tp_mult lever),
  4. DRAWDOWN CIRCUIT-BREAKER overlay: after running drawdown from the equity peak breaches
     `dd_limit`, stop taking NEW trades for `cooldown` trades, then re-probe (peak resets to the
     resume equity). Decision for trade i uses only trades < i -> causal, no look-ahead.

We grid engine-configs x breaker-settings, then report the best FEASIBLE config (maxDD within the
cap) by total P/L, plus the frontier.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path("/mnt/data/projects/trading")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJ)); sys.path.insert(0, str(ROOT))

import importlib.util
spec = importlib.util.spec_from_file_location("bm", ROOT / "scripts" / "17_backtest_matrix.py")
bm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bm)

NQ_PV = 20.0
DD_CAP_ABS = 5000.0
DD_CAP_FRAC = 0.10


def run_engine(df4, df1, box, sl_soft, sl_hard, tp, gate=None, mult=None):
    p = bm.SimpleStrategyParams(sl_soft_points=sl_soft, sl_hard_points=sl_hard,
                                tp_soft_points=tp, tp_hard_points=tp, data_path_4h="",
                                data_path_1min="", box_data_path="", flip_entry_direction=False)
    trades, _ = bm.SimpleStrategy(p).backtest(df4, df1, box, sl_tp_mult=mult, entry_gate=gate)
    closed = [t for t in trades if t.get("exit_reason") not in (None, "OPEN")]
    closed.sort(key=lambda t: pd.Timestamp(t["entry_time"]))
    pnl_d = np.array([float(t["pnl_points"]) * NQ_PV for t in closed])
    yr = np.array([pd.Timestamp(t["exit_time"]).year for t in closed])
    return pnl_d, yr


def breaker(pnl_d, yr, dd_limit, cooldown):
    """Causal drawdown circuit-breaker. Returns (kept_mask)."""
    peak = eq = 0.0
    locked = False; cd = 0
    keep = np.zeros(len(pnl_d), dtype=bool)
    for i, x in enumerate(pnl_d):
        if locked:
            cd -= 1
            if cd <= 0:
                locked = False; peak = eq      # resume: measure drawdown fresh from here
            else:
                continue                        # skip this trade (locked out)
        eq += x; keep[i] = True
        peak = max(peak, eq)
        if peak - eq >= dd_limit:
            locked = True; cd = cooldown
    return keep


def metrics(pnl_d, yr, keep=None):
    if keep is not None:
        pnl_d = pnl_d[keep]; yr = yr[keep]
    if len(pnl_d) == 0:
        return dict(pnl=0.0, p25=0.0, p26=0.0, n=0, win=0.0, dd=0.0)
    eq = np.cumsum(pnl_d); dd = float((np.maximum.accumulate(eq) - eq).max())
    return dict(pnl=float(pnl_d.sum()), p25=float(pnl_d[yr == 2025].sum()),
                p26=float(pnl_d[yr == 2026].sum()), n=int(len(pnl_d)),
                win=float((pnl_d > 0).mean() * 100), dd=dd)


def feasible(m):
    cap = min(DD_CAP_ABS, DD_CAP_FRAC * m["pnl"]) if m["pnl"] > 0 else DD_CAP_ABS
    strict = m["pnl"] > 0 and m["dd"] <= cap          # maxDD <= min($5k, 10%PL)
    abs_ok = m["pnl"] > 0 and m["dd"] <= DD_CAP_ABS    # maxDD <= $5k absolute
    return strict, abs_ok, cap


def main():
    df4, df1, box = bm.load_all()
    n2025 = int((df4["_year"] == 2025).sum())
    vf = bm.har_rv_forecast(df4)

    def gate_at(pct):
        return None if pct is None else (vf <= np.percentile(vf[:n2025], pct))
    S = bm.lever_sl_tp(vf, mode="expanding")

    # engine configs: (label, sl_soft, sl_hard, tp, gate_pct, use_mult)
    engine_cfgs = [
        ("base",          80, 100, 50, None, False),
        ("G80",           80, 100, 50, 80,   False),
        ("G60",           80, 100, 50, 60,   False),
        ("G50",           80, 100, 50, 50,   False),
        ("S+G80",         80, 100, 50, 80,   True),
        ("S+G60",         80, 100, 50, 60,   True),
        ("tSL_G80",       40,  50, 50, 80,   False),  # hard SL 50 (= $1000/loss)
        ("tSL_G60",       40,  50, 50, 60,   False),
        ("tSL_G50",       40,  50, 50, 50,   False),
        ("vSL_G80",       20,  25, 40, 80,   False),  # very tight: hard SL 25 (= $500/loss)
        ("vSL_G60",       20,  25, 40, 60,   False),
        ("vSL_G50",       20,  25, 40, 50,   False),
    ]
    breakers = [("none", None, None)] + [
        (f"L{int(L)}_cd{K}", L, K)
        for L in (1500, 2000, 2500, 3000) for K in (10, 15, 20, 30)
    ]

    rows = []
    cache = {}
    for (label, ss, sh, tp, gp, um) in engine_cfgs:
        key = (ss, sh, tp, gp, um)
        if key not in cache:
            cache[key] = run_engine(df4, df1, box, ss, sh, tp,
                                    gate=gate_at(gp), mult=(S if um else None))
        pnl_d, yr = cache[key]
        for (blab, L, K) in breakers:
            keep = None if L is None else breaker(pnl_d, yr, L, K)
            m = metrics(pnl_d, yr, keep)
            strict, abs_ok, cap = feasible(m)
            m.update(cfg=label, brk=blab, feasible=strict, abs5k=abs_ok, dd_cap=cap,
                     dd_pct=(m["dd"] / m["pnl"] * 100 if m["pnl"] > 0 else float("inf")))
            rows.append(m)

    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "outputs" / "wsg_drawdown_optimize.csv", index=False)
    cols = ["cfg", "brk", "pnl", "p25", "p26", "n", "win", "dd", "dd_pct", "dd_cap", "feasible"]

    pd.set_option("display.width", 160)
    print(f"TARGET: maximise P/L with maxDD <= min(${DD_CAP_ABS:,.0f}, {DD_CAP_FRAC:.0%} of P/L)\n")
    strict = df[df.feasible].sort_values("pnl", ascending=False)
    print(f"=== STRICT feasible (maxDD <= min($5k, 10% PL)): {len(strict)} of {len(df)} ===")
    print(strict[cols].head(10).to_string(index=False, float_format=lambda v: f"{v:,.1f}")
          if len(strict) else "  (NONE — the 10%-of-P/L rule needs PL>=$50k; not reachable on this n=1 data)")
    feas5 = df[df.abs5k].sort_values("pnl", ascending=False)
    print(f"\n=== FEASIBLE under $5k ABSOLUTE cap: {len(feas5)} of {len(df)}, best P/L first ===")
    print(feas5[cols].head(12).to_string(index=False, float_format=lambda v: f"{v:,.1f}")
          if len(feas5) else "  (none)")
    print("\n=== Highest P/L overall (regardless of cap) ===")
    print(df.sort_values("pnl", ascending=False)[cols].head(6).to_string(index=False, float_format=lambda v: f"{v:,.1f}"))


if __name__ == "__main__":
    main()
