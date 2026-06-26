"""L2 optimizer (round 1) — NSGA-III over L2 profiles on the frozen L1's dropped signals, scored
full-period in-sample (2025) with an OOS holdout (2026) per spec option-3. Reuses optimize.optimizer's
sampler / indicator search space / feasibility constraint; persists under prefix l2v1."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import optuna

_PI = Path(__file__).resolve().parents[2]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from optimize.l2 import engine, metrics, payload          # noqa: E402
from optimize import optimizer as OPT                      # noqa: E402
from optimize import storage as study_storage             # noqa: E402


def WINDOWS(l1) -> dict:
    """In-sample = first calendar segment (2025); OOS holdout = the rest (2026)."""
    n = len(l1.df_dec)
    return {"in": (0, int(l1.n_split)), "oos": (int(l1.n_split), n)}


def score_window(l1, l2_params: dict, lo: int, hi: int) -> dict:
    """metrics.score for the L2 book restricted to decision bars [lo, hi)."""
    n = len(l1.df_dec)
    mask = np.zeros(n, dtype=bool)
    mask[int(lo):int(hi)] = True
    return metrics.score(engine.run_l2(l1, l2_params, bar_mask=mask))


def suggest_l2_params(trial, b: dict, cap: int) -> dict:
    """Engine-ready L2 param dict from an Optuna trial — mirrors optimizer.objective's space (shared
    SL/TP; indicators on the 1-minute frame to match the lean L1 regime)."""
    sl_soft = trial.suggest_float("sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1]))
    delta = trial.suggest_float("sl_hard_delta", 0.0, float(b["sl_hard"][1]))
    tp = trial.suggest_float("tp", float(b["tp"][0]), float(b["tp"][1]))
    gate_pct = trial.suggest_float("gate_pct", 0.0, 100.0)
    dd_limit = trial.suggest_float("dd_limit", 0.0, OPT.DD_LIMIT_MAX)
    cooldown = trial.suggest_int("cooldown", 0, cap)
    flip = trial.suggest_categorical("flip", [False, True])
    specs = [{k: v for k, v in s.items() if k != "_searched"}
             for s in OPT._suggest_indicators(trial)]
    k_rule = trial.suggest_int("k", 1, 5)
    cap_1min = trial.suggest_int("cap_1min", 0, OPT.CAP_1MIN_MAX)   # max-hold (traded 1-min bars); 0 = off
    return dict(sl_soft=sl_soft, sl_hard=sl_soft + delta, tp=tp, gate_pct=gate_pct,
                dd_limit=dd_limit, cooldown=int(cooldown), flip=bool(flip), window="full",
                indicators=specs, k=int(k_rule), ind_1min=True, cap_1min=int(cap_1min))


def run(n_trials: int = 200, tf: str = "4h", study_prefix: str = "l2v1", seed: int = 1,
        min_trades: int = 5, sampler: str = "nsga3", storage_url: str | None = None,
        dd_pnl_cap: float = OPT.DD_PNL_CAP, l1_params: dict | None = None) -> dict:
    """NSGA-III search over L2 profiles. Objective = (in-sample L2 P/L, -in-sample max_dd, win-rate)
    with the DD<=dd_pnl_cap*P/L feasibility constraint; OOS (2026) is scored only for the champion.
    `l1_params` (optional) scores L2 on a CANDIDATE L1's residuals (e.g. the wsh6 cap_1min champion)
    instead of the frozen production L1 — used to run L2 over a new L1 without overwriting it."""
    l1 = payload.run_l1_cached(tf) if l1_params is None else payload.run_l1_cached(tf, params=l1_params)
    w = WINDOWS(l1)
    caps = OPT._load_json(OPT._CAPS); bounds = OPT._load_json(OPT._BOUNDS)
    cap = int(caps[tf]["cooldown_cap"]); b = bounds[tf]
    print(f"[l2:{tf}] in-sample bars {w['in']}  OOS {w['oos']}  trials={n_trials}  min_trades={min_trades}",
          flush=True)

    def objective(trial):
        params = suggest_l2_params(trial, b, cap)
        s = score_window(l1, params, *w["in"])
        if s["n"] < min_trades:
            raise optuna.TrialPruned()
        pnl, dd, win = float(s["pnl"]), float(s["max_dd"]), float(s["win"])
        trial.set_user_attr("in_pnl", pnl); trial.set_user_attr("in_dd", dd)
        trial.set_user_attr("in_win", win); trial.set_user_attr("in_n", int(s["n"]))
        trial.set_user_attr("params", json.dumps(params))
        trial.set_user_attr("constraint", [float(dd - dd_pnl_cap * pnl)])   # feasible iff <= 0
        return pnl, -dd, win

    def _constraints(trial):
        return trial.user_attrs.get("constraint", [1.0])

    study_name = f"{study_prefix}_{tf}"
    url = storage_url or study_storage.storage_url(OPT._db_for(tf, study_name))
    storage = optuna.storages.RDBStorage(url=url, engine_kwargs=study_storage.engine_kwargs(url))
    study = optuna.create_study(study_name=study_name, storage=storage,
                                directions=["maximize", "maximize", "maximize"],
                                sampler=OPT.make_sampler(sampler, seed, _constraints, n_objectives=3),
                                load_if_exists=True)
    import warnings; warnings.filterwarnings("ignore")
    study.optimize(objective, n_trials=n_trials)

    feasible = [t for t in study.trials
                if t.values is not None and t.user_attrs.get("constraint", [1.0])[0] <= 0]
    champion = None
    if feasible:
        best = max(feasible, key=lambda t: t.values[0])     # highest in-sample P/L among feasible
        cp = json.loads(best.user_attrs["params"])
        champion = {"params": cp,
                    "in_sample": score_window(l1, cp, *w["in"]),
                    "oos": score_window(l1, cp, *w["oos"])}
        print(f"[l2:{tf}] champion in-sample P/L ${champion['in_sample']['pnl']:,.0f} "
              f"(n={champion['in_sample']['n']}) -> OOS P/L ${champion['oos']['pnl']:,.0f} "
              f"(n={champion['oos']['n']})", flush=True)
    return {"study": study, "n_trials": len(study.trials), "n_feasible": len(feasible),
            "champion": champion}


def _export_champion(champion: dict, tf: str, out_dir, prefix: str = "l2v1") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{prefix}_{tf}_champion.json"
    rec = {"tf": tf, "prefix": prefix, "params": champion["params"],
           "in_sample": champion["in_sample"], "oos": champion["oos"]}
    path.write_text(json.dumps(rec, indent=1))
    return path


def _l1_params_from_champion(path: str, tf: str) -> dict:
    """Build an engine-ready L1 layer-params dict from a champion json (box + indicators dict) so L2 is
    scored on THIS L1's residuals (e.g. the wsh6cold cap=448 winner) instead of the frozen production L1.
    L1 champions are searched on the 1-minute frame, so ind_1min is forced True (presets._preset omits it,
    and the layer-schema default of False would compute indicators on the wrong frame → wrong residuals)."""
    import presets                                          # noqa: E402  (top-level module via _PI on sys.path)
    rec = json.loads(Path(path).read_text())
    c = rec.get(tf, rec)                                    # accept {tf:{...}} or a bare champion record
    lp = presets._preset(tf, c["box"], c.get("indicators", {}))
    lp["ind_1min"] = True
    return payload.validate_layer_params(lp)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="L2 optimizer (round 1, option-3 validation)")
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--prefix", default="l2v1")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--min-trades", type=int, default=5)
    ap.add_argument("--sampler", default="nsga3")
    ap.add_argument("--storage-url", default=None, help="override store (else WSH_STORAGE_URL / per-TF sqlite)")
    ap.add_argument("--l1-champion", default=None,
                    help="path to an L1 champion json; score L2 on THIS L1's residuals (candidate L1) "
                         "instead of the frozen production L1")
    ap.add_argument("--out", default=str(_PI / "optimize" / "results"))
    a = ap.parse_args()
    l1_params = _l1_params_from_champion(a.l1_champion, a.tf) if a.l1_champion else None
    if l1_params is not None:
        print(f"[l2:{a.tf}] scoring L2 on CANDIDATE L1 residuals from {a.l1_champion} "
              f"(cap_1min={l1_params.get('cap_1min')}, ind_1min={l1_params.get('ind_1min')})", flush=True)
    res = run(n_trials=a.trials, tf=a.tf, study_prefix=a.prefix, seed=a.seed,
              min_trades=a.min_trades, sampler=a.sampler, storage_url=a.storage_url, l1_params=l1_params)
    print(f"[l2:{a.tf}] {res['n_trials']} trials · {res['n_feasible']} feasible", flush=True)
    if res["champion"] is not None:
        p = _export_champion(res["champion"], a.tf, a.out, a.prefix)
        print(f"[l2:{a.tf}] champion -> {p}", flush=True)
    else:
        print(f"[l2:{a.tf}] no feasible champion (try more trials / lower --min-trades)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
