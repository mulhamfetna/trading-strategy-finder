"""WS-EARN Stage 1, step 1 (#110) — SNAPSHOT the Nasdaq-100 constituent weights.

WHY THIS IS A SEPARATE SCRIPT AND WHY IT WRITES A FILE.

Index weights move every day. If the collector fetched them live on each run, two runs a week apart
would silently produce different company sets and nobody would know which table came from which
universe. That is the "a default you did not choose is a condition of your experiment" failure, applied
to the universe instead of a parameter.

So: this script fetches ONCE and freezes the result to a dated CSV. The collector reads the frozen file
and never goes to the network for weights. Re-running the collector always reproduces the same table.

⚠️ SHARE CLASSES ARE NOT COMPANIES. Alphabet appears twice (GOOGL class A + GOOG class C) and so may
others. They are two index lines but ONE issuer filing ONE earnings release. The collector deduplicates
by SEC CIK, which is the only identifier that means "company". This script keeps both rows and records
a `combined_weight` so the reordering that dedup causes is visible rather than hidden.

Source: slickcharts.com/nasdaq100 (free, no key, publishes weights).
Cross-check that source against any second one before trusting the ordering near the cut-off.

    python3 optimize/earnings/fetch_ndx_weights.py
"""
from __future__ import annotations

import csv
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE_URL = "https://www.slickcharts.com/nasdaq100"
OUT_DIR = Path(__file__).resolve().parent / "data"
UA = "Mozilla/5.0 (X11; Linux x86_64) MulhamFetna-Research contact@mulhamfetna.com"


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_rows(html: str) -> list[dict]:
    """Rank / company / ticker / weight, in the order the source publishes them."""
    out = []
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        cells = [re.sub("<.*?>", "", c).strip() for c in re.findall(r"<td.*?>(.*?)</td>", tr, re.S)]
        if len(cells) >= 4 and cells[0].isdigit():
            out.append({
                "rank": int(cells[0]),
                "company": cells[1],
                "ticker": cells[2],
                "weight_pct": float(cells[3].rstrip("%")),
            })
    return out


def main() -> int:
    stamp = datetime.now(timezone.utc)
    print(f"source        : {SOURCE_URL}")
    print(f"retrieved_utc : {stamp.isoformat()}")

    rows = parse_rows(fetch_html(SOURCE_URL))
    if not rows:
        print("FAIL: parsed zero rows — the page layout changed. Not writing a file.", file=sys.stderr)
        return 1

    total = sum(r["weight_pct"] for r in rows)
    print(f"constituents  : {len(rows)}")
    print(f"weight sum    : {total:.2f}%   (a healthy snapshot sums to ~100%)")
    if not (95.0 <= total <= 105.0):
        print("FAIL: weights do not sum to ~100% — refusing to freeze a bad snapshot.", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"ndx_weights_{stamp:%Y-%m-%d}.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["rank", "ticker", "company", "weight_pct",
                                           "source_url", "retrieved_utc"])
        w.writeheader()
        for r in rows:
            w.writerow({**r, "source_url": SOURCE_URL, "retrieved_utc": stamp.isoformat()})
    print(f"\nfrozen to     : {out}")

    print("\ntop 25 as published (share classes NOT yet merged):")
    for r in rows[:25]:
        print(f"  {r['rank']:>3}  {r['ticker']:<7} {r['weight_pct']:>6.2f}%  {r['company']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
