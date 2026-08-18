"""WS-NEWS2 (#114) — collect actual · consensus · previous from the Nasdaq economic-events API.

WHY THIS SOURCE. Six others were probed and rejected (see SOURCE-EVALUATION-consensus.md):
investing.com and ForexFactory return 403 to everything including WebFetch; Trading Economics ignores
its own date parameters and its guest API is discontinued (410); FXStreet needs auth (401); Econoday
returns the current week for a 2010 request; DailyFX 403.

⭐ The Nasdaq API's event descriptions link to `investing.com/academy/...` — it carries **investing.com's
data**, which is the source originally asked for, through an endpoint that is not blocked. No rate
limiting observed: 15/15 requests at 0.3 s intervals returned 200, the exact pattern that got us blocked
from ForexFactory after four.

⚠️⚠️ TWO UNDOCUMENTED CONVENTIONS THIS MODULE CORRECTS. Both were verified against releases whose date
and value are independently known. Neither is mentioned by the API.

  1. THE DATE PARAMETER IS OFF BY ONE. `?date=D` returns the events of **D − 1**. Verified 3x:
        req 2010-01-09 -> NFP A=-85K   (Dec-2009 payrolls, released Fri 8 Jan 2010, actual -85,000)
        req 2010-07-03 -> NFP A=-125K  (released Fri 2 Jul 2010)
        req 2026-01-10 -> NFP A=50K C=66K P=56K  (released Fri 9 Jan 2026)

  2. THE `gmt` FIELD IS FIXED AT UTC-4 YEAR-ROUND — IT IS ONE HOUR FAST EVERY WINTER.
     Nonfarm Payrolls is 08:30 US-Eastern year-round. The field shows:
        summer (Jul 2010, 2012, 2013, 2017, 2018, 2019) -> 08:30   (== ET, correct)
        winter (Jan 2011, 2012, 2013, 2017, 2018, 2019) -> 09:30   (== ET + 1h)
     So the field is UTC-4 always. This module reads it as UTC-4 and converts to America/New_York.

     Taking it at face value would place EVERY WINTER EVENT ONE HOUR LATE — about half the sample —
     and it is invisible without a known-time release to check against. That is the same class of
     defect that displaced 22 earnings events by 4-5 hours in #110.

  ⚠️ PRE-2009 BREAKS RULE 2 (Jan 2007 and Jan 2008 show 08:30). Consensus is also unpopulated before
     2009. This module therefore refuses to run before 2009 unless forced.

⚠️ WHAT THIS MODULE DOES NOT ESTABLISH — THE REVISION QUESTION.
   Whether `actual` is the FIRST PRINT or a LATER REVISION is unverified. If revised, using it is
   LOOK-AHEAD CONTAMINATION — the exact defect round 1 avoided by pulling ALFRED point-in-time
   vintages. Payrolls alone were revised -801k to -1,032k jobs in 2025. `verify_revisions.py` must
   pass before any study consumes this table.

    python3 optimize/fundamentals/collect_nasdaq_calendar.py --start 2010-01-01 --end 2026-08-07
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
CACHE = HERE / "nasdaq_cache"
OUT = HERE / "nasdaq_calendar_us.csv"

API = "https://api.nasdaq.com/api/calendar/economicevents?date={d}"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
PAUSE = 0.35

ET = ZoneInfo("America/New_York")
FIELD_TZ = timezone(timedelta(hours=-4))    # ⚠️ the API's fixed offset — see convention 2 above
EARLIEST_SAFE = date(2009, 1, 1)            # before this, convention 2 does not hold


def fetch_day(request_date: date) -> list[dict] | None:
    """Fetch one day. `request_date` is the API parameter; it returns the events of request_date − 1."""
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{request_date}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink()
    for i in range(4):
        try:
            req = urllib.request.Request(API.format(d=request_date), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read())
            rows = (payload.get("data") or {}).get("rows") or []
            f.write_text(json.dumps(rows))
            time.sleep(PAUSE)
            return rows
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            if i == 3:
                print(f"    FAILED {request_date}: {type(exc).__name__}: {exc}", flush=True)
                return None
            time.sleep(PAUSE + 2.0 * (i + 1))
    return None


def to_et(event_day: date, gmt_field: str) -> str:
    """Convert the API's clock string to true US-Eastern wall-clock.

    The field is UTC-4 year-round (verified). Read it in that zone, then convert to America/New_York
    so daylight saving is applied correctly: identity in summer, minus one hour in winter.
    """
    gmt_field = (gmt_field or "").strip()
    if not gmt_field or ":" not in gmt_field:
        return ""
    try:
        hh, mm = (int(x) for x in gmt_field.split(":")[:2])
    except ValueError:
        return ""
    naive = datetime(event_day.year, event_day.month, event_day.day, hh, mm)
    return naive.replace(tzinfo=FIELD_TZ).astimezone(ET).replace(tzinfo=None).isoformat(sep=" ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    ap.add_argument("--allow-pre-2009", action="store_true")
    a = ap.parse_args()

    d0 = date.fromisoformat(a.start)
    d1 = date.fromisoformat(a.end)
    if d0 < EARLIEST_SAFE and not a.allow_pre_2009:
        raise SystemExit(f"refusing to start before {EARLIEST_SAFE}: the timezone convention differs "
                         f"and consensus is unpopulated. Pass --allow-pre-2009 only if you have "
                         f"re-derived the convention.")

    days = [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]
    print(f"event days      : {len(days):,}  ({d0} .. {d1})")
    print(f"⚠️ off-by-one   : requesting D+1 to obtain the events OF D")
    print(f"⚠️ timezone     : field read as UTC-4, converted to America/New_York")
    print(f"cache           : {CACHE}")
    print(f"output          : {OUT}\n")

    rows_out: list[dict] = []
    n_fail = 0
    for i, ev_day in enumerate(days, 1):
        rows = fetch_day(ev_day + timedelta(days=1))     # ⚠️ the off-by-one correction
        if rows is None:
            n_fail += 1
            continue
        for r in rows:
            if r.get("country") != "United States":
                continue
            rows_out.append({
                "event_date": ev_day.isoformat(),
                "event_et": to_et(ev_day, r.get("gmt", "")),
                "gmt_field_raw": r.get("gmt", ""),
                "event": (r.get("eventName") or "").strip(),
                "actual": (r.get("actual") or "").strip(),
                "consensus": (r.get("consensus") or "").strip(),
                "previous": (r.get("previous") or "").strip(),
            })
        if i % 100 == 0 or i == len(days):
            print(f"  ...{i}/{len(days)}  {ev_day}  (US rows so far: {len(rows_out):,})", flush=True)

    if not rows_out:
        print("no rows collected")
        return 1

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    print(f"\nwrote {len(rows_out):,} US rows -> {OUT}   ({n_fail} days failed)")

    # ---- verification, printed with the result so it cannot be skipped -------------------------
    from collections import Counter
    print("\n" + "=" * 88)
    print("VERIFICATION")
    print("=" * 88)
    have3 = [r for r in rows_out if r["actual"] and r["consensus"] and r["previous"]]
    print(f"  US rows                       : {len(rows_out):,}")
    print(f"  with all THREE numbers        : {len(have3):,}  ({100*len(have3)/len(rows_out):.1f}%)")
    print(f"  distinct releases             : {len({r['event'] for r in rows_out}):,}")
    nfp = [r for r in rows_out if r["event"] == "Nonfarm Payrolls"]
    print(f"  Nonfarm Payrolls rows         : {len(nfp)}")
    if nfp:
        times = Counter(r["event_et"][11:16] for r in nfp if r["event_et"])
        print(f"  NFP converted times           : {dict(times.most_common(4))}")
        print("  ^ MUST be 08:30 in ALL seasons. Any 09:30 means the timezone correction failed.")
        if set(times) - {"08:30"}:
            print("  ❌ TIMEZONE CORRECTION FAILED")
            return 1
        print("  ✅ timezone correction holds across the whole sample")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
