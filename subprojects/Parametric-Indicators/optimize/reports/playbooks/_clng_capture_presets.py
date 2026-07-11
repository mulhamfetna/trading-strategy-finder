"""Capture CL+NG exact champion presets (collectLayer('l1')) for the shareable bundle — {CL,NG} x 6 TFs.
Output: ~/Mulham/wsg-i/clng_presets_raw.json (list of {inst, tf, collect})."""
import json, os
from playwright.sync_api import sync_playwright

INSTS = ["CL", "NG"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
OUT = os.path.expanduser("~/Mulham/wsg-i/clng_presets_raw.json")

results = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1800})
    for inst in INSTS:
        for tf in TFS:
            pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
            pg.select_option("#inst_select", inst); pg.wait_for_timeout(1200)
            pg.select_option("#tf_select", tf); pg.wait_for_timeout(1500)  # champion auto-loads into the form
            cl = pg.evaluate("() => collectLayer('l1')")
            results.append({"inst": inst, "tf": tf, "collect": cl})
            en = [s["key"] for s in cl["indicators"] if s.get("enabled")]
            print(f"{inst} {tf:3}: k={cl['k']} flip={cl['flip']} ind_1min={cl['ind_1min']} "
                  f"cap={cl['cap_1min']}/{cl['cap_mode']} inds={en}", flush=True)
    b.close()

json.dump(results, open(OUT, "w"), indent=1)
print(f"\nDONE: {len(results)} CL+NG presets -> {OUT}", flush=True)
