#!/usr/bin/env python3
"""Experiment 3b — the REAL second-layer (L2) book (Exp3 follow-up).

Exp3 needed a profitable vol-HURT strategy; the naive mean-reversion had no edge. The mtf fusion book tags
every trade by layer (position_owner = L1 primary 1h / L2 secondary 4h) — a real, profitable second layer.
Test: is L2 vol-hurt (unlike the vol-seeking L1)? If so, does the vol veto HELP it (the Exp3 hypothesis)?

Per layer: condition P/L on the causal HMM regime; apply the p85 vol veto; try the vol size-ramp.

Run:  python3 l2_experiment.py <fusion_log.csv> <NQ_1h.csv>
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/dev/Mulham/regime-hmm")
sys.path.insert(0, "/home/dev/Mulham/tfm-repro/vendor-baseline")
from regime_baseline import daily_features, fit_hmm, bic, filtered_states, TRAIN_END, RESTARTS
from gate_service import VolGate, _stats


def regimes(nq_csv):
    feat = daily_features(nq_csv)
    tr = feat[feat.index < TRAIN_END]; mu, sd = tr.mean(), tr.std()
    Z = ((feat-mu)/sd).to_numpy(); Ztr = ((tr-mu)/sd).to_numpy()
    best = min(((k,)+(lambda x:(x[1],bic(x[1],k,Ztr.shape[1],len(Ztr)),x[0]))(fit_hmm(Ztr,k,RESTARTS)) for k in (2,3,4)), key=lambda z:z[2])
    n, model = best[0], best[3]
    reg,_ = filtered_states(model, Z)
    order = np.argsort(model.means_[:,1]); rank={s:i for i,s in enumerate(order)}
    return n, pd.Series([rank[s] for s in reg], index=feat.index)


def dd(p):
    eq=np.cumsum(p); return float((np.maximum.accumulate(eq)-eq).max()) if len(p) else 0.0


def analyse(name, g, daily_reg, n, nq_rv):
    g = g.sort_values("datetime").reset_index(drop=True)
    pnl = g["pnl"].to_numpy(float)
    reg = g["date"].map(daily_reg).to_numpy()
    base = _stats(pnl)
    print(f"\n=== {name}: n={base['n']} P/L=${base['pnl']:,.0f} DD=${base['dd']:,.0f} Ret/DD={base['ret_dd']:.2f} win={base['win']:.0f}% ===")
    # conditioned on regime (is this layer vol-hurt or vol-seeking?)
    valid = ~np.isnan(reg)
    for r in range(n):
        s = _stats(pnl[valid & (reg == r)])
        if s['n']: print(f"    regime {r} ({'calm' if r==0 else 'turbulent' if r==n-1 else 'mid'}): n={s['n']:>4} Ret/DD={s['ret_dd']:>6.2f} P/L=${s['pnl']:>8,.0f}")
    # vol veto p85 (single VolGate on this layer's entry-day realized vol)
    band = g["date"].map(nq_rv).to_numpy()
    gate = VolGate(pct=85.0)
    keep = np.array([gate.allow(b if np.isfinite(b) else None) for b in band])
    gated = _stats(pnl[keep])
    print(f"    + vol veto p85: Ret/DD {base['ret_dd']:.2f} -> {gated['ret_dd']:.2f}  ({'HELPS' if gated['ret_dd']>base['ret_dd'] else 'HURTS'}, vetoed {len(pnl)-keep.sum()})")
    # vol size-ramp (up in turbulent)
    if valid.any():
        ramp = np.linspace(0.5, 1.5, n)
        sc = np.where(valid, ramp[np.nan_to_num(reg).astype(int)], 1.0) * pnl
        rr = sc.sum()/dd(sc) if dd(sc) else 0
        print(f"    + vol size-ramp: Ret/DD {base['ret_dd']:.2f} -> {rr:.2f}  ({'helps' if rr>base['ret_dd'] else 'hurts'})")


def main():
    log = pd.read_csv(sys.argv[1]); ent = log[log["decision"] == "entry"].copy()
    ent["datetime"] = pd.to_datetime(ent["datetime"]); ent["date"] = ent["datetime"].dt.normalize()
    n, daily_reg = regimes(sys.argv[2])
    # NQ daily realized vol for the veto
    nq = pd.read_csv(sys.argv[2]); nq.columns=[c.strip().lower() for c in nq.columns]
    nq["date"]=pd.to_datetime(nq["datetime"]).dt.normalize(); nq["lr"]=np.log(nq["close"]).diff()
    rv = np.sqrt(nq.groupby("date")["lr"].apply(lambda x: np.nansum(x.values**2)))
    owners = ent["position_owner"].unique() if "position_owner" in ent.columns else ["ALL"]
    print("layers:", list(owners))
    for o in owners:
        g = ent[ent["position_owner"] == o] if o != "ALL" else ent
        analyse(f"layer {o}", g, daily_reg, n, rv)


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
