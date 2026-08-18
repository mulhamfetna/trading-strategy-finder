#!/usr/bin/env python3
"""WS-ESCPI (#139) ship-gate stage 3 — dashboard visual inspection, server-side Playwright.

Drives the REAL dashboard UI (no API shortcuts — the owner's rule: verify via the BROWSER):
loads the page, selects NQ 1h, loads the champion preset, clicks Run, waits for the report,
captures full-page screenshots, and extracts the headline numbers to compare against the
golden 1h baseline ($110,038 / n=353) on BOTH the branch instance (:8250, legacy18 with the
WS-ESCPI executor change) and production (:8200). A mismatch between the two instances or
against golden fails loudly.

Run ON THE SERVER (loopback — the WAN tunnel is ~46 KB/s, the lesson from #130):
    python3 escpi_dashboard_capture.py --out /tmp/escpi_shots
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# The DASHBOARD's verified 1h NQ book (established in the WS-DEPLOY #130 browser verification:
# 129 L1 entries, +$78,823). NOT the engine-golden $110,038/n=353 — that is a different
# measurement (optimizer champion, full window, --ind-1min); the engine side is covered by
# perf/check_golden.py, which this stage runs alongside, not instead of.
GOLDEN_1H = {"pl": "78,823", "n": 129}


def run_one(pw, base: str, tag: str, out: Path) -> dict:
    b = pw.chromium.launch()
    page = b.new_page(viewport={"width": 1600, "height": 1000})
    page.goto(f"{base}/", wait_until="networkidle", timeout=120_000)

    # instrument + timeframe + champion preset
    page.select_option("#inst_select", "NQ")
    page.wait_for_timeout(1500)
    page.select_option("#tf_select", "1h")
    page.wait_for_timeout(2500)                      # config + champion auto-load
    page.screenshot(path=str(out / f"{tag}_configured.png"), full_page=False)

    page.click("#run")
    # the 1h backtest takes a while server-side; poll the status/cards
    page.wait_for_function(
        "() => document.querySelector('#cards') && "
        "document.querySelector('#cards').innerText.includes('$')",
        timeout=600_000)
    page.wait_for_timeout(2000)
    page.screenshot(path=str(out / f"{tag}_report.png"), full_page=True)

    cards = page.inner_text("#cards")
    status = page.inner_text("#status") if page.query_selector("#status") else ""
    b.close()

    m_pl = re.search(r"\$([\d,]+)", cards)
    m_n = re.search(r"(\d+)\s*(?:trades|exits|entries)", cards, re.I)
    return {"tag": tag, "cards_head": cards[:400].replace("\n", " | "),
            "status": status[:120],
            "first_dollar": m_pl.group(1) if m_pl else None,
            "first_count": m_n.group(1) if m_n else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/escpi_shots")
    ap.add_argument("--branch", default="http://localhost:8250")
    ap.add_argument("--prod", default="http://localhost:8200")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        rb = run_one(pw, a.branch, "branch8250", out)
        rp = run_one(pw, a.prod, "prod8200", out)

    print(json.dumps({"branch": rb, "prod": rp}, indent=1))
    ok = True
    for r in (rb, rp):
        if GOLDEN_1H["pl"] not in r["cards_head"] or f"{GOLDEN_1H['n']} | L1 ENTRIES" \
                not in r["cards_head"].replace("\n", " | "):
            print(f"⚠️ {r['tag']}: verified 1h book ({GOLDEN_1H['pl']} / "
                  f"{GOLDEN_1H['n']} entries) NOT visible in cards")
            ok = False
    if rb["cards_head"] != rp["cards_head"]:
        print("⚠️ branch and production card text DIFFER")
        ok = False
    print("STAGE-3 DASHBOARD:", "PASS — both instances show the golden 1h report identically"
          if ok else "CHECK THE DIFFERENCES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
