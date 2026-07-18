#!/usr/bin/env python3
"""Experiment 1b — CLEANER concentration test (Exp1 follow-up).

Exp1's max-min spread control was too noisy (unequal buckets). Cleaner:
  1. Direct significance on the HIGH-vs-LOW concentration gap in per-trade mean P/L — a permutation test
     (shuffle labels) + a bootstrap CI. Per-trade mean P/L is stable where Return/DD is not.
  2. Concentration as a SIZING signal (the now-promoted framing): ramp size by concentration tercile,
     equal-risk P/L uplift + random control.
  3. Does concentration ADD to the vol size-ramp? (It's orthogonal to volatility.) Combined vol x conc.

Run:  python3 conc_clean.py <QQQ.json> <QQEW.json> <fusion_log.csv> <NQ_1h.csv>
"""
from __future__ import annotations
import json, sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/dev/Mulham/regime-hmm")
from regime_baseline import daily_features, fit_hmm, bic, filtered_states, TRAIN_END, RESTARTS

RNG = np.random.default_rng(31)


def yahoo_daily(path):
    d = json.load(open(path))["chart"]["result"][0]
    s = pd.Series(d["indicators"]["quote"][0]["close"],
                  index=pd.to_datetime(pd.Series(d["timestamp"]), unit="s").dt.normalize())
    return s.dropna()
def dd(p):
    eq = np.cumsum(p); return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0
def rdd(p):
    p = np.asarray(p, float); d = dd(p); return p.sum() / d if d else float("inf")


def main():
    qqq, qqew = yahoo_daily(sys.argv[1]), yahoo_daily(sys.argv[2])
    df = pd.DataFrame({"qqq": qqq, "qqew": qqew}).dropna()
    ratio = df["qqq"] / df["qqew"]
    cz = ((ratio - ratio.rolling(60).mean()) / ratio.rolling(60).std()).dropna()
    conc = cz.map(lambda z: 0 if z < -0.43 else (2 if z > 0.43 else 1))

    _, hmm = (lambda: (lambda n, s: (n, s))(*_regimes(sys.argv[4])))()

    log = pd.read_csv(sys.argv[3]); ent = log[log["decision"] == "entry"].copy()
    ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
    ent["c"] = ent["date"].map(conc); ent["r"] = ent["date"].map(hmm)
    e = ent.dropna(subset=["c", "r"]); pnl = e["pnl"].to_numpy(float)
    c = e["c"].to_numpy(int); r = e["r"].to_numpy(int)
    print(f"trades {len(e)}; flat P/L=${pnl.sum():,.0f} Ret/DD={rdd(pnl):.2f}")

    # 1. HIGH vs LOW concentration — per-trade mean P/L gap, permutation p + bootstrap CI
    hi, lo = pnl[c == 2], pnl[c == 0]
    gap = hi.mean() - lo.mean()
    perm = np.array([(lambda s: pnl[s == 2].mean() - pnl[s == 0].mean())(RNG.permutation(c)) for _ in range(3000)])
    p_perm = (np.abs(perm) >= abs(gap)).mean()
    boot = np.array([RNG.choice(hi, len(hi)).mean() - RNG.choice(lo, len(lo)).mean() for _ in range(3000)])
    print(f"\n=== 1. HIGH(mega-cap) vs LOW(broad) per-trade mean P/L ===")
    print(f"  high ${hi.mean():,.0f}/trade (n={len(hi)}) vs low ${lo.mean():,.0f}/trade (n={len(lo)}) => gap ${gap:,.0f}")
    print(f"  permutation p={p_perm:.3f}  bootstrap 90% CI [${np.percentile(boot,5):,.0f}, ${np.percentile(boot,95):,.0f}]  "
          f"({'SIGNIFICANT' if p_perm<0.05 and np.percentile(boot,5)>0 else 'not significant'})")

    # 2. concentration SIZING (equal-risk) + random control
    fdd = dd(pnl); ramp = np.linspace(0.5, 1.5, 3)
    cs = ramp[c] * pnl; r_cs = rdd(cs)
    null = np.array([rdd(RNG.permutation(ramp)[c] * pnl) for _ in range(2000)])
    print(f"\n=== 2. concentration SIZING (0.5->1.5 by tercile) ===")
    print(f"  Ret/DD {rdd(pnl):.2f} -> {r_cs:.2f}; EQUAL-RISK P/L ${r_cs*fdd:,.0f} (+${r_cs*fdd-pnl.sum():,.0f}); "
          f"beats {100*(null<r_cs).mean():.0f}% of random")

    # 3. does concentration ADD to the vol ramp?
    vramp = np.linspace(0.5, 1.5, int(r.max())+1)
    vs = vramp[r] * pnl; r_vs = rdd(vs)
    comb = vramp[r] * ramp[c] * pnl; r_comb = rdd(comb)
    print(f"\n=== 3. vol-ramp vs vol x concentration ===")
    print(f"  vol only:      Ret/DD {r_vs:.2f}  EQUAL-RISK P/L ${r_vs*fdd:,.0f}")
    print(f"  vol x conc:    Ret/DD {r_comb:.2f}  EQUAL-RISK P/L ${r_comb*fdd:,.0f}  "
          f"({'conc ADDS' if r_comb>r_vs else 'conc does not add'})")


def _regimes(nq_csv):
    feat = daily_features(nq_csv)
    tr = feat[feat.index < TRAIN_END]; mu, sd = tr.mean(), tr.std()
    Z = ((feat-mu)/sd).to_numpy(); Ztr = ((tr-mu)/sd).to_numpy()
    best = min(((k,)+(lambda x:(x[1],bic(x[1],k,Ztr.shape[1],len(Ztr)),x[0]))(fit_hmm(Ztr,k,RESTARTS)) for k in (2,3,4)), key=lambda z:z[2])
    n, model = best[0], best[3]
    reg,_ = filtered_states(model, Z)
    order = np.argsort(model.means_[:,1]); rank={s:i for i,s in enumerate(order)}
    return n, pd.Series([rank[s] for s in reg], index=feat.index)


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
