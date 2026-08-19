#!/usr/bin/env python3
"""FU-13 (#165) — the deployment battery for the Exp2 size-WITH-vol ramp.

Implements the pre-registered stages of docs/FU13-FU14-PREREGISTRATION.md:
  R  reproduce the deploy-card numbers on the original NQ book (exact)
  X  the independent ES book: the SAME a-priori ramp must show uplift > 0
  M  pooled NQ+ES equal-risk uplift: 90% bootstrap CI must exclude 0 (plus the
     random-map ranking, reported)

    python3 fu13_battery.py <nq_book.csv> <nq_regime.csv> <es_book.csv> <es_regime.csv>

Outputs fu13_result.json beside this file. The DEPLOY rule consumes the verdict.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_regime_sizing import apply_overlay, dd   # noqa: E402

RNG = np.random.default_rng(0)


def eq_risk_series(book: pd.DataFrame, regime: pd.DataFrame):
    flat, scaled, _ = apply_overlay(book, regime, True, 0.5, 1.5)
    return np.asarray(flat, float), np.asarray(scaled, float)


def random_map_rank(book: pd.DataFrame, regime: pd.DataFrame, n_maps: int = 1000):
    ent = book[book["decision"] == "entry"].copy()
    ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
    reg = regime.copy()
    reg["date"] = pd.to_datetime(reg["date"])
    m = ent.merge(reg, on="date", how="left").dropna(subset=["regime"])
    pnl = m["pnl"].to_numpy(float)
    regimes = m["regime"].to_numpy(int)
    ramp = np.linspace(0.5, 1.5, int(regimes.max()) + 1)

    def delta(mult):
        sc = pnl * mult[regimes]
        k = dd(pnl) / dd(sc) if dd(sc) else 1.0
        return float((sc * k).sum() - pnl.sum())

    real = delta(ramp)
    rand = [delta(RNG.permutation(ramp)) for _ in range(n_maps)]
    return real, float(100 * np.mean([r < real for r in rand])), float(np.median(rand))


def main() -> int:
    nq_b, nq_r, es_b, es_r = (pd.read_csv(p) for p in sys.argv[1:5])
    nqf, nqs = eq_risk_series(nq_b, nq_r)
    esf, ess = eq_risk_series(es_b, es_r)
    d_nq, d_es = float(nqs.sum() - nqf.sum()), float(ess.sum() - esf.sum())

    # R: the deploy-card expectations (pre-registered)
    r_ok = bool(abs(nqf.sum() - 151872) < 1 and abs(nqs.sum() - 162228) < 1)
    # X: independent-book direction
    x_ok = bool(d_es > 0)
    # M: pooled bootstrap
    pool = np.concatenate([nqs - nqf, ess - esf])
    sims = [RNG.choice(pool, len(pool)).sum() for _ in range(10_000)]
    ci = (float(np.percentile(sims, 5)), float(np.percentile(sims, 95)))
    m_ok = bool(ci[0] > 0)
    es_real, es_pctile, es_rand_med = random_map_rank(es_b, es_r)

    verdict = "DEPLOY" if (r_ok and x_ok and m_ok) else "NOT-DEPLOYED"
    res = {"prereg": "docs/FU13-FU14-PREREGISTRATION.md",
           "R": {"nq_flat_total": round(float(nqf.sum()), 2),
                 "nq_ramp_total": round(float(nqs.sum()), 2), "pass": r_ok},
           "X": {"es_uplift": round(d_es, 2), "pass": x_ok},
           "M": {"nq_uplift": round(d_nq, 2), "pooled_uplift": round(d_nq + d_es, 2),
                 "ci90": [round(c, 2) for c in ci], "pass": m_ok},
           "es_random_maps": {"real_delta": round(es_real, 2),
                              "percentile_of_1000": es_pctile,
                              "random_median": round(es_rand_med, 2)},
           "verdict": verdict}
    Path(__file__).with_name("fu13_result.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
