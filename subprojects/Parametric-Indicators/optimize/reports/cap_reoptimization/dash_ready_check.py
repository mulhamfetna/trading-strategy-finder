"""Prove the deployed champions are LIVE and USABLE on the server dashboard.

Not "the file is on disk" — actually drive the browser: pick the market + timeframe, press Run with ZERO
manual changes, and check the on-screen number equals the playbook's. That is the only proof that matters.

Spot-checks one champion per cap model, so all four exit rules are exercised.
"""
import json
import os

from playwright.sync_api import sync_playwright

# (market, timeframe, expected on-screen P/L, cap model)  — from the shipped playbooks
CHECKS = [
    ("GC", "15m", 80909, "none"),     # Gold — the biggest out-of-sample winner
    ("YM", "4h", 51917, "both"),      # Dow  — uses the BRAND-NEW "both" rule
    ("SI", "1h", 43984, "eod"),       # Silver — end-of-day only
    ("NQ", "4h", 148670, "bars"),     # Nasdaq 4h — the slot whose anchor we unlocked today
    ("NG", "15m", -1635, "none"),     # the DO-NOT-TRADE slot: must still show its loss
]

READ = ("() => (typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta) ? "
        "{boxes:VIEWS.l1.meta.boxes, cap:collectLayer('l1').cap_mode, "
        "capn:collectLayer('l1').cap_1min} : null")
DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")

out = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1600})
    for inst, tf, expect, cap in CHECKS:
        pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
        pg.select_option("#inst_select", inst); pg.wait_for_timeout(1200)
        pg.select_option("#tf_select", tf); pg.wait_for_timeout(1600)
        pg.click("#run")                                  # ZERO manual modification
        pg.wait_for_function(DONE, timeout=1200000)
        m = pg.evaluate(READ) or {}
        got = (m.get("boxes") or {}).get("pnl", 0)
        gcap = m.get("cap")
        ok = abs(got - expect) < 1 and gcap == cap
        out.append({"slot": f"{inst}_{tf}", "expected": expect, "got": got,
                    "cap_expected": cap, "cap_got": gcap, "ok": ok})
        print(f"  {inst:3} {tf:3}  on-screen ${got:>10,.0f}   playbook ${expect:>10,.0f}   "
              f"cap={gcap}/{m.get('capn')} (want {cap})   {'OK' if ok else '*** MISMATCH ***'}",
              flush=True)
    b.close()

json.dump(out, open(os.path.expanduser("~/Mulham/wsg-i/dash_ready.json"), "w"), indent=1)
n_ok = sum(1 for r in out if r["ok"])
print(f"\nDASH_READY: {n_ok}/{len(out)} champions load and reproduce with ZERO manual changes", flush=True)
