"""WS-EARN Stage 1, step 5 (#110) — INDEPENDENT cross-check of the announcement DATE.

WHAT C3 ORIGINALLY ASKED FOR, AND WHY IT CANNOT BE DELIVERED AS WRITTEN.

Criterion C3 in #110 asked for a second, independent source agreeing with EDGAR to within 60 seconds.
That is not obtainable at scale from free sources, and the evidence for that claim is direct: Nasdaq's
own earnings API returns, for Apple's 2026-07-30 report,

    {'symbol': 'AAPL', 'eps': '$1.91', 'surprise': '1.6', 'time': 'time-not-supplied'}

`time-not-supplied` is the norm, not the exception. Commercial vendors publish a BMO/AMC flag at best.
**EDGAR's acceptance timestamp is effectively the only free second-precision source that exists.**

Reporting "C3 passed" on a check that could not be run would be worse than reporting the limit. So C3
is split into what is actually verifiable:

  C3a  INDEPENDENT DATE agreement — this script. Nasdaq's calendar is a different organisation with a
       different data pipeline, so agreement on the calendar DATE is genuine external corroboration.
       It cannot corroborate the minute.
  C3b  INTERNAL TIME-OF-DAY STABILITY — `check_time_stability.py`. Not independent, but powerful:
       Apple files at 16:30:2x-4x ET for eleven consecutive quarters. A scheduled corporate process
       produces a stable clock time, and a genuine anomaly stands out against it (ASML's accidental
       early release of Q3-2024 landed at 11:34:59 ET against its usual 06:0x).
  C4   the owner's TradingView check remains the only human, fully-independent verification of the
       minute — which is exactly why #110 required it.

    python3 optimize/earnings/crosscheck_nasdaq_calendar.py
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CLASSIFIED = DATA / "earnings_events_classified.json"
RAW_CACHE = DATA / "nasdaq_calendar_raw.json"
OUT = DATA / "crosscheck_nasdaq_date.json"

URL = "https://api.nasdaq.com/api/calendar/earnings?date={date}"
UA = "Mozilla/5.0 (X11; Linux x86_64)"
PAUSE = 0.4


def fetch_day(date: str) -> dict:
    req = urllib.request.Request(URL.format(date=date), headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.loads(r.read())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        time.sleep(PAUSE)
        return {"__error__": f"{type(exc).__name__}"}
    time.sleep(PAUSE)
    rows = (d.get("data") or {}).get("rows") or []
    return {r["symbol"].upper(): {"eps": r.get("eps"), "surprise": r.get("surprise"),
                                  "time": r.get("time"), "name": r.get("name")} for r in rows}


def main() -> int:
    events = json.loads(CLASSIFIED.read_text())
    earn = [e for e in events.values() if e["label"] == "earnings"]
    print(f"earnings events to cross-check: {len(earn)}")

    cache = json.loads(RAW_CACHE.read_text()) if RAW_CACHE.exists() else {}
    dates = sorted({e["event_et"][:10] for e in earn})
    print(f"distinct calendar dates       : {len(dates)}\n")

    for i, d in enumerate(dates, 1):
        if d in cache and "__error__" not in cache[d]:
            continue
        cache[d] = fetch_day(d)
        if i % 20 == 0:
            RAW_CACHE.write_text(json.dumps(cache))
            print(f"  ...{i}/{len(dates)}")
    RAW_CACHE.write_text(json.dumps(cache))

    # Nasdaq lists a company on the date it reports. An AMC release can appear on the same day or,
    # for some vendors, the next — so a +-1 day window is allowed and RECORDED as such.
    results, agree, near, miss = [], 0, 0, 0
    for e in earn:
        d = e["event_et"][:10]
        tick = e["ticker"].upper()
        hit_same = tick in cache.get(d, {})
        from datetime import date as _d, timedelta
        y, m, dd = map(int, d.split("-"))
        neigh = [(_d(y, m, dd) + timedelta(days=k)).isoformat() for k in (-1, 1)]
        hit_near = any(tick in cache.get(n, {}) for n in neigh if n in cache)

        status = "exact_date" if hit_same else ("within_1_day" if hit_near else "no_match")
        agree += hit_same
        near += (not hit_same) and hit_near
        miss += status == "no_match"
        rec = cache.get(d, {}).get(tick, {})
        results.append({**{k: e[k] for k in ("ticker", "event_et", "accession")},
                        "nasdaq_status": status,
                        "nasdaq_time_field": rec.get("time"),
                        "nasdaq_eps": rec.get("eps"),
                        "nasdaq_surprise": rec.get("surprise")})

    OUT.write_text(json.dumps(results, indent=1))
    n = len(results)
    print(f"\n=== C3a INDEPENDENT DATE CROSS-CHECK ===")
    print(f"  exact date match     : {agree:>4} / {n}  ({100*agree/n:.1f}%)")
    print(f"  matched within 1 day : {near:>4} / {n}")
    print(f"  NO match             : {miss:>4} / {n}")

    times = {}
    for d in cache.values():
        for v in d.values():
            if isinstance(v, dict):
                times[v.get("time")] = times.get(v.get("time"), 0) + 1
    print(f"\n  Nasdaq 'time' field across all rows seen: {dict(sorted(times.items(), key=lambda x:-x[1])[:5])}")
    print("  ^ this is the evidence that no free vendor supplies the minute.")

    if miss:
        print("\n  events with NO independent date corroboration (listed, never hidden):")
        for r in results:
            if r["nasdaq_status"] == "no_match":
                print(f"    {r['ticker']:<7} {r['event_et']}  {r['accession']}")
    print(f"\nwrote -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
