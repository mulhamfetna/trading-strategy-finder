"""Stage-0bis — FIXED (non-overlapping) quarterly SL/TP sub-optimizer + DISTRIBUTION capture.

Motivation (user): the prior study used ROLLING 3-month windows (overlapping). Re-run on FIXED quarters
(Q1–Q4 2024, Q1–Q4 2025, Q1 2026 = 9 independent windows) AND — crucially — capture not just the single
BEST sl/tp per window (a noisy argmax) but the **distribution of GOOD sl/tp** (all trials within a P/L
tolerance of the best) → a center ± error-margin ("probability distribution of the best sl/tp").

Outputs:
  results/fixed_window_subopt.csv  — one row/window: price/vol features + best sl/tp + near-best BAND stats.
  results/fixed_window_trials.csv  — every COMPLETE trial (window, sl_soft, sl_hard, tp, pnl, n, dd, win)
                                     for downstream relationship fitting (relation_fit.py).

Reuses the frozen champion layer + per-window evaluator from suboptimizer.py (byte-consistent). CPU only.
Run:  python3 optimize/sub/fixed_window_subopt.py --trials 400 [--rolling]
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
import numpy as np
import pandas as pd
import optuna

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
optuna.logging.set_verbosity(optuna.logging.WARNING)

from indicators import classic                                              # noqa: E402
from optimize.sub.data_2024_2026 import load_bundle                          # noqa: E402
from optimize.sub import suboptimizer as S                                   # noqa: E402
from optimize.sub.windows import month_bounds, rolling_windows               # noqa: E402

HERE = Path(__file__).resolve().parent
BAND_TOL = 0.85   # "good" trial = pnl ≥ BAND_TOL · best_pnl (best_pnl>0); defines the near-best band


def quarter_windows(months: np.ndarray) -> list[dict]:
    """FIXED, non-overlapping COMPLETE 3-month calendar quarters."""
    uniq, bounds = month_bounds(months)
    groups: dict[tuple, list[str]] = {}
    for m in uniq:
        y, mo = m.split("-"); q = (int(mo) - 1) // 3 + 1
        groups.setdefault((int(y), q), []).append(m)
    out = []
    for (y, q), wm in groups.items():
        if len(wm) != 3:                 # keep only complete quarters (drops partial 2026-Q2)
            continue
        out.append({"anchor": f"{y}Q{q}", "start_month": wm[0], "end_month": wm[-1], "months": wm,
                    "idx_lo": bounds[wm[0]][0], "idx_hi": bounds[wm[-1]][1],
                    "n_bars": bounds[wm[-1]][1] - bounds[wm[0]][0] + 1})
    return out


def band_stats(trials, best_pnl):
    """Distribution of sl/tp over near-best trials (pnl ≥ tol·best). center ± spread = the error margin."""
    good = [t for t in trials if t.value is not None and best_pnl > 0 and t.value >= BAND_TOL * best_pnl]
    if len(good) < 3:
        good = [t for t in trials if t.value is not None]      # fallback: all complete trials
    ss = np.array([t.params["sl_soft"] for t in good], float)
    sh = np.array([t.user_attrs["sl_hard"] for t in good], float)
    tp = np.array([t.params["tp"] for t in good], float)
    def q(a, p): return float(np.percentile(a, p))
    return {"band_n": len(good),
            "sl_soft_mean": round(ss.mean(), 2), "sl_soft_std": round(ss.std(ddof=1) if len(ss) > 1 else 0, 2),
            "sl_soft_p10": round(q(ss, 10), 2), "sl_soft_p90": round(q(ss, 90), 2),
            "sl_hard_mean": round(sh.mean(), 2), "sl_hard_std": round(sh.std(ddof=1) if len(sh) > 1 else 0, 2),
            "tp_mean": round(tp.mean(), 2), "tp_std": round(tp.std(ddof=1) if len(tp) > 1 else 0, 2),
            "tp_p10": round(q(tp, 10), 2), "tp_p90": round(q(tp, 90), 2)}


def run_window(w, df4, df1, box, vf, atr, si_full, gate_full, champ, n_trials):
    lo, hi = w["idx_lo"], w["idx_hi"] + 1
    d_win = df4.iloc[lo:hi].reset_index(drop=True)
    vf_win, gate_win, si_win = vf[lo:hi], gate_full[lo:hi], si_full[lo:hi]
    B = S._bounds()

    def objective(trial):
        sl_soft = trial.suggest_float("sl_soft", *B["sl_soft"])
        dhi = (S.SL_MAX - sl_soft) if S.SL_MAX is not None else B["sl_hard_delta"][1]
        delta = trial.suggest_float("sl_hard_delta", 0.0, max(0.0, dhi))
        tp = trial.suggest_float("tp", *B["tp"])
        m = S._eval(d_win, df1, box, vf_win, gate_win, si_win, champ, sl_soft, sl_soft + delta, tp)
        if m["n_taken"] < S.MIN_TRADES:
            raise optuna.TrialPruned()
        trial.set_user_attr("n", m["n_taken"]); trial.set_user_attr("dd", m["max_dd"])
        trial.set_user_attr("win", m["win"]); trial.set_user_attr("sl_hard", sl_soft + delta)
        return float(m["pnl"])

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    done = [t for t in study.trials if t.value is not None]
    close = d_win["Close"].to_numpy(float)
    pmean = float(close.mean())
    if not done:
        return {"anchor": w["anchor"], "n_trades": 0, "note": "no feasible trial"}, []
    bt = study.best_trial
    ss, sh, tp = bt.params["sl_soft"], bt.user_attrs["sl_hard"], bt.params["tp"]
    atrw = atr[lo:hi]; atrm = float(atrw[~np.isnan(atrw)].mean())
    row = {"anchor": w["anchor"], "win_start": w["start_month"], "win_end": w["end_month"],
           "price_start": round(float(close[0]), 2), "price_end": round(float(close[-1]), 2),
           "price_mean": round(pmean, 2),
           "price_change_pct": round(100 * (close[-1] / close[0] - 1), 3),
           "range_pct": round(100 * (float(d_win["High"].max()) - float(d_win["Low"].min())) / pmean, 3),
           "atr_mean": round(atrm, 2), "harv_mean": round(float(vf_win.mean()), 4),
           "best_sl_soft": round(ss, 2), "best_sl_hard": round(sh, 2), "best_tp": round(tp, 2),
           "n_trades": int(bt.user_attrs["n"]), "pnl": round(float(bt.value), 2),
           "max_dd": round(float(bt.user_attrs["dd"]), 2), "win_rate": round(float(bt.user_attrs["win"]), 1),
           "n_complete_trials": len(done), **band_stats(done, float(bt.value))}
    trials = [{"anchor": w["anchor"], "sl_soft": round(t.params["sl_soft"], 2),
               "sl_hard": round(t.user_attrs["sl_hard"], 2), "tp": round(t.params["tp"], 2),
               "pnl": round(float(t.value), 2), "n": int(t.user_attrs["n"]),
               "dd": round(float(t.user_attrs["dd"]), 2), "win": round(float(t.user_attrs["win"]), 1)}
              for t in done]
    return row, trials


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=400)
    ap.add_argument("--rolling", action="store_true", help="also run the rolling windows (band capture)")
    ap.add_argument("--tag", default="fixed_window")
    a = ap.parse_args()

    champ = S.champion()
    print("loading 29-month bundle + freezing champion layer once…", flush=True)
    df4, df1, box, vf, months = load_bundle()
    atr = classic.atr(df4["High"].to_numpy(float), df4["Low"].to_numpy(float), df4["Close"].to_numpy(float), 14)
    si_full, gate_full = S.freeze_once(df4, df1, box, vf, champ)

    wins = rolling_windows(months, 3, 1) if a.rolling else quarter_windows(months)
    print(f"{'ROLLING' if a.rolling else 'FIXED-QUARTER'} windows: {len(wins)} · {a.trials} trials each\n", flush=True)
    rows, all_trials = [], []
    for w in wins:
        r, tr = run_window(w, df4, df1, box, vf, atr, si_full, gate_full, champ, a.trials)
        rows.append(r); all_trials.extend(tr)
        print(f"  [{r['anchor']}] best sl {r.get('best_sl_soft','-')}/{r.get('best_sl_hard','-')} "
              f"tp {r.get('best_tp','-')} | band sl_soft {r.get('sl_soft_mean','-')}±{r.get('sl_soft_std','-')} "
              f"tp {r.get('tp_mean','-')}±{r.get('tp_std','-')} | n={r.get('n_trades')} pnl={r.get('pnl')}", flush=True)

    (HERE / "results").mkdir(exist_ok=True)
    out = HERE / "results" / f"{a.tag}_subopt.csv"; tout = HERE / "results" / f"{a.tag}_trials.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    pd.DataFrame(all_trials).to_csv(tout, index=False)
    print(f"\nwrote {out} ({len(rows)} windows) + {tout} ({len(all_trials)} trials)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
