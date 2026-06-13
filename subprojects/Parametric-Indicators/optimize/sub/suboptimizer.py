"""Stage 1 · S1.2 + S1.4 — SL/TP sub-optimizer over rolling 3-month windows.

Freezes the `wsi1m_4h` champion (everything except SL/TP), computes its signal + gate layer ONCE over the
full 29-month series (correct warm-up), then for each rolling 3-month window runs an Optuna study over
ONLY (sl_soft, sl_hard, tp) with WIDENED bounds. Each trial reuses the parity-locked
`core.backtest_metrics` via its `gate_used=` bypass → just the vectorized engine + drawdown breaker on the
window slice (milliseconds). Emits one results row per window.

Run:  python3 optimize/sub/suboptimizer.py --smoke            # 1 window, few trials (sanity)
      python3 optimize/sub/suboptimizer.py --trials 400        # all 27 windows → results/subopt_table.csv
"""
from __future__ import annotations

import json
import os
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

import presets  # noqa: E402
from optimize import core, timeframes as TF, signals as sig_mod  # noqa: E402
from optimize.fast_engine import signals_to_int  # noqa: E402
from indicators import library, runner, classic  # noqa: E402
from optimize.sub.data_2024_2026 import load_bundle  # noqa: E402
from optimize.sub.windows import rolling_windows  # noqa: E402

_BAR_TD = TF.get("4h").bar_td
_BOUNDS = json.load(open(_HERE.parent / "sl_tp_bounds.json"))["4h"]
WIDEN = 3.0           # upper-bound widen factor (price-range premise — see ACTION_PLAN §S1.5)
MIN_TRADES = 3        # windows with fewer taken trades are pruned/flagged
N_TRIALS = 400
# Optional hard constraints (env): SUBOPT_SL_MAX caps sl_soft & sl_hard; SUBOPT_TP_MIN floors tp.
# Unset ⇒ original widened study (preserved). e.g. SUBOPT_SL_MAX=175 SUBOPT_TP_MIN=40.
SL_MIN = float(os.environ["SUBOPT_SL_MIN"]) if os.environ.get("SUBOPT_SL_MIN") else None
SL_MAX = float(os.environ["SUBOPT_SL_MAX"]) if os.environ.get("SUBOPT_SL_MAX") else None
TP_MIN = float(os.environ["SUBOPT_TP_MIN"]) if os.environ.get("SUBOPT_TP_MIN") else None
TP_MAX = float(os.environ["SUBOPT_TP_MAX"]) if os.environ.get("SUBOPT_TP_MAX") else None


def champion():
    for s in presets.strategies():
        if s["id"] == "wsi1m_4h":
            return s["preset"]
    raise RuntimeError("wsi1m_4h champion preset not found")


def freeze_once(df4, df1, box, vf, champ):
    """Compute the param(SL/TP)-independent layer ONCE over the full series: int signal + the
    gate_used mask (vol ∧ ¬veto ∧ confirm≥K). Returns (si_full, gate_full) aligned to df4."""
    si_full = signals_to_int(sig_mod.decision_signals(df4, box))
    gthr = float(np.percentile(vf, float(champ["gate_pct"])))
    volgate = vf <= gthr
    inds = library.from_specs(champ["indicators"])
    src = runner.indicator_source_1min(df4, df1, _BAR_TD)
    votes = runner.compute_votes(df4, box, inds, src=src)
    vmask = runner.veto_mask(df4, box, inds, src=src, votes=votes)
    cmask = runner.confirm_mask(df4, box, inds, int(champ["k"]), src=src, votes=votes)
    gate_full = volgate & ~vmask & cmask
    return si_full, gate_full


def _eval(d_win, df1, box, vf_win, gate_win, si_win, champ, sl_soft, sl_hard, tp):
    params = dict(sl_soft=sl_soft, sl_hard=sl_hard, tp=tp, gate_pct=0.0,
                  dd_limit=float(champ["dd_limit"]), cooldown=int(champ["cooldown"]),
                  flip=bool(champ["flip"]), window="full")
    return core.backtest_metrics(d_win, df1, box, vf_win, 0, params, _BAR_TD,
                                 gate_used=gate_win, sig_int=si_win, pv=float(champ["pv"]))


def _bounds():
    """Widened SL/TP search bounds (lower kept; upper × WIDEN), then apply optional hard constraints:
    SL_MAX caps the sl_soft upper (and sl_hard via the objective); TP_MIN raises the tp lower (floor)."""
    sl_lo, sl_hi = float(_BOUNDS["sl_soft"][0]), float(_BOUNDS["sl_soft"][1]) * WIDEN
    tp_lo, tp_hi = float(_BOUNDS["tp"][0]), float(_BOUNDS["tp"][1]) * WIDEN
    if SL_MIN is not None:
        sl_lo = max(sl_lo, SL_MIN)
    if SL_MAX is not None:
        sl_hi = min(sl_hi, SL_MAX)
    if TP_MIN is not None:
        tp_lo = max(tp_lo, TP_MIN)
    if TP_MAX is not None:
        tp_hi = min(tp_hi, TP_MAX)
    return {"sl_soft": (sl_lo, sl_hi),
            "sl_hard_delta": (0.0, float(_BOUNDS["sl_hard"][1]) * WIDEN),
            "tp": (tp_lo, tp_hi)}


