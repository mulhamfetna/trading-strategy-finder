"""P3 — Two-stage decomposition optimizer (REPORT_optimizer_algorithm_alternatives.md §4).

The superset paradox is caused by optimizing 56–62 MIXED dimensions at once: a finite stochastic search
thins out and collapses. P3 splits the problem so NO single stage is high-dimensional:

  STAGE A  (discrete, len(REGISTRY)+1 dims — 166 today, ~19 when this was written)
                                 — search ONLY the indicator on/off flags + flip, with the continuous
                                   knobs and indicator params FROZEN at the warm-start champion.
                                   → shortlist the top-K indicator subsets by median fold P/L.
                                   ⚠️ its trial budget must scale with that dimensionality — see
                                   `stage_a_trials` below (#81).
  STAGE B  (continuous, ~7–13 dims) — for EACH shortlisted subset, freeze the indicators and tune ONLY
                                   the continuous execution knobs (sl_soft, sl_hard_delta, tp, gate_pct,
                                   dd_limit, cooldown, k, +6 split) with a sample-efficient brain:
                                     • cmaes : gold-standard continuous ES, SINGLE-objective ⇒ we
                                               scalarize (median P/L − penalty·feasibility-violation).
                                     • gp    : native Gaussian-process BO, keeps all 3 objectives +
                                               the DD≤25%·P&L feasibility constraint.

Champion = best FEASIBLE (subset × tuned knobs) across all Stage-B studies. The warm-start champion's
exact indicator pattern is ALWAYS force-included in the shortlist and its continuous knobs are enqueued
as a Stage-B seed ⇒ the result is provably ≥ the prior champion (the wsh5 trap cannot recur).

The continuous dimensionality that broke wsh5 NEVER appears in a single search.

CLI:  python3 -m optimize.two_stage <tf> [--stage-a-trials N] [--stage-b-trials M] [--top-k K]
                                        [--stage-b {cmaes|gp}] [--split-sltp] [--no-warm-start]
      Indicators read the 1-MINUTE frame by default; pass --tf-indicators for the decision frame.
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

# Reuse the SAME engine + helpers as the main optimizer so scoring is identical (golden-locked path).
from optimize import optimizer as OPT                      # noqa: E402
from optimize import data as data_mod, timeframes as TF, signals as sig_mod  # noqa: E402
from optimize import storage as study_storage             # noqa: E402
from optimize.fast_engine import signals_to_int           # noqa: E402
from optimize.folds import score_walkforward              # noqa: E402
from optimize.core import backtest_metrics                # noqa: E402
from indicators import library                            # noqa: E402

DD_PNL_CAP = OPT.DD_PNL_CAP
DD_LIMIT_MAX = OPT.DD_LIMIT_MAX
STAGE_B_ENGINES = ("cmaes", "gp")
# Scalarization penalty for the single-objective cmaes brain: subtract this many dollars of objective per
# dollar of feasibility violation (full_dd over the 25%·P&L cap). Pushes CMA-ES toward feasible solutions
# while leaving feasible points scored by their raw median fold P/L.
CMAES_PENALTY = 1.0


# ─────────────────────────────────────────────────────────────────────────────────────────────────
# Shared evaluation — identical math to optimizer.objective (score_walkforward + full-period backtest).
# ─────────────────────────────────────────────────────────────────────────────────────────────────
class _Ctx:
    """Loaded-once per-TF context (data + frozen champion knobs/params) shared by both stages."""
    # Defaults are the PRODUCTION settings, so `_Ctx("4h")` means what the deployed book means. They
    # were all required-positional, which reads as neutrality but is not: benches and one-off scripts
    # build _Ctx directly, and each one had to re-state `ind_1min=True` or silently evaluate in the
    # wrong frame. See optimize/test_indicator_frame_default.py for what that cost.
    def __init__(self, tf_name: str, split_sltp: bool = False, ind_1min: bool = True, folds: int = 5,
                 min_trades: int = 5, warm_start: bool = False):
        self.tf_name = tf_name; self.split_sltp = split_sltp; self.ind_1min = ind_1min
        self.folds = folds; self.min_trades = min_trades
        self.tf = TF.get(tf_name)
        caps = OPT._load_json(OPT._CAPS); bounds = OPT._load_json(OPT._BOUNDS)
        if tf_name not in caps or tf_name not in bounds or "tp" not in bounds[tf_name]:
            raise KeyError(f"no derived caps/bounds for {tf_name}")
        self.cap = int(caps[tf_name]["cooldown_cap"]); self.b = bounds[tf_name]
        print(f"[{tf_name}] loading inputs ...", flush=True)
        self.df_dec, self.df1, self.box, self.vf, self.n_split = data_mod.load_inputs(tf_name)
        self.sig_int = signals_to_int(sig_mod.decision_signals(self.df_dec, self.box))
        # Frozen champion (warm-start) → native seed dict; absent ⇒ neutral mid/default fallback.
        seeds = OPT.warm_start_seeds(tf_name, split_sltp, self.b) if warm_start else []
        self.champ = seeds[0] if seeds else self._neutral_seed()
        self.has_champion = bool(seeds)
        # split champion knobs out of the native seed
        self.champ_en = {k: bool(self.champ.get(f"en_{k}", False)) for k in library.REGISTRY}
        self.champ_flip = bool(self.champ.get("flip", False))
        self.champ_ind_params = {
            k: {p["name"]: self.champ.get(f"{k}_{p['name']}", p["default"])
                for p in library.SCHEMA[k].get("params", [])}
            for k in library.REGISTRY}
        self.champ_cont = self._cont_from_seed(self.champ)

    def _neutral_seed(self) -> dict:
        b = self.b
        s = dict(sl_soft=float(b["sl_soft"][0]), sl_hard_delta=0.0, tp=float(b["tp"][0]),
                 gate_pct=0.0, dd_limit=0.0, cooldown=0, flip=False, k=1)
        for k in library.REGISTRY:
            s[f"en_{k}"] = False
            for p in library.SCHEMA[k].get("params", []):
                s[f"{k}_{p['name']}"] = p["default"]
        if self.split_sltp:
            s.update(long_sl_soft=s["sl_soft"], long_sl_hard_delta=0.0, long_tp=s["tp"],
                     short_sl_soft=s["sl_soft"], short_sl_hard_delta=0.0, short_tp=s["tp"])
        return s

    def _cont_from_seed(self, s: dict) -> dict:
        c = {k: s[k] for k in ("sl_soft", "sl_hard_delta", "tp", "gate_pct", "dd_limit", "cooldown", "k")}
        if self.split_sltp:
            for k in ("long_sl_soft", "long_sl_hard_delta", "long_tp",
                      "short_sl_soft", "short_sl_hard_delta", "short_tp"):
                c[k] = s[k]
        return c

    def build_params(self, en: dict, flip: bool, cont: dict) -> dict:
        """Assemble the engine param dict from an indicator on/off pattern, flip, and continuous knobs.
        Indicator params are always the FROZEN champion values (P3 tunes WHICH indicators, not their
        internals)."""
        specs = [{"key": k, "enabled": bool(en[k]), "mode": library.SCHEMA[k]["mode"],
                  "params": dict(self.champ_ind_params[k])} for k in library.REGISTRY]
        params = dict(sl_soft=cont["sl_soft"], sl_hard=cont["sl_soft"] + cont["sl_hard_delta"],
                      tp=cont["tp"], gate_pct=cont["gate_pct"], dd_limit=cont["dd_limit"],
                      cooldown=int(cont["cooldown"]), flip=bool(flip), window="full",
                      indicators=specs, k=int(cont["k"]), ind_1min=self.ind_1min)
        if self.split_sltp:
            params.update(long_sl_soft=cont["long_sl_soft"],
                          long_sl_hard=cont["long_sl_soft"] + cont["long_sl_hard_delta"],
                          long_tp=cont["long_tp"], short_sl_soft=cont["short_sl_soft"],
                          short_sl_hard=cont["short_sl_soft"] + cont["short_sl_hard_delta"],
                          short_tp=cont["short_tp"])
        return params

    def evaluate(self, params: dict):
        """Identical to optimizer.objective's scoring. Returns metrics dict or None if invalid (pruned)."""
        r = score_walkforward(self.df_dec, self.df1, self.box, self.vf, params, self.tf.bar_td,
                              k=self.folds, min_trades=self.min_trades, sig_int=self.sig_int)
        if not r["valid"]:
            return None
        full = backtest_metrics(self.df_dec, self.df1, self.box, self.vf, self.n_split,
                                dict(params, window="full"), self.tf.bar_td, sig_int=self.sig_int)
        fp = float(full["pnl"]); fd = float(full["max_dd"])
        return dict(median_pnl=r["median_pnl"], worst_dd=r["worst_dd"], median_win=r["median_win"],
                    full_pnl=fp, full_dd=fd, feasible=(fp > 0 and fd <= DD_PNL_CAP * fp))


