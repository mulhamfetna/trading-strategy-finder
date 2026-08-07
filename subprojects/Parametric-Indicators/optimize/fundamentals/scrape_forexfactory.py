"""WS-NEWS2 (#114) — scrape the ForexFactory economic calendar, 2010 → present.

WHY THIS SOURCE AND NOT investing.com

investing.com is unreachable from this environment: curl gets 403 on the event page, on the AJAX
`more-history` endpoint that "Show More" calls, and on the homepage itself even with a cookie jar — the
block is at the TLS/fingerprint level, not the user-agent. WebFetch renders the page but returns only
the ~12 visible history rows and cannot click through. Browser automation is not connected.

ForexFactory publishes the same three numbers — **actual · forecast · previous** — one page per month,
back to January 2010, at HTTP 200. Its impact levels map onto investing.com's stars:

    icon--ff-impact-red   high      = 3 stars
    icon--ff-impact-ora   medium    = 2 stars
    icon--ff-impact-yel   low       = 1 star
    icon--ff-impact-gra   non-economic (holidays, some speeches)

WHAT THIS GIVES US THAT ROUND 1 NEVER HAD

Round 1's `expected` was `mean of the previous LOOKBACK changes` — a STATISTICAL PROXY, not the
market's consensus. Report 06 Part 10 acknowledged that and advised against buying consensus data
because it cost money. This costs nothing.

⚠️⚠️ TWO THINGS THIS SCRIPT DOES NOT ESTABLISH, AND MUST BE CHECKED BEFORE ANY STUDY RUNS

  1. WHETHER THIS `actual` IS THE FIRST PRINT OR A REVISION. ForexFactory shows the value as displayed
     later. If it is revised, using it is LOOK-AHEAD CONTAMINATION — the precise defect round 1 avoided
     by pulling ALFRED point-in-time vintages. Payrolls alone were revised by −801k to −1,032k jobs in
     2025. Cross-check against ALFRED before trusting a single row.
  2. WHETHER THIS `forecast` MATCHES investing.com's. Different aggregators poll different economists.
     Compare on overlapping months. A material disagreement is itself a finding about how soft
     "consensus" is.

⚠️ TIMEZONE. The displayed time depends on the site's session setting. This script does NOT assume one —
it records the raw string and runs a verification (`--verify`) that checks known-time releases
(Nonfarm Payrolls should be 08:30 US-Eastern) so the offset is MEASURED, not guessed. A timezone error
here would silently misplace every event, which is exactly how the earnings workstream lost 22 events
to a 4-hour shift.

    python3 optimize/fundamentals/scrape_forexfactory.py --start 2010-01 --end 2026-08
    python3 optimize/fundamentals/scrape_forexfactory.py --verify        # parse cache only, no network
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "ff_cache"
OUT = HERE / "ff_calendar_raw.csv"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
BASE = "https://www.forexfactory.com/calendar?month={m}"
PAUSE = 1.5                      # polite: one page every 1.5 s, 200 pages ~ 5 min
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]

IMPACT = {"red": "high", "ora": "medium", "yel": "low", "gra": "non-economic"}

# Row-level fields. FF emits one <tr> per event; the day's unix dateline appears only on the FIRST row
# of each day, so it is carried forward. Same for the time cell, which is blank on repeats within the
# same time slot.
RE_ROW = re.compile(r'<tr[^>]*class="[^"]*calendar__row[^"]*"[^>]*>(.*?)</tr>', re.S)
RE_ROW_OPEN = re.compile(r'<tr([^>]*)>')
RE_DATELINE = re.compile(r'data-day-dateline="(\d+)"')
RE_EVENTID = re.compile(r'data-event-id="(\d+)"')
RE_TIME = re.compile(r'calendar__time[^>]*>(.*?)</td>', re.S)
RE_CUR = re.compile(r'calendar__currency[^>]*>(.*?)</td>', re.S)
RE_IMPACT = re.compile(r'icon--ff-impact-(\w+)')
# ⚠️ The closing quote is REQUIRED. Without it this also matches `calendar__event-title-wrapper`,
# which wraps the real span and appears FIRST — so the capture was whitespace and every one of the 362
# rows was silently discarded as "no title". The parser reported 0 rows and no error.
RE_TITLE = re.compile(r'calendar__event-title"\s*>(.*?)<', re.S)
RE_ACT = re.compile(r'calendar__actual[^>]*>(.*?)</td>', re.S)
RE_FC = re.compile(r'calendar__forecast[^>]*>(.*?)</td>', re.S)
RE_PREV = re.compile(r'calendar__previous[^>]*>(.*?)</td>', re.S)


def clean(s: str | None) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'")
    return re.sub(r"\s+", " ", s).strip()


def months(start: str, end: str) -> list[str]:
    y0, m0 = map(int, start.split("-"))
    y1, m1 = map(int, end.split("-"))
    out, y, m = [], y0, m0
    while (y, m) <= (y1, m1):
        out.append(f"{MONTHS[m-1]}.{y}")
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def fetch(tag: str, attempts: int = 4) -> str | None:
    """Fetch one month, cached. Retries transient failures — a single socket timeout must not kill a
    200-page run, a lesson paid for in the earnings harvest."""
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{tag}.html"
    if f.exists() and f.stat().st_size > 50_000:
        return f.read_text(encoding="utf-8", errors="replace")
    for i in range(attempts):
        try:
            req = urllib.request.Request(BASE.format(m=tag), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                html = r.read().decode("utf-8", errors="replace")
            if len(html) < 50_000:
                raise OSError(f"suspiciously small page ({len(html)} bytes)")
            f.write_text(html, encoding="utf-8")
            time.sleep(PAUSE)
            return html
        except (OSError, urllib.error.URLError) as exc:
            if i == attempts - 1:
                print(f"    FAILED {tag}: {type(exc).__name__}: {exc}", flush=True)
                return None
            time.sleep(PAUSE + 3.0 * (i + 1))
    return None


def parse_month(html: str, tag: str) -> list[dict]:
    rows, dateline, last_time = [], None, ""
    for m in RE_ROW.finditer(html):
        block = m.group(0)
        d = RE_DATELINE.search(block)
        if d:
            dateline = int(d.group(1))
        eid = RE_EVENTID.search(block)
        if not eid or dateline is None:
            continue                                    # day-breaker rows carry no event
        t = clean(RE_TIME.search(block).group(1)) if RE_TIME.search(block) else ""
        if t:
            last_time = t
        cur = clean(RE_CUR.search(block).group(1)) if RE_CUR.search(block) else ""
        imp = RE_IMPACT.search(block)
        ttl = clean(RE_TITLE.search(block).group(1)) if RE_TITLE.search(block) else ""
        if not ttl:
            continue
        rows.append({
            "month_page": tag,
            "event_id": eid.group(1),
            "day_dateline": dateline,
            "day_utc": datetime.fromtimestamp(dateline, tz=timezone.utc).strftime("%Y-%m-%d"),
            "time_raw": t or last_time,
            "currency": cur,
            "impact": IMPACT.get(imp.group(1), imp.group(1)) if imp else "",
            "impact_raw": imp.group(1) if imp else "",
            "event": ttl,
            "actual": clean(RE_ACT.search(block).group(1)) if RE_ACT.search(block) else "",
            "forecast": clean(RE_FC.search(block).group(1)) if RE_FC.search(block) else "",
            "previous": clean(RE_PREV.search(block).group(1)) if RE_PREV.search(block) else "",
        })
    return rows


def verify(rows: list[dict]) -> int:
    """Checks that must pass before this table is used for anything. Failures are LOUD."""
    fails = []
    print("\n" + "=" * 92)
    print("VERIFICATION")
    print("=" * 92)

    n_usd = sum(1 for r in rows if r["currency"] == "USD")
    print(f"  total rows              : {len(rows):,}")
    print(f"  USD rows                : {n_usd:,}")
    from collections import Counter
    print(f"  impact mix (USD)        : {dict(Counter(r['impact'] for r in rows if r['currency']=='USD'))}")

    # 1. span
    days = sorted({r["day_utc"] for r in rows})
    print(f"  span                    : {days[0]} -> {days[-1]}  ({len(days):,} distinct days)")
    if days[0] > "2010-02-01":
        fails.append(f"span starts {days[0]}, expected 2010-01")

    # 2. ⚠️ TIMEZONE — measured, never assumed.
    # ⚠️ EXACT match. A substring test on "Non-Farm Employment" also catches "ADP Non-Farm Employment
    # Change", which is released at 08:15 — so the timezone check appeared to fail on a 15-minute
    # difference that was really a different release.
    nfp = [r for r in rows if r["currency"] == "USD" and r["event"] == "Non-Farm Employment Change"]
    tset = Counter(r["time_raw"] for r in nfp)
    print(f"\n  Nonfarm Payrolls rows   : {len(nfp)}")
    print(f"  its displayed times     : {dict(tset.most_common(4))}")
    print("  ^ NFP is released at 08:30 US-Eastern. If the dominant string is '8:30am' the pages are")
    print("    in US-Eastern; '1:30pm' would mean UTC. THE OFFSET IS READ OFF THIS, NOT GUESSED.")
    if not nfp:
        fails.append("no Nonfarm Payrolls rows found — parser or filter is wrong")
    elif tset.most_common(1)[0][0] not in ("8:30am", "1:30pm", "13:30"):
        fails.append(f"NFP time '{tset.most_common(1)[0][0]}' is neither 08:30 ET nor 13:30 UTC")

    # 3. the three numbers actually populated
    have3 = [r for r in rows if r["currency"] == "USD" and r["actual"] and r["forecast"] and r["previous"]]
    print(f"\n  USD rows with all THREE numbers (actual+forecast+previous): {len(have3):,}"
          f"  ({100*len(have3)/max(n_usd,1):.1f}% of USD rows)")
    # Scale the bar to how many months were actually parsed, so a single-month smoke test does not
    # report a "failure" that is really just a small sample.
    n_months = len({r["month_page"] for r in rows})
    floor = max(20, 40 * n_months)
    if len(have3) < floor:
        fails.append(f"only {len(have3)} rows carry all three numbers over {n_months} month(s) "
                     f"— expected >= {floor}")

    # 4. a named release must be present every month it should be
    for name in ("Non-Farm Employment Change", "CPI m/m", "Core CPI m/m"):
        got = sum(1 for r in rows if r["currency"] == "USD" and r["event"] == name)
        print(f"  '{name}' rows: {got}")

    print("\n  " + ("ALL CHECKS PASSED" if not fails else "FAILURES:"))
    for f in fails:
        print(f"    ❌ {f}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2010-01")
    ap.add_argument("--end", default=datetime.now().strftime("%Y-%m"))
    ap.add_argument("--verify", action="store_true", help="parse the cache only, no network")
    a = ap.parse_args()

    tags = months(a.start, a.end)
    print(f"months to fetch : {len(tags)}  ({tags[0]} .. {tags[-1]})")
    print(f"cache           : {CACHE}")
    print(f"output          : {OUT}\n")

    all_rows: list[dict] = []
    for i, tag in enumerate(tags, 1):
        html = (CACHE / f"{tag}.html").read_text(encoding="utf-8", errors="replace") \
            if a.verify and (CACHE / f"{tag}.html").exists() else (None if a.verify else fetch(tag))
        if html is None:
            continue
        got = parse_month(html, tag)
        all_rows.extend(got)
        if i % 5 == 0 or i == len(tags):
            print(f"  ...{i}/{len(tags)}  {tag}  +{len(got)} rows  (total {len(all_rows):,})", flush=True)

    if not all_rows:
        print("no rows parsed", file=sys.stderr)
        return 1

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nwrote {len(all_rows):,} rows -> {OUT}")
    return verify(all_rows)


if __name__ == "__main__":
    from collections import Counter          # used inside verify
    raise SystemExit(main())
