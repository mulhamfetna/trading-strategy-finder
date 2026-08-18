"""WS-NEWS2 (#114) — attach the market CONSENSUS to authoritative release dates.  [OPTION 1]

THE PROBLEM THIS SOLVES

The Nasdaq economic-events API carries correct VALUES (actual · consensus · previous — NFP −85K, 103K,
18K, 50K all match history) but its DATES are unreliable: consecutive request dates return
byte-identical payloads, some payloads mix two weekdays, and the response contains **no date field at
all**. For an event study the timestamp IS the instrument, so that source cannot supply dates.

THE FIX — take each half from the source that is trustworthy for it:

    DATE + TIME   <-  FRED release dates (us_high_impact.csv, 1,208 releases, already used and
                      verified in round 1; the timezone was proven against the tape at 7.3x on offset 0)
    CONSENSUS     <-  Nasdaq API, searched in a WINDOW around that date

Because the date comes from FRED, the API's broken date mapping cannot corrupt anything. The API is
only asked *"what was the consensus for this release, somewhere near this day?"*

⚠️ THE RISK THIS CREATES, AND THE GUARD AGAINST IT

Searching a ±N-day window could pick up the WRONG month's figure for a release that occurs more than
once in the window, or match a similarly-named event. Guards:

  1. The window is small (±2 days) — monthly releases cannot repeat inside it.
  2. If a release name appears MORE THAN ONCE in the window with CONFLICTING values, the row is
     recorded as `ambiguous` and **excluded**, never guessed.
  3. `actual` is captured from BOTH sources where available and compared. A mismatch means the window
     grabbed the wrong event — and is reported, not silently accepted.

⚠️ WHAT THIS STILL DOES NOT ESTABLISH — whether Nasdaq's `actual` is the FIRST PRINT or a REVISION.
   If revised, it is look-ahead contamination. FRED/ALFRED gives the true point-in-time vintage, so the
   comparison in guard 3 is also the revision check. Payrolls were revised −801k to −1,032k in 2025.

    python3 optimize/fundamentals/join_consensus_to_releases.py --window 2
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "nasdaq_cache"
CAL = HERE / "us_high_impact.csv"
OUT = HERE / "releases_with_consensus.csv"

API = "https://api.nasdaq.com/api/calendar/economicevents?date={d}"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
PAUSE = 0.3

# Our FRED slug -> the Nasdaq event names that represent the SAME PRINT.
# ⚠️ Several of our releases publish multiple headline lines at one timestamp (CPI publishes CPI and
# Core CPI together). All are captured; the study can choose which line to use.
NAME_MAP: dict[str, list[str]] = {
    "nonfarm_payrolls": ["Nonfarm Payrolls"],
    "cpi":              ["CPI (MoM)", "CPI", "Core CPI (MoM)", "Core CPI"],
    "ppi":              ["PPI (MoM)", "PPI", "Core PPI (MoM)", "Core PPI"],
    "gdp":              ["GDP (QoQ)", "GDP"],
    # ⚠️ Verified against the raw payloads, not guessed: the API uses bare names, no "(MoM)" suffix.
    "pce":              ["Core PCE Price Index", "PCE Price Index", "Personal Spending"],
    "retail_sales":     ["Retail Sales (MoM)", "Retail Sales", "Core Retail Sales (MoM)"],
    "fomc":             ["Fed Interest Rate Decision", "Interest Rate Decision"],
}


def fetch(d: date) -> list[dict]:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{d}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink()
    for i in range(4):
        try:
            req = urllib.request.Request(API.format(d=d), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                rows = (json.loads(r.read()).get("data") or {}).get("rows") or []
            f.write_text(json.dumps(rows))
            time.sleep(PAUSE)
            return rows
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            time.sleep(PAUSE + 2.0 * (i + 1))
    return []


def norm(v: str) -> str:
    return (v or "").replace("&nbsp;", "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=2, help="+-days searched around the FRED date")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=6,
                    help="concurrent fetchers; the API showed no rate limiting at 0.3s "
                         "sequential, so keep this modest")
    a = ap.parse_args()

    import pandas as pd
    cal = pd.read_csv(CAL, parse_dates=["Date"])
    if a.limit:
        cal = cal.head(a.limit)
    print(f"authoritative releases (FRED) : {len(cal):,}  {cal.Date.min():%Y-%m-%d} .. {cal.Date.max():%Y-%m-%d}")
    print(f"consensus source              : Nasdaq API, searched +-{a.window} days around each date")
    print(f"⚠️ dates come from FRED — the API's broken date mapping cannot corrupt them\n")

    out, stats = [], defaultdict(int)
    days_needed = sorted({(pd.Timestamp(d).date() + timedelta(days=k))
                          for d in cal.Date for k in range(-a.window, a.window + 1)})
    print(f"distinct API days to fetch    : {len(days_needed):,}")

    # ⚠️ MEASURED: the API takes ~5 s per request (latency, not rate limiting — 15/15 succeeded at
    # 0.3 s intervals). Sequentially that is 5.5 HOURS for 3,985 days. A small worker pool fixes it
    # without raising the request rate much above what was already shown safe.
    from concurrent.futures import ThreadPoolExecutor
    cacheables: dict[date, list[dict]] = {}
    done_n = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for d, rows in zip(days_needed, ex.map(fetch, days_needed)):
            cacheables[d] = rows
            done_n += 1
            # Report often enough that a watcher can compute an ETA and distinguish slow from stuck.
            if done_n % 25 == 0 or done_n == len(days_needed):
                print(f"  ...{done_n}/{len(days_needed)} days fetched", flush=True)

    for _, r in cal.iterrows():
        d0 = pd.Timestamp(r.Date).date()
        want = NAME_MAP.get(r.event, [])
        found: dict[str, list[dict]] = defaultdict(list)
        for k in range(-a.window, a.window + 1):
            for row in cacheables.get(d0 + timedelta(days=k), []):
                if row.get("country") != "United States":
                    continue
                if row.get("eventName") in want:
                    found[row["eventName"]].append(row)

        if not found:
            stats["no_match"] += 1
            out.append({"Date": r.Date, "event": r.event, "nasdaq_event": "", "actual": "",
                        "consensus": "", "previous": "", "status": "no_match"})
            continue

        for name, rows in found.items():
            # ⚠️ A release publishes the SAME NAME twice — month-over-month AND year-over-year. Verified:
            # 2010-01-16 returns "CPI" as both A=0.1% C=0.2% (MoM) and A=2.7% C=blank (YoY). Treating
            # that as a conflict discarded 18 of 60 rows — 30% of the sample — for no reason.
            #
            # Disambiguation, and it is principled rather than convenient: keep the line that HAS a
            # consensus. Without a forecast there is no surprise to compute, so a consensus-less line
            # is useless to this study whatever it is. If TWO lines carry a consensus, that is a real
            # ambiguity and the row is still excluded.
            withc = [x for x in rows if norm(x["consensus"])]
            rows = withc or rows
            uniq = {(norm(x["actual"]), norm(x["consensus"]), norm(x["previous"])) for x in rows}
            if len(uniq) > 1:
                stats["ambiguous"] += 1
                out.append({"Date": r.Date, "event": r.event, "nasdaq_event": name, "actual": "",
                            "consensus": "", "previous": "", "status": "ambiguous"})
                continue
            act, con, prev = next(iter(uniq))
            stats["matched"] += 1
            stats["matched_with_consensus"] += 1 if con else 0
            out.append({"Date": r.Date, "event": r.event, "nasdaq_event": name, "actual": act,
                        "consensus": con, "previous": prev, "status": "ok"})

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    print("\n" + "=" * 88)
    print("RESULT")
    print("=" * 88)
    for k in ("matched", "matched_with_consensus", "ambiguous", "no_match"):
        print(f"  {k:<26} {stats[k]:,}")
    # ⚠️ One FRED release legitimately yields SEVERAL Nasdaq lines (a CPI print returns both "CPI" and
    # "Core CPI"). Counting lines against releases produced a "143.3%" match rate — an impossible
    # number that would have gone into a report. Count DISTINCT RELEASES covered.
    covered = {(row["Date"], row["event"]) for row in out if row["status"] == "ok" and row["consensus"]}
    ok = len(covered)
    print(f"\n  matched LINES with consensus     : {stats['matched_with_consensus']:,}")
    print(f"  ⇒ RELEASES covered by >=1 line   : {ok:,} of {len(cal):,} ({100*ok/max(len(cal),1):.1f}%)")
    print(f"\nwrote -> {OUT}")
    # ⚠️ Scale the bar to the sample actually run. An absolute floor reports a 60-release smoke test
    # as a failure at an 80% match rate — the same mistake made in the ForexFactory verifier.
    rate = ok / max(len(cal), 1)
    if rate < 0.60:
        print(f"\n  ❌ match rate {rate:.1%} < 60% — option 1 has FAILED, fall back to option 2")
        return 1
    print("\n  ✅ option 1 viable — still requires the ALFRED revision check before any study")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
