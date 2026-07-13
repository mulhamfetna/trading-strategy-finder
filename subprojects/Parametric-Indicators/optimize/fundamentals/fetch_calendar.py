"""One-time CLI: build the three-star US release calendar from free, authoritative sources.

WHY FRED AND NOT BLS
--------------------
Two reasons, both discovered the hard way:

  1. www.bls.gov returns HTTP 403 to every automated fetch, even with a browser User-Agent.
  2. More importantly, the 2025 and 2026 government shutdowns RESCHEDULED releases. BLS publishes a
     page titled "Revised news release dates following the 2025 and 2026 lapses in appropriations",
     plus a separate September-2025 CPI reschedule notice. A calendar built from the ORIGINALLY
     PLANNED dates would veto on quiet days and trade naked through the real ones.

FRED's release/dates endpoint records when each statistic ACTUALLY came out, so reschedules are
captured for free rather than special-cased.

Dates come from FRED. Times are per-release Eastern-time constants (below) — independently validated
by the volatility-envelope check in optimize/fundamentals/window.py: if a time here were wrong, the
measured volatility spike would not land on the release minute, and the test fails.

  export FRED_API_KEY=...        # free: https://fred.stlouisfed.org/docs/api/api_key.html
  python3 optimize/fundamentals/fetch_calendar.py --start 2025-01-01 --end 2026-06-30
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path

import pandas as pd

FRED = "https://api.stlouisfed.org/fred/release/dates"
FOMC_JSON = "https://www.federalreserve.gov/json/calendar.json"

# (fred_release_id, event slug, agency, Eastern release time)
#
# Every id here was verified against https://api.stlouisfed.org/fred/releases and returns a non-zero
# date count for 2025-01-01..2026-06-30. Do not guess ids — the build refuses to write a partial
# calendar precisely so that a wrong id cannot pass silently.
RELEASES = [
    (50,  "nonfarm_payrolls",  "BLS",    "08:30"),
    (10,  "cpi",               "BLS",    "08:30"),
    (46,  "ppi",               "BLS",    "08:30"),
    (53,  "gdp",               "BEA",    "08:30"),
    (54,  "pce",               "BEA",    "08:30"),
    (9,   "retail_sales",      "Census", "08:30"),   # "Advance Monthly Sales for Retail and Food
                                                     #  Services". NOT id 8 — that returns nothing.
]

# KNOWN GAP — ISM (Manufacturing PMI, Services PMI), both 10:00 ET.
#
# FRED does NOT carry ISM. It is a private organization and its PMI data is proprietary, so the
# St. Louis Fed does not host the series (searching "ISM" there returns unrelated state leading
# indexes). There is therefore NO authoritative recorded-date source for ISM in our free stack.
#
# We deliberately do NOT rule-derive the dates (1st / 3rd business day of the month). Rule-derived
# dates are exactly the class of unverified, assumed data this design exists to avoid — the whole
# reason we use FRED instead of a schedule is that the 2025/2026 shutdowns proved schedules lie.
#
# Consequence: the calendar contains no 10:00 events, so the veto never fires at 10:00.
# window.py's envelope measurement includes a diagnostic that reports whether 10:00 on ISM-shaped
# days IS in fact unusually volatile — i.e. whether this gap is costing us anything. If it is,
# source ISM properly (paid feed) rather than guessing its dates.

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        # utf-8-sig: the Fed's calendar.json is served with a UTF-8 byte-order mark, which plain
        # utf-8 decoding chokes on. Harmless for FRED, which has no BOM.
        return json.loads(r.read().decode("utf-8-sig"))


def fetch_fred_dates(release_id: int, start: str, end: str, api_key: str) -> list[str]:
    """The dates this release ACTUALLY landed on, between start and end."""
    url = (f"{FRED}?release_id={release_id}&file_type=json&api_key={api_key}"
           f"&realtime_start={start}&realtime_end={end}"
           f"&include_release_dates_with_no_data=false&limit=1000")
    payload = _get_json(url)
    return [d["date"] for d in payload.get("release_dates", [])]


def fetch_fomc_dates(start: str, end: str) -> list[str]:
    """FOMC rate-decision STATEMENT days (14:00 ET), from the Fed's own JSON calendar.

    The feed's `events` list carries three distinct FOMC entries, and they are NOT equal:

      * "FOMC Meeting"          2:00 p.m.  -- the rate decision statement.  <-- the three-star event
      * "FOMC Press Conference" 2:30 p.m.  -- genuinely high-impact, but the feed only lists these
                                              from 2025-09 onward, so including them would leave
                                              holes in the first two-thirds of our window. EXCLUDED.
      * "FOMC Minutes"          2:00 p.m.  -- released ~3 weeks after the meeting; moves markets far
                                              less than the statement. Not three-star. EXCLUDED.

    Titles in the feed carry inconsistent case and stray leading spaces ("FOMC meeting",
    " FOMC Minutes"), so match on a normalized title. `days` is the meeting's LAST day (the day the
    statement lands); it is occasionally a range, so take the max.
    """
    payload = _get_json(FOMC_JSON)
    out = []
    for e in payload.get("events", []):
        if e.get("type") != "FOMC":
            continue
        if (e.get("title") or "").strip().lower() != "fomc meeting":
            continue
        month = (e.get("month") or "").strip()            # "YYYY-MM"
        days = str(e.get("days") or "").strip()           # "29"  or occasionally "28-29"
        if not month or not days:
            continue
        last_day = max(int(d) for d in re.findall(r"\d+", days))
        stamp = f"{month}-{last_day:02d}"
        if start <= stamp <= end:
            out.append(stamp)
    return sorted(set(out))


def build(start: str, end: str, api_key: str) -> pd.DataFrame:
    rows = []
    for rid, event, agency, hhmm in RELEASES:
        dates = fetch_fred_dates(rid, start, end, api_key)
        print(f"  {event:20s} release_id={rid:<4d} -> {len(dates):>3d} dates")
        if not dates:
            raise RuntimeError(
                f"FRED returned 0 dates for {event} (release_id={rid}). The id is wrong — "
                "look it up at https://fred.stlouisfed.org/releases. Refusing to write a partial "
                "calendar."
            )
        for d in dates:
            rows.append({"Date": pd.Timestamp(f"{d} {hhmm}:00"), "event": event, "agency": agency})

    fomc = fetch_fomc_dates(start, end)
    print(f"  {'fomc':20s} federalreserve.gov -> {len(fomc):>3d} dates")
    for d in fomc:
        rows.append({"Date": pd.Timestamp(f"{d} 14:00:00"), "event": "fomc",
                     "agency": "Federal Reserve"})

    df = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
    # Two releases can share a minute (e.g. PPI and retail sales both at 08:30). Collapse to one row
    # per timestamp — the veto window is identical either way.
    before = len(df)
    df = df.drop_duplicates(subset=["Date"], keep="first").reset_index(drop=True)
    if before != len(df):
        print(f"\n  collapsed {before - len(df)} same-minute collisions "
              f"(two releases at the same instant => one window)")
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--out", default=str(Path(__file__).parent / "us_high_impact.csv"))
    a = ap.parse_args()

    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise SystemExit(
            "FRED_API_KEY not set.\n"
            "Free key (instant): https://fred.stlouisfed.org/docs/api/api_key.html"
        )

    print(f"Building three-star US release calendar  {a.start} .. {a.end}\n")
    df = build(a.start, a.end, key)
    df.to_csv(a.out, index=False)
    print(f"\nwrote {len(df)} events -> {a.out}\n")
    print(df["event"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
