#!/usr/bin/env python3
"""Stage 3: is the regime signal real? Test the INVERTED policy (sit-out the CALM regime) with a
RANDOM-REGIME CONTROL + per-year, for both the HMM and the Jump Model (prior-art says JM > HMM).

The 'calm' label comes from the model's realized-vol emission ranking (NOT from trade P/L), so
sitting out the calmest regime is an a-priori structural choice; the random control asks whether that
structural choice beats removing the same number of trades at random. Filtered/online (causal) regimes only.

Run:  python3 regime_stage3.py <NQ_1h.csv> <fusion_log.csv>
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, ".")
from regime_baseline import daily_features, fit_hmm, bic, filtered_states, stats, TRAIN_END, RESTARTS
from jumpmodels.jump import JumpModel

RNG = np.random.default_rng(7)


def ranked_regime_hmm(Ztr, Z, n, index):
    rows = [(k,) + fit_hmm(Ztr, k, RESTARTS)[::-1] for k in (n,)]  # fit chosen n
    _, ll, m = rows[0]
    reg, _ = filtered_states(m, Z)
    order = np.argsort(m.means_[:, 1])                       # feature 1 = logrv
    rank = {s: i for i, s in enumerate(order)}
    return pd.Series([rank[s] for s in reg], index=index)


def ranked_regime_jm(Xtr, X, n, index, penalty):
    jm = JumpModel(n_components=n, jump_penalty=penalty, random_state=0, n_init=10)
    jm.fit(Xtr)
    lab = np.asarray(jm.predict_online(X))                   # CAUSAL online labels
    # rank by mean logrv (feature 1) within each label
    means = [X[lab == s, 1].mean() if (lab == s).any() else np.inf for s in range(n)]
    order = np.argsort(means)
    rank = {s: i for i, s in enumerate(order)}
    return pd.Series([rank[s] for s in lab], index=index)


def policy_test(name, daily_reg, ent, pnl, n_states):
    reg = ent["date"].map(daily_reg).to_numpy()
    yr = pd.to_datetime(ent["datetime"]).dt.year.to_numpy()
    base = stats(pnl)
    print(f"\n===== {name} =====")
    for r in range(n_states):
        s = stats(pnl[reg == r])
        print(f"  regime {r}: trades={s['n']:>4} P/L=${s['pnl']:>9,.0f} Ret/DD={s['rdd']:>6.2f} win={s['win']:.0f}%")
    for cut in (1, 2):                                       # sit out the calmest 1, then 2 regimes
        keep = reg >= cut
        s = stats(pnl[keep]); nrem = int((~keep).sum())
        # random control: remove nrem random trades
        rand = []
        for _ in range(2000):
            k = np.ones(len(pnl), bool); k[RNG.choice(len(pnl), nrem, replace=False)] = False
            rr = stats(pnl[k])
            if np.isfinite(rr["rdd"]): rand.append(rr["rdd"])
        rand = np.array(rand)
        beats = 100 * (rand < s["rdd"]).mean()
        # per-year deltas (policy Ret/DD - base Ret/DD, within year)
        peryr = []
        for y in sorted(set(yr)):
            my = yr == y
            b = stats(pnl[my]); g = stats(pnl[my & keep])
            peryr.append(f"{y}:{g['rdd']-b['rdd']:+.2f}")
        print(f"  SIT-OUT calmest {cut}: keep {s['n']} Ret/DD {s['rdd']:.2f} (base {base['rdd']:.2f}, remove {nrem}) | "
              f"beats {beats:.0f}% of random | per-yr Δ {' '.join(peryr)}")


def main():
    feat = daily_features(sys.argv[1])
    tr = feat[feat.index < TRAIN_END]
    mu, sd = tr.mean(), tr.std()
    Z = ((feat - mu) / sd).to_numpy(); Ztr = ((tr - mu) / sd).to_numpy()

    # choose n by BIC (reuse baseline logic quickly)
    best = min(((k,) + (lambda r: (r[1], bic(r[1], k, Ztr.shape[1], len(Ztr)), r[0]))(fit_hmm(Ztr, k, RESTARTS))
                for k in (2, 3, 4)), key=lambda x: x[2])
    n = best[0]; print(f"chosen n_states={n} (BIC)")

    log = pd.read_csv(sys.argv[2]); ent = log[log["decision"] == "entry"].copy()
    ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
    ent = ent[ent["date"].isin(feat.index)]
    pnl = ent["pnl"].to_numpy(float)

    hmm_reg = ranked_regime_hmm(Ztr, Z, n, feat.index)
    policy_test(f"HMM ({n} states)", hmm_reg, ent, pnl, n)
    for pen in (25.0, 50.0):
        jm_reg = ranked_regime_jm(Ztr, Z, n, feat.index, pen)
        policy_test(f"Jump Model ({n} states, penalty {pen})", jm_reg, ent, pnl, n)


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
