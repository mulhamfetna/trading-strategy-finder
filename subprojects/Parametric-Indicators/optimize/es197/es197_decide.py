"""#197 — the frozen adopt/retain decision (docs/WS-ES197-PREREGISTRATION.md §3–4). Server-side.

Per TF: score the INCUMBENT (deployed best ES params) and the FRESH champion (row 0 of the es197b
feasible-Pareto CSV, rebuilt via build_champions_from_pareto) through the exact fold objective on the
corrected box; ADOPT iff fresh median-fold net@$25 > incumbent median-fold net@$25 + incumbent fold SE
AND the fresh full-book passes allowlist criteria 3–5; else RETAIN. For every ADOPT, 20 random COMPLETE
trials from the same study (rng(197)) must sit below the adopted champion (p95) on the same metric.
Outputs: es197b champions JSON (already built), decision JSON, full books for fresh champions.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
PI = HERE.parents[2]
sys.path.insert(0, str(PI))

COST = 25.0
TFS = ("4h", "2h", "1h", "15m", "5m", "2m")


def fold_nets(params: dict, tf: str, df_dec, df1, box, vf, sig_int, bar_td) -> list[float]:
    from optimize import folds as F
    r = F.score_walkforward(df_dec, df1, box, vf, dict(params), bar_td, k=5, min_trades=5,
                            sig_int=sig_int, pv=50.0)
    if not r["valid"]:
        return []
    return [f["pnl"] - COST * f["n_taken"] for f in r["folds"] if "pnl" in f]


def full_book(l1p: dict, tf: str) -> dict:
    from optimize.l2 import payload as P
    view = P.build_view_payload(dict(l1p), P._scaled_permissive("ES"), tf, "l1", instrument="ES")
    tr = view["trades"]
    pnl = [t["pnl"] for t in tr]
    dc = view["meta"]["dropped_counts"]
    n_sig = len(tr) + dc["total"]
    return {"n": len(tr), "gross_per_trade": (sum(pnl) / len(tr)) if tr else 0.0,
            "net25": sum(pnl) - COST * len(tr),
            "entry_rate": len(tr) / n_sig if n_sig else 0.0,
            "trades": tr}


def main() -> None:
    import optuna
    from optimize import data as D, timeframes as TF
    from optimize.fast_engine import signals_to_int
    from optimize import signals as sig_mod
    from optimize.l2 import payload as P

    outdir = Path(os.environ.get("ES197_OUT", "/home/dev/Mulham/wsg-i/es197/decision"))
    outdir.mkdir(parents=True, exist_ok=True)
    inc_all = json.loads((PI / "optimize" / "results" / "best_champions_full_ES.json").read_text())
    fresh_all = json.loads((PI / "optimize" / "results" / "es197b_champions_full_ES.json").read_text())
    storage = os.environ["WSH_STORAGE_URL"]
    rng = np.random.default_rng(197)
    out = {"preregistration": "docs/WS-ES197-PREREGISTRATION.md", "issue": "#197", "cost_rt": COST}

    for tf in TFS:
        df_dec, df1, box, vf, _ = D.load_inputs(tf, instrument="ES")
        sig_int = signals_to_int(sig_mod.decision_signals(df_dec, box))
        bar_td = TF.get(tf).bar_td
        inc_p = P._champion_layer_params(tf, inc_all[tf])
        fr_p = P._champion_layer_params(tf, fresh_all[tf])
        inc_nets = fold_nets(inc_p, tf, df_dec, df1, box, vf, sig_int, bar_td)
        fr_nets = fold_nets(fr_p, tf, df_dec, df1, box, vf, sig_int, bar_td)
        inc_med = float(np.median(inc_nets)) if inc_nets else float("nan")
        fr_med = float(np.median(fr_nets)) if fr_nets else float("nan")
        inc_se = float(np.std(inc_nets, ddof=1) / np.sqrt(len(inc_nets))) if len(inc_nets) > 1 else float("inf")
        fb = full_book(fr_p, tf)
        crit = {"beats_incumbent_by_SE": bool(fr_nets) and fr_med > inc_med + inc_se,
                "gross_2x_friction": fb["gross_per_trade"] >= 2 * COST,
                "full_net25_pos": fb["net25"] > 0,
                "not_gate_dark": fb["entry_rate"] >= 0.05}
        adopt = all(crit.values())
        row = {"tf": tf, "incumbent_fold_nets25": [round(x, 2) for x in inc_nets],
               "fresh_fold_nets25": [round(x, 2) for x in fr_nets],
               "incumbent_median": round(inc_med, 2), "incumbent_fold_se": round(inc_se, 2),
               "fresh_median": round(fr_med, 2), "criteria": crit,
               "fresh_full": {k: round(v, 4) if isinstance(v, float) else v
                              for k, v in fb.items() if k != "trades"},
               "decision": "ADOPT" if adopt else "RETAIN"}
        if adopt:
            study = optuna.load_study(study_name=f"es197b_{tf}_ES", storage=storage)
            done = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
            pick = rng.choice(len(done), size=min(20, len(done)), replace=False)
            ctl = []
            from indicators import library as _lib
            _schema = {key: {pp["name"]: type(pp["default"]) for pp in _lib.SCHEMA[key].get("params", [])}
                       for key in _lib.REGISTRY}

            def _trial_champion(t):
                """Rebuild the trial's FULL config — including its enabled indicators and their params —
                exactly as build_champions_from_pareto does for the real champion (a control with the
                indicator layer stripped would not be the trial that was scored)."""
                inds = {}
                for key, casters in _schema.items():
                    if t.params.get(f"en_{key}"):
                        inds[key] = {pn: caster(t.params[f"{key}_{pn}"]) for pn, caster in casters.items()
                                     if f"{key}_{pn}" in t.params}
                return {"box": {"sl_soft": t.params["sl_soft"],
                                "sl_hard": t.params["sl_soft"] + t.params["sl_hard_delta"],
                                "tp": t.params["tp"], "gate_pct": t.params["gate_pct"], "dd_limit": 0.0,
                                "cooldown": 0, "flip": t.params["flip"], "k": t.params.get("k", 1)},
                        "indicators": inds}

            for i in pick:
                t = done[int(i)]
                p = P._champion_layer_params(tf, _trial_champion(t))
                nets = fold_nets(p, tf, df_dec, df1, box, vf, sig_int, bar_td)
                ctl.append(float(np.median(nets)) if nets else float("nan"))
            ctl = [c for c in ctl if np.isfinite(c)]
            p95 = float(np.percentile(ctl, 95)) if ctl else float("nan")
            row["random_trial_control"] = {"n": len(ctl), "p95": round(p95, 2),
                                           "passes": bool(ctl) and fr_med > p95}
            if not row["random_trial_control"]["passes"]:
                row["decision"] = "RETAIN"
                row["retain_cause"] = "random-trial control not beaten"
        if row["decision"] == "ADOPT":
            import csv as _csv
            bookf = outdir / f"es197b_book_ES_{tf}.csv"
            cols = ["layer", "entry_time", "exit_time", "direction", "entry_price", "exit_price",
                    "exit_reason", "pnl"]
            with open(bookf, "w", newline="") as f:
                w = _csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for t in sorted(fb["trades"], key=lambda r: r["entry_time"]):
                    w.writerow(t)
        out[tf] = row
        print(tf, row["decision"], "| inc med", row["incumbent_median"], "SE", row["incumbent_fold_se"],
              "| fresh med", row["fresh_median"], "| crit", crit,
              "| ctl", row.get("random_trial_control", "-"), flush=True)

    (outdir / "es197_decision.json").write_text(json.dumps(out, indent=1))
    print("->", outdir / "es197_decision.json")


if __name__ == "__main__":
    main()
