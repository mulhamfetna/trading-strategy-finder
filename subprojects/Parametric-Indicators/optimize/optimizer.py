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


def _suggest_indicators(trial, exclude=(), only=()):
    """WS-I.8 search space: each registered indicator on/off + its params (rectangular — params always
    suggested so NSGA crossover stays well-defined). Mode = the schema default. Keys in `exclude`, or (when
    `only` is non-empty) keys NOT in `only`, are forced OFF with default params and NOT suggested (α: revert
    to wsh4-era / restrict to a subset ⇒ fewer dimensions). `_searched` flags which keys entered the search."""
    specs = []
    for key in library.REGISTRY:
        meta = library.SCHEMA[key]
        searched = (key not in exclude) and (not only or key in only)
        if not searched:
            params = {p["name"]: p["default"] for p in meta["params"]}
            specs.append({"key": key, "enabled": False, "mode": meta["mode"], "params": params, "_searched": False})
            continue
        enabled = trial.suggest_categorical(f"en_{key}", [False, True])
        params = {p["name"]: _suggest_param(trial, f"{key}_{p['name']}", p) for p in meta["params"]}
        specs.append({"key": key, "enabled": enabled, "mode": meta["mode"], "params": params, "_searched": True})
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

# ─────────────────────────────────────────────────────────────────────────────────────────────────
# Search-space sizing + dimension-proportional trial budget (anti "bigger space, fewer samples" trap).
# See study_range_regime/REPORT_optimizer_superset_paradox_and_system_breakdown.md: NSGA-III is a finite
# stochastic search, so when dimensions grow the trial budget MUST grow with them or sampling thins out
# and the best-found point can regress. We scale trials ∝ dimensions and report the plan for acceptance.
# ─────────────────────────────────────────────────────────────────────────────────────────────────
TRIALS_PER_DIM = 100   # empirical norm: wsh4 ran ~5483 trials over 52 dims ≈ 105/dim (wsh5 ≈ 87/dim)


def search_dims(split_sltp: bool) -> dict:
    """Breakdown of the tunable search dimensions for the current REGISTRY/SCHEMA.
    base continuous (sl_soft, sl_hard_delta, tp, gate_pct, dd_limit)=5; categorical (flip)=1;
    integer (cooldown, k)=2; one on/off flag per indicator; every indicator param; +6 if split_sltp."""
    en_flags = len(library.REGISTRY)
    ind_params = sum(len(library.SCHEMA[k].get("params", [])) for k in library.REGISTRY)
    split = 6 if split_sltp else 0
    d = dict(base_cont=5, base_cat=1, base_int=2, en_flags=en_flags, ind_params=ind_params, split=split)
    d["total"] = sum(d.values())
    return d


def recommended_trials(split_sltp: bool, per_dim: int = TRIALS_PER_DIM) -> int:
    """Dimension-proportional trial budget: total search dimensions × per_dim. Grows automatically when
    indicators or split SL/TP add dimensions, so sampling density stays roughly constant across regimes."""
    return search_dims(split_sltp)["total"] * int(per_dim)


def print_plan(tf_name: str, split_sltp: bool, per_dim: int = TRIALS_PER_DIM, n_trials: int | None = None,
               sampler: str = "nsga3"):
    """Print the search-space size + recommended (dimension-proportional) trial budget. Used by the
    `--plan` dry-run and before every real launch so the budget is reported and can be accepted."""
    d = search_dims(split_sltp)
    rec = recommended_trials(split_sltp, per_dim)
    print(f"── OPTIMIZER PLAN [{tf_name}] {'SPLIT long/short SL/TP' if split_sltp else 'shared SL/TP'} "
          f"· sampler={sampler} ──", flush=True)
    print(f"   dimensions: base {d['base_cont']}c+{d['base_cat']}cat+{d['base_int']}i = "
          f"{d['base_cont']+d['base_cat']+d['base_int']}  |  indicators {d['en_flags']} on/off + "
          f"{d['ind_params']} params  |  split {d['split']}  →  TOTAL {d['total']} dims", flush=True)
    print(f"   trials/dim {per_dim}  →  RECOMMENDED {rec:,} trials  (∝ dimensions; grows if you add more)", flush=True)
    if n_trials is not None and n_trials != rec:
        print(f"   (requested --trials {n_trials:,} ⇒ {n_trials/d['total']:.0f}/dim)", flush=True)
    return rec