# ─────────────────────────────────────────────────────────────────────────────────────────────────
# STAGE A — discrete indicator-set selection (continuous knobs + indicator params frozen at champion).
# ─────────────────────────────────────────────────────────────────────────────────────────────────
def _stage_a_objective(ctx: _Ctx):
    def obj(trial: optuna.Trial):
        en = {k: trial.suggest_categorical(f"en_{k}", [False, True]) for k in library.REGISTRY}
        flip = trial.suggest_categorical("flip", [False, True])
        m = ctx.evaluate(ctx.build_params(en, flip, ctx.champ_cont))
        if m is None:
            raise optuna.TrialPruned()
        trial.set_user_attr("constraint", [float(m["full_dd"] - DD_PNL_CAP * m["full_pnl"])])
        for kk in ("worst_dd", "median_pnl", "median_win", "full_pnl", "full_dd"):
            trial.set_user_attr(kk, m[kk])
        return m["median_pnl"], -m["worst_dd"], m["median_win"]
    return obj


def run_stage_a(ctx: _Ctx, n_trials: int, top_k: int, seed: int = 1) -> list[dict]:
    """Returns the shortlist: up to top_k feasible indicator patterns (each a dict {key:bool}+flip),
    ALWAYS including the champion's exact pattern (so the final result is ≥ the champion)."""
    cf = lambda t: t.user_attrs.get("constraint", [1.0])
    study = optuna.create_study(directions=["maximize", "maximize", "maximize"],
                                sampler=optuna.samplers.NSGAIIISampler(seed=seed, constraints_func=cf))
    # seed the champion's own pattern first
    champ_pattern = {f"en_{k}": ctx.champ_en[k] for k in library.REGISTRY}
    champ_pattern["flip"] = ctx.champ_flip
    study.enqueue_trial(champ_pattern, skip_if_exists=True)
    t0 = time.time()
    study.optimize(_stage_a_objective(ctx), n_trials=n_trials, show_progress_bar=False,
                   catch=(optuna.exceptions.StorageInternalError,))
    feas = [t for t in study.trials
            if t.values is not None and all(v <= 0 for v in t.user_attrs.get("constraint", [1.0]))]
    feas.sort(key=lambda t: t.values[0], reverse=True)
    print(f"[{ctx.tf_name}] STAGE A: {len(study.trials)} trials in {time.time()-t0:.0f}s; "
          f"{len(feas)} feasible; taking top {top_k}", flush=True)
    shortlist = []
    seen = set()
    # force-include the champion pattern, then the top-K distinct feasible patterns
    def add(en_flip: dict):
        key = tuple(sorted((k, v) for k, v in en_flip.items()))
        if key in seen:
            return
        seen.add(key); shortlist.append(en_flip)
    add({**{k: ctx.champ_en[k] for k in library.REGISTRY}, "flip": ctx.champ_flip})
    for t in feas:
        if len(shortlist) >= top_k + 1:   # +1 because champion is always slot 0
            break
        en_flip = {k: bool(t.params[f"en_{k}"]) for k in library.REGISTRY}
        en_flip["flip"] = bool(t.params["flip"])
        add(en_flip)
    n = lambda ef: sum(1 for k in library.REGISTRY if ef[k])
    for i, ef in enumerate(shortlist):
        tag = "champion" if i == 0 else f"#{i}"
        print(f"   subset {tag}: +{n(ef)}ind flip={ef['flip']}", flush=True)
    return shortlist


