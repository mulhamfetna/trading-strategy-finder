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


# Cross-instrument contributor search block now lives in optimize/contributor_search.py (shared with the L1
# optimizer). Keep the original names as back-compat aliases so existing call-sites/tests are unchanged.
from optimize import contributor_search as _csearch          # noqa: E402
SMC_COMMITTEE_KEYS = _csearch.SMC_COMMITTEE_KEYS      # historical set; NOT the default (#95)
DEFAULT_COMMITTEE_EXCLUDE = _csearch.DEFAULT_COMMITTEE_EXCLUDE
_suggest_contributor = _csearch.suggest_contributor


def suggest_l2_params(trial, b: dict, cap: int, contrib_tokens=(),
                      contrib_exclude=DEFAULT_COMMITTEE_EXCLUDE, intracandle: bool = False,
                      only_inds=(), exclude_inds=()) -> dict:
    """Engine-ready L2 param dict from an Optuna trial — mirrors optimizer.objective's space (shared
    SL/TP; indicators on the 1-minute frame to match the lean L1 regime). `contrib_tokens` (opt-in) adds
    a searchable cross-instrument contributor block + topology; empty ⇒ byte-identical to the prior space.
    `contrib_exclude` keys are dropped from EACH contributor's committee search. Default is NOTHING
    dropped (#95 removed the SMC exclusion — its cost justification had fallen 100x).

    `only_inds` / `exclude_inds` scope the indicator search, exactly as the L1 optimizer's
    --only-indicators / --exclude-indicators do. They were missing here, so L2 always searched the FULL
    registry with every internal parameter, on the 1-MINUTE frame. That was affordable when the registry
    held 18 indicators; at 165 it is the reason `test_run_small_study_smoke` stopped finishing (#80).
    Empty (the default) ⇒ the whole registry, byte-identical to the prior space."""
    sl_soft = trial.suggest_float("sl_soft", float(b["sl_soft"][0]), float(b["sl_soft"][1]))
    delta = trial.suggest_float("sl_hard_delta", 0.0, float(b["sl_hard"][1]))
    tp = trial.suggest_float("tp", float(b["tp"][0]), float(b["tp"][1]))
    gate_pct = trial.suggest_float("gate_pct", 0.0, 100.0)
    dd_limit = trial.suggest_float("dd_limit", 0.0, OPT.DD_LIMIT_MAX)
    cooldown = trial.suggest_int("cooldown", 0, cap)
    flip = trial.suggest_categorical("flip", [False, True])
    specs = [{k: v for k, v in s.items() if k != "_searched"}
             for s in OPT._suggest_indicators(trial, exclude=tuple(exclude_inds), only=tuple(only_inds))]
    k_rule = trial.suggest_int("k", 1, 5)
    cap_1min = trial.suggest_int("cap_1min", 0, OPT.CAP_1MIN_MAX)   # max-hold (traded 1-min bars); 0 = off
    params = dict(sl_soft=sl_soft, sl_hard=sl_soft + delta, tp=tp, gate_pct=gate_pct,
                  dd_limit=dd_limit, cooldown=int(cooldown), flip=bool(flip), window="full",
                  indicators=specs, k=int(k_rule), ind_1min=True, cap_1min=int(cap_1min))
    if contrib_tokens:
        params["contributor_topology"] = trial.suggest_categorical(
            "contributor_topology", ["separate_and", "merged", "or_boost"])
        params["contributors"] = [_suggest_contributor(trial, tok, exclude_committee=contrib_exclude,
                                                       only_committee=tuple(only_inds))
                                   for tok in contrib_tokens]
    if intracandle:
        # E3a focused study: force the intra-candle timing ON for L2's vetoed stream and search the wait
        # window N. Empty/off ⇒ default L2 search space unchanged (byte-identical).
        params["l2_intracandle"] = True
        params["l2_intracandle_max_wait"] = trial.suggest_categorical(
            "l2_intracandle_max_wait", [30, 60, 120, 240])
    return params


