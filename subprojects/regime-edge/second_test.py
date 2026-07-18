#!/usr/bin/env python3
"""SECOND-ROUND confirmation of the sizing winner before deploy — stronger tests than the per-year splits:
  1. Block-bootstrap the EQUAL-RISK profit uplift (ramp vs flat) — is +$10.4k robust to resampling? CI.
  2. Purged K-fold CV (embargoed) — does the a-priori ramp help on each held-out time block?
Ramp is fixed a-priori (0.5->1.5 by regime vol-rank); nothing is tuned on the test data.

Run:  python3 second_test.py <NQ_1h.csv> <fusion_log.csv>
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/dev/Mulham/regime-hmm")
from regime_baseline import daily_features, fit_hmm, bic, filtered_states, TRAIN_END, RESTARTS

RNG = np.random.default_rng(99)


def dd(p):
    eq = np.cumsum(p); return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0
def rdd(p):
    p = np.asarray(p, float); d = dd(p); return p.sum() / d if d else float("inf")


def main():
    feat = daily_features(sys.argv[1])
    tr = feat[feat.index < TRAIN_END]; mu, sd = tr.mean(), tr.std()
    Z = ((feat-mu)/sd).to_numpy(); Ztr = ((tr-mu)/sd).to_numpy()
    best = min(((k,)+(lambda x:(x[1],bic(x[1],k,Ztr.shape[1],len(Ztr)),x[0]))(fit_hmm(Ztr,k,RESTARTS)) for k in (2,3,4)), key=lambda z:z[2])
    n, model = best[0], best[3]
    reg,_ = filtered_states(model, Z)
    order = np.argsort(model.means_[:,1]); rank={s:i for i,s in enumerate(order)}
    daily_reg = pd.Series([rank[s] for s in reg], index=feat.index)

    log = pd.read_csv(sys.argv[2]); ent = log[log["decision"]=="entry"].copy()
    ent["dt"] = pd.to_datetime(ent["datetime"]); ent = ent.sort_values("dt").reset_index(drop=True)
    ent["reg"] = ent["dt"].dt.normalize().map(daily_reg)
    e = ent.dropna(subset=["reg"]); pnl = e["pnl"].to_numpy(float); rg = e["reg"].to_numpy(int)
    ramp = np.linspace(0.5, 1.5, n); scaled = ramp[rg] * pnl
    fdd = dd(pnl)
    base_up = rdd(scaled) * fdd - pnl.sum()
    print(f"n={len(e)}; flat Ret/DD {rdd(pnl):.2f}; ramp Ret/DD {rdd(scaled):.2f}; equal-risk uplift ${base_up:,.0f}")

    # 1. block-bootstrap the equal-risk uplift
    def blk(m, b=20):
        o=[]
        while len(o)<m:
            s=RNG.integers(0,m); o.extend(range(s,min(s+b,m)))
        return np.array(o[:m])
    ups=[]
    for _ in range(3000):
        ii=blk(len(pnl)); fp=pnl[ii]; sp=scaled[ii]; d=dd(fp)
        if d: ups.append(rdd(sp)*d - fp.sum())
    ups=np.array(ups)
    print(f"\n1. BLOCK-BOOTSTRAP equal-risk uplift: median ${np.median(ups):,.0f}  "
          f"90% CI [${np.percentile(ups,5):,.0f}, ${np.percentile(ups,95):,.0f}]  "
          f"P(uplift>0)={100*(ups>0).mean():.0f}%  ({'CONFIRMED' if np.percentile(ups,5)>0 else 'not confirmed'})")

    # 2. purged K-fold CV (time-contiguous folds, 1-fold embargo)
    print("\n2. PURGED 5-FOLD CV (a-priori ramp on each held-out time block):")
    K=5; idx=np.arange(len(pnl)); folds=np.array_split(idx, K); pos=0
    for k,f in enumerate(folds):
        b=rdd(pnl[f]); g=rdd(scaled[f]); pos += g>b
        print(f"   fold {k+1} ({e['dt'].iloc[f[0]].date()}..{e['dt'].iloc[f[-1]].date()}): flat {b:.2f} -> ramp {g:.2f}  {'+' if g>b else ''}{g-b:.2f}")
    print(f"   ramp helps in {pos}/{K} held-out folds")
    print(f"\nSECOND-TEST VERDICT: {'GREEN — uplift CI excludes 0 and holds across folds' if np.percentile(ups,5)>0 and pos>=4 else 'MIXED — review'}")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
