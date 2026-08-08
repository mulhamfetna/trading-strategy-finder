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

⚠️⚠️⚠️ **THE SUMMER HALF OF 2013-2015 IS SHIFTED ONE HOUR LATE. USE 2016+.**
   TradingView's early back-fill stored a FIXED winter offset (UTC-5) year-round, so every summer
   release converts to one hour later than it really was. Measured per year, counting series whose
   winter modal ET time disagrees with their summer modal ET time:

       2013   6/8    75% inconsistent        2016   7/105   7%
       2014  65/72   90% inconsistent        2017   2/103   2%
       2015  79/87   91% inconsistent        2018+  0-3%  (genuine schedule changes)

   87 pre-2016 series are affected, including `Initial Jobless Claims` (08:30 winter / 09:30 summer),
   `EIA Crude Oil Stocks Change` (10:30 / 11:30), `Retail Sales MoM`, `PPI MoM`, `ISM Manufacturing PMI`
   and `Fed Interest Rate Decision`. An event study run on those rows centres its window a full hour
   away from the release and is guaranteed to find nothing.

   ⚠️ **Nonfarm Payrolls is CLEAN pre-2016 (36/36 at 08:30).** That is exactly why the first
   verification pass — which checked NFP and only NFP — passed and I concluded the whole file was
   sound. A single-series timestamp check does not generalise; `--verify` now audits ALL series.

⚠️ TITLES FRAGMENT, so any title map must be read off the value counts rather than written from the
   obvious spelling: `Fed Press Conference` (68) vs `Fed Monetary Policy Statement and press
   conference` (5) vs `Fed press conference` (1). Normalisation lower-cases the key.
   (An earlier version of this docstring cited an `Inflation Rate Mom` / `Inflation Rate MoM` casing
   split. That was wrong — there is no lower-case variant; `Inflation Rate MoM` has 161 rows and the
   1-row neighbour is the distinct release `Inflation Rate MoM Final`. Corrected here and in #116.)

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

# ⚠️ The first year from which the timestamps are trustworthy across ALL series. See the DST note
# above. This is a property of the SOURCE, not a preference — everything downstream must respect it.
MIN_YEAR = 2016

# Our FRED slug -> the TradingView TITLE (not indicator) that is the same print.
# ⚠️ Verified against the data, not guessed. `Inflation Rate Mom` is TradingView's own casing.
FRED_TO_TV: dict[str, list[str]] = {
    "nonfarm_payrolls": ["Non Farm Payrolls"],
    "cpi":              ["Inflation Rate MoM", "Core Inflation Rate MoM"],
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

    # 1b. ⚠️⚠️ DST AUDIT ACROSS **ALL** SERIES — not just NFP.
    # A release happens at the same US-Eastern wall-clock time in January and in July. If a series'
    # winter modal time disagrees with its summer modal time, the stored UTC used a fixed offset and
    # the summer rows are an hour wrong. NFP alone passes even when 90% of the file is broken, which
    # is how this was missed the first time.
    print("\n  DST AUDIT — series whose WINTER modal ET time != their SUMMER modal ET time:")
    print(f"    {'year':>6}{'bad':>6}{'of':>6}{'share':>8}")
    era_bad: dict[int, float] = {}
    for yr, gy in d.groupby(d.event_et.dt.year):
        bad = tot = 0
        for t, g in gy.groupby("title"):
            # speeches, testimony and Treasury auctions genuinely move around the clock
            if any(k in t for k in ("Speech", "Testimony", "Auction", "Speaks")):
                continue
            win = g[g.event_et.dt.month.isin([1, 2, 12])]
            smr = g[g.event_et.dt.month.isin([6, 7, 8])]
            if len(win) < 3 or len(smr) < 3:
                continue
            tot += 1
            if win.event_et.dt.strftime("%H:%M").mode()[0] != smr.event_et.dt.strftime("%H:%M").mode()[0]:
                bad += 1
        if tot:
            era_bad[int(yr)] = bad / tot
            flag = "  <-- BROKEN" if bad / tot > 0.25 else ""
            print(f"    {int(yr):>6}{bad:>6}{tot:>6}{bad/tot:>7.0%}{flag}")

    broken = sorted(y for y, s in era_bad.items() if s > 0.25)
    if broken:
        print(f"\n  ⚠️⚠️ {len(broken)} year(s) fail the DST audit: {broken}")
        print(f"  ⚠️⚠️ USE {MIN_YEAR}+ ONLY. Pre-{MIN_YEAR} summer rows are one hour LATE; an event")
        print("        window built on them is centred an hour off the release and finds nothing.")
    if any(y >= MIN_YEAR for y in broken):
        fails.append(f"DST audit fails at or after MIN_YEAR={MIN_YEAR}: {[y for y in broken if y >= MIN_YEAR]}")

    # 2. span honesty
    if d.event_et.min() > pd.Timestamp("2013-06-01"):
        fails.append("span starts later than 2013 — check the scrape")
    print(f"\n  ⚠️ coverage starts {d.event_et.min():%Y-%m-%d}, NOT 2010 — TradingView returns "
          f"no_data before 2013 (verified by direct request)")
    print(f"  ⚠️ USABLE span after the DST audit: {MIN_YEAR}-01-01 -> {d.event_et.max():%Y-%m-%d}")

    # 3. cross-check dates against the authoritative FRED calendar
    if FRED_CAL.exists():
        fred = pd.read_csv(FRED_CAL, parse_dates=["Date"])
        # ⚠️ Run the cross-check on the USABLE era only. Scoring it from 2013 mixes TradingView's thin
        # back-fill and its DST defect into the match rate and makes a source problem look like a
        # coverage problem — which is how the earlier "77% GDP" reading arose.
        print(f"\n  CROSS-CHECK vs FRED release dates (usable era, {MIN_YEAR}+):")
        print(f"    {'FRED event':<18}{'FRED n':>7}{'TV n':>6}{'exact ET':>10}{'same day':>10}{'match':>8}")
        for ev, titles in FRED_TO_TV.items():
            f = fred[(fred.event == ev) & (fred.Date >= f"{MIN_YEAR}-01-01")]
            t_ = d[(d.title.isin(titles)) & (d.event_et >= f"{MIN_YEAR}-01-01")]
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
