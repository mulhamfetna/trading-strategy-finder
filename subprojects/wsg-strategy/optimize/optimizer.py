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

from optimize import data as data_mod, timeframes as TF  # noqa: E402
from optimize.folds import score_walkforward             # noqa: E402

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
        params = dict(sl_soft=sl_soft, sl_hard=sl_soft + delta, tp=tp, gate_pct=gate_pct,
                      dd_limit=dd_limit, cooldown=cooldown, flip=flip, window="full")
        r = score_walkforward(df_dec, df1, box, vf, params, tf.bar_td, k=folds, min_trades=min_trades)
        if not r["valid"]:
            raise optuna.TrialPruned()
        trial.set_user_attr("worst_dd", r["worst_dd"])
        trial.set_user_attr("median_pnl", r["median_pnl"])
        trial.set_user_attr("total_pnl", r.get("total_pnl"))
        return r["median_pnl"], -r["worst_dd"]

    study = optuna.create_study(
        study_name=f"wsh_{tf_name}",
        storage=f"sqlite:///{_DB}",
        directions=["maximize", "maximize"],
        sampler=optuna.samplers.NSGAIISampler(seed=seed),
        load_if_exists=True,
    )
    t0 = time.time()
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    dur = time.time() - t0

    front = sorted(study.best_trials, key=lambda t: t.values[0], reverse=True)
    print(f"[{tf_name}] {len(study.trials)} trials in {dur:.0f}s; Pareto front {len(front)} points:",
          flush=True)
    for t in front[:12]:
        p = t.params
        print(f"   P/L(med) ${t.values[0]:>7,.0f}  maxDD ${-t.values[1]:>6,.0f}  | "
              f"slS {p['sl_soft']:.0f} slH {p['sl_soft']+p['sl_hard_delta']:.0f} tp {p['tp']:.0f} "
              f"gate {p['gate_pct']:.0f} dd {p['dd_limit']:.0f} cd {p['cooldown']} flip {p['flip']}",
              flush=True)
    return {"timeframe": tf_name, "n_trials": len(study.trials), "front": len(front), "dur_s": dur}


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
