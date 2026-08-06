"""WS-EARN Stage 1, step 5 (#110) — resolve every timestamp from EDGAR's AUTHORITATIVE header.

⚠️ THE BUG THIS EXISTS TO KILL — EDGAR's JSON API is not internally consistent.

`data.sec.gov/submissions/CIK*.json` publishes `acceptanceDateTime` with a trailing `Z`, which means
UTC. For most filings it genuinely is UTC. For some it is **Eastern wall-clock with a spurious `Z`**.
Two filings from the same week make this undeniable:

    MSFT 0001193125-26-323632   JSON 2026-07-29T16:04:53Z   SGML 20260729160453   -> agree = ET, not UTC
    AAPL 0000320193-26-000018   JSON 2026-07-30T20:30:28Z   SGML 20260730163028   -> differ 4h = true UTC

Both companies release just after the 16:00 ET close, and the SGML header puts both there. Converting
the JSON field as UTC therefore lands Microsoft's earnings at **12:04 ET — four hours before it
happened, in the middle of the trading session instead of after the close.**

For an event study that is not a small error. It moves the event into the wrong session, so the
"reaction" measured would be ordinary midday trading and the real reaction would sit outside the window
entirely. It is also completely silent: the timestamp looks perfectly plausible.

It was caught by the C3b time-of-day stability check — Microsoft's median release time came out as
12:03 with a ±60 minute spread, which is not what a scheduled corporate process looks like. That is the
instrument doing its job.

THE FIX: take the timestamp from `{accession}-index-headers.html`, whose `ACCEPTANCE-DATETIME` field is
EDGAR's own record in Eastern time, for EVERY event. No special-casing of Microsoft — the unreliable
field is simply not used. Every disagreement is recorded rather than quietly corrected.

    python3 optimize/earnings/resolve_authoritative_times.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CLASSIFIED = DATA / "earnings_events_classified.json"
CACHE = DATA / "authoritative_times.json"

UA = "MulhamFetna-Research contact@mulhamfetna.com"
PAUSE = 0.15
HDR_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accn}/{acc}-index-headers.html"
ACCEPT_RE = re.compile(r"ACCEPTANCE-DATETIME&?g?t?;?>?(\d{14})")


def fetch_acceptance(cik: int, acc: str) -> str | None:
    url = HDR_URL.format(cik=cik, accn=acc.replace("-", ""), acc=acc)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        time.sleep(PAUSE)
        return None
    time.sleep(PAUSE)
    m = ACCEPT_RE.search(body)
    return m.group(1) if m else None


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="", help="suffix for all data files, e.g. 16y")
    a = ap.parse_args()
    sfx = f"_{a.tag}" if a.tag else ""
    global CLASSIFIED, CACHE
    CLASSIFIED = DATA / f"earnings_events_classified{sfx}.json"
    CACHE = DATA / f"authoritative_times{sfx}.json"
    print(f"classified : {CLASSIFIED.name}\nout        : {CACHE.name}\n")

    events = json.loads(CLASSIFIED.read_text())
    earn = {a: v for a, v in events.items() if v["label"] == "earnings"}
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    print(f"earnings events to resolve: {len(earn)}")
    print("authoritative field       : ACCEPTANCE-DATETIME from {accession}-index-headers.html (Eastern)\n")

    n_new = 0
    for i, (acc, v) in enumerate(sorted(earn.items(), key=lambda x: x[1]["event_et"]), 1):
        if acc in cache and cache[acc].get("sgml"):
            continue
        raw = fetch_acceptance(v["cik"], acc)
        cache[acc] = {"sgml": raw, "json_et": v["event_et"], "ticker": v["ticker"]}
        n_new += 1
        if n_new % 25 == 0:
            CACHE.write_text(json.dumps(cache, indent=1))
            print(f"  ...{i}/{len(earn)}")
    CACHE.write_text(json.dumps(cache, indent=1))

    mism, missing = [], []
    for acc, v in earn.items():
        rec = cache.get(acc, {})
        raw = rec.get("sgml")
        if not raw:
            missing.append((v["ticker"], v["event_et"], acc))
            continue
        sgml = datetime.strptime(raw, "%Y%m%d%H%M%S")
        jdt = datetime.fromisoformat(v["event_et"])
        dh = (sgml - jdt).total_seconds() / 3600.0
        rec["delta_hours"] = round(dh, 3)
        if abs(dh) > 0.02:
            mism.append((v["ticker"], v["event_et"], sgml.isoformat(sep=" "), dh, acc))
    CACHE.write_text(json.dumps(cache, indent=1))

    n = len(earn)
    print(f"\n=== AUTHORITATIVE TIME RESOLUTION ({n} events, {n_new} newly fetched) ===")
    print(f"  resolved from SGML header : {n - len(missing)}")
    print(f"  header UNAVAILABLE        : {len(missing)}")
    print(f"  JSON field DISAGREED      : {len(mism)}  ({100*len(mism)/max(n,1):.1f}%)")

    if mism:
        from collections import Counter
        print("\n  companies affected by the JSON timezone defect:")
        for t, k in Counter(m[0] for m in mism).most_common():
            print(f"    {t:<7} {k:>3} events")
        print("\n  sample corrections (JSON -> authoritative):")
        for t, j, s, dh, acc in sorted(mism)[:6]:
            print(f"    {t:<7} {j}  ->  {s}   ({dh:+.0f}h)   {acc}")
    if missing:
        print("\n  ⚠️ events with NO authoritative header (listed, never guessed):")
        for t, e, acc in missing[:10]:
            print(f"    {t:<7} {e}  {acc}")

    print(f"\nwrote -> {CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
