#!/usr/bin/env python3
"""Robustness battery for the TimesFM vol-gate on the EXTENDED 2024-2026 NQ fusion book.

The n=1 concern: the +$20.7k was one 16.5-month bull window. Here we add 2024 (incl. the Aug-2024
vol spike) — a 539-trade book with the fusion's own gate trained on 2024 — and stress the TimesFM
gate five ways:

  1. HEADLINE   reference vs causal p85 gate on the full 2024-2026 book.
  2. PER-YEAR   does the gate help in 2024, 2025, 2026 separately? (or only the bull years?)
  3. THRESHOLD  sensitivity across p75/p80/p85/p90.
  4. BLOCK-BOOTSTRAP  resample contiguous 20-trade blocks 2000x; distribution of Delta(Return/DD);
                 fraction of resamples where the gate helps. (Is the benefit broad or a few tails?)
  5. RANDOM-VETO CONTROL  veto the SAME number of trades at random 2000x; where does TimesFM's
                 gated Return/DD fall in that null? (Is the specific trade selection special?)

Inputs: nq_2426_mtf_log.csv (extended book) + nq_2426_relband.csv (TimesFM bands, per 1h bar).
Run:  python3 robustness_2426.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor-baseline"))
from gate_service import VolGate, _stats  # noqa: E402

BOOK = HERE / "nq_2426_mtf_log.csv"
BANDS = HERE / "nq_2426_relband.csv"
SEED = 12345


def load_book_with_bands():
    log = pd.read_csv(BOOK)
    ent = log[log["decision"] == "entry"].copy()
    ent["datetime"] = pd.to_datetime(ent["datetime"])
    ent = ent.sort_values("datetime").reset_index(drop=True)
    b = pd.read_csv(BANDS)
    b["datetime"] = pd.to_datetime(b["datetime"])
    idx = {t: k for k, t in enumerate(b["datetime"])}
    rel = b["rel_band"].to_numpy(float)
    bands = np.full(len(ent), np.nan)
    for i, t in enumerate(ent["datetime"]):
        k = idx.get(t)
        if k is not None and k - 1 >= 0 and np.isfinite(rel[k - 1]):
            bands[i] = rel[k - 1]                 # forecast from the bar BEFORE entry (causal)
    return ent, ent["pnl"].to_numpy(float), bands


def gate_keep(bands, pct):
    g = VolGate(pct=pct)
    return np.array([g.allow(b if np.isfinite(b) else None) for b in bands])


def line(tag, s):
    rd = "inf" if s["ret_dd"] == float("inf") else f"{s['ret_dd']:.2f}"
    return f"  {tag:20} n={s['n']:>4}  P/L=${s['pnl']:>10,.0f}  DD=${s['dd']:>9,.0f}  Ret/DD={rd:>6}  win={s['win']:.1f}%"


def main():
    rng = np.random.default_rng(SEED)
    ent, pnl, bands = load_book_with_bands()
    yr = ent["datetime"].dt.year.to_numpy()
    have = int(np.isfinite(bands).sum())
    print(f"extended book: {len(ent)} entries  bands mapped: {have}/{len(ent)}  years: {sorted(set(yr))}\n")

    base = _stats(pnl)
    keep85 = gate_keep(bands, 85.0)
    g85 = _stats(pnl[keep85])
    print("=== 1. HEADLINE (2024-2026) ===")
    print(line("reference (all)", base)); print(line("TimesFM p85", g85))
    dd_red = 100 * (1 - g85["dd"] / base["dd"]) if base["dd"] else 0
    print(f"   -> Return/DD {base['ret_dd']:.2f} -> {g85['ret_dd']:.2f}, DD {dd_red:+.0f}%, vetoed {len(pnl)-keep85.sum()}\n")

    print("=== 2. PER-YEAR (gate applied causally over the WHOLE series, then bucketed) ===")
    for y in sorted(set(yr)):
        mask = yr == y
        b_y = _stats(pnl[mask]); g_y = _stats(pnl[mask & keep85])
        print(f"  {y}:  ref Ret/DD {b_y['ret_dd']:>6.2f} (P/L ${b_y['pnl']:>8,.0f}, n={b_y['n']})   "
              f"gated {g_y['ret_dd']:>6.2f} (P/L ${g_y['pnl']:>8,.0f}, n={g_y['n']})   "
              f"{'HELP' if g_y['ret_dd']>b_y['ret_dd'] else 'HURT/flat'}")
    print()

    print("=== 3. THRESHOLD sensitivity ===")
    for p in (75, 80, 85, 90):
        s = _stats(pnl[gate_keep(bands, float(p))])
        print(line(f"p{p}", s))
    print()

    print("=== 4. BLOCK-BOOTSTRAP (2000x, 20-trade blocks): Delta Return/DD = gated - reference ===")
    def block_resample(n, block=20):
        out = []
        while len(out) < n:
            start = rng.integers(0, n)
            out.extend(range(start, min(start + block, n)))
        return np.array(out[:n])
    deltas = []
    for _ in range(2000):
        ii = block_resample(len(pnl))
        rb = _stats(pnl[ii]); rg = _stats(pnl[ii][keep85[ii]])
        if np.isfinite(rb["ret_dd"]) and np.isfinite(rg["ret_dd"]):
            deltas.append(rg["ret_dd"] - rb["ret_dd"])
    deltas = np.array(deltas)
    print(f"  median Delta Ret/DD = {np.median(deltas):+.2f}   "
          f"5th pct = {np.percentile(deltas,5):+.2f}   95th = {np.percentile(deltas,95):+.2f}   "
          f"P(gate helps) = {100*(deltas>0).mean():.0f}%\n")

    print("=== 5. RANDOM-VETO CONTROL (2000x): veto the same COUNT at random ===")
    n_veto = int((~keep85).sum())
    real = g85["ret_dd"]
    rand_rdd = []
    for _ in range(2000):
        keep = np.ones(len(pnl), bool)
        keep[rng.choice(len(pnl), n_veto, replace=False)] = False
        s = _stats(pnl[keep])
        if np.isfinite(s["ret_dd"]): rand_rdd.append(s["ret_dd"])
    rand_rdd = np.array(rand_rdd)
    pct_rank = 100 * (rand_rdd < real).mean()
    print(f"  TimesFM gated Ret/DD = {real:.2f}   random-veto median = {np.median(rand_rdd):.2f}   "
          f"TimesFM beats {pct_rank:.0f}% of random vetoes  (>95% => selection is special)\n")

    helps_years = sum(1 for y in set(yr)
                      if _stats(pnl[(yr==y)&keep85])["ret_dd"] > _stats(pnl[yr==y])["ret_dd"])
    print("=== VERDICT ===")
    print(f"  gate helps in {helps_years}/{len(set(yr))} years; "
          f"bootstrap P(helps)={100*(deltas>0).mean():.0f}%; beats {pct_rank:.0f}% of random vetoes.")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