_RESULTS_DIR = _HERE / "results"

# ─────────────────────────────────────────────────────────────────────────────────────────────────
# Selectable sampler (P2 — REPORT_optimizer_algorithm_alternatives.md).
# Optuna decouples the OBJECTIVE (what we score — the walk-forward backtest) from the SAMPLER (the
# "brain" that, given all past trials, proposes the next params to try). NSGA-III is the historical
# hard-coded default but it is a genetic search that COLLAPSES toward one basin in high dimensions —
# the root of the superset paradox. Making the brain a choice lets us pilot more sample-efficient
# Bayesian samplers (TPE/MOTPE, GP-BO) at zero code cost, and exposes CMA-ES as the Stage-B engine for
# the two-stage decomposition (P3). DEFAULT is nsga3 ⇒ byte-identical to every prior run.
# ─────────────────────────────────────────────────────────────────────────────────────────────────
SAMPLER_CHOICES = ("nsga3", "nsga2", "tpe", "motpe", "gp", "cmaes")


def make_sampler(name: str, seed: int, constraints_func, n_objectives: int):
    """Build an Optuna sampler by short name.

    Multi-objective-capable (drop-in for the full 3-objective study): nsga3 (default), nsga2, tpe/motpe, gp.
    Single-objective + CONTINUOUS-only: cmaes — raises here if asked to drive the >1-objective study; it is
    the Stage-B engine of the two-stage decomposition (P3), not a drop-in for the full mixed search.
    All multi-objective samplers receive the SAME feasibility constraint (DD≤25%·P&L) as NSGA-III, so
    swapping the brain never changes which trials are 'feasible'."""
    nm = (name or "nsga3").lower()
    if nm in ("nsga3", "nsga", "nsgaiii"):
        return optuna.samplers.NSGAIIISampler(seed=seed, constraints_func=constraints_func)
    if nm in ("nsga2", "nsgaii"):
        return optuna.samplers.NSGAIISampler(seed=seed, constraints_func=constraints_func)
    if nm in ("tpe", "motpe"):
        # multivariate+group model parameter interactions (this is MOTPE when directions>1). constraints_func
        # keeps the feasibility constraint honoured exactly as NSGA-III does.
        return optuna.samplers.TPESampler(seed=seed, multivariate=True, group=True,
                                          constraints_func=constraints_func)
    if nm in ("gp", "gpbo", "botorch"):
        # Native Gaussian-process Bayesian optimisation (no BoTorch dependency in this Optuna build).
        # Most sample-efficient once dimensions are small — the intended Stage-B brain for GP-BO in P3.
        return optuna.samplers.GPSampler(seed=seed, constraints_func=constraints_func)
    if nm in ("cmaes", "cma"):
        if n_objectives > 1:
            raise ValueError(
                "cmaes is SINGLE-objective + CONTINUOUS-only — it cannot drive the 3-objective / "
                "categorical-indicator study. Use it via the two-stage decomposition (P3, Stage B) on the "
                "continuous sub-problem, or scalarize to one objective first.")
        return optuna.samplers.CmaEsSampler(seed=seed)
    raise ValueError(f"unknown sampler '{name}' (choices: {', '.join(SAMPLER_CHOICES)})")