def run(n_trials: int = 200, tf: str = "4h", study_prefix: str = "l2v1", seed: int = 1,
        min_trades: int = 5, sampler: str = "nsga3", storage_url: str | None = None,
        dd_pnl_cap: float = OPT.DD_PNL_CAP, l1_params: dict | None = None,
        contrib_tokens=(), contrib_exclude=DEFAULT_COMMITTEE_EXCLUDE, instrument: str = "NQ",
        intracandle: bool = False, only_inds=(), exclude_inds=()) -> dict:
    """NSGA-III search over L2 profiles. Objective = (in-sample L2 P/L, -in-sample max_dd, win-rate)
    with the DD<=dd_pnl_cap*P/L feasibility constraint; OOS (2026) is scored only for the champion.
    `l1_params` (optional) scores L2 on a CANDIDATE L1's residuals (e.g. the wsh6 cap_1min champion)
    instead of the frozen production L1 — used to run L2 over a new L1 without overwriting it."""
    l1 = (payload.run_l1_cached(tf, instrument=instrument) if l1_params is None
          else payload.run_l1_cached(tf, params=l1_params, instrument=instrument))
    w = WINDOWS(l1)
    caps = OPT._load_json(OPT._CAPS); bounds = OPT._load_json(OPT._BOUNDS)
    cap = int(caps[tf]["cooldown_cap"]); b = bounds[tf]
    from indicators import library as _lib
    _scope = OPT.searchable_indicators(tuple(only_inds), tuple(exclude_inds))
    print(f"[l2:{tf}] in-sample bars {w['in']}  OOS {w['oos']}  trials={n_trials}  min_trades={min_trades}"
          f"  indicators searched={len(_scope)}/{len(_lib.REGISTRY)}", flush=True)
    if contrib_tokens and contrib_exclude:
        print(f"[l2:{tf}] **NOTE: SMC indicators {list(contrib_exclude)} are EXCLUDED from the "
              f"cross-instrument committee search (speed — ifvg/breaker are ~90% of per-trial cost, "
              f"PERFORMANCE.md §9). They remain available in the manual dashboard backtester.**", flush=True)

    def objective(trial):
        params = suggest_l2_params(trial, b, cap, contrib_tokens=contrib_tokens,
                                   contrib_exclude=contrib_exclude, intracandle=intracandle,
                                   only_inds=only_inds, exclude_inds=exclude_inds)
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

    study_name = f"{study_prefix}_{tf}{OPT._study_suffix(instrument)}"
    url = storage_url or study_storage.storage_url(OPT._db_for(tf, study_name, instrument))
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
    smc_excluded = list(contrib_exclude) if (contrib_tokens and contrib_exclude) else []
    return {"study": study, "n_trials": len(study.trials), "n_feasible": len(feasible),
            "champion": champion, "contrib_smc_excluded": smc_excluded}


def _export_champion(champion: dict, tf: str, out_dir, prefix: str = "l2v1",
                     contrib_smc_excluded=(), instrument: str = "NQ") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{prefix}_{tf}{OPT._study_suffix(instrument)}_champion.json"
    rec = {"tf": tf, "prefix": prefix, "instrument": instrument, "params": champion["params"],
           "in_sample": champion["in_sample"], "oos": champion["oos"]}
    if contrib_smc_excluded:
        rec["contrib_smc_excluded"] = list(contrib_smc_excluded)
        rec["contrib_smc_excluded_note"] = ("SMC indicators excluded from the cross-instrument committee "
                                            "SEARCH for speed (PERFORMANCE.md §9); available in the dashboard.")
    path.write_text(json.dumps(rec, indent=1))
    return path


