"""Does the CONTENT of a release predict which way NQ moves? The free gate before any vendor spend.

THE USER'S THESIS, tested: "the whole reason of analysing the news content instead of just knowing its
time is to invest in the volatility time smartly." Two free studies have now closed every path that
uses TIMING ALONE — the veto (defensive) and the price-reaction trade (offensive). If content matters,
this is where it shows up.

WHAT A SURPRISE IS. actual - expectation. The expensive half is the MARKET's expectation (the
economist consensus, sold by vendors). The free half is the actual, which ALFRED gives us as the
FIRST PRINT (see alfred.py: 2025 payrolls were later revised by ~1M jobs, so this distinction is not
academic).

So we build a STATISTICAL expectation instead: what a reasonable forecaster would have predicted using
ONLY the numbers published before that morning. Weaker than the true consensus — but it answers the
question that actually gates the spend: does the number's CONTENT predict direction AT ALL? If not,
the paid consensus must carry the whole signal alone, which is a far higher bar and worth knowing
BEFORE paying.

CAUSALITY — the whole game.
  For a release on morning D of series S:
    vintage   = ALFRED S as of D           (every value as it stood that morning, nothing later)
    actual    = the change just published  = last(vintage) - second_last(vintage)
    expected  = mean of the previous LOOKBACK changes WITHIN THAT SAME VINTAGE
    surprise  = (actual - expected) / rolling sd of past surprises      (standardized, unitless)
    outcome   = NQ return from close[D 08:29] -> close[D 08:30 + h]
  The expectation uses only pre-D publications. The outcome is entirely after the print. Nothing peeks.

  NOTE we do NOT impose a sign. Whether strong jobs are bullish (growth) or bearish (hawkish Fed) is
  regime-dependent and arguing about it is how people fool themselves. We MEASURE the correlation.

HONESTY. The null is a SHUFFLE of the surprises across releases: same surprise values, same release
dates, randomly re-paired. That destroys any real link between content and outcome while preserving
both distributions exactly. If the real pairing is not distinguishable from a shuffled one, the
content carries no signal. Same discipline that killed the previous two heads.

  python3 optimize/fundamentals/study_surprise.py --n-shuffle 2000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import data                                     # noqa: E402
from optimize.fundamentals import alfred                      # noqa: E402
from optimize.fundamentals import release_calendar as rc      # noqa: E402

# event slug -> (FRED series, how the market reads it)
#   "diff"  : the market trades the CHANGE (payrolls: jobs added this month)
#   "pct"   : the market trades the PERCENT change (price indexes: monthly inflation)
SERIES = {
    "nonfarm_payrolls": ("PAYEMS",     "diff"),
    "cpi":              ("CPIAUCSL",   "pct"),
    "ppi":              ("PPIFIS",     "pct"),
    "retail_sales":     ("RSAFS",      "pct"),
    "pce":              ("PCEPI",      "pct"),
}
LOOKBACK = 6          # months of prior changes used to form the naive expectation
HS = [5, 15, 30, 60]  # minutes held after the print


def build_surprises(cal: pd.DataFrame, lookback: int = LOOKBACK) -> pd.DataFrame:
    """One row per release we can price: (Date, event, actual, expected, surprise_z)."""
    rows = []
    for event, (sid, kind) in SERIES.items():
        ev = cal[cal["event"] == event].sort_values("Date")
        raw = []
        for ts in ev["Date"]:
            try:
                v = alfred.vintage(sid, ts.strftime("%Y-%m-%d"))
            except Exception as e:                       # noqa: BLE001
                print(f"  ! {event} {ts.date()}: {e}")
                continue
            chg = v.diff() if kind == "diff" else v.pct_change() * 100.0
            chg = chg.dropna()
            if len(chg) < lookback + 1:
                continue
            actual = float(chg.iloc[-1])                        # the number just published
            expected = float(chg.iloc[-(lookback + 1):-1].mean())   # from PRIOR publications only
            raw.append({"Date": ts, "event": event, "actual": actual,
                        "expected": expected, "raw_surprise": actual - expected})
        if len(raw) < 8:
            print(f"  ! {event}: only {len(raw)} usable releases — skipped")
            continue
        d = pd.DataFrame(raw)
        # standardize WITHIN the event type: a 50k payrolls miss and a 0.1pp CPI miss are not comparable
        # in raw units. Expanding (not full-sample) sd so the scaling itself stays causal.
        sd = d["raw_surprise"].expanding(min_periods=4).std().shift(1)
        d["surprise_z"] = d["raw_surprise"] / sd
        rows.append(d.dropna(subset=["surprise_z"]))
        print(f"  {event:<18} {sid:<10} {len(d):>3} releases")
    return pd.concat(rows).sort_values("Date").reset_index(drop=True) if rows else pd.DataFrame()


def outcomes(df1: pd.DataFrame, sur: pd.DataFrame, h: int) -> tuple[np.ndarray, np.ndarray]:
    """NQ return from the last bar BEFORE the print to h minutes after it. Causal by construction."""
    idx = pd.Index(df1["Date"])
    close = df1["Close"].to_numpy(dtype=np.float64)
    t0 = idx.get_indexer(sur["Date"])
    ok = (t0 >= 1) & (t0 + h < len(close)) & (t0 >= 0)
    t0 = t0[ok]
    ret = close[t0 + h] / close[t0 - 1] - 1.0
    return sur["surprise_z"].to_numpy()[ok], ret


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--n-shuffle", type=int, default=2000)
    a = ap.parse_args()

    _, df1, *_ = data.load_inputs(a.tf)
    cal = rc.load_calendar()

    print("Pulling ALFRED first-print vintages (one per release)...\n")
    sur = build_surprises(cal)
    if sur.empty:
        print("no usable surprises")
        return 1
    print(f"\n{len(sur)} priced releases with a causal surprise\n")

    rng = np.random.default_rng(0)
    print(f"{'h':>4} {'n':>4} | {'corr':>7} {'sign-hit':>9} | {'shuffled corr':>16} | {'p':>6}")
    print("-" * 62)
    any_sig = False
    for h in HS:
        z, ret = outcomes(df1, sur, h)
        if len(z) < 30:
            continue
        corr = float(np.corrcoef(z, ret)[0, 1])
        # does the surprise predict the SIGN of the move?
        hit = float((np.sign(ret) == np.sign(z)).mean())

        # NULL: shuffle the surprises against the outcomes. Preserves both distributions exactly,
        # destroys only the pairing — i.e. exactly the thing under test.
        null = np.array([abs(np.corrcoef(rng.permutation(z), ret)[0, 1])
                         for _ in range(a.n_shuffle)])
        p = float((null >= abs(corr)).mean())
        any_sig |= p < 0.05
        star = "  <<<" if p < 0.05 else ""
        print(f"{h:>4} {len(z):>4} | {corr:>+7.3f} {100*hit:>8.1f}% | "
              f"{null.mean():>7.3f} ±{null.std():>6.3f} | {p:>6.3f}{star}")

    print()
    if not any_sig:
        print("VERDICT: no link between the surprise and the move. A statistical expectation carries")
        print("         no signal, so the paid consensus would have to carry ALL of it alone.")
        print("         That is a much higher bar — decide deliberately before spending.")
        return 0

    # ---------------------------------------------------------------- THE REAL TEST
    # In-sample structure means nothing until it survives data it has never seen. The sign of the
    # relationship is FROZEN on 2025 and applied unchanged to 2026. No refitting, no horizon shopping.
    print("=" * 62)
    print("OUT OF SAMPLE — fit the sign on 2025, apply it unchanged to 2026")
    print("=" * 62)
    is_mask = sur["Date"].dt.year == 2025
    print(f"  in-sample (2025): {int(is_mask.sum())} releases   "
          f"out-of-sample (2026): {int((~is_mask).sum())} releases")
    print(f"  NOTE: {int((~is_mask).sum())} OOS events is very few. Low power — a null result here is")
    print("        weak evidence against, and a positive one is weak evidence for.\n")

    print(f"{'h':>4} | {'2025 corr':>10} {'sign':>5} | {'2026 corr':>10} | "
          f"{'2026 $/trade':>12} {'2026 hit':>9} | {'holds?':>7}")
    print("-" * 72)
    for h in HS:
        z, ret = outcomes(df1, sur, h)
        yr = sur["Date"].dt.year.to_numpy()[
            (pd.Index(df1["Date"]).get_indexer(sur["Date"]) >= 1)]
        if len(z) != len(yr):
            yr = yr[:len(z)]
        m25, m26 = yr == 2025, yr == 2026
        if m25.sum() < 15 or m26.sum() < 8:
            continue
        c25 = float(np.corrcoef(z[m25], ret[m25])[0, 1])
        c26 = float(np.corrcoef(z[m26], ret[m26])[0, 1])
        side = -np.sign(c25)          # the 2025 rule, frozen: trade AGAINST a positive surprise if c25<0
        pnl26 = side * np.sign(z[m26]) * ret[m26]        # fractional return per unit
        hit26 = float((np.sign(pnl26) > 0).mean())
        holds = "YES" if np.sign(c26) == np.sign(c25) else "no"
        print(f"{h:>4} | {c25:>+10.3f} {int(side):>+5} | {c26:>+10.3f} | "
              f"{1e4*pnl26.mean():>+9.1f}bp {100*hit26:>8.1f}% | {holds:>7}")

    print()
    print("  'holds?' = did the 2026 correlation keep the SAME SIGN as 2025. If it flips, the")
    print("  relationship is regime-dependent and would have traded backwards out of sample.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