def _native_seed(box: dict, inds: dict, split_sltp: bool, b: dict) -> dict:
    """Convert a champion (dashboard schema: box + indicators) into the optimizer's NATIVE param space
    (sl_hard_delta not sl_hard; en_<key> + every <key>_<param>; long/short deltas when split). Clamped to
    the search bounds so Optuna.enqueue_trial accepts it. A fully-specified point ⇒ a deterministic seed."""
    clamp = lambda v, lo, hi: max(lo, min(hi, v))
    seed = dict(
        sl_soft=clamp(float(box["sl_soft"]), float(b["sl_soft"][0]), float(b["sl_soft"][1])),
        sl_hard_delta=clamp(float(box["sl_hard"]) - float(box["sl_soft"]), 0.0, float(b["sl_hard"][1])),
        tp=clamp(float(box["tp"]), float(b["tp"][0]), float(b["tp"][1])),
        gate_pct=clamp(float(box["gate_pct"]), 0.0, 100.0),
        dd_limit=clamp(float(box["dd_limit"]), 0.0, DD_LIMIT_MAX),
        cooldown=int(box["cooldown"]), flip=bool(box["flip"]), k=int(box["k"]),
    )
    for key in library.REGISTRY:
        on = key in inds
        seed[f"en_{key}"] = bool(on)
        for p in library.SCHEMA[key].get("params", []):
            nm, st = p["name"], float(p.get("step", 1))
            val = inds.get(key, {}).get(nm, p["default"]) if on else p["default"]
            val = clamp(float(val), float(p["min"]), float(p["max"]))
            seed[f"{key}_{nm}"] = int(round(val)) if (st.is_integer() and float(p["default"]).is_integer()) else float(val)
    if split_sltp:
        g = lambda k, dflt: (float(box[k]) if box.get(k) is not None else float(dflt))
        seed.update(
            long_sl_soft=clamp(g("long_sl_soft", box["sl_soft"]), float(b["sl_soft"][0]), float(b["sl_soft"][1])),
            long_sl_hard_delta=clamp(g("long_sl_hard", box["sl_hard"]) - g("long_sl_soft", box["sl_soft"]), 0.0, float(b["sl_hard"][1])),
            long_tp=clamp(g("long_tp", box["tp"]), float(b["tp"][0]), float(b["tp"][1])),
            short_sl_soft=clamp(g("short_sl_soft", box["sl_soft"]), float(b["sl_soft"][0]), float(b["sl_soft"][1])),
            short_sl_hard_delta=clamp(g("short_sl_hard", box["sl_hard"]) - g("short_sl_soft", box["sl_soft"]), 0.0, float(b["sl_hard"][1])),
            short_tp=clamp(g("short_tp", box["tp"]), float(b["tp"][0]), float(b["tp"][1])),
        )
    return seed


def warm_start_seeds(tf_name: str, split_sltp: bool, b: dict) -> list[dict]:
    """Known champions to enqueue as the optimizer's FIRST trials so the returned front is provably ≥ their
    score (defeats the 'larger space sampled worse' trap). Reads the per-TF wsh4 champion + (4h) the wsh5
    split champion from optimize/results/*.json. Missing files ⇒ fewer/no seeds (safe)."""
    seeds = []
    for fn in ("wsh4_champions_full.json", "wsi_champions_full.json"):
        f = _RESULTS_DIR / fn
        if f.exists():
            try:
                c = json.loads(f.read_text()).get(tf_name)
                if c:
                    seeds.append(_native_seed(c["box"], c.get("indicators", {}), split_sltp, b)); break
            except Exception:
                pass
    split_f = _RESULTS_DIR / f"wsh5_{tf_name}_split_champion.json"
    if split_sltp and split_f.exists():
        try:
            c = json.loads(split_f.read_text()).get(tf_name)
            if c:
                seeds.append(_native_seed(c["box"], c.get("indicators", {}), split_sltp, b))
        except Exception:
            pass
    # α: also seed the β lean champion (cci/order_block/structure_trend) when present, so a decision-pause
    # search starts from the known lean point too (front guaranteed ≥ it).
    lean_f = _RESULTS_DIR / "wsh_lean_4h_champion.json"
    if lean_f.exists():
        try:
            c = json.loads(lean_f.read_text()).get(tf_name)
            if c:
                seeds.append(_native_seed(c["box"], c.get("indicators", {}), split_sltp, b))
        except Exception:
            pass
    return seeds


def _load_json(p: Path) -> dict:
    if not p.exists():
        raise FileNotFoundError(f"missing {p.name} — run the H.4/H.5 derivation first")
    return json.loads(p.read_text())


