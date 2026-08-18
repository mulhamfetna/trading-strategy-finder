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
import urllib.request
from pathlib import Path

import pandas as pd

FRED = "https://api.stlouisfed.org/fred/release/dates"
FOMC_JSON = "https://www.federalreserve.gov/json/calendar.json"

# (fred_release_id, event slug, agency, Eastern release time)
RELEASES = [
    (50,  "nonfarm_payrolls",  "BLS",    "08:30"),
    (10,  "cpi",               "BLS",    "08:30"),
    (46,  "ppi",               "BLS",    "08:30"),
    (53,  "gdp",               "BEA",    "08:30"),
    (54,  "pce",               "BEA",    "08:30"),
    (8,   "retail_sales",      "Census", "08:30"),
    (175, "ism_manufacturing", "ISM",    "10:00"),
    (176, "ism_services",      "ISM",    "10:00"),
]

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch_fred_dates(release_id: int, start: str, end: str, api_key: str) -> list[str]:
    """The dates this release ACTUALLY landed on, between start and end."""
    url = (f"{FRED}?release_id={release_id}&file_type=json&api_key={api_key}"
           f"&realtime_start={start}&realtime_end={end}"
           f"&include_release_dates_with_no_data=false&limit=1000")
    payload = _get_json(url)
    return [d["date"] for d in payload.get("release_dates", [])]


def fetch_fomc_dates(start: str, end: str) -> list[str]:
    """FOMC statement days. The Fed's JSON calendar marks multi-day meetings; the statement lands on
    the LAST day, at 14:00 ET."""
    payload = _get_json(FOMC_JSON)
    out = []
    for m in payload.get("mc", []):
        days = m.get("days") or []
        if not days:
            continue
        last = f"{m['year']}-{int(m['month']):02d}-{int(max(days)):02d}"
        if start <= last <= end:
            out.append(last)
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
