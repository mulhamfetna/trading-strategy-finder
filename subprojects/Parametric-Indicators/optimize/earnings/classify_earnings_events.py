"""WS-EARN Stage 1, step 4 (#110) — classify each filing from DOCUMENT TEXT, not metadata.

WHY METADATA IS NOT ENOUGH — three failures found in our own 20 companies:

  1. APPLIED MATERIALS mis-tagged its Q2-FY2024 earnings 8-K as Item 2.01 instead of 2.02
     (2024-05-16 16:03:55 ET). Item-code filtering dropped a whole quarter, silently.
  2. TESLA files Item 2.02 for QUARTERLY DELIVERY NUMBERS as well as for earnings.
  3. ASML files Form 6-K, which carries NO item codes at all.

WHY HEADLINE MATCHING IS NOT ENOUGH EITHER — v1 of this script got ASML, Walmart and Tesla wrong:

  · ASML's press release is named `pressreleasequarterlyresul.htm` and Walmart's `earningsreleasefy24q4.htm`.
    Neither matches "ex99", so v1 read no press release at all and fell back to the filing body — which
    for Walmart is raw XBRL cover data and for ASML is the SEC cover page. Both scored "other".
  · Tesla's DELIVERY release is titled "Tesla Vehicle Production & Deliveries **and Date for Financial
    Results & Webcast**". It contains both phrases. And Tesla's EARNINGS deck opens with delivery tables.
    First-match-wins cannot separate them in either direction.

THE DISCRIMINATOR THAT ACTUALLY WORKS

    An earnings release contains FINANCIAL STATEMENTS — earnings per share, net income, consolidated
    statements of operations. A delivery report contains vehicle counts and none of that.

So classification scores the *presence of financial-statement language*, not headline phrasing, and
counts DISTINCT markers so a single stray phrase cannot decide a row. Every row records the markers
that fired, so any classification can be audited without re-running anything.

    python3 optimize/earnings/classify_earnings_events.py
"""
from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
CACHE = DATA / "filing_documents.json"
TEXT_CACHE = DATA / "filing_text.json"
OUT = DATA / "earnings_events_classified.json"

UA = "MulhamFetna-Research contact@mulhamfetna.com"
SEC_PAUSE = 0.15
DOC_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{name}"

# ---------------------------------------------------------------------------------------------
# THE RULES — printed at run time; the markers that fired are stored on every row.
# ---------------------------------------------------------------------------------------------
# Financial-statement language. Deliberately EXCLUDES the bare phrase "financial results", because
# Tesla's delivery release contains it ("...and Date for Financial Results & Webcast") while carrying
# no financial statements at all. These markers describe the CONTENT of an earnings release.
FIN_MARKERS = [
    ("eps",            re.compile(r"earnings per (diluted )?share|diluted (eps|earnings)|per share data", re.I)),
    ("net_income",     re.compile(r"net income|net loss|net earnings", re.I)),
    ("statements",     re.compile(r"consolidated (condensed )?(statements|balance sheets)"
                                  r"|statements of (income|operations)", re.I)),
    ("revenue",        re.compile(r"net sales|total revenue|revenues? (of|were|was|increased|decreased)"
                                  r"|total net sales", re.I)),
    ("margin",         re.compile(r"gross margin|operating income|operating margin", re.I)),
]

# Vehicle production/delivery reporting — Tesla's separate, non-earnings Item 2.02 disclosure.
DEL_MARKERS = [
    ("prod_deliver",   re.compile(r"production,?\s*(and|&)\s*deliver|vehicle production"
                                  r"|deliveries\s*&\s*deployments", re.I)),
    ("vehicle_counts", re.compile(r"(produced|delivered)\s+(over\s+)?[\d,]{4,}\s+vehicles", re.I)),
]

# A filename that names the document an earnings release is strong evidence on its own.
EARNINGS_DOCNAME = re.compile(
    r"earning|quarterlyresul|financialresul|financialstatement|cfocommentary|q[1-4]fy\d*pr", re.I)