def run(tf_name: str, n_trials: int = 200, folds: int = 5, min_trades: int = 5,
        seed: int = 1, ind_1min: bool = False, study_prefix: str = "wsh3",
        split_sltp: bool = False, warm_start: bool = True, sampler: str = "nsga3",
        objective: str = "winrate", exclude_inds: tuple = (), only_inds: tuple = (),
        dd_pnl_cap: float = DD_PNL_CAP) -> dict:
    # split_sltp (Q3 / E2): when True the optimizer searches SEPARATE long vs short SL/TP (long_*/short_*),
    # widening the space per the user's point-5 goal. Default False ⇒ shared SL/TP ⇒ identical to prior runs.
    # NOTE FOR THE NEXT FULL RUN (wsh5): launch with split_sltp=True to let longs and shorts get their own
    # stops/targets; the deployed wsh4 champion used shared values (long==short).
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
        specs = [{k: v for k, v in s.items() if k != "_searched"}      # strip the test-hook key before engine use
                 for s in _suggest_indicators(trial, exclude_inds, only_inds)]   # α: scoped search space
        k_rule = trial.suggest_int("k", 1, 5)           # clamped to #confirmers by confirm_mask
        params = dict(sl_soft=sl_soft, sl_hard=sl_soft + delta, tp=tp, gate_pct=gate_pct,
                      dd_limit=dd_limit, cooldown=cooldown, flip=flip, window="full",
                      indicators=specs, k=k_rule, ind_1min=ind_1min)
        if split_sltp:                                   # separate long vs short SL/TP (point 5)
            l_ss = trial.suggest_float("long_sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1]))
            l_d = trial.suggest_float("long_sl_hard_delta", 0.0, float(b["sl_hard"][1]))
            l_tp = trial.suggest_float("long_tp", float(b["tp"][0]), float(b["tp"][1]))
            s_ss = trial.suggest_float("short_sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1]))
            s_d = trial.suggest_float("short_sl_hard_delta", 0.0, float(b["sl_hard"][1]))
            s_tp = trial.suggest_float("short_tp", float(b["tp"][0]), float(b["tp"][1]))
            params.update(long_sl_soft=l_ss, long_sl_hard=l_ss + l_d, long_tp=l_tp,
                          short_sl_soft=s_ss, short_sl_hard=s_ss + s_d, short_tp=s_tp)
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
        dec_pause = float(full.get("max_no_entry_days_decision", full.get("max_no_entry_days", 0.0)))
        trial.set_user_attr("worst_dd", worst_dd)
        trial.set_user_attr("median_pnl", r["median_pnl"])
        trial.set_user_attr("median_win", med_win)
        trial.set_user_attr("full_pnl", full_pnl)
        trial.set_user_attr("full_dd", full_dd)
        trial.set_user_attr("decision_pause_days", dec_pause)
        # feasible iff full_dd ≤ cap·full_pnl ⇒ (full_dd − cap·full_pnl) ≤ 0 (P/L≤0 ⇒ infeasible). The cap
        # defaults to 0.25 but is RELAXABLE (--dd-pnl-cap / WSH_DD_CAP) — e.g. for the decision-pause search,
        # where shorter pauses trade more and need a looser DD allowance to stay feasible.
        trial.set_user_attr("constraint", [float(full_dd - dd_pnl_cap * full_pnl)])
        # 3 objectives, all maximised: median fold P/L, −worst-fold DD, and the 3rd is either median win-rate
        # (default) or −decision_pause (objective='decision_pause' ⇒ MINIMISE the recurring no-entry pause).
        third = (-dec_pause) if objective == "decision_pause" else med_win
        return r["median_pnl"], -worst_dd, third

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
    # Sampler is selectable (P2); default nsga3 reproduces every prior run exactly. The feasibility
    # constraint is passed identically to whichever brain we pick, so swapping it cannot change which
    # trials count as feasible — only WHICH points get sampled.
    _sampler = make_sampler(sampler, seed, _constraints, n_objectives=3)
    print(f"[{tf_name}] sampler = {sampler} → {type(_sampler).__name__}  objective={objective}  "
          f"dd_pnl_cap={dd_pnl_cap:.2f}" + ("  (RELAXED from 0.25)" if abs(dd_pnl_cap - DD_PNL_CAP) > 1e-9 else ""),
          flush=True)
    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        directions=["maximize", "maximize", "maximize"],
        sampler=_sampler,
        load_if_exists=True,
    )
    # Warm-start: enqueue known champions as the FIRST trials so the returned front is provably ≥ their
    # score (the wsh5 "bigger space, worse result" trap cannot recur). skip_if_exists keeps resumes idempotent.
    if warm_start:
        seeds = warm_start_seeds(tf_name, split_sltp, b)
        n_seeded = 0
        for s in seeds:
            try:
                study.enqueue_trial(s, skip_if_exists=True); n_seeded += 1
            except Exception as e:
                print(f"[{tf_name}] warm-start seed skipped ({type(e).__name__}: {e})", flush=True)
        if n_seeded:
            print(f"[{tf_name}] warm-started {n_seeded} known-champion seed trial(s) — "
                  f"the front is guaranteed ≥ their score", flush=True)

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
        print(f"   P/L(med) ${t.values[0]:>7,.0f}  maxDD ${-t.values[1]:>6,.0f}  "
              f"win {ua.get('median_win',0):4.1f}%  pause {ua.get('decision_pause_days',0):4.1f}d  | "
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
    ap.add_argument("--split-sltp", action="store_true",
                    help="search SEPARATE long vs short SL/TP (Q3/E2). Off ⇒ shared (wsh4 behaviour). "
                         "Use for the wsh5 run to let longs/shorts get their own stops/targets.")
    ap.add_argument("--auto-trials", action="store_true",
                    help="set trials = (search dimensions × --trials-per-dim) so the budget scales with the "
                         "space automatically; overrides --trials. Prints the plan.")
    ap.add_argument("--trials-per-dim", type=int, default=TRIALS_PER_DIM,
                    help=f"trials per search dimension for --auto-trials (default {TRIALS_PER_DIM}; "
                         f"wsh4 ran ~105/dim)")
    ap.add_argument("--plan", action="store_true",
                    help="DRY RUN: print the search-space size + dimension-proportional trial budget, then "
                         "exit WITHOUT running. Use this to review/accept the budget before launching.")
    ap.add_argument("--no-warm-start", action="store_true",
                    help="do NOT enqueue known champions as seed trials (warm-start is ON by default and "
                         "guarantees the front is ≥ the prior champion's score)")
    ap.add_argument("--sampler", default="nsga3", choices=SAMPLER_CHOICES,
                    help="optimizer 'brain' (default nsga3 = unchanged baseline). nsga2/tpe/motpe/gp are "
                         "drop-in multi-objective alternatives; cmaes is single-objective/continuous-only "
                         "(Stage-B of the two-stage decomposition, refused on the full study).")
    ap.add_argument("--objective", default="winrate", choices=["winrate", "decision_pause"],
                    help="3rd objective: winrate* (unchanged) or decision_pause (α: MINIMISE the recurring "
                         "no-entry pause, S0 max_no_entry_days_decision)")
    ap.add_argument("--exclude-indicators", default="",
                    help="comma-separated keys forced OFF (α: ifvg,breaker,cisd reverts to the wsh4-era 15)")
    ap.add_argument("--only-indicators", default="",
                    help="comma-separated keys; ONLY these are searched, all others forced off (α: lean subset)")
    ap.add_argument("--dd-pnl-cap", type=float, default=DD_PNL_CAP,
                    help=f"feasibility cap: max full-window DD as a fraction of full-window P/L (default "
                         f"{DD_PNL_CAP}; RELAX e.g. 0.5 to let shorter-pause/higher-DD strategies qualify)")
    a = ap.parse_args()
    # report the plan (search size + recommended trials) — always, so the budget is visible
    rec = print_plan(a.timeframe, a.split_sltp, a.trials_per_dim,
                     n_trials=(None if a.auto_trials else a.trials), sampler=a.sampler)
    if a.plan:
        print("   [--plan] dry run — not launching. Re-run without --plan (optionally --auto-trials) to start.",
              flush=True)
        return 0
    n_trials = rec if a.auto_trials else a.trials
    _excl = tuple(x for x in a.exclude_indicators.split(",") if x)
    _only = tuple(x for x in a.only_indicators.split(",") if x)
    run(a.timeframe, n_trials=n_trials, folds=a.folds, min_trades=a.min_trades,
        ind_1min=a.ind_1min, study_prefix=a.study_prefix, split_sltp=a.split_sltp,
        warm_start=not a.no_warm_start, sampler=a.sampler,
        objective=a.objective, exclude_inds=_excl, only_inds=_only, dd_pnl_cap=a.dd_pnl_cap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
