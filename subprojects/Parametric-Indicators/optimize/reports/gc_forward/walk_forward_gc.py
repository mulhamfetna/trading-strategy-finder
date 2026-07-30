"""FORWARD-VALIDATION (#4) of gold's inverse macro reaction — a walk-forward, no-peek track record.

GC-01 found gold's +5min move is inversely rank-correlated with the macro surprise (Spearman -0.193,
negative 15/16 years, both halves). gc_robust.py validated that IN-SAMPLE (each year's own correlation).
This is the stronger test: at EACH release, decide the trade sign using ONLY prior releases (expanding
Spearman), then bank the realized move. That is what trading it live, year by year, would actually have
produced — a genuine out-of-sample track record with real power (~hundreds of OOS events, not the 2025->2026
handful). Reports GROSS and NET-of-cost (to re-confirm the 'un-tradeable at cost' verdict forward), an NQ
control (should stay null), sign stability, and a per-year OOS breakdown.

  python3 walk_forward_gc.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT = "/home/dev/Mulham/code/.worktrees/fundamental/subprojects/Parametric-Indicators"
sys.path.insert(0, ROOT)
from optimize.fundamentals import release_calendar as rc          # noqa: E402
from optimize.fundamentals.extended_data import load_1m_extended  # noqa: E402
from optimize.fundamentals.study_surprise import build_surprises  # noqa: E402
from optimize.fundamentals.study_pattern import paths_for         # noqa: E402

WARMUP = 100          # first N releases are training-only (need a stable prior Spearman) — not counted OOS
MIN_PRIOR = 60        # and never fit a sign on fewer than this many prior releases
GC_PV, GC_TICK = 100.0, 0.10   # $ per point, point size of one tick


def walk_forward(z, m, dates):
    """OOS per-trade P&L (points), fitting the trade sign from PRIOR releases only (expanding Spearman)."""
    n = len(z)
    pnl, tdates, signs_neg = [], [], []
    for i in range(n):
        if i < max(WARMUP, MIN_PRIOR):
            continue
        if z[i] == 0:
            continue
        rho = stats.spearmanr(z[:i], m[:i])[0]     # fitted on the PAST only
        if not np.isfinite(rho) or rho == 0:
            continue
        signs_neg.append(rho < 0)
        pos = np.sign(rho) * np.sign(z[i])         # go WITH the historical relationship
        pnl.append(pos * m[i])                     # realized +5min move, in points
        tdates.append(dates[i])
    return np.array(pnl), pd.to_datetime(pd.Series(tdates)), np.array(signs_neg)


def report(inst, z, m, dates):
    pnl, td, signs_neg = walk_forward(z, m, dates)
    if len(pnl) < 30:
        print(f"\n{inst}: too few OOS trades ({len(pnl)})"); return
    mu, sd = pnl.mean(), pnl.std()
    t = mu / (sd / np.sqrt(len(pnl)))
    print(f"\n================ {inst}  —  WALK-FORWARD OOS ({len(pnl)} trades, "
          f"{td.dt.year.min()}-{td.dt.year.max()}) ================")
    print(f"  fitted sign was NEGATIVE in {100*signs_neg.mean():.1f}% of trades  (sign stability)")
    print(f"  GROSS  mean {mu:+.3f} pts/trade  swing +-{sd:.2f}  t={t:+.2f}  "
          f"=> ${GC_PV*mu:+.2f}/trade, cum ${GC_PV*pnl.sum():+,.0f}")
    print(f"  NET of round-trip cost (slippage + $4 commission):")
    for ticks in (0, 1, 2, 3, 5):
        cost = 2 * ticks * GC_TICK + 0.04            # both-side slippage in points + commission
        net = pnl - cost
        tn = net.mean() / (net.std() / np.sqrt(len(net)))
        alive = "PROFITABLE" if net.mean() > 0 and tn > 2 else ("marginal" if net.mean() > 0 else "DEAD")
        print(f"     {ticks} tick/side (cost {cost:.2f}pt=${GC_PV*cost:.0f}): "
              f"${GC_PV*net.mean():+7.2f}/trade  t={tn:+5.2f}  cum ${GC_PV*net.sum():+9,.0f}  [{alive}]")
    if inst == "GC":
        print("  per-YEAR OOS (gross):")
        for y in sorted(td.dt.year.unique()):
            msk = (td.dt.year == y).values
            if msk.sum() < 10:
                continue
            p = pnl[msk]
            print(f"     {y}  n={msk.sum():3d}  {p.mean():+7.3f} pts/trade  "
                  f"hit {100*(p>0).mean():5.1f}%  ${GC_PV*p.sum():+8,.0f}")


def main():
    print("Loading surprises (cached) + price frames...")
    sur = build_surprises(rc.load_calendar())
    for inst in ("GC", "NQ"):
        df1 = load_1m_extended(inst)
        P, z, dates = paths_for(df1, sur)
        report(inst, z, P[:, 4], dates)         # P[:,4] = +5 min move, exactly as GC-01/gc_robust
    print("\nREAD: GC gross t-stat >0 with a stable negative sign = the inverse reaction survives a true")
    print("no-peek forward test. Whether any NET row stays PROFITABLE decides if it is tradeable forward.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
