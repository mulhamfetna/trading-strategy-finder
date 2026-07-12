"""Capture the EXACT preset the dashboard sends for every deployed champion (collectLayer('l1')).

This is the bundle's source of truth: the champion JSONs must carry the object the UI actually sends, or
the shareable backtester will not reproduce the playbook numbers to the dollar.

All 9 markets x 6 timeframes = 54. Fast (a form read, no backtest).
Output: ~/Mulham/wsg-i/final_presets_raw.json
"""
import json
import os

from playwright.sync_api import sync_playwright

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
OUT = os.path.expanduser("~/Mulham/wsg-i/final_presets_raw.json")

results = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1800})
    for inst in INSTS:
        for tf in TFS:
            pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
            pg.select_option("#inst_select", inst); pg.wait_for_timeout(1100)
            pg.select_option("#tf_select", tf); pg.wait_for_timeout(1400)   # champion auto-loads
            cl = pg.evaluate("() => collectLayer('l1')")
            results.append({"inst": inst, "tf": tf, "collect": cl})
            en = [s["key"] for s in cl["indicators"] if s.get("enabled")]
            print(f"{inst:3} {tf:3}: k={cl['k']} flip={cl['flip']} ind_1min={cl['ind_1min']} "
                  f"cap={cl['cap_1min']}/{cl['cap_mode']} inds={len(en)}", flush=True)
    b.close()

json.dump(results, open(OUT, "w"), indent=1)
print(f"\nCAPTURE_DONE: {len(results)} presets -> {OUT}", flush=True)
