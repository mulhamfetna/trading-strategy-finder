"""#116 — the Phase 2 pair matrix, derived rather than guessed.

WHY THIS EXISTS. #116 was written before we had a calendar and states "~30 releases x 9 instruments =
~270 pairs". I then "corrected" that to 927 (103 series x 9 instruments) — and that was ALSO WRONG, in
a way that only checking the PRICE side exposes:

⚠️⚠️ HISTORY OF THIS NUMBER, because it has been wrong twice and both errors are instructive:

   270   the issue's original guess, made before we had a calendar
   927   my "correction" — 103 series x 9 instruments. ALSO WRONG: it assumed all nine instruments had
         the 2016+ era, when seven of them held only eighteen months. I counted the EVENT side and
         never checked the PRICE side. It also made me headline "EIA Crude Oil -> CL, ~510 releases"
         when the CL frame reached 79 of them — wrong by ~6x.
   221   the decidable matrix under the 18-month constraint
   643   ⭐ CURRENT. The owner supplied long history on 2026-08-12 and every frame passed the #121
         acceptance gate (volume-profile rho=1.000 and 100.0000% identical Close on the overlap).

   The lesson that survives all of it: A JOIN HAS TWO SIDES, AND AN `n` QUOTED FROM ONE OF THEM IS NOT
   AN `n`.

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

RESULT: 643 decidable pairs across 8 instruments (YM excluded — its 1-minute frame is empty).

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

# ---- ⭐ UPDATED 2026-08-15: the owner supplied long history for the missing instruments, and every
# frame passed the #121 acceptance gate (volume-profile agreement rho=1.000 and 100.0000% identical
# Close on the overlap, for all eight). The 18-month constraint is GONE.
#
# ⚠️ But the floor is now PER INSTRUMENT, not global. The gate reported, for each frame, the first year
# with full bar coverage — pre-2016 the source is sparse and the sparsity differs by instrument. Using
# one global floor would either throw away good years (HG/SI/GC are complete from 2011) or admit thin
# ones (RTY only from 2019, NG from 2017).
#
#   instrument   full coverage from   note
#   NQ, ES, CL   2016                 sparse 2010-2012, tapering
#   NG           2017
#   GC, HG, SI   2011
#   RTY          2019                 the contract itself only lists from 2017-07
#   YM           n/a                  ⛔ EVERY aggregated frame is 0 bytes; only YM_1s.csv has data
#
# ⚠️ The CALENDAR floor is 2016 regardless (the TradingView DST defect, #114), so the effective floor
# is max(2016, instrument floor). HG/SI/GC gain nothing from their earlier data for THIS study.
INSTRUMENT_FLOOR = {
    "NQ": 2016, "GC": 2016, "ES": 2016, "CL": 2016, "HG": 2016, "SI": 2016,
    "NG": 2017, "RTY": 2019,
}
# ⛔ YM is EXCLUDED: its 1-minute frame is empty. See #121.
EXCLUDED_INSTRUMENTS = {"YM": "every aggregated frame is 0 bytes; the 1s source exists but the "
                              "resample produced nothing and raised no error"}
SPAN_END = "2026-08-07"

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
    out: list[tuple[str, str, int]] = []
    for inst, floor in INSTRUMENT_FLOOR.items():
        sub = t[(t.et >= f"{floor}-01-01") & (t.et <= SPAN_END)]
        for k, v in sub.groupby("title").size().items():
            out.append((str(k), inst, int(v)))
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
    print(f"  history of this number: 270 (guess) -> 927 (wrong: assumed all 9 instruments had the")
    print(f"     2016+ era) -> 221 (18-month constraint) -> {len(q)} (long history supplied, #121)")
    print(f"  ⛔ excluded instruments: {EXCLUDED_INSTRUMENTS}")
    print(f"  per-instrument study floor: {INSTRUMENT_FLOOR}")
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
