"""H.7 — NSGA-II per-timeframe optimiser driver (TASK.md D3).

For one decision timeframe, search the strategy parameters with Optuna's NSGA-II multi-objective
sampler and score each candidate by walk-forward folds (H.6). Two objectives, both maximised:
  obj0 =  median fold P/L            (profit, consistent across folds)
  obj1 = -worst-fold maxDD           (drawdown, conservative; maximise the negative = minimise DD)
The result is the full PARETO FRONT (profit vs drawdown) — no single winner is auto-picked (D3).

Search space (per-TF bounds from H.5 sl_tp_bounds.json; cooldown cap from H.4 cooldown_caps.json):
  sl_soft      ∈ bounds.sl_soft
  sl_hard      = sl_soft + delta,  delta ∈ [0, bounds.sl_hard[1]]   (engine needs sl_hard ≥ sl_soft)
  tp           ∈ bounds.tp
  gate_pct     ∈ [0, 100]          (0 = gate off)
  dd_limit     ∈ [0, 5000]         (0 = breaker off)
  cooldown     ∈ [0, cap(TF)]      (int; D1 realized-trade-gap cap)
  flip         ∈ {False, True}

Studies persist to optimize/studies/wsh.db (SQLite, resumable). The Pareto front is written by H.8.

CLI:  python3 subprojects/wsg-strategy/optimize/optimizer.py <tf> [--trials N] [--folds K]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import optuna

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize import data as data_mod, timeframes as TF, signals as sig_mod  # noqa: E402
from optimize.fast_engine import signals_to_int          # noqa: E402
from optimize.folds import score_walkforward             # noqa: E402
from indicators import library                            # noqa: E402

DD_PNL_CAP = 0.25   # WS-I.8 constraint: feasible iff worst-fold maxDD ≤ 25% of total P/L


def _suggest_param(trial, name, p):
    """Suggest one indicator param from its schema entry (int if integer step+default, else float)."""
    lo, hi, st = float(p["min"]), float(p["max"]), float(p.get("step", 1))
    if st.is_integer() and float(p["default"]).is_integer():
        return trial.suggest_int(name, int(lo), int(hi), step=max(1, int(st)))
    return trial.suggest_float(name, lo, hi, step=st)


def _suggest_indicators(trial):
    """Full WS-I.8 search space: every registered indicator on/off + its params (rectangular —
    params always suggested so NSGA crossover stays well-defined). Mode = the schema default."""
    specs = []
    for key in library.REGISTRY:
        meta = library.SCHEMA[key]
        enabled = trial.suggest_categorical(f"en_{key}", [False, True])
        params = {p["name"]: _suggest_param(trial, f"{key}_{p['name']}", p) for p in meta["params"]}
        specs.append({"key": key, "enabled": enabled, "mode": meta["mode"], "params": params})
    return specs

_STUDIES = _HERE / "studies"
_STUDIES.mkdir(exist_ok=True)
_DB = _STUDIES / "wsh.db"
_CAPS = _HERE / "cooldown_caps.json"
_BOUNDS = _HERE / "sl_tp_bounds.json"

DD_LIMIT_MAX = 5000.0


def _load_json(p: Path) -> dict:
    if not p.exists():
        raise FileNotFoundError(f"missing {p.name} — run the H.4/H.5 derivation first")
    return json.loads(p.read_text())


def run(tf_name: str, n_trials: int = 200, folds: int = 5, min_trades: int = 5,
        seed: int = 1) -> dict:
    tf = TF.get(tf_name)
    caps = _load_json(_CAPS)
    bounds = _load_json(_BOUNDS)
    if tf_name not in caps or tf_name not in bounds or "tp" not in bounds[tf_name]:
        raise KeyError(f"no derived caps/bounds for {tf_name} (run cooldown.py + sl_tp_bounds.py)")
    cap = int(caps[tf_name]["cooldown_cap"])
    b = bounds[tf_name]

    print(f"[{tf_name}] loading inputs ...", flush=True)
    df_dec, df1, box, vf, _n = data_mod.load_inputs(tf_name)
    sig_int = signals_to_int(sig_mod.decision_signals(df_dec, box))   # precompute once (param-independent)
    print(f"[{tf_name}] {len(df_dec)} decision bars; cooldown cap {cap}; "
          f"bounds sl_soft{b['sl_soft']} sl_hard{b['sl_hard']} tp{b['tp']}", flush=True)

    def objective(trial: optuna.Trial):
        sl_soft = trial.suggest_float("sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1]))
        delta = trial.suggest_float("sl_hard_delta", 0.0, float(b["sl_hard"][1]))
        tp = trial.suggest_float("tp", float(b["tp"][0]), float(b["tp"][1]))
        gate_pct = trial.suggest_float("gate_pct", 0.0, 100.0)
        dd_limit = trial.suggest_float("dd_limit", 0.0, DD_LIMIT_MAX)
        cooldown = trial.suggest_int("cooldown", 0, cap)
        flip = trial.suggest_categorical("flip", [False, True])
        specs = _suggest_indicators(trial)              # WS-I.8 full indicator search space
        k_rule = trial.suggest_int("k", 1, 5)           # clamped to #confirmers by confirm_mask
        params = dict(sl_soft=sl_soft, sl_hard=sl_soft + delta, tp=tp, gate_pct=gate_pct,
                      dd_limit=dd_limit, cooldown=cooldown, flip=flip, window="full",
                      indicators=specs, k=k_rule)
        r = score_walkforward(df_dec, df1, box, vf, params, tf.bar_td, k=folds,
                              min_trades=min_trades, sig_int=sig_int)
        if not r["valid"]:
            raise optuna.TrialPruned()
        worst_dd = r["worst_dd"]; total_pnl = r.get("total_pnl", 0.0); med_win = r["median_win"]
        trial.set_user_attr("worst_dd", worst_dd)
        trial.set_user_attr("median_pnl", r["median_pnl"])
        trial.set_user_attr("total_pnl", total_pnl)
        trial.set_user_attr("median_win", med_win)
        # constraint: worst_dd ≤ 25% of total P/L  ⇒  (worst_dd − 0.25·total_pnl) ≤ 0 is feasible.
        trial.set_user_attr("constraint", [float(worst_dd - DD_PNL_CAP * total_pnl)])
        # 3 objectives, all maximised: median P/L, −worst DD, median win-rate.
        return r["median_pnl"], -worst_dd, med_win

    def _constraints(trial):
        return trial.user_attrs.get("constraint", [1.0])   # missing ⇒ infeasible

    study = optuna.create_study(
        study_name=f"wsh3_{tf_name}",
        storage=f"sqlite:///{_DB}",
        directions=["maximize", "maximize", "maximize"],
        sampler=optuna.samplers.NSGAIIISampler(seed=seed, constraints_func=_constraints),
        load_if_exists=True,
    )
    t0 = time.time()
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    dur = time.time() - t0

    def feasible(t):
        c = t.user_attrs.get("constraint", [1.0])
        return all(v <= 0 for v in c)

    front = [t for t in study.best_trials if feasible(t)]
    front.sort(key=lambda t: t.values[0], reverse=True)
    n_enabled = lambda p: sum(1 for k_, v in p.items() if k_.startswith("en_") and v)
    print(f"[{tf_name}] {len(study.trials)} trials in {dur:.0f}s; feasible Pareto front "
          f"{len(front)}/{len(study.best_trials)} (DD≤25%·P&L):", flush=True)
    for t in front[:12]:
        p = t.params
        print(f"   P/L(med) ${t.values[0]:>7,.0f}  maxDD ${-t.values[1]:>6,.0f}  win {t.values[2]:4.1f}%  | "
              f"slS {p['sl_soft']:.0f} slH {p['sl_soft']+p['sl_hard_delta']:.0f} tp {p['tp']:.0f} "
              f"gate {p['gate_pct']:.0f} dd {p['dd_limit']:.0f} cd {p['cooldown']} flip {p['flip']} "
              f"K{p['k']} +{n_enabled(p)}ind", flush=True)
    return {"timeframe": tf_name, "n_trials": len(study.trials),
            "front": len(front), "front_all": len(study.best_trials), "dur_s": dur}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("timeframe")
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--min-trades", type=int, default=5)
    a = ap.parse_args()
    run(a.timeframe, n_trials=a.trials, folds=a.folds, min_trades=a.min_trades)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
