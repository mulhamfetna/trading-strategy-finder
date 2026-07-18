#!/usr/bin/env python3
"""Same specialness battery (block-bootstrap + random-veto) on the CANONICAL 2025-26 book,
so the in-sample (canonical) vs OOS (extended 2024-26) contrast is apples-to-apples."""
import sys, numpy as np, pandas as pd
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor-baseline"))
from gate_service import VolGate, _stats
rng = np.random.default_rng(12345)
d = pd.read_csv(HERE / "vendor-baseline" / "nq_gated_book.csv")
pnl = d["pnl"].to_numpy(float); band = d["rel_band"].to_numpy(float)
_g = VolGate(pct=85)  # SINGLE instance so history accumulates (fresh-per-call = always warm-up = 0 vetoes)
keep = np.array([_g.allow(b if np.isfinite(b) else None) for b in band])
base = _stats(pnl); g = _stats(pnl[keep])
print("CANONICAL 2025-26 book (481 trades):")
print(f"  reference Ret/DD {base['ret_dd']:.2f}  gated {g['ret_dd']:.2f}  (DD ${base['dd']:,.0f} -> ${g['dd']:,.0f})")
def blk(n, b=20):
    o = []
    while len(o) < n:
        s = rng.integers(0, n); o.extend(range(s, min(s + b, n)))
    return np.array(o[:n])
dl = []
for _ in range(2000):
    ii = blk(len(pnl)); rb = _stats(pnl[ii]); rg = _stats(pnl[ii][keep[ii]])
    if np.isfinite(rb['ret_dd']) and np.isfinite(rg['ret_dd']): dl.append(rg['ret_dd'] - rb['ret_dd'])
dl = np.array(dl)
print(f"  block-bootstrap: median Delta={np.median(dl):+.2f}  P(gate helps)={100*(dl>0).mean():.0f}%")
nv = int((~keep).sum()); rr = []
for _ in range(2000):
    k = np.ones(len(pnl), bool); k[rng.choice(len(pnl), nv, replace=False)] = False
    s = _stats(pnl[k])
    if np.isfinite(s['ret_dd']): rr.append(s['ret_dd'])
rr = np.array(rr)
print(f"  random-veto: TimesFM {g['ret_dd']:.2f} beats {100*(rr<g['ret_dd']).mean():.0f}% of random vetoes (median {np.median(rr):.2f})")
