"""WS-FWD Phase 3 (#176) — the dashboard visual gate (SSH tunnel + Playwright, NEVER interactive).

Drives the branch dashboard (:8250, running on the FWD extended root) through the real UI for
every instrument x TF slot: select instrument + timeframe, click Run, wait for the L1 view to
finish, read the ON-SCREEN headline (total P/L card + trade count from the status line), and
screenshot the page as committed evidence. The on-screen dollar figure must equal
round(book pnl) from the Phase-1 core books (DB.money renders signed, rounded, comma'd).

Prereq: `ssh -f -N -L 18250:127.0.0.1:8250 amd-trading` already up.
Usage:  python3 optimize/fwd/fwd_dashboard_gate.py --books optimize/fwd/data \
            --shots optimize/fwd/data/shots --out optimize/fwd/data/fwd_dashboard_gate.json
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

# Overridable so the SAME script runs on the server (browser next to the dashboard —
# the local 15GB box froze under the chart-render RAM load, 2026-08-21) or locally via
# the SSH tunnel. Both modes are scripted Playwright with committed screenshots.
import os
CHROME = os.environ.get("WSH_GATE_CHROME",
                        str(Path.home() / ".cache/ms-playwright/chromium-1228/chrome-linux64/chrome"))
URL = os.environ.get("WSH_GATE_URL", "http://127.0.0.1:18250/")
TOKENS = ("NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM")
TFS = ("4h", "2h", "1h", "15m", "5m", "2m")
RUN_TIMEOUT_MS = 20 * 60 * 1000


def money(n: float) -> str:
    r = round(n)
    return ("+" if r >= 0 else "-") + "$" + f"{abs(r):,}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", required=True)
    ap.add_argument("--shots", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--slots", default="", help="optional comma list TOK_TF to restrict")
    args = ap.parse_args()
    shots = Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    summary = {f"{r['instrument']}_{r['tf']}": r
               for r in json.loads((Path(args.books) / "fwd_run_summary.json").read_text())}
    only = {s for s in args.slots.split(",") if s}

    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME, headless=True)
        page = browser.new_page(viewport={"width": 1680, "height": 1200})
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector("#run", timeout=30000)
        for tok in TOKENS:
            for tf in TFS:
                key = f"{tok}_{tf}"
                if only and key not in only:
                    continue
                exp = summary.get(key, {})
                if exp.get("status") != "ok":
                    results[key] = {"status": exp.get("status", "missing")}
                    continue
                t0 = time.time()
                try:
                    # ⚠️ the page's INITIAL form is a legacy preset — the `best` champion loads
                    # only on a real (instrument, tf) change event. Force one: prime with a
                    # different tf, then select the target, and wait for the exact switch line.
                    page.select_option("#inst_select", tok)
                    primer = "2h" if tf != "2h" else "1h"
                    page.select_option("#tf_select", primer)
                    page.wait_for_function(
                        "() => document.getElementById('status').textContent.startsWith('switched to')",
                        timeout=60000)
                    page.select_option("#tf_select", tf)
                    page.wait_for_function(
                        f"() => document.getElementById('status').textContent.includes('switched to {tok} {tf}')",
                        timeout=60000)
                    page.click("#run")
                    # the run is finished when all three views are filled; the per-view trade
                    # count only appears in the status line after (re-)selecting the L1 tab
                    page.wait_for_function(
                        "() => document.getElementById('status').textContent.includes('all three tabs filled')",
                        timeout=RUN_TIMEOUT_MS)
                    page.click("#viewtabs button[data-view='l1']")
                    page.wait_for_function(
                        "() => /L1 · \\d+ trades/.test(document.getElementById('status').textContent)",
                        timeout=60000)
                    body = page.inner_text("body")
                    # .card .k renders uppercase (CSS text-transform) — match case-insensitively
                    m_pnl = re.search(r"([+\-]\$[\d,]+|\$-[\d,]+)\s*\n?\s*total P/L", body, re.IGNORECASE)  # DB.money renders a negative as "$-437"
                    m_dd = re.search(r"(\$[\d,]+)\s*\n?\s*max drawdown", body, re.IGNORECASE)
                    m_n = re.search(r"L1 · (\d+) trades", body)
                    seen_pnl = m_pnl.group(1) if m_pnl else None
                    if seen_pnl and seen_pnl.startswith("$-"):
                        seen_pnl = "-$" + seen_pnl[2:]                    # normalise to the books' "-$435" form
                    seen_dd = m_dd.group(1) if m_dd else None
                    seen_n = int(m_n.group(1)) if m_n else None
                    want_pnl = money(exp["pnl"])
                    shot = shots / f"fwd_dash_{key}.png"
                    page.screenshot(path=str(shot), full_page=False)
                    ok = (seen_pnl == want_pnl) and (seen_n == exp["n_trades"])
                    results[key] = {"status": "ok" if ok else "MISMATCH",
                                    "seen_pnl": seen_pnl, "want_pnl": want_pnl,
                                    "seen_n": seen_n, "want_n": exp["n_trades"],
                                    "seen_dd": seen_dd, "book_dd": exp.get("max_dd"),
                                    "secs": round(time.time() - t0, 1), "shot": shot.name}
                except Exception as e:  # noqa: BLE001
                    results[key] = {"status": f"ERROR: {type(e).__name__}: {e}"}
                print(f"[{key}] {results[key]}", flush=True)
        browser.close()

    Path(args.out).write_text(json.dumps(results, indent=1))
    ok = sum(1 for v in results.values() if v.get("status") == "ok")
    print(f"GATE DONE match={ok}/{len(results)} -> {args.out}", flush=True)


if __name__ == "__main__":
    main()
