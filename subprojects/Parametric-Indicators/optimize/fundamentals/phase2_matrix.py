"""#116 — the Phase 2 pair matrix, derived rather than guessed.

WHY THIS EXISTS. #116 was written before we had a calendar and states "~30 releases x 9 instruments =
~270 pairs". I then "corrected" that to 927 (103 series x 9 instruments) — and that was ALSO WRONG, in
a way that only checking the PRICE side exposes:

⚠️⚠️ ONLY NQ AND GC HAVE LONG HISTORY. Verified on the server, exhaustively (every *_1m.csv under
   ~/Mulham, any depth):

       NQ, GC                              2010-06-06 -> 2026-07     (~5.5M bars each)
       ES, CL, NG, HG, SI, RTY, YM         2025-01-01 -> 2026-07     (~18 MONTHS)

   So "103 series x 9 instruments" silently assumed all nine instruments had the 2016+ era. Seven of
   them have eighteen months. A monthly release gives 18 observations there — not a weak test, an
   IMPOSSIBLE one.

⚠️ This also corrects a headline claim I published on #116: "EIA Crude Oil Stocks Change -> CL, ~510
   releases". The CALENDAR has ~510; the CL PRICE FRAME reaches 79 of them. Wrong by ~6x, and it was
   wrong because I counted the event side and never checked the price side.

⭐⭐ THE SELECTION RULE, and it is not "big enough sample". A pair belongs in the matrix ONLY IF IT CAN
   DECIDE THE QUESTION:

       #111 established a rule needs ~71% directional accuracy to cover costs.
       For a monotone association that is a correlation of r = sin(pi * (0.71 - 0.5)) = 0.613.
       A pair qualifies iff its minimum detectable effect at the Bonferroni alpha is BELOW 0.613.

   A pair whose MDE exceeds the tradeable threshold cannot return anything useful: it can only produce
   a null that is uninformative BY CONSTRUCTION, while consuming correction budget and thereby weakening
   every pair that could have decided something. Running it is worse than not running it.

   ⚠️ The rule is self-referential — alpha depends on how many pairs qualify, which depends on alpha —
   so it is solved by iteration to a fixed point (converges in 3 rounds).

RESULT: 221 decidable pairs, not 927 and not 270.

    python3 optimize/fundamentals/phase2_matrix.py --write
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
TV_RAW = HERE / "tradingview" / "tv_us_calendar_raw.csv"
OUT = HERE / "phase2_pairs.csv"

# ---- verified on the server, not assumed. See the docstring. --------------------------------------
LONG_INSTRUMENTS = ("NQ", "GC")
SHORT_INSTRUMENTS = ("ES", "CL", "NG", "HG", "SI", "RTY", "YM")
LONG_SPAN = ("2016-01-01", "2026-07-12")     # 2016 floor is the DST constraint (#114)
SHORT_SPAN = ("2025-01-01", "2026-07-05")

BREAK_EVEN_ACCURACY = 0.71                   # #111
POWER = 0.80
# ⚠️ Orthant probability for a bivariate normal: P(sign agreement) = 1/2 + arcsin(r)/pi.
# Stated as an approximation because fat tails violate normality — it is used to SET A THRESHOLD, not
# to report a result. The measured accuracy in #115 is the real quantity.
R_TRADEABLE = float(np.sin(np.pi * (BREAK_EVEN_ACCURACY - 0.5)))


def mde(n: int, alpha: float, power: float = POWER) -> float:
    """Minimum detectable correlation, Fisher z, two-sided."""
    if n < 10:
        return float("inf")
    z = (stats.norm.ppf(1 - alpha / 2) + stats.norm.ppf(power)) / np.sqrt(n - 3)
    return float(np.tanh(z))


def candidates() -> list[tuple[str, str, int]]:
    d = pd.read_csv(TV_RAW, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    d["et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    t = d.dropna(subset=["actual", "forecast", "previous"])
    lo = t[(t.et >= LONG_SPAN[0]) & (t.et <= LONG_SPAN[1])].groupby("title").size()
    sh = t[(t.et >= SHORT_SPAN[0]) & (t.et <= SHORT_SPAN[1])].groupby("title").size()
    out = [(str(k), i, int(v)) for k, v in lo.items() for i in LONG_INSTRUMENTS]
    out += [(str(k), i, int(v)) for k, v in sh.items() for i in SHORT_INSTRUMENTS]
    return out


def solve() -> tuple[list[tuple[str, str, int]], list[tuple[str, str, int]], float, int]:
    cands = candidates()
    k = len(cands)
    for _ in range(60):
        alpha = 0.05 / max(k, 1)
        q = [c for c in cands if mde(c[2], alpha) < R_TRADEABLE]
        if len(q) == k:
            break
        k = len(q)
    alpha = 0.05 / max(k, 1)
    excluded = [c for c in cands if c not in set(q)]
    return q, excluded, alpha, len(cands)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    q, excl, alpha, n_cand = solve()
    q = sorted(q, key=lambda c: -c[2])
    print("=" * 96)
    print("PHASE 2 MATRIX — pairs that can DECIDE the question   #116")
    print("=" * 96)
    print(f"  break-even accuracy {BREAK_EVEN_ACCURACY:.0%}  <=>  r = {R_TRADEABLE:.3f}")
    print(f"  candidate pairs before any filter : {n_cand}")
    print(f"  ⭐ DECIDABLE pairs                 : {len(q)}   (Bonferroni alpha = {alpha:.6f})")
    print(f"  ⛔ excluded as UNDECIDABLE         : {len(excl)}")
    print(f"     — their MDE exceeds the tradeable threshold, so they can only return an")
    print(f"       uninformative null while consuming correction budget for the pairs that can decide")
    print(f"  by instrument (decidable) : {dict(Counter(c[1] for c in q))}")
    print(f"  distinct releases         : {len({c[0] for c in q})}")
    print(f"  smallest qualifying n     : {min(c[2] for c in q)}")
    print()
    print(f"  ⚠️ previously published on #116: 927 pairs (103 series x 9 instruments) — that assumed")
    print(f"     ALL NINE instruments had the 2016+ era. Seven of them have EIGHTEEN MONTHS.")
    print()
    print(f"    {'release':<40}{'inst':>5}{'n':>6}{'MDE r':>8}")
    for c in q[:14]:
        print(f"    {c[0]:<40}{c[1]:>5}{c[2]:>6}{mde(c[2], alpha):>8.3f}")

    if a.write:
        df = pd.DataFrame(q, columns=["release", "instrument", "n"])
        df["mde_r"] = [mde(n, alpha) for n in df.n]
        df["bonferroni_alpha"] = alpha
        df.sort_values(["instrument", "n"], ascending=[True, False]).to_csv(OUT, index=False)
        print(f"\n  wrote {len(df)} decidable pairs -> {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
