#!/usr/bin/env python3
"""FU-6 (#158) — per-event outcome prediction. Implements docs/FU6-PREREGISTRATION.md.

Locked-holdout exploration: fixed logistic (L2, C=1) + fixed depth-3 tree on the FU-9 stance
vector; TRAIN = NQ <2022; HOLDOUT-1 = NQ >=2022; HOLDOUT-2 = ES/RTY/YM. One look each.

    python3 optimize/fundamentals/fu6_outcome_model.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
LEGS = {"NQ": ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"],
        "RTY": ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"],
        "ES": ["Inflation Rate MoM"], "YM": ["Inflation Rate MoM"]}
SPLIT = pd.Timestamp("2022-01-01")
N_BOOT, N_SHUF, SEED, AUC_BAR = 10000, 20, 20260820, 0.58


def load_leg(inst: str) -> pd.DataFrame:
    d = pd.read_csv(HERE / f"fu9_event_state_{inst}.csv", parse_dates=["et"])
    d = d[d.title.isin(LEGS[inst])].dropna(subset=["ride_net_stressed_usd"])
    return d.sort_values("et").reset_index(drop=True)


def auc(y: np.ndarray, p: np.ndarray) -> float:
    from sklearn.metrics import roc_auc_score
    return float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    rng = np.random.default_rng(SEED)
    print(f"[FU-6] pre-reg docs/FU6-PREREGISTRATION.md · split {SPLIT.date()} · AUC bar "
          f"{AUC_BAR} · N_SHUF={N_SHUF} SEED={SEED}", flush=True)

    frames = {i: load_leg(i) for i in LEGS}
    nq = frames["NQ"]
    cols = [c for c in nq.columns if c.startswith(("cdir_", "vdir_"))]
    tr = nq[nq.et < SPLIT]
    h1 = nq[nq.et >= SPLIT]
    keep = [c for c in cols if tr[c].nunique() > 1]      # train-slice variance filter ONLY
    Xtr = tr[keep].to_numpy(float)
    ytr = (tr.ride_net_stressed_usd > 0).to_numpy()
    Xh1 = h1[keep].to_numpy(float)
    yh1 = (h1.ride_net_stressed_usd > 0).to_numpy()
    print(f"[FU-6] NQ train {len(tr)} (win {ytr.mean():.1%}) · holdout1 {len(h1)} "
          f"(win {yh1.mean():.1%}) · features {len(keep)}/{len(cols)}", flush=True)

    models = {
        "logistic": LogisticRegression(penalty="l2", C=1.0, solver="saga", max_iter=2000),
        "tree_d3": DecisionTreeClassifier(max_depth=3, min_samples_leaf=20,
                                          random_state=SEED),
    }
    res = {"n_train": int(len(tr)), "n_holdout1": int(len(h1)),
           "n_features": int(len(keep)), "models": {}}
    for name, mdl in models.items():
        mdl.fit(Xtr, ytr)
        p_tr = mdl.predict_proba(Xtr)[:, 1]
        p_h1 = mdl.predict_proba(Xh1)[:, 1]
        a_tr, a_h1 = auc(ytr, p_tr), auc(yh1, p_h1)
        thr = float(np.median(p_tr))
        top = h1.ride_net_stressed_usd.to_numpy()[p_h1 > thr]
        bot = h1.ride_net_stressed_usd.to_numpy()[p_h1 <= thr]
        if len(top) >= 10 and len(bot) >= 10:
            diff = float(top.mean() - bot.mean())
            boots = [top[rng.integers(0, len(top), len(top))].mean()
                     - bot[rng.integers(0, len(bot), len(bot))].mean()
                     for _ in range(N_BOOT)]
            ci = [round(float(np.percentile(boots, 5)), 2),
                  round(float(np.percentile(boots, 95)), 2)]
        else:
            diff, ci = float("nan"), [None, None]
        shuf = []
        for s in range(N_SHUF):
            r2 = np.random.default_rng(SEED + 1 + s)
            m2 = models[name].__class__(**models[name].get_params())
            m2.fit(Xtr, r2.permutation(ytr))
            shuf.append(auc(yh1, m2.predict_proba(Xh1)[:, 1]))
        shuf95 = float(np.percentile(shuf, 95))
        h2 = {}
        for i in ("ES", "RTY", "YM"):
            d2 = frames[i]
            X2 = d2.reindex(columns=keep, fill_value=0).to_numpy(float)
            y2 = (d2.ride_net_stressed_usd > 0).to_numpy()
            h2[i] = round(auc(y2, mdl.predict_proba(X2)[:, 1]), 4)
        agree = sum(1 for v in h2.values() if np.isfinite(v) and v > 0.5)
        armed = (np.isfinite(a_h1) and a_h1 >= AUC_BAR and a_h1 > shuf95
                 and ci[0] is not None and ci[0] > 0 and agree >= 2)
        verdict = "ARMED" if armed else "CLOSED-NULL"
        res["models"][name] = {"auc_train": round(a_tr, 4), "auc_holdout1": round(a_h1, 4),
                               "shuffle_p95_auc": round(shuf95, 4),
                               "money_top_minus_bottom": (round(diff, 2)
                                                          if np.isfinite(diff) else None),
                               "money_ci90": ci, "auc_holdout2": h2,
                               "h2_above_half": agree, "verdict": verdict}
        m = res["models"][name]
        print(f"[FU-6] {name}: AUC train {m['auc_train']} · H1 {m['auc_holdout1']} "
              f"(shuf95 {m['shuffle_p95_auc']}) · money Δ {m['money_top_minus_bottom']} "
              f"CI {m['money_ci90']} · H2 {h2} ({agree}/3 >0.5) -> {verdict}", flush=True)

    res["verdict"] = ("ARMED" if any(v["verdict"] == "ARMED"
                                     for v in res["models"].values()) else "CLOSED-NULL")
    (Path(a.out) / "fu6_result.json").write_text(json.dumps(res, indent=2))
    print(f"[FU-6] FINAL VERDICT {res['verdict']} -> fu6_result.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
