"""Re-capture the dashboard screenshot embedded in each playbook, for the 54 DEPLOYED champions.

The builder reads snapshots/<INST>_<TF>.png. Those were last written on 07-07 — they show the OLD
champions. So the shipped playbooks paired correct text with a screenshot of a DIFFERENT strategy, which
is arguably worse than no screenshot: the reader trusts the picture.

Drives the live server dashboard with ZERO manual changes (so what is captured is exactly what a user
sees when they pick that market + timeframe), full-page.
"""
import os
import time

from playwright.sync_api import sync_playwright

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
SNAP = os.path.expanduser("~/Mulham/wsg-i/snapshots")
os.makedirs(SNAP, exist_ok=True)

UNCLIP = ("html,body{height:auto!important;min-height:0!important;}"
          ".body{overflow:visible!important;height:auto!important;}"
          "aside{overflow-y:visible!important;height:auto!important;}"
          "main{overflow-y:visible!important;height:auto!important;}")
DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")
READ = "() => VIEWS.l1.meta.boxes.pnl"

total = len(INSTS) * len(TFS)
t0 = time.time()
n = 0
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1800})
    for inst in INSTS:
        for tf in TFS:
            n += 1
            try:
                pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
                pg.select_option("#inst_select", inst); pg.wait_for_timeout(1200)
                pg.select_option("#tf_select", tf); pg.wait_for_timeout(1600)
                pg.click("#run")                                  # zero manual modification
                pg.wait_for_function(DONE, timeout=1800000)
                pnl = pg.evaluate(READ)
                try:
                    pg.click(".segctl button[data-view='l1']", timeout=3000)
                except Exception:
                    pass
                pg.add_style_tag(content=UNCLIP)
                pg.wait_for_timeout(700)
                pg.screenshot(path=os.path.join(SNAP, f"{inst}_{tf}.png"), full_page=True)
                print(f"[{n:2d}/{total}] {inst:3} {tf:3}  captured  (on-screen ${pnl:,.0f})", flush=True)
            except Exception as e:
                print(f"[{n:2d}/{total}] {inst:3} {tf:3}  ERROR {str(e)[:110]}", flush=True)
            el = time.time() - t0
            print(f"PROGRESS {n}/{total} elapsed {el/60:.1f}m ETA {(el/n)*(total-n)/60:.1f}m", flush=True)
    b.close()

print("SNAPSHOTS_DONE", flush=True)
