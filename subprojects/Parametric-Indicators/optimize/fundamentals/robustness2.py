"""ROBUSTNESS ROUND 2 — is the cross-market signal REAL, or is it ONE factor wearing nine costumes?

Round 1 found every one of our 9 markets negatively correlated with the macro surprise, 5 of them
with a bootstrap CI excluding zero. That FORCED a correction: "dead" was too strong.

But it also tripped the alarm-detector test from spec 3.4 — all nine move the SAME way, and a strong
jobs number making COPPER fall is economically absurd (copper tracks growth). So before believing
anything, three questions:

  Q1. IS IT ONE FACTOR? Correlate the 9 markets' release-window returns with EACH OTHER. If they are
      all ~0.9 correlated, we do not have 9 tests — we have ~1, and "5 of 9 significant" is an
      illusion created by counting the same bet nine times.

  Q2. THE PROPER NULL. A bootstrap CI asks "how uncertain is this correlation?" — it does NOT ask
      "could a random surprise series produce this?" Only the SHUFFLED-surprise null answers that,
      and it is the test that killed the single-market result. Run it per market.

  Q3. MULTIPLE COMPARISONS. Nine markets x four horizons = 36 tests. Some WILL look significant by
      luck. Report the family-wise picture, not the best cell.

  python3 optimize/fundamentals/robustness2.py --n-shuffle 3000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data, instruments                        # noqa: E402
from optimize.fundamentals import release_calendar as rc      # noqa: E402
from optimize.fundamentals.robustness import outcomes_for     # noqa: E402
from optimize.fundamentals.study_surprise import build_surprises   # noqa: E402

HS = [5, 15, 30, 60]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-shuffle", type=int, default=3000)
    a = ap.parse_args()
    rng = np.random.default_rng(0)

    cal = rc.load_calendar()
    sur = build_surprises(cal)
    print(f"\n{len(sur)} causal surprises\n")

    # ---------------------------------------------------------------- Q1: is it one factor?
    rets = {}
    for tok in instruments.TOKENS:
        _, df1, *_ = data.load_inputs("4h", instrument=tok)
        z, r, yr = outcomes_for(df1, sur, 5)
        rets[tok] = pd.Series(r, index=sur["Date"].to_numpy()[
            pd.Index(df1["Date"]).get_indexer(sur["Date"]) >= 1][:len(r)])

    R = pd.DataFrame(rets).dropna()
    C = R.corr()
    print("=" * 84)
    print("Q1 — DO THE 9 MARKETS JUST MOVE TOGETHER? (correlation of their 5-min release returns)")
    print("=" * 84)
    print(C.round(2).to_string())

    # how much of the variance is ONE factor?
    X = ((R - R.mean()) / R.std()).to_numpy()
    ev = np.linalg.svd(X, full_matrices=False)[1] ** 2
    pc1 = ev[0] / ev.sum()
    print(f"\n  First principal component explains {100*pc1:.1f}% of all variance across the 9 markets.")
    eff = 1.0 / (C.to_numpy() ** 2).mean()
    print(f"  Effective number of INDEPENDENT markets ≈ {eff:.1f}  (not 9)")
    if pc1 > 0.5:
        print("  ⇒ These are NOT 9 independent tests. One common factor dominates. '5 of 9 significant'")
        print("    is largely the SAME BET counted several times.")

    # equity bloc vs the rest
    eq = ["NQ", "ES", "RTY", "YM"]
    print(f"\n  mean corr WITHIN the equity bloc {eq}: "
          f"{C.loc[eq, eq].values[np.triu_indices(4, 1)].mean():.2f}")
    others = [t for t in instruments.TOKENS if t not in eq]
    print(f"  mean corr equities vs non-equities:      "
          f"{C.loc[eq, others].to_numpy().mean():.2f}")

    # ---------------------------------------------------------------- Q2 + Q3: the proper null
    print()
    print("=" * 84)
    print(f"Q2 — THE PROPER NULL (shuffled surprises, {a.n_shuffle} draws) — the test that killed NQ")
    print("=" * 84)
    print(f"{'mkt':<5} | " + " ".join(f"{'h='+str(h):>13}" for h in HS))
    print("-" * 84)

    ps = []
    for tok in instruments.TOKENS:
        _, df1, *_ = data.load_inputs("4h", instrument=tok)
        cells = []
        for h in HS:
            z, r, yr = outcomes_for(df1, sur, h)
            if len(z) < 20:
                cells.append("      n/a    ")
                continue
            c = float(np.corrcoef(z, r)[0, 1])
            null = np.array([abs(np.corrcoef(rng.permutation(z), r)[0, 1])
                             for _ in range(a.n_shuffle)])
            p = float((null >= abs(c)).mean())
            ps.append(p)
            star = "*" if p < 0.05 else " "
            cells.append(f"{c:>+6.3f} p{p:>5.3f}{star}")
        print(f"{tok:<5} | " + " ".join(cells))

    ps = np.array(ps)
    n_sig = int((ps < 0.05).sum())
    print()
    print("=" * 84)
    print("Q3 — MULTIPLE COMPARISONS")
    print("=" * 84)
    print(f"  tests run:                {len(ps)}  (9 markets x 4 horizons)")
    print(f"  significant at p<0.05:    {n_sig}")
    print(f"  expected by LUCK alone:   {0.05*len(ps):.1f}")
    # Bonferroni: the honest family-wise threshold
    bonf = 0.05 / len(ps)
    n_bonf = int((ps < bonf).sum())
    print(f"  Bonferroni threshold:     p < {bonf:.4f}  →  {n_bonf} survive")
    print()
    if n_bonf == 0:
        print("  ⇒ NOTHING survives correction for testing 36 cells. Combined with Q1 (the markets")
        print("     are one factor, not nine), the cross-market 'signal' does not clear the bar.")
    else:
        print(f"  ⇒ {n_bonf} cell(s) survive even Bonferroni — that is a genuinely strong result.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
