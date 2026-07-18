#!/usr/bin/env python3
"""Experiment 2: SIZING not veto. Reuse the causal HMM regime; scale each fusion trade's P/L by an
A-PRIORI per-regime multiplier (downsize calm, upsize turbulent — the strategy's edge is in vol).
Compare vs flat sizing and vs classic vol-targeting; run a RANDOM-MULTIPLIER control + per-year.

A-priori (not tuned on P/L) => no selection overfit; the test is whether regime-scaling beats flat AND
beats a random assignment of the same multipliers. Max-DD scales with size — computed honestly on the
scaled equity curve.

Run:  python3 sizing_experiment.py <NQ_1h.csv> <fusion_log.csv>
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/dev/Mulham/regime-hmm")
from regime_baseline import daily_features, fit_hmm, bic, filtered_states, TRAIN_END, RESTARTS

RNG = np.random.default_rng(11)


def dd(p):
    eq = np.cumsum(p); return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0
def rdd(p):
    p = np.asarray(p, float); d = dd(p); return p.sum() / d if d else float("inf")


def main():
    feat = daily_features(sys.argv[1])
    tr = feat[feat.index < TRAIN_END]; mu, sd = tr.mean(), tr.std()
    Z = ((feat - mu) / sd).to_numpy(); Ztr = ((tr - mu) / sd).to_numpy()
    # BIC pick
    best = min(((k,) + (lambda r: (r[1], bic(r[1], k, Ztr.shape[1], len(Ztr)), r[0]))(fit_hmm(Ztr, k, RESTARTS))
                for k in (2, 3, 4)), key=lambda x: x[2])
    n, model = best[0], best[3]
    reg, _ = filtered_states(model, Z)
    order = np.argsort(model.means_[:, 1]); rank = {s: i for i, s in enumerate(order)}
    daily_reg = pd.Series([rank[s] for s in reg], index=feat.index)

    log = pd.read_csv(sys.argv[2]); ent = log[log["decision"] == "entry"].copy()
    ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
    ent["reg"] = ent["date"].map(daily_reg); ent["yr"] = pd.to_datetime(ent["datetime"]).dt.year
    e = ent.dropna(subset=["reg"]); pnl = e["pnl"].to_numpy(float); rg = e["reg"].to_numpy(int)
    print(f"n_states={n}; trades labeled {len(e)}")

    # a-priori linear size ramp: calmest -> 0.5x, most turbulent -> 1.5x
    ramp = np.linspace(0.5, 1.5, n)
    scaled = ramp[rg] * pnl
    flat = pnl
    print(f"\nFLAT sizing:         P/L=${flat.sum():,.0f} DD=${dd(flat):,.0f} Ret/DD={rdd(flat):.2f}")
    print(f"REGIME ramp (0.5->1.5): P/L=${scaled.sum():,.0f} DD=${dd(scaled):,.0f} Ret/DD={rdd(scaled):.2f}")

    # classic vol-targeting dumb control: size ∝ 1/realized_vol at entry day (normalized to mean 1)
    rvmap = feat["logrv"]  # log realized vol per day
    inv = 1.0 / np.exp(e["date"].map(rvmap).to_numpy())
    inv = inv / np.nanmean(inv)
    vt = inv * pnl
    print(f"VOL-TARGET (1/rv):   P/L=${vt.sum():,.0f} DD=${dd(vt):,.0f} Ret/DD={rdd(vt):.2f}")

    # random-multiplier control: assign the SAME ramp multipliers to shuffled regimes
    real = rdd(scaled); null = []
    for _ in range(2000):
        perm = RNG.permutation(ramp)          # same multipliers, random regime->mult mapping
        null.append(rdd(perm[rg] * pnl))
    null = np.array(null)
    print(f"\nRANDOM-MULTIPLIER control: regime ramp Ret/DD {real:.2f} beats {100*(null < real).mean():.0f}% "
          f"of random assignments (median {np.median(null):.2f})  (>95% => real)")

    print("\nper-year Ret/DD  flat -> regime-ramp:")
    for y in sorted(e["yr"].unique()):
        m = e["yr"].to_numpy() == y
        print(f"  {y}: {rdd(flat[m]):.2f} -> {rdd(scaled[m]):.2f}")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
