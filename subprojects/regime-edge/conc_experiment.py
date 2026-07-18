#!/usr/bin/env python3
"""Experiment 1: NQ concentration as a NON-vol regime signal.

Concentration proxy = QQQ (cap-weight NDX) / QQEW (equal-weight NDX). Rising ratio = mega-caps dominate =
high concentration. Signal = causal 60d z-score of the ratio (uses only past). Label the 2024-26 fusion
trades by concentration tercile (causal), condition P/L, and run per-year + a random-label control. Also a
dumb-control: does concentration separate P/L differently than realized volatility?

Run:  python3 conc_experiment.py <QQQ.json> <QQEW.json> <fusion_log.csv> <NQ_1h.csv>
"""
from __future__ import annotations
import json, sys
import numpy as np
import pandas as pd

RNG = np.random.default_rng(7)


def yahoo_daily(path):
    d = json.load(open(path))["chart"]["result"][0]
    ts = d["timestamp"]; cl = d["indicators"]["quote"][0]["close"]
    s = pd.Series(cl, index=pd.to_datetime(pd.Series(ts), unit="s").dt.normalize())
    return s.dropna()


def dd(p):
    eq = np.cumsum(p); return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0
def stats(p):
    p = np.asarray(p, float); d = dd(p)
    return dict(n=len(p), pnl=p.sum(), dd=d, rdd=(p.sum()/d if d else float("inf")), win=100*(p>0).mean() if len(p) else 0)


def main():
    qqq = yahoo_daily(sys.argv[1]); qqew = yahoo_daily(sys.argv[2])
    df = pd.DataFrame({"qqq": qqq, "qqew": qqew}).dropna()
    df["ratio"] = df["qqq"] / df["qqew"]
    # causal 60d z-score of the concentration ratio
    m = df["ratio"].rolling(60).mean(); s = df["ratio"].rolling(60).std()
    df["cz"] = (df["ratio"] - m) / s
    conc = df["cz"].dropna()
    print(f"concentration series: {len(conc)} days {conc.index.min().date()}..{conc.index.max().date()}")

    # tercile buckets by fixed normal cutoffs (causal: cz uses only past 60d): 0=low, 1=mid, 2=high conc
    def bucket(z): return 0 if z < -0.43 else (2 if z > 0.43 else 1)
    conc_reg = conc.map(bucket)

    # realized-vol regime (dumb control) from NQ 1h daily rv
    nq = pd.read_csv(sys.argv[4]); nq.columns = [c.strip().lower() for c in nq.columns]
    nq["dt"] = pd.to_datetime(nq["datetime"]); nq["date"] = nq["dt"].dt.normalize()
    nq["lr"] = np.log(nq["close"]).diff()
    rv = np.sqrt(nq.groupby("date")["lr"].apply(lambda x: np.nansum(x.values**2)))
    rvz = ((rv - rv.rolling(60).mean()) / rv.rolling(60).std()).dropna()
    rv_reg = rvz.map(bucket)

    log = pd.read_csv(sys.argv[3]); ent = log[log["decision"] == "entry"].copy()
    ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
    ent["conc"] = ent["date"].map(conc_reg); ent["rvr"] = ent["date"].map(rv_reg)
    ent["yr"] = pd.to_datetime(ent["datetime"]).dt.year
    e = ent.dropna(subset=["conc"]); pnl = e["pnl"].to_numpy(float)
    print(f"fusion trades labeled by concentration: {len(e)}/{len(ent)}")

    base = stats(pnl)
    print(f"\nALL: n={base['n']} P/L=${base['pnl']:,.0f} DD=${base['dd']:,.0f} Ret/DD={base['rdd']:.2f}")
    print("\n=== conditioned on CONCENTRATION (0=low/broad .. 2=high/mega-cap) ===")
    for r in (0, 1, 2):
        st = stats(pnl[e["conc"].to_numpy() == r])
        print(f"  conc {r}: trades={st['n']:>4} P/L=${st['pnl']:>9,.0f} Ret/DD={st['rdd']:>6.2f} win={st['win']:.0f}%")
    print("\n=== conditioned on REALIZED VOL (dumb control) ===")
    er = ent.dropna(subset=["rvr"]); pr = er["pnl"].to_numpy(float)
    for r in (0, 1, 2):
        st = stats(pr[er["rvr"].to_numpy() == r])
        print(f"  vol {r}: trades={st['n']:>4} P/L=${st['pnl']:>9,.0f} Ret/DD={st['rdd']:>6.2f}")

    # spread across concentration regimes vs a random-label null (is the separation real?)
    rdds = [stats(pnl[e["conc"].to_numpy() == r])["rdd"] for r in (0, 1, 2)]
    real_spread = np.nanmax(rdds) - np.nanmin(rdds)
    null = []
    lab = e["conc"].to_numpy()
    for _ in range(2000):
        sh = RNG.permutation(lab)
        v = [stats(pnl[sh == r])["rdd"] for r in (0, 1, 2)]
        null.append(np.nanmax(v) - np.nanmin(v))
    null = np.array(null)
    print(f"\n=== is the concentration separation real? ===")
    print(f"  Ret/DD spread across conc regimes = {real_spread:.2f}; random-label null median {np.median(null):.2f}; "
          f"real beats {100*(null < real_spread).mean():.0f}% of shuffles  (>95% => real signal)")
    print("\n=== per-year: worst concentration regime's P/L share ===")
    for y in sorted(e["yr"].unique()):
        ey = e[e["yr"] == y]; py = ey["pnl"].to_numpy(float)
        by = [stats(py[ey["conc"].to_numpy() == r])["pnl"] for r in (0, 1, 2)]
        print(f"  {y}: P/L by conc regime [low,mid,high] = {[f'${x:,.0f}' for x in by]}")


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