def optimize_window(w, df4, df1, box, vf, atr, si_full, gate_full, champ, n_trials, seed=42):
    lo, hi = w["idx_lo"], w["idx_hi"] + 1                      # inclusive → slice end
    d_win = df4.iloc[lo:hi].reset_index(drop=True)
    vf_win, gate_win, si_win = vf[lo:hi], gate_full[lo:hi], si_full[lo:hi]
    B = _bounds()

    def objective(trial):
        sl_soft = trial.suggest_float("sl_soft", *B["sl_soft"])
        # cap sl_hard ≤ SL_MAX (the hard stop is the real risk line); else widened delta
        dhi = (SL_MAX - sl_soft) if SL_MAX is not None else B["sl_hard_delta"][1]
        delta = trial.suggest_float("sl_hard_delta", 0.0, max(0.0, dhi))
        tp = trial.suggest_float("tp", *B["tp"])
        m = _eval(d_win, df1, box, vf_win, gate_win, si_win, champ, sl_soft, sl_soft + delta, tp)
        if m["n_taken"] < MIN_TRADES:
            raise optuna.TrialPruned()
        trial.set_user_attr("n", m["n_taken"]); trial.set_user_attr("dd", m["max_dd"])
        trial.set_user_attr("win", m["win"]); trial.set_user_attr("sl_hard", sl_soft + delta)
        return float(m["pnl"])

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    close = d_win["Close"].to_numpy(float)
    price_start, price_end, price_mean = float(close[0]), float(close[-1]), float(close.mean())
    bt = study.best_trial if study.best_trials else None
    if bt is None:
        return {"anchor": w["anchor"], "n_trades": 0, "note": "no feasible trial (min-trades)"}
    p = bt.params; ss = p["sl_soft"]; sh = bt.user_attrs["sl_hard"]; tp = p["tp"]
    clipped = (ss > 0.98 * B["sl_soft"][1]) or (tp > 0.98 * B["tp"][1])
    return {
        "anchor": w["anchor"], "win_start": w["start_month"], "win_end": w["end_month"],
        "price_start": round(price_start, 2), "price_end": round(price_end, 2),
        "price_mean": round(price_mean, 2),
        "atr_mean": round(float(atr[lo:hi][~np.isnan(atr[lo:hi])].mean()), 2),
        "harv_mean": round(float(vf_win.mean()), 4),
        "best_sl_soft": round(ss, 2), "best_sl_hard": round(sh, 2), "best_tp": round(tp, 2),
        "n_trades": int(bt.user_attrs["n"]), "pnl": round(float(bt.value), 2),
        "max_dd": round(float(bt.user_attrs["dd"]), 2), "win_rate": round(float(bt.user_attrs["win"]), 1),
        "sl_pct_of_price": round(100 * ss / price_mean, 4), "tp_pct_of_price": round(100 * tp / price_mean, 4),
        "bound_clipped": int(clipped),
    }


def run(n_trials=N_TRIALS, smoke=False):
    champ = champion()
    print(f"loading 29-month bundle + freezing champion layer (once)…", flush=True)
    df4, df1, box, vf, months = load_bundle()
    atr = classic.atr(df4["High"].to_numpy(float), df4["Low"].to_numpy(float),
                      df4["Close"].to_numpy(float), 14)
    si_full, gate_full = freeze_once(df4, df1, box, vf, champ)
    print(f"  gate_used active bars: {int(gate_full.sum())}/{len(gate_full)}", flush=True)
    windows = rolling_windows(months, size=3, step=1)
    if smoke:
        windows = windows[:1]; n_trials = min(n_trials, 40)
    rows = []
    for w in windows:
        r = optimize_window(w, df4, df1, box, vf, atr, si_full, gate_full, champ, n_trials)
        rows.append(r)
        print(f"  [{r['anchor']}] sl {r.get('best_sl_soft','-')}/{r.get('best_sl_hard','-')} "
              f"tp {r.get('best_tp','-')} | n={r.get('n_trades')} pnl={r.get('pnl')} "
              f"dd={r.get('max_dd')} price~{r.get('price_mean')} clip={r.get('bound_clipped')}", flush=True)
    return rows


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=N_TRIALS)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default=str(_HERE / "results" / "subopt_table.csv"))
    a = ap.parse_args()
    rows = run(n_trials=a.trials, smoke=a.smoke)
    if not a.smoke:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_csv(a.out, index=False)
        print(f"\nwrote {a.out} ({len(rows)} windows)")
