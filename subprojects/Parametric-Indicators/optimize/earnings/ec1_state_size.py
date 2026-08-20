#!/usr/bin/env python3
"""E-C1 — earnings × indicators. Implements docs/EC1-PREREGISTRATION.md (frozen).

Does the 165-stance vector add SIZE information beyond P_hist? Ridge + depth-3 tree on
[pred, stances] vs the P_hist baseline; locked holdouts (NQ<2023 train, NQ>=2023 one look,
ES untouched); stance-permutation control.

    python3 optimize/earnings/ec1_state_size.py
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SPLIT = pd.Timestamp("2023-01-01")
N_BOOT, N_PERM, SEED = 10000, 20, 20260820


def load(inst: str) -> pd.DataFrame:
    d = pd.read_csv(HERE / "data" / f"es1_event_state_{inst}.csv", parse_dates=["et"])
    return d.dropna(subset=["pred", "jump_pct"]).sort_values("et").reset_index(drop=True)


def rho(a, b) -> float:
    from scipy import stats
    return float(stats.spearmanr(a, b)[0])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "data"))
    a = ap.parse_args()
    from sklearn.linear_model import Ridge
    from sklearn.tree import DecisionTreeRegressor
    rng = np.random.default_rng(SEED)
    print(f"[E-C1] pre-reg docs/EC1-PREREGISTRATION.md · split {SPLIT.date()} · "
          f"N_PERM={N_PERM} SEED={SEED}", flush=True)

    nq = load("NQ")
    es = load("ES")
    cols = [c for c in nq.columns if c.startswith(("cdir_", "vdir_"))]
    tr = nq[nq.et < SPLIT]
    h1 = nq[nq.et >= SPLIT]
    keep = [c for c in cols if tr[c].nunique() > 1]
    print(f"[E-C1] NQ train {len(tr)} · holdout1 {len(h1)} · ES holdout2 {len(es)} · "
          f"features 1+{len(keep)}", flush=True)

    def X(d):
        return np.c_[d.pred.to_numpy(float), d[keep].to_numpy(float)]

    ytr = tr.jump_pct.to_numpy(float)
    base_h1 = rho(h1.pred, h1.jump_pct)
    base_h2 = rho(es.pred, es.jump_pct)
    models = {"ridge": Ridge(alpha=1.0),
              "tree_d3": DecisionTreeRegressor(max_depth=3, min_samples_leaf=20,
                                               random_state=SEED)}
    res = {"n_train": int(len(tr)), "n_h1": int(len(h1)), "n_h2": int(len(es)),
           "n_features": 1 + len(keep),
           "baseline_rho": {"h1": round(base_h1, 4), "h2": round(base_h2, 4)},
           "models": {}}
    for name, mdl in models.items():
        mdl.fit(X(tr), ytr)
        p_h1 = mdl.predict(X(h1))
        r_h1 = rho(p_h1, h1.jump_pct)
        delta = r_h1 - base_h1
        # event bootstrap of the delta on H1
        jh = h1.jump_pct.to_numpy(float)
        ph = h1.pred.to_numpy(float)
        boots = []
        for _ in range(N_BOOT):
            ii = rng.integers(0, len(jh), len(jh))
            boots.append(rho(p_h1[ii], jh[ii]) - rho(ph[ii], jh[ii]))
        ci = [round(float(np.percentile(boots, 5)), 4),
              round(float(np.percentile(boots, 95)), 4)]
        # stance-permutation control
        perms = []
        for s in range(N_PERM):
            r2 = np.random.default_rng(SEED + 1 + s)
            Xp = np.c_[tr.pred.to_numpy(float),
                       tr[keep].to_numpy(float)[r2.permutation(len(tr))]]
            m2 = models[name].__class__(**models[name].get_params())
            m2.fit(Xp, ytr)
            Xh = np.c_[h1.pred.to_numpy(float),
                       h1[keep].to_numpy(float)[r2.permutation(len(h1))]]
            perms.append(rho(m2.predict(Xh), jh) - base_h1)
        p95 = float(np.percentile(perms, 95))
        d_h2 = rho(mdl.predict(X(es)), es.jump_pct) - base_h2
        armed = delta > 0 and ci[0] > 0 and delta > p95 and d_h2 > 0
        verdict = "ARMED" if armed else "CLOSED-NULL"
        sd = float(np.std(boots, ddof=1))
        res["models"][name] = {"rho_h1": round(r_h1, 4), "delta_h1": round(delta, 4),
                               "delta_ci90": ci, "perm_p95": round(p95, 4),
                               "delta_h2": round(d_h2, 4),
                               "mde": round(1.645 * sd, 4), "verdict": verdict}
        m = res["models"][name]
        print(f"[E-C1] {name}: H1 rho {m['rho_h1']} (base {res['baseline_rho']['h1']}) "
              f"Δ {m['delta_h1']:+.4f} CI {ci} perm95 {m['perm_p95']:+.4f} · H2 Δ "
              f"{m['delta_h2']:+.4f} -> {verdict}", flush=True)

    res["verdict"] = ("ARMED" if any(v["verdict"] == "ARMED"
                                     for v in res["models"].values()) else "CLOSED-NULL")
    (Path(a.out) / "ec1_result.json").write_text(json.dumps(res, indent=2))
    print(f"[E-C1] FINAL VERDICT {res['verdict']} -> ec1_result.json", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
