"""Drive the SERVER dashboard in a real browser and prove the eod1 champion set is selectable and runs.

The backtest executes on the server; the browser only drives the UI. Zero manual parameter edits — pick the
market, the timeframe, the champion set, press Run, read what is ON SCREEN (meta.boxes = the causal engine,
the only number that counts).
"""
from playwright.sync_api import sync_playwright

URL = "http://192.168.50.62:8200/"
CHECKS = [("YM", "4h"), ("NQ", "4h")]

READ = ("() => (typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta) ? "
        "{pnl: VIEWS.l1.meta.boxes.pnl, dd: VIEWS.l1.meta.boxes.max_dd, n: VIEWS.l1.meta.boxes.n_taken, "
        " cap: collectLayer('l1').cap_mode, capn: collectLayer('l1').cap_1min} : null")
DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1200})
    for inst, tf in CHECKS:
        for cset in ("deployed", "eod1"):
            pg.goto(URL, wait_until="networkidle", timeout=60000)
            pg.select_option("#inst_select", inst); pg.wait_for_timeout(1000)
            pg.select_option("#tf_select", tf); pg.wait_for_timeout(1200)
            pg.select_option("#champ_set", cset); pg.wait_for_timeout(1800)
            warned = pg.is_visible("#champ_warn")
            pg.click("#run")
            pg.wait_for_function(DONE, timeout=1800000)
            m = pg.evaluate(READ) or {}
            print(f"  {inst:3} {tf:3} [{cset:8}]  on-screen ${m.get('pnl',0):>10,.0f}  "
                  f"DD ${m.get('dd',0):>8,.0f}  n={m.get('n'):>4}  "
                  f"cap={m.get('cap')}/{m.get('capn')}  warning-banner={'SHOWN' if warned else 'hidden'}",
                  flush=True)
    b.close()
print("UI_CHECK_DONE")
