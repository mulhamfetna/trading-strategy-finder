"""FORWARD-VALIDATION #4 v2 — CAUSAL entry. Fixes the look-ahead in v1.

v1 measured the +5min move from the bar BEFORE the print (paths_for anchor = close[t0-1]), so it captured
the release-instant jump you CANNOT trade (you only learn the surprise AT the release). GC-01 found ~60% of
gold's move happens in the first second — exactly that un-tradeable jump. This version enters at the CLOSE
of the release-minute bar (t0, ~1 min after the number is public) and holds to +5 min. Reports both, so the
gap between them IS the un-tradeable jump, and only the causal row decides tradeability.

  python3 walk_forward_gc2.py
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

WARMUP, MIN_PRIOR, H = 100, 60, 5
GC_PV, GC_TICK = 100.0, 0.10


def moves_for(df1, sur):
    """Return z, full_move (pre-print anchor = look-ahead), caus_move (enter at release-bar close), dates."""
    idx = pd.Index(df1["Date"])
    close = df1["Close"].to_numpy(np.float64)
    t0 = idx.get_indexer(sur["Date"])
    ok = (t0 >= 1) & (t0 + H < len(close))
    t0 = t0[ok]
    full = close[t0 + H] - close[t0 - 1]     # pre-print -> +5m  (INCLUDES the release jump; look-ahead)
    caus = close[t0 + H] - close[t0]         # release-bar close -> +5m  (CAUSAL, tradeable)
    return sur["surprise_z"].to_numpy()[ok], full, caus, sur["Date"].to_numpy()[ok]


def walk_forward(z, fit_m, real_m, dates):
    pnl, td, negs = [], [], []
    for i in range(len(z)):
        if i < max(WARMUP, MIN_PRIOR) or z[i] == 0:
            continue
        rho = stats.spearmanr(z[:i], fit_m[:i])[0]
        if not np.isfinite(rho) or rho == 0:
            continue
        negs.append(rho < 0)
        pnl.append(np.sign(rho) * np.sign(z[i]) * real_m[i])
        td.append(dates[i])
    return np.array(pnl), pd.to_datetime(pd.Series(td)), np.array(negs)


def line(label, pnl):
    mu, sd = pnl.mean(), pnl.std()
    t = mu / (sd / np.sqrt(len(pnl)))
    print(f"  {label:<26} mean {mu:+.3f} pts  t={t:+.2f}  ${GC_PV*mu:+7.2f}/trade  cum ${GC_PV*pnl.sum():+9,.0f}")
    return t


def report(inst, z, full, caus, dates):
    # fit the sign on the CAUSAL series (self-consistent, no peeking at the jump), trade the causal move
    p_full, td, negs = walk_forward(z, caus, full, dates)   # same trades, but bank the full (look-ahead) move
    p_caus, _, _ = walk_forward(z, caus, caus, dates)       # bank only the causal move
    print(f"\n================ {inst} — WALK-FORWARD OOS ({len(p_caus)} trades, "
          f"{td.dt.year.min()}-{td.dt.year.max()}) ================")
    print(f"  fitted sign NEGATIVE in {100*negs.mean():.1f}% of trades")
    line("FULL move (look-ahead)", p_full)
    tc = line("CAUSAL move (tradeable)", p_caus)
    print(f"  => the gap is the un-tradeable release-instant jump.")
    print(f"  CAUSAL net of round-trip cost:")
    for ticks in (0, 1, 2, 3, 5):
        cost = 2 * ticks * GC_TICK + 0.04
        net = p_caus - cost
        tn = net.mean() / (net.std() / np.sqrt(len(net)))
        alive = "PROFITABLE" if net.mean() > 0 and tn > 2 else ("marginal" if net.mean() > 0 else "DEAD")
        print(f"     {ticks} tick/side (${GC_PV*cost:3.0f}): ${GC_PV*net.mean():+7.2f}/trade  t={tn:+5.2f}  [{alive}]")
    if inst == "GC":
        print("  per-YEAR OOS (causal, gross):")
        for y in sorted(td.dt.year.unique()):
            msk = (td.dt.year == y).values
            if msk.sum() < 10: continue
            p = p_caus[msk]
            print(f"     {y}  n={msk.sum():3d}  {p.mean():+7.3f} pts  hit {100*(p>0).mean():5.1f}%  ${GC_PV*p.sum():+8,.0f}")


def main():
    print("Loading surprises (cached) + price frames...")
    sur = build_surprises(rc.load_calendar())
    for inst in ("GC", "NQ"):
        df1 = load_1m_extended(inst)
        z, full, caus, dates = moves_for(df1, sur)
        report(inst, z, full, caus, dates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