# Periodic filings that CONTAIN financial statements but are NOT the earnings announcement.
# ASML publishes its statutory annual report weeks after it has already announced Q4/full-year results
# (2025-03-05 and 2026-02-25). The text is full of financial-statement language, so a content-only rule
# scores it as earnings — which would both double-count the year and insert an event on a date when
# nothing was announced. Same for AGM notices and investor days. Filename decides; text cannot.
NON_EARNINGS_DOCNAME = re.compile(
    r"annualreport|annualxreport|annualrep|noticeannual|agm|investorday", re.I)

# ⚠️ EDGAR's own index pages sit in the document list and end in .htm/.html. Reading one gives the
# SGML submission header — which contains no financial-statement language at all, so the filing scores
# "other". That is what silently zeroed Lam Research (11 real earnings -> 0) in an earlier revision.
SKIP_DOC = re.compile(r"^r\d+\.htm|^filingsummary|\.xsd$|_(cal|def|lab|pre)\.xml$"
                      r"|-index\.htm|-index-headers\.htm|^index\.|\.hdr\.sgml", re.I)

# Exhibit filenames are wildly inconsistent and include outright typos in the filer's own naming:
#   tsla-ex99_1.htm   lrcx_exhibitx991xq2x2024.htm   exhbit991.htm ("exhbit" — Tesla's spelling)
# Matching the "exh"/"ex99" stem covers every form observed across the 20 companies.
EXHIBIT_DOCNAME = re.compile(r"exh|ex99|ex_99|ex-99", re.I)


def _get(url: str, max_bytes: int = 90_000) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read(max_bytes)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        time.sleep(SEC_PAUSE)
        return f"__FETCH_FAILED__ {type(exc).__name__}"
    time.sleep(SEC_PAUSE)
    return raw.decode("utf-8", errors="replace")


def to_text(raw: str) -> str:
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t).strip()


def pick_documents(v: dict, k: int = 2) -> list[str]:
    """Best k documents to read. Prefers a named earnings release, then any exhibit, then the body."""
    cands = [d for d in v.get("documents", [])
             if d.lower().endswith((".htm", ".html")) and not SKIP_DOC.search(d)]

    def score(d: str) -> int:
        s = 0
        if EARNINGS_DOCNAME.search(d):
            s += 4
        if EXHIBIT_DOCNAME.search(d):
            s += 3
        if d == v.get("primary_doc"):
            s -= 1                       # the 8-K cover page is usually boilerplate
        return -s
    return sorted(cands, key=score)[:k]


def classify(text: str, docnames: str) -> tuple[str, list[str]]:
    """Return (label, markers). Distinct-marker counting: one stray phrase cannot decide a row."""
    # Highest precedence: a periodic filing is not an announcement, whatever its text contains.
    if NON_EARNINGS_DOCNAME.search(docnames) and not EARNINGS_DOCNAME.search(docnames):
        return "periodic_filing", ["doc:non_earnings_periodic"]

    fin = [n for n, p in FIN_MARKERS if p.search(text)]
    del_ = [n for n, p in DEL_MARKERS if p.search(text)]
    named = bool(EARNINGS_DOCNAME.search(docnames))

    earn_score = len(fin) + (2 if named else 0)
    del_score = len(del_)
    ev = [f"fin:{x}" for x in fin] + [f"del:{x}" for x in del_] + (["doc:named_earnings"] if named else [])

    # An earnings release carries SEVERAL financial-statement markers. A delivery report carries none.
    if earn_score >= 2 and earn_score > del_score:
        return "earnings", ev
    if del_score >= 1:
        return "production_delivery", ev
    if earn_score >= 2:
        return "earnings", ev
    return "other", ev


