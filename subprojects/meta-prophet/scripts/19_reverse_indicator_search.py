"""Phase H — search for a SMART, SMALL-DATA reverse (flip) indicator.

The existing flip rule (trends_agenitic_analysis) needs 300 trailing signals (~6 months) — too much
data / too laggy for production. Here we hunt for an indicator that decides normal-vs-flipped from a
SMALL lookback, using the engine symmetry: realized pnl = +pnl(normal) or −pnl(flipped) per trade.

Every decision is CAUSAL: mode for trade i uses only trades strictly before i.

Families compared:
  A. trailing-mean window W                 (the existing family; baseline)
  B. EWMA (half-life H)                      (recency-weighted; smaller effective memory)
  C. CUSUM change-point detector            (adaptive; uses as little data as needed)
all optionally with a dead-band θ to suppress whipsaw.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PV = 20.0


def realized(pnl, mode):
    """mode: array of +1 (normal) / −1 (flipped). realized pnl per trade."""
    return pnl * mode


def eval_modes(pnl, mode, exit_year):
    real = realized(pnl, mode)
    trans = int((np.diff(mode) != 0).sum())
    tot = real.sum() * PV
    p25 = real[exit_year == 2025].sum() * PV
    p26 = real[exit_year == 2026].sum() * PV
    return dict(total=tot, y2025=p25, y2026=p26, transitions=trans)


# ---- decision rules (all causal: decide trade i from pnl[:i]) ----
def rule_trailing(pnl, W, theta=0.0):
    n = len(pnl); mode = np.ones(n); prev = 1
    for i in range(n):
        if i >= W:
            m = pnl[i - W:i].mean()
            if m > theta: prev = 1
            elif m < -theta: prev = -1
        mode[i] = prev
    return mode


def rule_ewma(pnl, halflife, theta=0.0):
    n = len(pnl); mode = np.ones(n); prev = 1
    lam = 0.5 ** (1.0 / halflife); e = 0.0; seen = 0
    for i in range(n):
        if seen > 0:
            if e > theta: prev = 1
            elif e < -theta: prev = -1
        mode[i] = prev
        e = lam * e + (1 - lam) * pnl[i]; seen += 1   # update AFTER deciding (causal)
    return mode


def rule_cusum(pnl, k, h):
    """Two-sided CUSUM change-point detector on trade pnl. Switches mode when accumulated
    evidence of an edge-sign change exceeds threshold h (slack k). Adaptive lookback."""
    n = len(pnl); mode = np.ones(n); prev = 1
    s_hi = s_lo = 0.0
    for i in range(n):
        mode[i] = prev
        x = pnl[i]
        s_hi = max(0.0, s_hi + x - k)     # evidence edge is POSITIVE (normal good)
        s_lo = max(0.0, s_lo - x - k)     # evidence edge is NEGATIVE (flip)
        if s_lo > h:
            prev = -1; s_lo = 0.0; s_hi = 0.0
        elif s_hi > h:
            prev = 1; s_hi = 0.0; s_lo = 0.0
    return mode


def main():
    df = pd.read_csv(ROOT / "outputs" / "normal_trade_stream.csv")
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    pnl = df["pnl"].to_numpy(float)
    yr = df["exit_time"].dt.year.to_numpy()
    n = len(pnl)
    print(f"{n} trades. always-normal={pnl.sum()*PV:+,.0f}  always-flipped={-pnl.sum()*PV:+,.0f}  "
          f"oracle={np.abs(pnl).sum()*PV:+,.0f}\n")

    rows = []
    # A. trailing windows
    for W in [5, 10, 20, 30, 50, 100, 200, 300]:
        for th in [0.0, 5.0]:
            r = eval_modes(pnl, rule_trailing(pnl, W, th), yr); r["rule"] = f"trail W={W} θ={th}"
            rows.append(r)
    # B. EWMA
    for H in [5, 10, 20, 40]:
        for th in [0.0, 5.0]:
            r = eval_modes(pnl, rule_ewma(pnl, H, th), yr); r["rule"] = f"ewma HL={H} θ={th}"
            rows.append(r)
    # C. CUSUM
    for k in [5.0, 10.0, 20.0]:
        for h in [50.0, 100.0, 200.0, 400.0]:
            r = eval_modes(pnl, rule_cusum(pnl, k, h), yr); r["rule"] = f"cusum k={k} h={h}"
            rows.append(r)

    res = pd.DataFrame(rows)[["rule", "total", "y2025", "y2026", "transitions"]].sort_values("total", ascending=False)
    res.to_csv(ROOT / "outputs" / "reverse_indicator_search.csv", index=False)
    pd.set_option("display.width", 120)
    print("TOP 15 by total P/L:")
    print(res.head(15).to_string(index=False))
    print("\nExisting baseline (trail W=300 θ=0):")
    print(res[res["rule"].str.contains("W=300")].to_string(index=False))
    print("\nBest SMALL-data rules (CUSUM + EWMA):")
    small = res[res["rule"].str.contains("cusum|ewma")].head(6)
    print(small.to_string(index=False))


if __name__ == "__main__":
    main()
