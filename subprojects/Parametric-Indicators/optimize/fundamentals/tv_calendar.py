"""WS-NEWS2 (#114) — the TradingView economic calendar: loader, normaliser and verifier.

WHY THIS IS THE SOURCE WE USE

Seven sources were probed and rejected before this one (SOURCE-EVALUATION-consensus.md). Every failure
was one of two kinds: **access** (403) or **dates** (no usable timestamp).

    investing.com      403 to curl everywhere; WebFetch renders TODAY only
    ForexFactory       200 for 3 requests, then 403 to everything including WebFetch
    Trading Economics  site ignores its own date params; guest API discontinued (410)
    FXStreet           401
    Econoday           date params ignored — returns the current week for a 2010 request
    DailyFX            403
    Nasdaq API         values correct, but NO DATE FIELD and an unreliable date parameter

TradingView's public calendar endpoint has neither problem:

    https://economic-calendar.tradingview.com/events?from=<iso>&to=<iso>&countries=US

⭐ It returns a real ISO-8601 **UTC** timestamp per event, with daylight saving correctly encoded.
   Verified: Nonfarm Payrolls is 13:30Z in winter and 12:30Z in summer — **both 08:30 US-Eastern**.
   164 of 166 NFP rows land exactly on 08:30 ET. That is the exact property whose absence disqualified
   the Nasdaq API and whose mishandling cost 22 events in the earnings workstream (#110).

⚠️ THE FILE IS NAMED 2010 BUT THE DATA STARTS 2013-01-04.
   TradingView returns `{"status":"no_data"}` for anything before 2013 — confirmed by direct request for
   2010-01 and 2012-06. The scrape asked for 2010 and got nothing for the first three years. Anyone
   reading the filename would reasonably assume 2010 coverage. **It is 2013-01-04 → 2026-08-31.**

⚠️⚠️ `indicator` IS A CATEGORY. `title` IS THE EVENT.
   205 distinct `indicator` values vs **649** distinct `title` values. The indicator "Interest Rate"
   carries 3,653 rows because it includes "Fed Williams Speech", "Fed Bostic Speech", FOMC projections
   and the actual decision. **Joining on `indicator` silently mixes speeches into rate decisions.**
   Always key on `title`.

⚠️ TradingView has a CASING INCONSISTENCY IN ITS OWN DATA: both `Inflation Rate MoM` (1 row) and
   `Inflation Rate Mom` (157 rows) exist. Matching case-sensitively on the obvious spelling finds 1 row
   and looks like a coverage gap. Normalisation lower-cases the key.

IMPORTANCE, and how it maps to the star ratings the owner filters on:

    importance  1  = HIGH    (3 stars)   2,118 rows
    importance  0  = MEDIUM  (2 stars)  16,474 rows
    importance -1  = LOW     (1 star)   20,629 rows

    python3 optimize/fundamentals/tv_calendar.py --verify
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

HERE = Path(__file__).resolve().parent
RAW = HERE / "tradingview" / "tv_us_calendar_raw.csv"
OUT = HERE / "tradingview" / "tv_us_events.csv"
FRED_CAL = HERE / "us_high_impact.csv"

IMPORTANCE = {1: "high", 0: "medium", -1: "low"}

# Our FRED slug -> the TradingView TITLE (not indicator) that is the same print.
# ⚠️ Verified against the data, not guessed. `Inflation Rate Mom` is TradingView's own casing.
FRED_TO_TV: dict[str, list[str]] = {
    "nonfarm_payrolls": ["Non Farm Payrolls"],
    "cpi":              ["Inflation Rate Mom", "Inflation Rate MoM", "Core Inflation Rate MoM"],
    "ppi":              ["PPI MoM", "Producer Price Inflation MoM", "Core PPI MoM"],
    # ⚠️ GDP is published THREE TIMES per quarter — Advance, 2nd Estimate, Final — each a separate
    # market-moving release with its own consensus. Mapping only one of them matched 27% of FRED dates
    # and looked like a coverage failure; it was a structural misunderstanding of the release.
    "gdp":              ["GDP Growth Rate QoQ Adv", "GDP Growth Rate QoQ 2nd Est",
                         "GDP Growth Rate QoQ Final", "GDP Growth Rate QoQ"],
    "pce":              ["Core PCE Price Index MoM", "PCE Price Index MoM"],
    "retail_sales":     ["Retail Sales MoM"],
    "fomc":             ["Fed Interest Rate Decision"],
}


def load(raw: Path = RAW):
    """Normalised US events: UTC + true US-Eastern wall-clock, importance labelled, title as the key."""
    import pandas as pd

    d = pd.read_csv(raw, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    # ⚠️ tz_localize(None) AFTER converting to New York: this yields Eastern WALL-CLOCK, the same
    # convention the NQ price frame uses. Doing it in the other order silently keeps UTC.
    d["event_et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)
    d["impact"] = d["importance"].map(IMPORTANCE).fillna("unknown")
    d["title_key"] = d["title"].astype(str).str.strip().str.lower()
    return d


def verify(d) -> int:
    import pandas as pd
    fails: list[str] = []
    print("=" * 96)
    print("TRADINGVIEW CALENDAR — VERIFICATION")
    print("=" * 96)
    print(f"  rows                : {len(d):,}")
    print(f"  span (ET)           : {d.event_et.min()} -> {d.event_et.max()}")
    print(f"  distinct indicators : {d.indicator.nunique():,}")
    print(f"  distinct TITLES     : {d.title.nunique():,}   <- the real event identity")
    print(f"  impact mix          : {d.impact.value_counts().to_dict()}")

    trip = d.dropna(subset=["actual", "forecast", "previous"])
    print(f"  rows with actual+forecast+previous : {len(trip):,} ({100*len(trip)/len(d):.1f}%)")

    # 1. ⚠️ TIMEZONE — the check that disqualified two other sources.
    nfp = d[d.title == "Non Farm Payrolls"]
    t = nfp.event_et.dt.strftime("%H:%M").value_counts()
    print(f"\n  Nonfarm Payrolls    : {len(nfp)} rows; ET times {t.head(3).to_dict()}")
    print("  ^ NFP is 08:30 US-Eastern YEAR-ROUND. A fixed-offset source shows 09:30 in winter.")
    if t.empty or t.index[0] != "08:30":
        fails.append(f"NFP dominant ET time is {t.index[0] if not t.empty else 'n/a'}, expected 08:30")
    else:
        share = t.iloc[0] / len(nfp)
        print(f"  ✅ {share:.1%} of NFP rows are exactly 08:30 ET — DST is correctly encoded")

    # 2. span honesty
    if d.event_et.min() > pd.Timestamp("2013-06-01"):
        fails.append("span starts later than 2013 — check the scrape")
    print(f"\n  ⚠️ coverage starts {d.event_et.min():%Y-%m-%d}, NOT 2010 — TradingView returns "
          f"no_data before 2013 (verified by direct request)")

    # 3. cross-check dates against the authoritative FRED calendar
    if FRED_CAL.exists():
        fred = pd.read_csv(FRED_CAL, parse_dates=["Date"])
        print("\n  CROSS-CHECK vs FRED release dates (overlap 2013+):")
        print(f"    {'FRED event':<18}{'FRED n':>7}{'TV n':>6}{'exact ET':>10}{'same day':>10}{'match':>8}")
        for ev, titles in FRED_TO_TV.items():
            f = fred[(fred.event == ev) & (fred.Date >= "2013-01-01")]
            t_ = d[d.title.isin(titles)]
            fset = {pd.Timestamp(x) for x in f.Date}
            tset = {pd.Timestamp(x) for x in t_.event_et}
            exact = len(fset & tset)
            day = len({x.date() for x in fset} & {x.date() for x in tset})
            rate = exact / max(len(f), 1)
            print(f"    {ev:<18}{len(f):>7}{len(t_):>6}{exact:>10}{day:>10}{rate:>7.0%}")

    print("\n  " + ("ALL CHECKS PASSED" if not fails else "FAILURES:"))
    for f_ in fails:
        print(f"    ❌ {f_}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--write", action="store_true", help="write the normalised events table")
    a = ap.parse_args()

    d = load()
    rc = verify(d) if (a.verify or not a.write) else 0
    if a.write:
        cols = ["event_et", "utc", "title", "indicator", "impact", "importance", "actual", "forecast",
                "previous", "actualRaw", "forecastRaw", "previousRaw", "unit", "scale", "period",
                "referenceDate", "source", "ticker", "id"]
        d[cols].sort_values("event_et").to_csv(OUT, index=False)
        print(f"\nwrote {len(d):,} normalised rows -> {OUT}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
