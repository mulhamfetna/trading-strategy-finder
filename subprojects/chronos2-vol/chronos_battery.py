#!/usr/bin/env python3
"""Chronos-2 vol-gate battery + A/B vs TimesFM, on the SAME 2024-26 fusion book.

Reuses the TimesFM VolGate (single stateful instance!) and the same causal p85 rule. Runs: headline,
per-year, threshold sweep, block-bootstrap P(helps), random-veto control, gated-DD tell — for the Chronos
band — and prints TimesFM's numbers on the same book side-by-side, plus band correlations.

Run:  python3 chronos_battery.py <chronos_band.csv> <fusion_log.csv> <timesfm_band.csv>
"""
from __future__ import annotations
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/dev/Mulham/tfm-repro/vendor-baseline")
from gate_service import VolGate, _stats

RNG = np.random.default_rng(12345)


def entry_bands(book, band_csv):
    ent = book.copy()
    b = pd.read_csv(band_csv); b["datetime"] = pd.to_datetime(b["datetime"])
    idx = {t: k for k, t in enumerate(b["datetime"])}
    rel = b["rel_band"].to_numpy(float)
    out = np.full(len(ent), np.nan)
    for i, t in enumerate(ent["datetime"]):
        k = idx.get(t)
        if k is not None and k - 1 >= 0 and np.isfinite(rel[k - 1]):
            out[i] = rel[k - 1]
    return out


def gate_keep(bands, pct):
    g = VolGate(pct=pct)
    return np.array([g.allow(b if np.isfinite(b) else None) for b in bands])


def battery(name, pnl, bands, yr):
    base = _stats(pnl)
    keep = gate_keep(bands, 85.0); g = _stats(pnl[keep])
    print(f"\n=== {name} ===")
    print(f"  reference   n={base['n']} P/L=${base['pnl']:,.0f} DD=${base['dd']:,.0f} Ret/DD={base['rdd'] if False else base['ret_dd']:.2f}")
    print(f"  p85 gate    n={g['n']} P/L=${g['pnl']:,.0f} DD=${g['dd']:,.0f} Ret/DD={g['ret_dd']:.2f}  (vetoed {len(pnl)-keep.sum()})")
    # per-year
    py = []
    for y in sorted(set(yr)):
        m = yr == y; b = _stats(pnl[m]); gg = _stats(pnl[m & keep])
        py.append(f"{y}:{b['ret_dd']:.2f}->{gg['ret_dd']:.2f}")
    print("  per-year Ret/DD:", "  ".join(py))
    # threshold sweep
    print("  thresholds:", "  ".join(f"p{p}:{_stats(pnl[gate_keep(bands,float(p))])['ret_dd']:.2f}" for p in (75,80,85,90)))
    # block-bootstrap
    def blk(n, bl=20):
        o=[]
        while len(o)<n:
            s=RNG.integers(0,n); o.extend(range(s,min(s+bl,n)))
        return np.array(o[:n])
    dl=[]
    for _ in range(2000):
        ii=blk(len(pnl)); rb=_stats(pnl[ii]); rg=_stats(pnl[ii][keep[ii]])
        if np.isfinite(rb['ret_dd']) and np.isfinite(rg['ret_dd']): dl.append(rg['ret_dd']-rb['ret_dd'])
    dl=np.array(dl)
    # random veto
    nv=int((~keep).sum()); rr=[]
    for _ in range(2000):
        k=np.ones(len(pnl),bool); k[RNG.choice(len(pnl),nv,replace=False)]=False
        s=_stats(pnl[k])
        if np.isfinite(s['ret_dd']): rr.append(s['ret_dd'])
    rr=np.array(rr)
    print(f"  block-bootstrap P(helps)={100*(dl>0).mean():.0f}%  |  beats {100*(rr<g['ret_dd']).mean():.0f}% of random vetoes")
    return keep


def main():
    chronos_csv, book_csv, tfm_csv = sys.argv[1], sys.argv[2], sys.argv[3]
    log = pd.read_csv(book_csv); ent = log[log["decision"]=="entry"].copy()
    ent["datetime"]=pd.to_datetime(ent["datetime"]); ent=ent.sort_values("datetime").reset_index(drop=True)
    pnl=ent["pnl"].to_numpy(float); yr=ent["datetime"].dt.year.to_numpy()
    cb=entry_bands(ent, chronos_csv); tb=entry_bands(ent, tfm_csv)
    print(f"entries {len(ent)}  chronos-band mapped {np.isfinite(cb).sum()}  timesfm-band mapped {np.isfinite(tb).sum()}")
    v=np.isfinite(cb)&np.isfinite(tb)
    print(f"corr(chronos band, timesfm band) = {np.corrcoef(cb[v],tb[v])[0,1]:.2f}")
    battery("Chronos-2 p85", pnl, cb, yr)
    battery("TimesFM p85 (A/B on same book)", pnl, tb, yr)


if __name__ == "__main__":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
