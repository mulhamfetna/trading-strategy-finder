"""WS-EARN Stage 1, step 3 (#110) — harvest the DOCUMENT LIST of every 8-K / 6-K in span.

WHY THIS EXISTS — a metadata field lied to us.

Stage 2 filtered on EDGAR's `items` field == "2.02". Applied Materials' Q2-FY2024 earnings release
(2024-05-16 16:03:55 ET, exactly in AMAT's 16:03-16:05 quarterly slot) is tagged **Item 2.01**, not
2.02. The filing plainly contains `exhibit991q22024earningsre.htm` — "Q2 2024 earnings release", 478 KB.
The item code is simply wrong, and item-code filtering silently DROPPED a whole quarter without a
warning. That is the exact failure mode this project keeps getting bitten by: a filter that is quiet
when it is wrong.

Foreign private issuers make it worse: ASML and ARM file Form 6-K, which carries NO item codes at all,
so there is nothing to filter on in the first place.

THE FIX — stop trusting metadata, read the documents.

Every 8-K and 6-K in span is harvested here with its full document list, regardless of item code. The
filenames are the evidence: `pressreleasequarterlyresul.htm`, `exhibit991q22024earningsre.htm`. The
classifier that consumes this cache records WHICH filename justified each decision, so every row is
auditable rather than trusted.

The result is cached to JSON so classification rules can be iterated without re-hitting SEC. SEC's
fair-access policy is respected: <10 req/s with an identifying User-Agent.

    python3 optimize/earnings/harvest_filing_documents.py [--top 20] [--start 2024-01-01]
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CACHE = DATA / "filing_documents.json"

UA = "MulhamFetna-Research contact@mulhamfetna.com"
SEC_PAUSE = 0.15
ET = ZoneInfo("America/New_York")

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://data.sec.gov/submissions/{name}"
INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
    time.sleep(SEC_PAUSE)
    return raw


def _get_json(url: str) -> dict:
    return json.loads(_get(url))


def load_universe(top_n: int) -> list[dict]:
    """Same universe construction as the collector: merge share classes by CIK, rank by combined weight."""
    snaps = sorted(DATA.glob("ndx_weights_*.csv"))
    if not snaps:
        raise SystemExit("run fetch_ndx_weights.py first")
    with snaps[-1].open() as fh:
        rows = [{**r, "rank": int(r["rank"]), "weight_pct": float(r["weight_pct"])}
                for r in csv.DictReader(fh)]

    tmap = {v["ticker"].upper(): int(v["cik_str"]) for v in _get_json(TICKER_MAP_URL).values()}
    by_cik: dict[int, dict] = {}
    for r in rows:
        cik = tmap.get(r["ticker"].upper())
        if cik is None:
            continue
        e = by_cik.setdefault(cik, {"cik": cik, "company": r["company"], "tickers": [],
                                    "combined_weight": 0.0})
        e["tickers"].append(r["ticker"])
        e["combined_weight"] += r["weight_pct"]
    merged = sorted(by_cik.values(), key=lambda e: -e["combined_weight"])
    for i, e in enumerate(merged, 1):
        e["company_rank"] = i
    return merged[:top_n]


def filings_in_span(cik: int, start: str, end: str) -> list[dict]:
    """EVERY 8-K and 6-K in span — no item-code filter. That filter is what lost AMAT's quarter."""
    sub = _get_json(SUBMISSIONS_URL.format(cik=cik))
    blocks = [sub["filings"]["recent"]]
    for f in sub["filings"].get("files", []):
        if f.get("filingTo", "") >= start:
            blocks.append(_get_json(ARCHIVE_URL.format(name=f["name"])))

    out = []
    for b in blocks:
        n = len(b.get("form", []))
        for i in range(n):
            if b["form"][i] not in ("8-K", "6-K"):
                continue
            acc_utc = datetime.fromisoformat(b["acceptanceDateTime"][i].replace("Z", "+00:00"))
            if acc_utc.tzinfo is None:
                acc_utc = acc_utc.replace(tzinfo=timezone.utc)
            dt_et = acc_utc.astimezone(ET)
            if not (start <= dt_et.strftime("%Y-%m-%d") <= end):
                continue
            out.append({
                "form": b["form"][i],
                "items": (b.get("items") or [""] * n)[i] or "",
                "accession": b["accessionNumber"][i],
                "filing_date": b["filingDate"][i],
                "report_date": (b.get("reportDate") or [""] * n)[i] or "",
                "event_et": dt_et.replace(tzinfo=None).isoformat(sep=" "),
                "event_utc": acc_utc.replace(tzinfo=None).isoformat(sep=" ") + "Z",
                "primary_doc": (b.get("primaryDocument") or [""] * n)[i] or "",
                "doc_description": (b.get("primaryDocDescription") or [""] * n)[i] or "",
            })
    out.sort(key=lambda r: r["event_et"])
    return out


def document_names(cik: int, accession: str) -> list[str]:
    url = INDEX_URL.format(cik=cik, acc=accession.replace("-", ""))
    try:
        d = _get_json(url)
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError) as exc:
        return [f"__FETCH_FAILED__:{type(exc).__name__}"]
    return [it["name"] for it in d.get("directory", {}).get("item", [])]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=datetime.now(ET).strftime("%Y-%m-%d"))
    a = ap.parse_args()

    print(f"span   : {a.start} .. {a.end}")
    print(f"forms  : 8-K and 6-K — ALL of them, NO item-code filter")
    print(f"cache  : {CACHE}\n")

    universe = load_universe(a.top)
    cache: dict = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text())
    n_new = 0

    for e in universe:
        tick = "+".join(e["tickers"])
        try:
            fl = filings_in_span(e["cik"], a.start, a.end)
        except Exception as exc:
            print(f"  {tick:<12} SUBMISSIONS FAILED: {type(exc).__name__}: {exc}")
            continue

        for f in fl:
            key = f["accession"]
            if key in cache and not cache[key].get("documents", [""])[0].startswith("__FETCH_FAILED__"):
                continue
            f["documents"] = document_names(e["cik"], key)
            f["cik"] = e["cik"]
            f["ticker"] = e["tickers"][0]
            f["all_tickers"] = "|".join(e["tickers"])
            f["company"] = e["company"]
            f["company_rank"] = e["company_rank"]
            f["combined_weight_pct"] = round(e["combined_weight"], 4)
            cache[key] = f
            n_new += 1

        print(f"  {tick:<12} {len(fl):>3} 8-K/6-K in span")
        CACHE.write_text(json.dumps(cache, indent=1))       # checkpoint: a crash never loses the work

    print(f"\ncached {len(cache)} filings total ({n_new} newly fetched) -> {CACHE}")
    failed = [k for k, v in cache.items()
              if v.get("documents") and str(v["documents"][0]).startswith("__FETCH_FAILED__")]
    if failed:
        print(f"⚠️  {len(failed)} document fetches FAILED — re-run to retry: {failed[:5]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