def main() -> int:
    ap = argparse.ArgumentParser()
    # A tag keeps a second collection (e.g. the 16-year run) in its own files. Without it the 16-year
    # pass would overwrite the verified 2.4-year artifacts in place — destroying the only table that
    # has been through five verification checks.
    ap.add_argument("--tag", default="", help="suffix for all data files, e.g. 16y")
    a = ap.parse_args()
    sfx = f"_{a.tag}" if a.tag else ""
    global CACHE, TEXT_CACHE, OUT
    CACHE = DATA / f"filing_documents{sfx}.json"
    TEXT_CACHE = DATA / f"filing_text{sfx}.json"
    OUT = DATA / f"earnings_events_classified{sfx}.json"
    print(f"cache : {CACHE.name}\ntext  : {TEXT_CACHE.name}\nout   : {OUT.name}\n")

    filings = json.loads(CACHE.read_text())
    tcache = json.loads(TEXT_CACHE.read_text()) if TEXT_CACHE.exists() else {}

    print("financial-statement markers (an earnings release has SEVERAL):")
    for n, p in FIN_MARKERS:
        print(f"  fin:{n:<14} {p.pattern[:80]}")
    print("delivery markers (Tesla's separate non-earnings 2.02 disclosure):")
    for n, p in DEL_MARKERS:
        print(f"  del:{n:<14} {p.pattern[:80]}")
    print("\nrule: earnings if (distinct fin markers + 2·named-file) >= 2 and > delivery markers\n")

    cands = []
    for acc, v in filings.items():
        items = [s.strip() for s in v.get("items", "").split(",") if s.strip()]
        if "2.02" in items or v["form"] == "6-K" or EARNINGS_DOCNAME.search(" ".join(v.get("documents", []))):
            cands.append((acc, v))
    cands.sort(key=lambda x: (x[1]["ticker"], x[1]["event_et"]))
    print(f"candidate filings: {len(cands)}")

    n_fetch = 0
    results = {}
    for i, (acc, v) in enumerate(cands, 1):
        entry = tcache.get(acc, {})
        text = entry.get("text_v2")
        used = entry.get("docs_v2", [])

        # Discard any cached text that came from an EDGAR index page rather than a filing document.
        # Leaving it would keep a wrong classification alive behind a cache hit — the worst kind of
        # bug, because re-running "confirms" it.
        if used and any(SKIP_DOC.search(u) for u in used):
            text, used = None, []

        if not text:
            # Reuse v1's cached press-release text when it actually captured one; only pay for a fetch
            # when v1 read nothing (its doc selector missed non-"ex99" filenames).
            old = (entry.get("exhibit") or "")
            if len(old) > 400:
                text, used = old + " " + (entry.get("body") or ""), ["<v1 cached exhibit+body>"]
            else:
                used = pick_documents(v)
                parts = []
                for d in used:
                    parts.append(to_text(_get(DOC_URL.format(cik=v["cik"], acc=acc.replace("-", ""), name=d)))[:9000])
                text = " ".join(parts)
                n_fetch += 1
                if n_fetch % 10 == 0:
                    print(f"  ...fetched {n_fetch} (at candidate {i}/{len(cands)})")
            tcache.setdefault(acc, {}).update({"text_v2": text[:20000], "docs_v2": used})
            if n_fetch % 10 == 0:
                TEXT_CACHE.write_text(json.dumps(tcache))

        label, ev = classify(text, " ".join(v.get("documents", [])))
        results[acc] = {**{k: v[k] for k in ("ticker", "company", "company_rank", "combined_weight_pct",
                                             "cik", "form", "items", "event_et", "event_utc",
                                             "filing_date", "report_date")},
                        "label": label, "evidence": ",".join(ev),
                        "evidence_source": "|".join(used)[:120], "accession": acc}

    TEXT_CACHE.write_text(json.dumps(tcache))
    OUT.write_text(json.dumps(results, indent=1))

    print(f"\n=== classification ({len(results)} filings, {n_fetch} newly fetched) ===")
    for lab, k in Counter(r["label"] for r in results.values()).most_common():
        print(f"  {lab:<22} {k}")

    print("\n=== per company ===")
    by = {}
    for r in results.values():
        by.setdefault(r["ticker"], []).append(r)
    for t in sorted(by):
        rs = by[t]
        e = sum(1 for r in rs if r["label"] == "earnings")
        d = sum(1 for r in rs if r["label"] == "production_delivery")
        o = sum(1 for r in rs if r["label"] == "other")
        flag = "" if 9 <= e <= 12 else "   <-- CHECK: expected 10-11 over this span"
        print(f"  {t:<7} earnings={e:>3}  deliveries={d:>3}  other={o:>3}{flag}")
    print(f"\nwrote -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
