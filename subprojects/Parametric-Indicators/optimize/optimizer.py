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
import sqlite3
import sys
import time
from pathlib import Path

import optuna

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize import data as data_mod, timeframes as TF, signals as sig_mod  # noqa: E402
from optimize import storage as study_storage  # noqa: E402  (Tier 1 — centralized storage URL)
from optimize.fast_engine import signals_to_int          # noqa: E402
from optimize.folds import score_walkforward             # noqa: E402
from optimize.core import backtest_metrics               # noqa: E402
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
_DB = _STUDIES / "wsh.db"          # legacy SHARED store (one file, all timeframes) — kept for back-compat


def _study_in(db_path: Path, study_name: str) -> bool:
    """True iff an Optuna study named `study_name` already lives in the SQLite file `db_path`."""
    if not db_path.exists():
        return False
    try:
        con = sqlite3.connect(db_path)
        try:
            rows = con.execute("SELECT study_name FROM studies").fetchall()
        finally:
            con.close()
        return any(r[0] == study_name for r in rows)
    except Exception:
        return False


def _db_for(tf_name: str, study_name: str) -> Path:
    """Resolve which SQLite file to use for one timeframe's study.

    New layout: each timeframe gets its OWN file (wsh_<tf>.db) so ~30 workers split across 6 locks
    instead of contending on one (see optimize/server/INCIDENT_wsh4_sqlite_contention.md).

    Backward-compatibility (prefix-aware): if no per-TF file exists yet but the legacy shared wsh.db
    ALREADY CONTAINS this exact study, keep using the shared file so it resumes correctly (and shout a
    loud FALLBACK warning). Otherwise use the new per-TF file. This guarantees studies created under the
    old single-file layout — including those the server is producing right now — stay readable/resumable.
    """
    per_tf = _STUDIES / f"wsh_{tf_name}.db"
    if per_tf.exists():
        return per_tf
    if _study_in(_DB, study_name):
        print(f"⚠️  FALLBACK: per-TF file '{per_tf.name}' absent, but study '{study_name}' lives in the "
              f"legacy shared '{_DB.name}' — using the SHARED file for '{tf_name}'. (New isolated per-TF "
              f"file will NOT be created while the shared DB holds this study.)", flush=True)
        return _DB
    return per_tf                  # fresh study → create the isolated per-TF file
_CAPS = _HERE / "cooldown_caps.json"
_BOUNDS = _HERE / "sl_tp_bounds.json"

DD_LIMIT_MAX = 5000.0


def _load_json(p: Path) -> dict:
    if not p.exists():
        raise FileNotFoundError(f"missing {p.name} — run the H.4/H.5 derivation first")
    return json.loads(p.read_text())


