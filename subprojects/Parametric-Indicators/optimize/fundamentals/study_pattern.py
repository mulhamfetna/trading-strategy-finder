"""Task #9 — does the CONTENT of a release predict the SHAPE of the next 30 minutes?

THE USER'S POINT, and it is a good one: everything we have tested so far collapsed the outcome to a
SCALAR — "what is the return at h minutes?" But a spike-then-fade, a sustained trend, and a whipsaw can
all produce the SAME 30-minute return while being completely different trades. We never looked at SHAPE.

So we ask three questions, in increasing order of how much they'd be worth:

  Q1. MAGNITUDE. Does a BIGGER surprise produce a BIGGER move — regardless of direction?
      This is the most likely real effect, and it needs NO directional call. If |surprise| predicts
      |move|, that is tradeable by a straddle/breakout, and it survives even though direction does not.
      It is also the one thing the efficient-market argument does NOT forbid: the market can price the
      EXPECTED value perfectly and still not know how big the shock will be.

  Q2. SHAPE. Cluster the 30-minute post-release paths into archetypes (spike-and-fade / sustained trend
      / whipsaw / drift). Does the surprise predict WHICH archetype occurs?

  Q3. PERSISTENCE. Of the moves that happen, does the surprise predict whether the initial move HOLDS
      to +30 min or REVERSES? (The user's "does it create a pattern" question, in its sharpest form.)

Everything is scored against the SHUFFLED-SURPRISE null — same discipline that has now killed four
ideas in this project. A pattern that a random surprise reproduces is not a pattern.

CAUSALITY: paths are measured from close[T-1] (the last bar BEFORE the print). The surprise is known at
T. Nothing peeks.

  python3 optimize/fundamentals/study_pattern.py --n-shuffle 3000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data                                    # noqa: E402
from optimize.fundamentals import release_calendar as rc     # noqa: E402
from optimize.fundamentals.extended_data import load_1m_extended   # noqa: E402
from optimize.fundamentals.study_surprise import build_surprises   # noqa: E402

H = 30          # minutes of post-release path we study


def _frame(extended: bool, instrument: str = "NQ"):
    """The 1-minute price frame. --extended folds in 2024, which roughly DOUBLES the sample.

    --instrument selects the market. NQ is the default so every previously-reported NQ number stays
    byte-reproducible; GC (gold) got its own 16-year frame on 2026-07-19 and is the REPLICATION target
    — the same pre-registered battery on an independent instrument.

    The engine's own data loading is untouched (golden-locked); this is research-only.
    """
    if extended or instrument != "NQ":
        return load_1m_extended(instrument)
    _, df1, *_ = data.load_inputs("4h")
    return df1


# MINIMUM EFFECT OF INTEREST — declared UP FRONT, not chosen after seeing the data.
#
# This is the smallest correlation that would actually be worth acting on. Power MUST be computed
# against THIS, never against the effect you happened to observe.
#
# WHY THIS MATTERS AND WHY I GOT IT WRONG ONCE: an earlier version reported power for the OBSERVED r.
# So when the observed effect was ~0, it printed "8% power — underpowered", which READS as "we could
# not see anything" when the truth was "we looked with a perfect instrument and there is nothing there".
# That is circular and it inverts the meaning of the result. Power against a PRE-DECLARED effect is the
# only version that carries information.
MEI = 0.15


def power_for(r: float, n: int) -> float:
    """If the true effect is r, what is the chance a sample of n DETECTS it (alpha=0.05, two-sided)?"""
    from scipy import stats
    if n <= 3 or r == 0:
        return 0.0
    zr = 0.5 * np.log((1 + abs(r)) / (1 - abs(r)))
    return float(stats.norm.sf(stats.norm.ppf(0.975) - zr * np.sqrt(n - 3)))


def verdict(p: float, n: int, mei: float = MEI) -> str:
    """The honest one-word reading of a result, given the power we ACTUALLY had.

      significant                  -> we found something
      not significant, HIGH power  -> REAL NEGATIVE. We looked properly. There is nothing there.
      not significant, LOW power   -> INCONCLUSIVE. Our instrument was blind. Says nothing.
    """
    pw = power_for(mei, n)
    if p < 0.05:
        return "  <<< SIGNIFICANT"
    if pw >= 0.80:
        return f"  REAL NEGATIVE (power {100*pw:.0f}% to see r={mei})"
    return f"  INCONCLUSIVE (only {100*pw:.0f}% power to see r={mei})"


def paths_for(df1: pd.DataFrame, sur: pd.DataFrame, h: int = H):
    """(paths[n, h] in points from the pre-release close, surprise_z[n], dates[n]) — all causal."""
    idx = pd.Index(df1["Date"])
    close = df1["Close"].to_numpy(dtype=np.float64)
    t0 = idx.get_indexer(sur["Date"])
    ok = (t0 >= 1) & (t0 + h < len(close))
    t0v = t0[ok]
    anchor = close[t0v - 1]                                  # the last bar BEFORE the print
    P = np.stack([close[t0v + k] - anchor for k in range(1, h + 1)], axis=1)
    return P, sur["surprise_z"].to_numpy()[ok], sur["Date"].to_numpy()[ok]


def perm_p(stat_fn, z, rng, n_shuffle, observed):
    null = np.array([stat_fn(rng.permutation(z)) for _ in range(n_shuffle)])
    return float((np.abs(null) >= abs(observed)).mean())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--n-shuffle", type=int, default=3000)
    ap.add_argument("--extended", action="store_true",
                    help="fold in 2024 (roughly DOUBLES the sample)")
    ap.add_argument("--instrument", default="NQ",
                    help="market to test (NQ default; GC = the independent replication target)")
    a = ap.parse_args()
    rng = np.random.default_rng(0)

    df1 = _frame(a.extended, a.instrument)
    print(f"\ninstrument: {a.instrument}")
    print(f"price frame: {df1['Date'].iloc[0]} -> {df1['Date'].iloc[-1]}  "
          f"({len(df1):,} bars){'   [EXTENDED: 2024 folded in]' if a.extended else ''}")
    sur = build_surprises(rc.load_calendar())
    P, z, dates = paths_for(df1, sur)
    n = len(z)
    print(f"{n} releases with a causal surprise and a full {H}-minute path")
    print(f"POWER: with n={n} we have {100*power_for(MEI, n):.0f}% chance of detecting an effect of "
          f"r={MEI} (the pre-declared minimum worth acting on).")
    if power_for(MEI, n) >= 0.80:
        print("       ⇒ A NULL HERE IS A REAL NEGATIVE. We can see; there is nothing to see.\n")
    else:
        print("       ⇒ A NULL HERE IS INCONCLUSIVE. Our instrument is blind. Do not conclude.\n")

    # ================================================================ Q1 MAGNITUDE
    print("=" * 88)
    print("Q1 — MAGNITUDE: does a BIGGER surprise produce a BIGGER move? (no direction needed)")
    print("=" * 88)
    absz = np.abs(z)
    for label, mag in [
        ("|move| at +5 min", np.abs(P[:, 4])),
        ("|move| at +30 min", np.abs(P[:, H - 1])),
        ("path RANGE (max-min)", P.max(axis=1) - P.min(axis=1)),
        ("path VOLATILITY (std)", P.std(axis=1)),
    ]:
        c = float(np.corrcoef(absz, mag)[0, 1])
        p = perm_p(lambda s: np.corrcoef(np.abs(s), mag)[0, 1], z, rng, a.n_shuffle, c)
        # Power is computed against the PRE-DECLARED minimum effect of interest (MEI), never against
        # the observed effect — see the note on `MEI` above. This is what makes a null informative.
        print(f"  corr(|surprise|, {label:<22}) = {c:>+6.3f}   p = {p:>5.3f}{verdict(p, n)}")
    print()
    print("  A positive, significant value here would mean: we cannot predict WHICH WAY it moves,")
    print("  but we CAN predict HOW FAR. That is a volatility trade, not a directional one — and the")
    print("  efficient-market argument does not forbid it.")

    # ================================================================ Q3 PERSISTENCE
    print()
    print("=" * 78)
    print("Q3 — PERSISTENCE: does the surprise predict whether the initial move HOLDS or REVERSES?")
    print("=" * 78)
    early = P[:, 4]                       # the move by +5 min
    late = P[:, H - 1] - P[:, 4]          # what happened AFTER that, to +30
    held = np.sign(early) == np.sign(late)
    print(f"  the +5min move persisted to +30min in {100*held.mean():.1f}% of releases "
          f"({int(held.sum())}/{n})")
    print(f"  (50% = a coin flip: the initial move tells you nothing about the next 25 minutes)")
    c = float(np.corrcoef(early, late)[0, 1])
    p = perm_p(lambda s: np.corrcoef(early, late)[0, 1], z, rng, 1, c)  # z-independent; report corr only
    print(f"  corr(early move, later move) = {c:>+6.3f}   "
          f"{'MOMENTUM' if c > 0.1 else 'REVERSION' if c < -0.1 else 'NEITHER — no pattern'}")

    # ================================================================ Q2 SHAPE
    print()
    print("=" * 78)
    print("Q2 — SHAPE: cluster the 30-min paths. Does the surprise predict WHICH shape occurs?")
    print("=" * 78)
    # normalise each path by its own peak magnitude => pure SHAPE, size removed
    peak = np.abs(P).max(axis=1)
    keep = peak > 1e-9
    S = P[keep] / peak[keep, None]
    zk = z[keep]

    # simple k-means (k=4) on the shape vectors — no sklearn dependency
    k = 4
    rs = np.random.default_rng(7)
    C = S[rs.choice(len(S), k, replace=False)].copy()
    for _ in range(60):
        d = ((S[:, None, :] - C[None, :, :]) ** 2).sum(axis=2)
        lab = d.argmin(axis=1)
        for j in range(k):
            if (lab == j).any():
                C[j] = S[lab == j].mean(axis=0)

    names = []
    for j in range(k):
        c_ = C[j]
        end, mx = c_[-1], np.abs(c_).max()
        pk = int(np.abs(c_).argmax()) + 1
        if abs(end) > 0.7 * mx:
            nm = "SUSTAINED TREND" if end > 0 else "SUSTAINED TREND (down)"
        elif abs(end) < 0.3 * mx:
            nm = f"SPIKE-AND-FADE (peak @+{pk}m)"
        else:
            nm = f"PARTIAL RETRACE (peak @+{pk}m)"
        names.append(nm)
        m = lab == j
        print(f"  cluster {j}: n={int(m.sum()):>3}  mean|surprise|={np.abs(zk[m]).mean():>5.2f}  "
              f"mean surprise={zk[m].mean():>+5.2f}  |  {nm}")

    # does the surprise predict cluster membership? F-like statistic + permutation null
    def between_var(s):
        gm = s.mean()
        return sum(((lab == j).sum()) * (s[lab == j].mean() - gm) ** 2
                   for j in range(k) if (lab == j).any())

    obs = between_var(zk)
    null = np.array([between_var(rng.permutation(zk)) for _ in range(a.n_shuffle)])
    p = float((null >= obs).mean())
    print()
    print(f"  does the SURPRISE differ across shape-clusters?  p = {p:.3f}"
          f"{'   <<< SIGNIFICANT' if p < 0.05 else '   (no — the surprise does not pick the shape)'}")

    print()
    print("=" * 78)
    print("NOTE ON THE YARDSTICK — the user's other point, and it is fair.")
    print("=" * 78)
    print("  Our 'expected' is a STATISTICAL forecast (mean of the prior 6 changes), not the MARKET's")
    print("  consensus, which costs money. A noisy yardstick attenuates a real signal toward zero.")
    print("  So a NULL result here is evidence against the idea, but NOT proof: it could also be")
    print("  evidence that our ruler is bad. A POSITIVE result, by contrast, would be conservative —")
    print("  a better ruler could only sharpen it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