def _l1_params_from_champion(path: str, tf: str) -> dict:
    """Build an engine-ready L1 layer-params dict from a champion json (box + indicators dict) so L2 is
    scored on THIS L1's residuals (e.g. the wsh6cold cap=448 winner) instead of the frozen production L1.
    L1 champions are searched on the 1-minute frame, so ind_1min is forced True (presets._preset omits it,
    and the layer-schema default of False would compute indicators on the wrong frame → wrong residuals)."""
    rec = json.loads(Path(path).read_text())
    c = rec.get(tf, rec)                                    # accept {tf:{...}} or a bare champion record
    return payload._champion_layer_params(tf, c)


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
    ap.add_argument("--contributors", default="",
                    help="FUSION STUDY ONLY. Comma-separated cross-instrument contributor tokens to "
                         "SEARCH (e.g. 'ES'). NOT a native indicator. Requires "
                         "--enable-fusion-contributors. Empty (default) ⇒ no contributor block.")
    ap.add_argument("--enable-fusion-contributors", action="store_true",
                    help="acknowledge the fusion opt-in required by --contributors (#96)")
    # #95 INVERTED THIS FLAG. It used to be --contrib-include-smc, an opt-IN, because the SMC family was
    # excluded by default "for speed — ~10x slower per trial". That is measured false today: admitting all
    # eight costs +4.4% of a trial, and four of the six were never expensive at all. Withholding is now the
    # thing you ask for, and you ask for it by NAMING the keys rather than by invoking a family.
    ap.add_argument("--contrib-exclude", default="",
                    help="comma-separated indicators to withhold from the contributor committee SEARCH. "
                         "Empty (default) ⇒ nothing withheld (#95). Pass "
                         "'structure_trend,order_block,fvg,ifvg,breaker,cisd' to reproduce a "
                         "pre-2026-08-01 run.")
    ap.add_argument("--out", default=str(_PI / "optimize" / "results"))
    ap.add_argument("--intracandle", action="store_true",
                    help="E3a: force L2 intra-candle entry timing ON for the vetoed stream + search the wait "
                         "window N. Use with --prefix l2ic1. Off ⇒ default L2 search space unchanged.")
    ap.add_argument("--instrument", default="NQ",
                    help="instrument to optimize L2 on (NQ default, or ES). Non-NQ studies/champions are "
                         "suffixed (_ES); L1 residuals + pv follow the instrument automatically.")
    a = ap.parse_args()
    from optimize import instruments as _inst
    if not _inst.is_valid(a.instrument):
        print(f"unknown instrument {a.instrument!r}; known {list(_inst.TOKENS)}", flush=True); return 2
    contrib_tokens = tuple(t.strip() for t in a.contributors.split(",") if t.strip())
    try:
        _csearch.require_fusion_optin(contrib_tokens, a.enable_fusion_contributors)
    except _csearch.FusionNotEnabled as e:
        print(f"\n{e}\n", flush=True)
        return 4
    contrib_exclude = tuple(x for x in a.contrib_exclude.split(',') if x)
    l1_params = _l1_params_from_champion(a.l1_champion, a.tf) if a.l1_champion else None
    if l1_params is not None:
        print(f"[l2:{a.tf}] scoring L2 on CANDIDATE L1 residuals from {a.l1_champion} "
              f"(cap_1min={l1_params.get('cap_1min')}, ind_1min={l1_params.get('ind_1min')})", flush=True)
    if contrib_tokens:
        print(f"[l2:{a.tf}] searching cross-instrument contributors {list(contrib_tokens)} "
              f"(+ topology) — search space roughly doubles per contributor", flush=True)
    res = run(n_trials=a.trials, tf=a.tf, study_prefix=a.prefix, seed=a.seed,
              min_trades=a.min_trades, sampler=a.sampler, storage_url=a.storage_url, l1_params=l1_params,
              contrib_tokens=contrib_tokens, contrib_exclude=contrib_exclude, instrument=a.instrument,
              intracandle=a.intracandle)
    print(f"[l2:{a.tf}] {res['n_trials']} trials · {res['n_feasible']} feasible", flush=True)
    if res["champion"] is not None:
        p = _export_champion(res["champion"], a.tf, a.out, a.prefix,
                             contrib_smc_excluded=res.get("contrib_smc_excluded", ()), instrument=a.instrument)
        print(f"[l2:{a.tf}] champion -> {p}", flush=True)
    else:
        print(f"[l2:{a.tf}] no feasible champion (try more trials / lower --min-trades)", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