# ─────────────────────────────────────────────────────────────────────────────────────────────────
# STAGE B — continuous knob tuning for ONE fixed indicator subset (cmaes scalar | gp multi-objective).
# ─────────────────────────────────────────────────────────────────────────────────────────────────
def _suggest_cont(trial: optuna.Trial, ctx: _Ctx) -> dict:
    b = ctx.b
    c = dict(sl_soft=trial.suggest_float("sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1])),
             sl_hard_delta=trial.suggest_float("sl_hard_delta", 0.0, float(b["sl_hard"][1])),
             tp=trial.suggest_float("tp", float(b["tp"][0]), float(b["tp"][1])),
             gate_pct=trial.suggest_float("gate_pct", 0.0, 100.0),
             dd_limit=trial.suggest_float("dd_limit", 0.0, DD_LIMIT_MAX),
             cooldown=trial.suggest_int("cooldown", 0, ctx.cap),
             k=trial.suggest_int("k", 1, 5))
    if ctx.split_sltp:
        c.update(long_sl_soft=trial.suggest_float("long_sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1])),
                 long_sl_hard_delta=trial.suggest_float("long_sl_hard_delta", 0.0, float(b["sl_hard"][1])),
                 long_tp=trial.suggest_float("long_tp", float(b["tp"][0]), float(b["tp"][1])),
                 short_sl_soft=trial.suggest_float("short_sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1])),
                 short_sl_hard_delta=trial.suggest_float("short_sl_hard_delta", 0.0, float(b["sl_hard"][1])),
                 short_tp=trial.suggest_float("short_tp", float(b["tp"][0]), float(b["tp"][1])))
    return c


def run_stage_b(ctx: _Ctx, en_flip: dict, engine: str, n_trials: int, seed: int = 1) -> dict | None:
    """Tune continuous knobs for one fixed indicator subset. Returns the best FEASIBLE point as a dict
    (metrics + cont + en_flip) or None if none feasible. The champion's continuous knobs are enqueued as
    the first trial so a subset == champion pattern can never score below the champion."""
    en = {k: en_flip[k] for k in library.REGISTRY}
    flip = en_flip["flip"]
    cf = lambda t: t.user_attrs.get("constraint", [1.0])

    def record(trial, m):
        trial.set_user_attr("constraint", [float(m["full_dd"] - DD_PNL_CAP * m["full_pnl"])])
        for kk in ("worst_dd", "median_pnl", "median_win", "full_pnl", "full_dd", "feasible"):
            trial.set_user_attr(kk, m[kk])

    if engine == "gp":
        study = optuna.create_study(directions=["maximize", "maximize", "maximize"],
                                    sampler=optuna.samplers.GPSampler(seed=seed, constraints_func=cf))

        def obj(trial):
            cont = _suggest_cont(trial, ctx)
            m = ctx.evaluate(ctx.build_params(en, flip, cont))
            if m is None:
                raise optuna.TrialPruned()
            record(trial, m)
            return m["median_pnl"], -m["worst_dd"], m["median_win"]
    elif engine == "cmaes":
        study = optuna.create_study(direction="maximize",
                                    sampler=optuna.samplers.CmaEsSampler(seed=seed))

        def obj(trial):
            cont = _suggest_cont(trial, ctx)
            m = ctx.evaluate(ctx.build_params(en, flip, cont))
            if m is None:
                raise optuna.TrialPruned()
            record(trial, m)
            violation = max(0.0, m["full_dd"] - DD_PNL_CAP * m["full_pnl"])
            return m["median_pnl"] - CMAES_PENALTY * violation     # scalarized
    else:
        raise ValueError(f"unknown stage-b engine '{engine}' (choices: {STAGE_B_ENGINES})")

    study.enqueue_trial(ctx.champ_cont, skip_if_exists=True)       # guarantee ≥ champion on its own pattern
    study.optimize(obj, n_trials=n_trials, show_progress_bar=False,
                   catch=(optuna.exceptions.StorageInternalError,))
    best = None
    for t in study.trials:
        ua = t.user_attrs
        if not ua.get("feasible"):
            continue
        if best is None or ua["median_pnl"] > best["median_pnl"]:
            best = dict(median_pnl=ua["median_pnl"], worst_dd=ua["worst_dd"], median_win=ua["median_win"],
                        full_pnl=ua["full_pnl"], full_dd=ua["full_dd"], params=dict(t.params),
                        en_flip=en_flip, n_ind=sum(1 for k in library.REGISTRY if en[k]))
    return best


# ─────────────────────────────────────────────────────────────────────────────────────────────────
# Orchestrator.
# ─────────────────────────────────────────────────────────────────────────────────────────────────
def stage_a_recommended_trials(per_dim: int = OPT.TRIALS_PER_DIM) -> int:
    """Dimension-proportional budget for Stage A, exactly like the L1 optimizer's --auto-trials.

    Stage A searches one on/off flag per registry entry plus `flip`. That was ~19 dimensions when the
    default of 200 trials was chosen (≈10.5 trials/dim). The registry is now 165, so Stage A is 166
    dimensions and 200 trials is **1.2 trials/dim** — close to random sampling, which means the
    "shortlist the best indicator subsets" step cannot do its job and Stage B then tunes subsets that
    were barely selected. See #81.
    """
    return (len(library.REGISTRY) + 1) * int(per_dim)


def run(tf_name: str, stage_a_trials: int | None = None, stage_b_trials: int = 100, top_k: int = 3,
        stage_b_engine: str = "cmaes", folds: int = 5, min_trades: int = 5, seed: int = 1,
        ind_1min: bool = True, split_sltp: bool = False, warm_start: bool = False) -> dict:
    if stage_b_engine not in STAGE_B_ENGINES:
        raise ValueError(f"unknown stage-b engine '{stage_b_engine}' (choices: {STAGE_B_ENGINES})")
    t0 = time.time()
    # None ⇒ derive from dimensionality (#81). An explicit value is still honoured, but a SHORT one is
    # announced rather than silently accepted — 200 trials over 166 dims is ~random sampling.
    _a_dims = len(library.REGISTRY) + 1
    if stage_a_trials is None:
        stage_a_trials = stage_a_recommended_trials()
    elif stage_a_trials < _a_dims:
        print(f"[{tf_name}] ⚠️  stage-A budget {stage_a_trials} is BELOW its {_a_dims} dimensions "
              f"({stage_a_trials / _a_dims:.2f} trials/dim). The shortlist will be close to random; "
              f"the dimension-proportional budget is {stage_a_recommended_trials():,}.", flush=True)
    ctx = _Ctx(tf_name, split_sltp, ind_1min, folds, min_trades, warm_start)
    print(f"[{tf_name}] TWO-STAGE  stage-A={stage_a_trials} trials over {_a_dims} dims "
          f"({stage_a_trials / _a_dims:.1f}/dim; {len(library.REGISTRY)} en+flip)  →  top-{top_k}  →  "
          f"stage-B={stage_b_trials} trials/subset "
          f"({stage_b_engine}; continuous {7 + (6 if split_sltp else 0)} dims)  "
          f"{'[has champion seed]' if ctx.has_champion else '[NO champion seed]'}", flush=True)

    shortlist = run_stage_a(ctx, stage_a_trials, top_k, seed=seed)

    results = []
    for i, en_flip in enumerate(shortlist):
        tag = "champion" if i == 0 else f"#{i}"
        b = run_stage_b(ctx, en_flip, stage_b_engine, stage_b_trials, seed=seed)
        if b:
            results.append(b)
            print(f"   STAGE B [{tag}] best feasible: med ${b['median_pnl']:,.0f}  worstDD "
                  f"${b['worst_dd']:,.0f}  win {b['median_win']:.1f}%  full ${b['full_pnl']:,.0f} "
                  f"DD ${b['full_dd']:,.0f}  +{b['n_ind']}ind", flush=True)
        else:
            print(f"   STAGE B [{tag}]: no feasible point", flush=True)

    if not results:
        print(f"[{tf_name}] TWO-STAGE: NO feasible champion found", flush=True)
        return {"timeframe": tf_name, "champion": None, "dur_s": time.time() - t0}
    champ = max(results, key=lambda r: r["median_pnl"])
    print(f"[{tf_name}] TWO-STAGE CHAMPION ({time.time()-t0:.0f}s total): "
          f"median ${champ['median_pnl']:,.0f}  worstDD ${champ['worst_dd']:,.0f}  "
          f"win {champ['median_win']:.1f}%  full ${champ['full_pnl']:,.0f} DD ${champ['full_dd']:,.0f}  "
          f"+{champ['n_ind']}ind flip={champ['en_flip']['flip']}", flush=True)
    return {"timeframe": tf_name, "champion": champ, "n_subsets": len(results), "dur_s": time.time() - t0,
            "stage_b_engine": stage_b_engine}


def main() -> int:
    ap = argparse.ArgumentParser(description="P3 two-stage decomposition optimizer")
    ap.add_argument("timeframe")
    # default None ⇒ dimension-proportional (len(REGISTRY)+1) * TRIALS_PER_DIM. The old literal 200 was
    # chosen at ~19 dims and is 1.2 trials/dim at 166 — see stage_a_recommended_trials() and #81.
    ap.add_argument("--stage-a-trials", type=int, default=None,
                    help="Stage-A trial budget (default: dimension-proportional, currently %d)"
                         % stage_a_recommended_trials())
    ap.add_argument("--stage-b-trials", type=int, default=100)
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--stage-b", default="cmaes", choices=STAGE_B_ENGINES,
                    help="continuous-tuning brain for stage B (cmaes = scalarized ES; gp = multi-objective BO)")
    ap.add_argument("--folds", type=int, default=5)
    ap.add_argument("--min-trades", type=int, default=5)
    OPT.add_indicator_frame_args(ap)
    ap.add_argument("--split-sltp", action="store_true")
    OPT.add_warm_start_args(ap)
    a = ap.parse_args()
    run(a.timeframe, stage_a_trials=a.stage_a_trials, stage_b_trials=a.stage_b_trials, top_k=a.top_k,
        stage_b_engine=a.stage_b, folds=a.folds, min_trades=a.min_trades, ind_1min=a.ind_1min,
        split_sltp=a.split_sltp, warm_start=a.warm_start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
