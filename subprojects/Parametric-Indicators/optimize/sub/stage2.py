"""Stage 2 — try 3 dynamic-SL/TP rules and pick the best OUT-OF-SAMPLE vs the fixed champion.

A dynamic rule = a per-4h-bar multiplier `mult[bar]` applied to the champion's base SL/TP via the engine's
`sl_tp_mult` hook (so SL & TP scale together — the shape is the champion's, the magnitude is dynamic). All
rules are fit on TRAIN (2024-01 … 2025-06) and judged on TEST (2025-07 … 2026-05) against the fixed champion
on the same TEST window. A rule only "wins" if it beats fixed OOS.

Rules:
  1. ATR-multiple   — mult = a · ATR_bar / ATR_ref(train), global a fit on train (the recommended path).
  2. Robustified    — re-optimize SL/TP per train window with NARROW bounds + min-trades≥8 (stable optima),
                      fit magnitude-scale vs ATR, apply.
  3. Aggregate      — Stage-1 per-window optimal scale → rolling-median → linear fit vs ATR, apply.

Engine path = the exact `SimpleStrategy.backtest(sl_tp_mult=…)` + the global-HWM breaker (copied from
core.backtest_metrics). Parity-anchored: mult≡1 reproduces the fixed champion.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_HERE = Path(__file__).resolve().parent
_PI = _HERE.parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import optuna  # noqa: E402
optuna.logging.set_verbosity(optuna.logging.WARNING)

from engine import SimpleStrategy, SimpleStrategyParams  # noqa: E402
from indicators import classic  # noqa: E402
from optimize import timeframes as TF, core  # noqa: E402
from optimize.sub.data_2024_2026 import load_bundle  # noqa: E402
from optimize.sub.suboptimizer import champion, freeze_once  # noqa: E402

_BAR = TF.get("4h").bar_td
TRAIN_END = "2025-06"          # train ≤ this month; test = after
MULT_CLIP = (0.3, 3.0)


def _breaker(cand, dd_limit, cooldown, pv):
    """Global-HWM drawdown breaker overlay — identical math to core.backtest_metrics."""
    use_brk = dd_limit > 0
    peak = eq = 0.0; locked = False; cd = 0; taken = []
    for t in cand:
        pnl = float(t["pnl_points"]) * pv
        if use_brk and locked:
            cd -= 1
            if cd <= 0:
                locked = False
            else:
                continue
        eq += pnl; peak = max(peak, eq); taken.append({"pnl": pnl, "eq": eq})
        if use_brk and (peak - eq) >= dd_limit:
            locked = True; cd = cooldown
    if not taken:
        return {"pnl": 0.0, "max_dd": 0.0, "n": 0, "win": 0.0}
    p = np.array([t["pnl"] for t in taken]); e = np.array([t["eq"] for t in taken])
    return {"pnl": float(p.sum()), "max_dd": float((np.maximum.accumulate(e) - e).max()),
            "n": len(taken), "win": round(100 * (p > 0).mean(), 1)}


def eval_dynamic(df4, df1, box, gate_full, sig_obj, champ, mult_full, lo, hi):
    """Run the exact engine with per-bar `mult_full[lo:hi]` on the window [lo:hi); return breaker metrics.
    `sig_obj` is the OBJECT 'long'/'short'/'hold' array (engine.signals=), NOT the int fast-path array."""
    d = df4.iloc[lo:hi].reset_index(drop=True)
    t0 = d["Date"].iloc[0]; t1 = d["Date"].iloc[-1] + _BAR
    d1 = df1[(df1["Date"] >= t0) & (df1["Date"] < t1)].reset_index(drop=True)
    sp = SimpleStrategyParams(sl_soft_points=float(champ["sl_soft"]), sl_hard_points=float(champ["sl_hard"]),
                              tp_soft_points=float(champ["tp"]), tp_hard_points=float(champ["tp"]),
                              data_path_4h="", data_path_1min="", box_data_path="", flip_entry_direction=False)
    mult = None if mult_full is None else np.asarray(mult_full[lo:hi], dtype=float)
    trades, _ = SimpleStrategy(sp).backtest(d, d1, box, entry_gate=np.asarray(gate_full[lo:hi], bool),
                                            signals=sig_obj[lo:hi], sl_tp_mult=mult)
    cand = sorted([t for t in trades if t.get("exit_reason") not in (None, "OPEN")],
                  key=lambda t: pd.Timestamp(t["entry_time"]))
    return _breaker(cand, float(champ["dd_limit"]), int(champ["cooldown"]), float(champ["pv"]))


def main() -> int:
    champ = champion()
    print("loading bundle + freeze-once …", flush=True)
    df4, df1, box, vf, months = load_bundle()
    atr = classic.atr(df4["High"].to_numpy(float), df4["Low"].to_numpy(float), df4["Close"].to_numpy(float), 14)
    atr = np.nan_to_num(atr, nan=np.nanmean(atr))
    si_full, gate_full = freeze_once(df4, df1, box, vf, champ)
    from optimize import signals as sig_mod
    sig_obj = sig_mod.decision_signals(df4, box)        # OBJECT 'long'/'short'/'hold' for the engine
    N = len(df4)
    train = months <= TRAIN_END
    tr_hi = int(np.nonzero(train)[0][-1]) + 1            # train = [0:tr_hi); test = [tr_hi:N)
    atr_ref = float(atr[:tr_hi].mean())
    ones = np.ones(N)

    # ---- parity anchor: mult≡1 over the full series == fixed champion (core path) ----
    fix_full = eval_dynamic(df4, df1, box, gate_full, sig_obj, champ, ones, 0, N)
    can = core.backtest_metrics(df4, df1, box, vf, N,
                                dict(sl_soft=champ["sl_soft"], sl_hard=champ["sl_hard"], tp=champ["tp"],
                                     gate_pct=0.0, dd_limit=champ["dd_limit"], cooldown=champ["cooldown"],
                                     flip=False, window="full"), _BAR, gate_used=gate_full, sig_int=si_full,
                                pv=champ["pv"])
    par = (round(fix_full["pnl"]) == round(can["pnl"]) and fix_full["n"] == can["n_taken"])
    print(f"parity (mult=1 == fixed champion): {'OK' if par else 'MISMATCH'} "
          f"[dyn {fix_full['pnl']:.0f}/{fix_full['n']} vs core {can['pnl']:.0f}/{can['n_taken']}]")

    def test_metrics(mult):
        return eval_dynamic(df4, df1, box, gate_full, sig_obj, champ, mult, tr_hi, N)

    # ---- baseline: fixed champion on TEST ----
    fixed = test_metrics(ones)

    # ---- Rule 1: ATR-multiple (fit global a on train) ----
    base = atr / atr_ref
    best_a, best_trpnl = 1.0, -1e18
    for a in np.linspace(0.5, 1.8, 14):
        m = np.clip(a * base, *MULT_CLIP)
        tr = eval_dynamic(df4, df1, box, gate_full, sig_obj, champ, m, 0, tr_hi)
        if tr["pnl"] > best_trpnl:
            best_trpnl, best_a = tr["pnl"], a
    r1 = test_metrics(np.clip(best_a * base, *MULT_CLIP))
    r1["note"] = f"a={best_a:.2f}, ATR_ref={atr_ref:.0f}"

    # ---- Rule 3: aggregate Stage-1 optima → rolling-median → linear scale(ATR) ----
    tbl = pd.read_csv(_HERE / "results" / "subopt_table.csv")
    tbl["scale"] = 0.5 * (tbl.best_sl_soft / champ["sl_soft"] + tbl.best_tp / champ["tp"])
    tr_tbl = tbl[tbl.anchor <= TRAIN_END].copy()
    tr_tbl["scale_s"] = tr_tbl["scale"].rolling(3, min_periods=1, center=True).median()
    A = np.polyfit(tr_tbl.atr_mean, tr_tbl.scale_s, 1) if len(tr_tbl) >= 2 else [0.0, 1.0]
    scale_hat = np.clip(A[0] * atr + A[1], *MULT_CLIP)
    r3 = test_metrics(scale_hat)
    r3["note"] = f"scale≈{A[0]:+.2e}·ATR{A[1]:+.2f}"

    # ---- Rule 2: robustified per-window scale (grid over a single scalar s, min-trades≥8) → fit scale(ATR) ----
    from optimize.sub.windows import rolling_windows
    S_GRID = np.linspace(0.4, 2.0, 9)                          # NARROW magnitude scale (robust, not extreme)
    rob_pts = []
    for w in [w for w in rolling_windows(months, 3, 1) if w["anchor"] <= TRAIN_END]:
        lo, hi = w["idx_lo"], w["idx_hi"] + 1
        best_s, best_pnl = None, -1e18
        for s in S_GRID:
            mm = eval_dynamic(df4, df1, box, gate_full, sig_obj, champ, _full_at(N, lo, hi, s), lo, hi)
            if mm["n"] >= 8 and mm["pnl"] > best_pnl:
                best_pnl, best_s = mm["pnl"], s
        if best_s is not None:
            rob_pts.append((float(atr[lo:hi].mean()), float(best_s)))
    if len(rob_pts) >= 2:
        xa = np.array([p[0] for p in rob_pts]); ya = np.array([p[1] for p in rob_pts])
        B = np.polyfit(xa, ya, 1); scale2 = np.clip(B[0] * atr + B[1], *MULT_CLIP)
        r2 = test_metrics(scale2); r2["note"] = f"{len(rob_pts)} robust pts, scale≈{B[0]:+.2e}·ATR{B[1]:+.2f}"
    else:
        r2 = dict(fixed); r2["note"] = "insufficient robust points"

    # ---- verdict ----
    print(f"\nTEST window = months > {TRAIN_END}  (fixed champion baseline below)")
    rows = [("fixed", fixed), ("opt1_ATR", r1), ("opt2_robust", r2), ("opt3_aggregate", r3)]
    print(f"{'rule':16s} {'pnl':>10s} {'maxDD':>9s} {'n':>4s} {'win%':>5s} {'DD/PL%':>7s} {'ret/DD':>7s}  vs_fix  note")
    for name, m in rows:
        ddpl = 100 * m["max_dd"] / m["pnl"] if m["pnl"] > 0 else float("inf")
        rdd = m["pnl"] / m["max_dd"] if m["max_dd"] > 0 else float("inf")
        m["ddpl"], m["rdd"] = ddpl, rdd
        print(f"{name:16s} {m['pnl']:>10.0f} {m['max_dd']:>9.0f} {m['n']:>4d} {m['win']:>5.1f} "
              f"{ddpl:>7.1f} {rdd:>7.2f}  {m['pnl']-fixed['pnl']:>+8.0f}  {m.get('note','')}")
    # Risk-aware verdict: this is the DRAWDOWN-CAPPED strategy → require DD/PL ≤ 25% (its design discipline),
    # then rank survivors by P/L. A higher-P/L rule that breaches the DD budget is NOT a clean win.
    DD_BUDGET = 25.0
    cand = [(n, m) for n, m in rows if n != "fixed"]
    feasible = [(n, m) for n, m in cand if m["ddpl"] <= DD_BUDGET]
    by_pnl = max(cand, key=lambda x: x[1]["pnl"])
    by_rdd = max(cand, key=lambda x: x[1]["rdd"])
    print(f"\nhighest raw P/L: {by_pnl[0]} (${by_pnl[1]['pnl']:.0f}, DD/PL {by_pnl[1]['ddpl']:.0f}%"
          f"{' — BREACHES 25% DD budget' if by_pnl[1]['ddpl']>DD_BUDGET else ''})")
    print(f"best risk-adjusted (ret/DD): {by_rdd[0]} (ret/DD {by_rdd[1]['rdd']:.2f}, "
          f"P/L ${by_rdd[1]['pnl']:.0f}, DD/PL {by_rdd[1]['ddpl']:.0f}%)")
    if feasible:
        best = max(feasible, key=lambda x: x[1]["pnl"])
        beats = best[1]["pnl"] > fixed["pnl"]
        print(f"VERDICT: within the 25% DD budget, best dynamic = {best[0]} "
              f"(${best[1]['pnl']:.0f} vs fixed ${fixed['pnl']:.0f}) → "
              f"{'BEATS fixed ✓' if beats else 'does NOT beat fixed on P/L (but check DD)'}")
    else:
        print("VERDICT: NO dynamic rule stays within the 25% DD budget — keep fixed.")
    return 0


def _full_at(N, lo, hi, m):
    a = np.ones(N); a[lo:hi] = m; return a


if __name__ == "__main__":
    raise SystemExit(main())
