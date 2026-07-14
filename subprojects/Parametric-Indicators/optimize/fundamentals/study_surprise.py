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


_CACHE = Path(__file__).parent / "surprises_cache.csv"
_CACHE_SIG = Path(__file__).parent / "surprises_cache.sig"


def _calendar_signature(cal: pd.DataFrame) -> str:
    """A fingerprint of the calendar that PRODUCED a cache.

    The cache is valid iff it was built from THIS calendar. Anything else is a guess.
    """
    ev = "|".join(f"{e}:{int((cal['event'] == e).sum())}" for e in sorted(SERIES))
    return f"n={len(cal)} {cal['Date'].min()} -> {cal['Date'].max()} {ev}"


def build_surprises(cal: pd.DataFrame, lookback: int = LOOKBACK,
                    use_cache: bool = True) -> pd.DataFrame:
    """One row per release we can price: (Date, event, actual, expected, surprise_z).

    CACHED. Building this from scratch pulls one ALFRED point-in-time vintage PER RELEASE — ~1,150 API
    calls over 17 years, roughly ten minutes. And the answers are IMMUTABLE: a point-in-time vintage is,
    by definition, what the number was on a date that has already passed. It cannot change. So we cache
    it to disk and only refetch when the calendar grows.

    Pass use_cache=False to force a rebuild.
    """
    sig = _calendar_signature(cal)
    if use_cache and _CACHE.exists() and _CACHE_SIG.exists():
        # VALID IFF IT WAS BUILT FROM THIS EXACT CALENDAR.
        #
        # The previous check compared the cache's DATE SPAN against the calendar's, and it could never
        # pass. The calendar legitimately contains releases the cache can never hold: FUTURE scheduled
        # dates (out to 2026-12-09 — no vintage exists yet, and no price either) and releases from before
        # our price history begins. So the cache's span is ALWAYS narrower than the calendar's, the check
        # always said "stale", and 945 ALFRED fetches were re-run on every single invocation while the
        # log cheerfully printed "rebuilding" as though that were normal.
        #
        # A cache that never hits is not a cache. Fingerprint the calendar instead: identical calendar =>
        # identical vintages (a point-in-time vintage is immutable by definition), so the cache is exact.
        if _CACHE_SIG.read_text().strip() == sig:
            c = pd.read_csv(_CACHE, parse_dates=["Date"])
            print(f"  [cache] HIT — {len(c)} surprises from {_CACHE.name} "
                  f"({c['Date'].min().date()} -> {c['Date'].max().date()}); skipping ALFRED entirely")
            return c
        print(f"  [cache] MISS — the calendar changed since this cache was built. Rebuilding.")
        print(f"          cached: {_CACHE_SIG.read_text().strip()}")
        print(f"          now:    {sig}")

    import time as _t
    rows = []
    total = sum(int((cal["event"] == e).sum()) for e in SERIES)
    done = 0
    # TWO KINDS OF DROP, AND CONFLATING THEM COST A HEALTHY RUN ITS LIFE ON 2026-07-14.
    #
    #   expected  — the series has no ALFRED vintage that far back. PPIFIS starts 2014-02-19, so all 43
    #               PPI releases in our 2010-2026 calendar before that date return HTTP 400. This is a
    #               FACT ABOUT THE DATA. It is permanent, it is fine, and it needs no alarm.
    #   transient — a 502/timeout. THIS IS A REAL, RECOVERABLE LOSS: one 502 on PAYEMS 2016-02-05 silently
    #               cost us a genuine payrolls release, and the same request succeeded on retry.
    #
    # Reported as one undifferentiated "errors=44", these are indistinguishable — so 43 expected drops
    # masked 1 real one, and I misread the whole thing as a degradation and killed the run.
    expected_drops: list[str] = []
    transient_fails: list[str] = []
    t0 = _t.time()
    print(f"  [fetch] {total} ALFRED point-in-time vintages to pull "
          f"(one per release — this is the slow part)", flush=True)

    for event, (sid, kind) in SERIES.items():
        ev = cal[cal["event"] == event].sort_values("Date")
        raw = []
        for ts in ev["Date"]:
            done += 1
            # PROGRESS — every 25 vintages, with a rate and an ETA.
            #
            # WHY flush=True MATTERS: Python BUFFERS stdout when it is redirected to a file. Without
            # the flush, a 10-minute run writes an EMPTY log and looks indistinguishable from a hang.
            # That is a silent failure by construction, and it bit us on 2026-07-14.
            if done % 25 == 0 or done == total:
                el = _t.time() - t0
                rate = done / el if el > 0 else 0
                eta = (total - done) / rate if rate > 0 else 0
                # The two counts are reported SEPARATELY. "expected" is allowed to be large and boring;
                # "TRANSIENT" is the one that must never be nonzero, and it is spelled loudly.
                print(f"  [fetch] {done:>5}/{total}  ({100*done/total:>5.1f}%)  "
                      f"{rate:>5.1f}/s  eta {eta/60:>5.1f} min  "
                      f"expected-drops={len(expected_drops)}  "
                      f"TRANSIENT-FAILS={len(transient_fails)}", flush=True)
            try:
                v = alfred.vintage(sid, ts.strftime("%Y-%m-%d"))
            except alfred.SeriesNotInAlfred:
                # Permanent and expected: this series simply did not exist yet. Not a failure.
                expected_drops.append(f"{event} {ts.date()}")
                continue
            except Exception as e:                       # noqa: BLE001
                # Survived all retries. This is a genuine hole in the sample.
                transient_fails.append(f"{event} {ts.date()}: {e}")
                print(f"  🚨 TRANSIENT FAIL (survived {alfred.RETRIES} retries) "
                      f"{event} {ts.date()}: {e}", flush=True)
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
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows).sort_values("Date").reset_index(drop=True)

    # ---- THE FETCH LEDGER — say out loud what we got and what we lost --------------------------------
    print()
    print(f"  [fetch] DONE. {len(out)} surprises from {total} calendar releases.")
    if expected_drops:
        by_ev: dict[str, int] = {}
        for d in expected_drops:
            by_ev[d.split()[0]] = by_ev.get(d.split()[0], 0) + 1
        print(f"  [fetch] {len(expected_drops)} EXPECTED drops (series predates ALFRED's archive — "
              f"permanent, not a failure):")
        for ev, n in sorted(by_ev.items()):
            print(f"            {ev}: {n}")

    # ---- THE GATE: a cache with silent holes in it is worse than no cache ----------------------------
    #
    # A transient failure drops a release. If we then WRITE that sample to the cache, every future run
    # HITS the degraded cache and the hole becomes PERMANENT — a network blip from one afternoon, baked
    # into every study forever, invisible. That is the single most dangerous outcome in this module.
    #
    # So: any surviving transient failure and we refuse to cache. The study still runs (you get the
    # DataFrame back), but nothing is persisted, and a re-run will fetch cleanly.
    if transient_fails:
        print()
        print(f"  🚨 {len(transient_fails)} TRANSIENT FAILURE(S) SURVIVED {alfred.RETRIES} RETRIES:")
        for f in transient_fails:
            print(f"       {f}")
        print(f"  🚨 REFUSING TO WRITE THE CACHE. These are real, recoverable releases — caching this")
        print(f"     sample would bake the holes in permanently. Re-run to fetch them.")
        return out

    out.to_csv(_CACHE, index=False)          # immutable by construction — safe to cache forever
    _CACHE_SIG.write_text(sig)               # ...but ONLY for the calendar that produced it
    print(f"  [cache] wrote {len(out)} surprises -> {_CACHE.name}  (0 transient failures — clean)")
    return out


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
    ap.add_argument("--extended", action="store_true",
                    help="fold in 2024 (roughly DOUBLES the sample)")
    a = ap.parse_args()

    if a.extended:
        from optimize.fundamentals.extended_data import load_1m_extended
        df1 = load_1m_extended("NQ")
        print(f"[EXTENDED] price frame {df1['Date'].iloc[0]} -> {df1['Date'].iloc[-1]} "
              f"({len(df1):,} bars)")
    else:
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
