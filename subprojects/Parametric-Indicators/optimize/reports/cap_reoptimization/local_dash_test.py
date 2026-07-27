"""Prove the LOCAL dashboard now produces the FIXED numbers.

Drives the browser with zero manual changes and checks the on-screen figure against the shipped playbook.
Deliberately sticks to LIGHT timeframes (4h / 1h / 15m) — 2m and 5m have OOM-frozen this 14 GB box before.

Exercises all four exit rules so the whole fix chain is covered:
    bars  — the bar cap reaches the engine
    eod   — end-of-day close works
    both  — the brand-new "whichever fires first" rule (the dropdown could not even express this before)
    none  — no cap
"""
import json

import pytest

# This is a manual BROWSER verification script, not a unit test — it needs both `playwright` and a running
# local dashboard. pytest collects it because of the `*_test.py` name, so guard the import: without
# playwright installed this SKIPS cleanly instead of erroring out collection for the entire suite.
sync_playwright = pytest.importorskip("playwright.sync_api",
                                      reason="playwright not installed — browser verification script"
                                      ).sync_playwright

# (market, tf, expected on-screen P/L, expected exit rule)  — from the shipped playbooks
CHECKS = [
    ("NQ", "4h", 148670, "bars"),   # the slot whose frozen anchor we unlocked
    ("YM", "4h", 51917, "both"),    # the BRAND-NEW rule the dashboard could not represent
    ("SI", "1h", 43984, "eod"),     # end-of-day only
    ("GC", "15m", 80909, "none"),   # biggest out-of-sample winner
]

READ = ("() => (typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta) ? "
        "{pnl: VIEWS.l1.meta.boxes.pnl, n: VIEWS.l1.meta.boxes.n_taken, "
        " cap: collectLayer('l1').cap_mode, capn: collectLayer('l1').cap_1min} : null")
DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")

rows = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="chrome")
    pg = b.new_page(viewport={"width": 1500, "height": 1600})
    for inst, tf, expect, cap in CHECKS:
        pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
        pg.select_option("#inst_select", inst); pg.wait_for_timeout(1200)
        pg.select_option("#tf_select", tf); pg.wait_for_timeout(1600)
        pg.click("#run")                                    # ZERO manual modification
        pg.wait_for_function(DONE, timeout=1800000)
        m = pg.evaluate(READ) or {}
        got, gcap = m.get("pnl", 0), m.get("cap")
        ok = abs(got - expect) < 1 and gcap == cap
        rows.append(ok)
        print(f"  {inst:3} {tf:4} on-screen ${got:>10,.0f}  playbook ${expect:>10,.0f}   "
              f"cap={gcap}/{m.get('capn')} (want {cap})   n={m.get('n')}   "
              f"{'OK' if ok else '*** MISMATCH ***'}", flush=True)
    b.close()

print(f"\nLOCAL DASHBOARD: {sum(rows)}/{len(rows)} reproduce the shipped numbers with zero manual changes")
