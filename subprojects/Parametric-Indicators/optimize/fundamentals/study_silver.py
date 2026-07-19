"""D3 — THE PRE-REGISTERED SILVER TEST. Test it properly, or drop it explicitly.

WHY THIS EXISTS. Silver (SI) was the one loose end of the 9-market robustness study (report 05): its
surprise->return correlation at h=5 was −0.360, p=0.007 (the strongest of all 36 cells), and — uniquely —
it STRENGTHENED out-of-sample: 2025 −0.140 -> 2026 −0.500. Everything else decayed OOS; silver grew. I
refused to either bury it or chase it, and logged it as an OPEN question requiring a pre-registered test.

This is that test. And it is constrained by a hard fact discovered while setting it up:

  ⚠️  THERE IS NO LONG SILVER HISTORY. The 17-year frame that let us settle NQ at 99% power is NQ ONLY.
      Silver price data exists only for 2025-01-01 .. 2026-07-02 — the SAME ~18-month window we JUST
      proved (for NQ magnitude) is where flukes live (+0.281 in 2025, the luckiest of 17 years; −0.006
      across 2010-2023 at 100% power). So the gold-standard powered test is IMPOSSIBLE for silver.

We therefore cannot confirm silver. But we CAN try to KILL it with tests the existing data supports —
and if it survives all of them, freeze a forward-data pre-registration rather than start building.

================================================================================================
THE PRE-REGISTERED CRITERION — declared HERE, before the run. It does not move.
================================================================================================

  Silver STAYS ALIVE (=> freeze a forward-data test, do NOT drop) ONLY IF ALL THREE hold:

    (1) ENOUGH EVENTS.       The 2026 out-of-sample slice has n >= 25 releases. Below that, −0.500 is a
                             handful of points and means nothing.
    (2) INDEPENDENT OF GOLD. Silver is 0.85-correlated with gold, and GOLD SHOWED THE SAME OOS MOVE
                             (GC: 2025 −0.113 -> 2026 −0.366). So the real question is whether silver
                             carries ANY signal gold does not already provide. Test: the PARTIAL
                             correlation r(surprise, SI_return | GC_return) at h=5 must itself be
                             significant under the shuffled-surprise null (p < 0.05). If silver is just
                             gold in a costume, this collapses to zero.
    (3) STABLE.              The h=5 correlation is negative in >= 3 of 4 chronological quarters — i.e.
                             a persistent tilt, not one cluster of events driving the whole thing.

  Silver is DROPPED if it fails ANY of the three. Rationale: being the best of 36 cells, with an OOS blip
  that its 0.85-correlated sister SHARES, confined entirely to the fluke-prone window, is EXACTLY what
  luck produces. The bar to keep it alive must be genuinely independent, adequately-sized evidence.

CAUSALITY. Returns are close[T+h] / close[T-1] − 1 (anchored to the last bar BEFORE the print). The
surprise is known at T. Nothing peeks. Same machinery as robustness.outcomes_for.

  WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 -u optimize/fundamentals/study_silver.py --n-shuffle 5000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data                                          # noqa: E402
from optimize.fundamentals import release_calendar as rc           # noqa: E402
from optimize.fundamentals.robustness import outcomes_for          # noqa: E402
from optimize.fundamentals.study_surprise import build_surprises   # noqa: E402

H = 5                           # the headline horizon (minutes) where silver was strongest
OOS_MIN_N = 25                  # criterion (1)
from scipy import stats         # noqa: E402


def power_for(r: float, n: int) -> float:
    if n <= 3 or r == 0:
        return 0.0
    zr = 0.5 * np.log((1 + abs(r)) / (1 - abs(r)))
    return float(stats.norm.sf(stats.norm.ppf(0.975) - zr * np.sqrt(n - 3)))


def corr(a, b):
    if len(a) < 4:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def shuffle_p(z, y, observed, rng, n_shuffle, stat=corr):
    null = np.array([stat(rng.permutation(z), y) for _ in range(n_shuffle)])
    null = null[np.isfinite(null)]
    return float((np.abs(null) >= abs(observed)).mean())


def partial_corr(z, si, gc):
    """r(z, si | gc): correlation of surprise z with silver return, after removing the part of silver
    return that gold return explains. If silver is just gold + noise, this is ~0."""
    if len(z) < 5:
        return float("nan")
    # residual of si after regressing on gc
    b = np.polyfit(gc, si, 1)
    si_res = si - (b[0] * gc + b[1])
    return corr(z, si_res)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-shuffle", type=int, default=5000)
    a = ap.parse_args()
    rng = np.random.default_rng(0)

    print("\n" + "=" * 84)
    print("D3 — PRE-REGISTERED SILVER TEST  (criterion declared in-source; see the docstring)")
    print("=" * 84)

    sur = build_surprises(rc.load_calendar())
    _, si1, *_ = data.load_inputs("4h", instrument="SI")
    _, gc1, *_ = data.load_inputs("4h", instrument="GC")
    print(f"  SI 1-min: {si1['Date'].iloc[0]} -> {si1['Date'].iloc[-1]}  ({len(si1):,} bars)")
    print(f"  GC 1-min: {gc1['Date'].iloc[0]} -> {gc1['Date'].iloc[-1]}  ({len(gc1):,} bars)")

    z_si, r_si, yr_si = outcomes_for(si1, sur, H)
    z_gc, r_gc, yr_gc = outcomes_for(gc1, sur, H)

    # ---------------------------------------------------------------- (1) ENOUGH EVENTS
    n_full = len(z_si)
    n_25 = int((yr_si == 2025).sum())
    n_26 = int((yr_si >= 2026).sum())
    print("\n" + "-" * 84)
    print("CRITERION (1) — ENOUGH EVENTS?")
    print("-" * 84)
    print(f"  silver releases with a causal h={H} return:  full={n_full}   2025={n_25}   2026={n_26}")
    print(f"  full-sample corr(surprise, SI) = {corr(z_si, r_si):+.3f}   "
          f"2025 = {corr(z_si[yr_si==2025], r_si[yr_si==2025]):+.3f}   "
          f"2026 = {corr(z_si[yr_si>=2026], r_si[yr_si>=2026]):+.3f}")
    print(f"  POWER at the OOS n={n_26} to see r=0.15: {100*power_for(0.15, n_26):.0f}%  "
          f"(a null here would be blind — but a POSITIVE still counts against a pre-set bar)")
    pass1 = n_26 >= OOS_MIN_N
    print(f"  => (1) {'PASS' if pass1 else 'FAIL'}: 2026 OOS n={n_26} "
          f"{'>=' if pass1 else '<'} {OOS_MIN_N}")

    # ---------------------------------------------------------------- (2) INDEPENDENT OF GOLD?
    print("\n" + "-" * 84)
    print("CRITERION (2) — INDEPENDENT OF GOLD? (silver is 0.85-corr with gold; gold did the same OOS)")
    print("-" * 84)
    # align silver & gold on the SAME release dates (both have the full 2025-2026 window, but guard anyway)
    idx = pd.Index(si1["Date"])
    t0 = idx.get_indexer(sur["Date"])
    ok_si = (t0 >= 1) & (t0 + H < len(si1))
    idxg = pd.Index(gc1["Date"])
    t0g = idxg.get_indexer(sur["Date"])
    ok_gc = (t0g >= 1) & (t0g + H < len(gc1))
    both = ok_si & ok_gc
    zc = sur["surprise_z"].to_numpy()[both]
    si_r = si1["Close"].to_numpy()[t0[both] + H] / si1["Close"].to_numpy()[t0[both] - 1] - 1.0
    gc_r = gc1["Close"].to_numpy()[t0g[both] + H] / gc1["Close"].to_numpy()[t0g[both] - 1] - 1.0
    print(f"  aligned silver+gold release events: n={len(zc)}")
    print(f"  corr(SI return, GC return) = {corr(si_r, gc_r):+.3f}   (the sisters move together)")
    r_si_raw = corr(zc, si_r)
    r_gc_raw = corr(zc, gc_r)
    r_partial = partial_corr(zc, si_r, gc_r)
    p_raw = shuffle_p(zc, si_r, r_si_raw, rng, a.n_shuffle)
    p_partial = shuffle_p(zc, si_r, r_partial, rng, a.n_shuffle,
                          stat=lambda zz, _ss: partial_corr(zz, si_r, gc_r))
    print(f"  corr(surprise, SI)            = {r_si_raw:+.3f}   shuffle p = {p_raw:.3f}")
    print(f"  corr(surprise, GC)            = {r_gc_raw:+.3f}")
    print(f"  PARTIAL corr(surprise, SI|GC) = {r_partial:+.3f}   shuffle p = {p_partial:.3f}"
          f"   <- does silver add ANYTHING beyond gold?")
    pass2 = (p_partial < 0.05)
    print(f"  => (2) {'PASS' if pass2 else 'FAIL'}: silver's signal beyond gold is "
          f"{'significant' if pass2 else 'INDISTINGUISHABLE FROM ZERO'} (p={p_partial:.3f})")

    # ---------------------------------------------------------------- (3) STABLE across time?
    print("\n" + "-" * 84)
    print("CRITERION (3) — STABLE? (negative in >= 3 of 4 chronological quarters)")
    print("-" * 84)
    order = np.argsort(si1["Date"].to_numpy()[t0[ok_si]])   # chronological
    zq = sur["surprise_z"].to_numpy()[ok_si][order]
    rq = (si1["Close"].to_numpy()[t0[ok_si] + H] / si1["Close"].to_numpy()[t0[ok_si] - 1] - 1.0)[order]
    quarters = np.array_split(np.arange(len(zq)), 4)
    negs = 0
    for i, q in enumerate(quarters):
        c = corr(zq[q], rq[q])
        neg = c < 0
        negs += int(neg)
        print(f"  quarter {i+1}: n={len(q):>3}  corr = {c:+.3f}  {'(neg)' if neg else '(pos)'}")
    pass3 = negs >= 3
    print(f"  => (3) {'PASS' if pass3 else 'FAIL'}: negative in {negs}/4 quarters "
          f"({'>=' if pass3 else '<'} 3)")

    # ---------------------------------------------------------------- VERDICT
    print("\n" + "=" * 84)
    print("VERDICT — against the PRE-DECLARED criterion (all three must pass to stay alive)")
    print("=" * 84)
    print(f"  (1) enough events      : {'PASS' if pass1 else 'FAIL'}")
    print(f"  (2) independent of gold: {'PASS' if pass2 else 'FAIL'}")
    print(f"  (3) stable across time : {'PASS' if pass3 else 'FAIL'}")
    print()
    if pass1 and pass2 and pass3:
        print("  ✅ SILVER SURVIVES. Freeze a forward-data pre-registration: silver only, h=5, the frozen")
        print("     rule applied to NEW data past 2026-07-02 that we have not yet seen. Do NOT start")
        print("     building on it — it still cannot be confirmed without long history or forward data.")
    else:
        print("  ❌ SILVER IS DROPPED. It fails the pre-declared bar. The strongest cell of 36 turned out")
        print("     to be a metals-complex blip its 0.85-correlated sister shares, confined to the")
        print("     fluke-prone window, with no independent, adequately-sized, stable signal of its own.")
        print("     This closes the last open statistical thread of the fundamental-analysis workstream.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
