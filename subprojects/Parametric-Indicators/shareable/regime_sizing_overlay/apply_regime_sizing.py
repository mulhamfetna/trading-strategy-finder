#!/usr/bin/env python3
"""EXPERIMENTAL regime size-ramp overlay for the backtesting system — OFF BY DEFAULT (golden-safe).

  ⚠️  EXPERIMENTAL CANDIDATE — NOT a confirmed edge.
  Signal is real (regime ordering beats 96% of random, helps 4/5 purged folds) but the dollar magnitude
  is UNCONFIRMED on the n=1 (2024-26) book (bootstrap 90% CI [-$21k,+$61k] includes zero). See
  docs/SECOND_TEST.md. Do NOT treat its output as a proven improvement.

Applies, per trade, a size multiplier = linear ramp by the day's causal HMM regime vol-rank
(calmest LO x -> most turbulent HI x), then normalizes so the book's max-drawdown stays within the flat
risk budget (equal-risk). Reads a precomputed static regime CSV — no model needed at run time.

  --enable        turn the overlay ON (default: OFF -> book returned unchanged, byte-identical)
  --lo / --hi     ramp endpoints (default 0.5 / 1.5)

Run:  python3 apply_regime_sizing.py <fusion_log.csv> <regime.csv> [--enable] [--lo 0.5 --hi 1.5]
"""
from __future__ import annotations
import argparse
import numpy as np, pandas as pd


def dd(p):
    eq = np.cumsum(p); return float((np.maximum.accumulate(eq) - eq).max()) if len(p) else 0.0
def stats(p):
    p = np.asarray(p, float); d = dd(p)
    return dict(n=len(p), pnl=p.sum(), dd=d, rdd=(p.sum()/d if d else float("inf")), win=100*(p>0).mean() if len(p) else 0)


def apply_overlay(book, regime, enable, lo, hi):
    """Return (per-trade scaled pnl, note). OFF -> unchanged (golden-safe)."""
    ent = book[book["decision"] == "entry"].copy()
    ent["date"] = pd.to_datetime(ent["datetime"]).dt.normalize()
    pnl = ent["pnl"].to_numpy(float)
    if not enable:
        return pnl, pnl, "OVERLAY OFF (default) — book unchanged"
    rmap = dict(zip(pd.to_datetime(regime["date"]).dt.normalize(), regime["regime"]))
    n = int(regime["n_regimes"].iloc[0])
    ramp = np.linspace(lo, hi, n)
    rg = ent["date"].map(rmap)
    mult = np.where(rg.notna(), ramp[np.nan_to_num(rg.to_numpy()).astype(int)], 1.0)
    scaled = mult * pnl
    k = dd(pnl) / dd(scaled) if dd(scaled) else 1.0          # normalize to equal risk (flat DD)
    return pnl, scaled * k, f"OVERLAY ON — regime ramp {lo}->{hi}, equal-risk normalized (x{k:.3f})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("book"); ap.add_argument("regime")
    ap.add_argument("--enable", action="store_true"); ap.add_argument("--lo", type=float, default=0.5)
    ap.add_argument("--hi", type=float, default=1.5); ap.add_argument("--out", default=None)
    a = ap.parse_args()
    book = pd.read_csv(a.book); regime = pd.read_csv(a.regime)
    flat, scaled, note = apply_overlay(book, regime, a.enable, a.lo, a.hi)
    print("=" * 74)
    print("  EXPERIMENTAL regime size-ramp overlay — CANDIDATE, magnitude UNCONFIRMED (n=1)")
    print("=" * 74)
    print(f"  {note}\n")
    b, g = stats(flat), stats(scaled)
    print(f"  flat book:     n={b['n']} P/L=${b['pnl']:,.0f} DD=${b['dd']:,.0f} Ret/DD={b['rdd']:.2f}")
    print(f"  with overlay:  n={g['n']} P/L=${g['pnl']:,.0f} DD=${g['dd']:,.0f} Ret/DD={g['rdd']:.2f}")
    if a.enable:
        print(f"  equal-risk profit delta: ${g['pnl']-b['pnl']:+,.0f}  (⚠️ candidate — not a confirmed edge)")
    else:
        print(f"  identical to flat: {'YES (golden-safe)' if np.allclose(flat, scaled) else 'NO — BUG'}")
    if a.out:
        pd.DataFrame({"pnl_flat": flat, "pnl_overlay": scaled}).to_csv(a.out, index=False)


if __name__ == "__main__":
    import sys
    try: sys.stdout.reconfigure(encoding="utf-8")
    except Exception: pass
    main()
