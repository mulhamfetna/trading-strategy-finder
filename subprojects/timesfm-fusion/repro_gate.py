#!/usr/bin/env python3
"""Reproduce the teammate's NQ TimesFM vol-gate headline from the vendored audit trail
(vendor-baseline/nq_gated_book.csv) and INDEPENDENTLY re-verify the causal gate.

This does NOT re-derive the forecast bands from the .npz (that needs the reference MTF trade
log + price series, which aren't on the server yet — a follow-up). It proves two things that
the audit trail fully determines:
  1. HEADLINE: reference vs gated P/L, maxDD, Return/DD, win — match FINDINGS.md?
  2. MECHANISM: re-run gate_service.VolGate(pct=85) on the rel_band column from scratch and
     confirm it reproduces the exact keep/veto mask recorded in the CSV (the causal rule works).

Run:  python3 repro_gate.py
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor-baseline"))
from gate_service import VolGate, _stats  # the teammate's exact deployable rule

BOOK = HERE / "vendor-baseline" / "nq_gated_book.csv"

# Targets from vendor-baseline/FINDINGS.md (NQ 1h, p85)
TGT = dict(ref_pnl=173_789, ref_dd=18_572, ref_rdd=9.36,
           gat_pnl=194_536, gat_dd=10_358, gat_rdd=18.78)


def _fmt(s, tag):
    rd = "inf" if s["ret_dd"] == float("inf") else f"{s['ret_dd']:.2f}"
    return (f"  {tag:22} trades={s['n']:>4}  P/L=${s['pnl']:>10,.0f}  "
            f"maxDD=${s['dd']:>9,.0f}  Return/DD={rd:>6}  win={s['win']:.1f}%")


def main():
    df = pd.read_csv(BOOK)
    print(f"loaded {BOOK.name}: {len(df)} trades, cols={list(df.columns)}\n")
    pnl = df["pnl"].to_numpy(float)
    band = df["rel_band"].to_numpy(float)
    kept_csv = df["kept"].astype(str).str.lower().isin(["true", "1"]).to_numpy()

    # ---- 1. HEADLINE from the audit trail ----
    base = _stats(pnl)
    gated_csv = _stats(pnl[kept_csv])
    print("=== HEADLINE (from recorded audit trail) ===")
    print(_fmt(base, "reference (all)"))
    print(_fmt(gated_csv, "+ vol gate (recorded)"))

    # ---- 2. MECHANISM: re-run VolGate from scratch on the bands ----
    gate = VolGate(pct=85.0)
    keep_recomputed = np.array([gate.allow(b if np.isfinite(b) else None) for b in band])
    match = int((keep_recomputed == kept_csv).sum())
    print(f"\n=== MECHANISM (independent VolGate p85 replay) ===")
    print(f"  keep-mask matches recorded: {match}/{len(df)} "
          f"({'EXACT' if match == len(df) else 'MISMATCH -> ' + str(len(df)-match) + ' differ'})")
    gated_re = _stats(pnl[keep_recomputed])
    print(_fmt(gated_re, "+ vol gate (replay)"))

    # ---- 3. what the gate removed (causality flavour) ----
    vetoed = pnl[~kept_csv]
    print(f"\n=== VETOED trades ===")
    print(f"  {len(vetoed)} vetoed, net ${vetoed.sum():,.0f}, win {100*(vetoed>0).mean():.0f}% "
          f"(FINDINGS: ~34 trades ≈ -$20.7k @ 36%)")

    # ---- 4. compare to FINDINGS targets ----
    def chk(name, got, tgt, tol):
        ok = abs(got - tgt) <= tol
        print(f"  {name:26} got {got:>12,.2f}  target {tgt:>12,.2f}  "
              f"{'OK' if ok else 'DIFF'} (±{tol:,})")
        return ok
    print("\n=== vs FINDINGS.md (NQ 1h p85) ===")
    allok = all([
        chk("reference P/L", base["pnl"], TGT["ref_pnl"], 50),
        chk("reference maxDD", base["dd"], TGT["ref_dd"], 50),
        chk("reference Return/DD", base["ret_dd"], TGT["ref_rdd"], 0.05),
        chk("gated P/L", gated_csv["pnl"], TGT["gat_pnl"], 50),
        chk("gated maxDD", gated_csv["dd"], TGT["gat_dd"], 50),
        chk("gated Return/DD", gated_csv["ret_dd"], TGT["gat_rdd"], 0.05),
    ])
    print(f"\nRESULT: {'REPRODUCED — all headline metrics + causal gate match' if allok and match==len(df) else 'DISCREPANCY — see DIFF/MISMATCH above'}")
    return 0 if (allok and match == len(df)) else 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raise SystemExit(main())