def run(tf_name: str, n_trials: int = 200, folds: int = 5, min_trades: int = 5,
        seed: int = 1, ind_1min: bool = False, study_prefix: str = "wsh3") -> dict:
    tf = TF.get(tf_name)
    caps = _load_json(_CAPS)
    bounds = _load_json(_BOUNDS)
    if tf_name not in caps or tf_name not in bounds or "tp" not in bounds[tf_name]:
        raise KeyError(f"no derived caps/bounds for {tf_name} (run cooldown.py + sl_tp_bounds.py)")
    cap = int(caps[tf_name]["cooldown_cap"])
    b = bounds[tf_name]

    print(f"[{tf_name}] loading inputs ...", flush=True)
    df_dec, df1, box, vf, n_split = data_mod.load_inputs(tf_name)
    sig_int = signals_to_int(sig_mod.decision_signals(df_dec, box))   # precompute once (param-independent)
    print(f"[{tf_name}] {len(df_dec)} decision bars; cooldown cap {cap}; "
          f"bounds sl_soft{b['sl_soft']} sl_hard{b['sl_hard']} tp{b['tp']}; "
          f"indicators on {'1-MINUTE frame' if ind_1min else 'decision TF'}", flush=True)

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
                      indicators=specs, k=k_rule, ind_1min=ind_1min)
        r = score_walkforward(df_dec, df1, box, vf, params, tf.bar_td, k=folds,
                              min_trades=min_trades, sig_int=sig_int)
        if not r["valid"]:
            raise optuna.TrialPruned()
        worst_dd = r["worst_dd"]; med_win = r["median_win"]
        # FULL-PERIOD feasibility (user): full-window max DD ≤ 25% of full-window P/L. One extra
        # backtest over the whole window (gate frozen causally on vf[:n_split]).
        full = backtest_metrics(df_dec, df1, box, vf, n_split, dict(params, window="full"),
                                tf.bar_td, sig_int=sig_int)
        full_pnl = float(full["pnl"]); full_dd = float(full["max_dd"])
        trial.set_user_attr("worst_dd", worst_dd)
        trial.set_user_attr("median_pnl", r["median_pnl"])
        trial.set_user_attr("median_win", med_win)
        trial.set_user_attr("full_pnl", full_pnl)
        trial.set_user_attr("full_dd", full_dd)
        # feasible iff full_dd ≤ 0.25·full_pnl ⇒ (full_dd − 0.25·full_pnl) ≤ 0 (P/L≤0 ⇒ infeasible).
        trial.set_user_attr("constraint", [float(full_dd - DD_PNL_CAP * full_pnl)])
        # 3 objectives, all maximised: median fold P/L, −worst-fold DD, median fold win-rate.
        return r["median_pnl"], -worst_dd, med_win

    def _constraints(trial):
        return trial.user_attrs.get("constraint", [1.0])   # missing ⇒ infeasible

    # Per-timeframe DB file (back-compat resolver) splits the write-lock ~6× and, with the hardening
    # below, removes the many-writer contention (see optimize/server/INCIDENT_wsh4_sqlite_contention.md +
    # MIGRATION_per_tf_db.md). WAL lets readers run alongside the single writer; a 60s busy_timeout makes
    # a worker WAIT for the lock instead of erroring out.
    study_name = f"{study_prefix}_{tf_name}"
    db_path = _db_for(tf_name, study_name)
    # Tier 1: one source of truth for the store URL. WSH_STORAGE_URL (e.g. postgresql://…) overrides the
    # per-TF sqlite path; unset ⇒ the per-TF sqlite file, byte-identical to before. WAL/busy_timeout file
    # hardening applies only to a sqlite file; a served RDB (Postgres) uses MVCC + a connection pool.
    _url = study_storage.storage_url(db_path)
    if study_storage.is_sqlite(_url):
        with sqlite3.connect(db_path) as _c:
            _c.execute("PRAGMA journal_mode=WAL;")
            _c.execute("PRAGMA synchronous=NORMAL;")
    storage = optuna.storages.RDBStorage(url=_url, engine_kwargs=study_storage.engine_kwargs(_url))
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        directions=["maximize", "maximize", "maximize"],
        sampler=optuna.samplers.NSGAIIISampler(seed=seed, constraints_func=_constraints),
        load_if_exists=True,
    )
    t0 = time.time()
    # A transient store error (e.g. SQLite "database is locked" under many concurrent workers) fails
    # only THIS trial — it must never kill the worker, or the study loses capacity for the rest of the
    # run. See optimize/server/INCIDENT_wsh4_sqlite_contention.md.
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False,
                   catch=(optuna.exceptions.StorageInternalError,))
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
        p = t.params; ua = t.user_attrs
        fp = ua.get("full_pnl", 0.0); fd = ua.get("full_dd", 0.0)
        ratio = (fd / fp) if fp > 0 else float("inf")
        print(f"   P/L(med) ${t.values[0]:>7,.0f}  maxDD ${-t.values[1]:>6,.0f}  win {t.values[2]:4.1f}%  | "
              f"full P/L ${fp:>7,.0f} DD ${fd:>6,.0f} ({ratio*100:.0f}%) | "
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
    ap.add_argument("--ind-1min", action="store_true",
                    help="indicators read the 1-minute frame (sampled at each decision bar's last "
                         "closed minute) instead of the decision timeframe")
    ap.add_argument("--study-prefix", default="wsh3",
                    help="study name prefix (use a fresh one, e.g. wsh4, for a new regime so it "
                         "doesn't mix with prior trials)")
    a = ap.parse_args()
    run(a.timeframe, n_trials=a.trials, folds=a.folds, min_trades=a.min_trades,
        ind_1min=a.ind_1min, study_prefix=a.study_prefix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
