"""UI-verify the 6 HG champions: drive the live dashboard for HG × {4h,2h,1h,15m,5m,2m} × {full, 2026},
read the exact on-screen L1 figures (VIEWS.l1.meta.boxes) + the window-aware summary (for 2026 OOS), and
full-page snapshot each. Confirms the deployed champion reproduces + measures 2026 out-of-sample.
Output: ~/Mulham/wsg-i/hg_verify.json + snapshots/HG_<tf>.png"""
import json, os
from playwright.sync_api import sync_playwright

TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
WINDOWS = [("full", "full"), ("oos2026", "2026")]
OUT = os.path.expanduser("~/Mulham/wsg-i/hg_verify.json")
SNAP = os.path.expanduser("~/Mulham/wsg-i/snapshots"); os.makedirs(SNAP, exist_ok=True)
UNCLIP = ("html,body{height:auto!important;min-height:0!important;}.body{overflow:visible!important;height:auto!important;}"
          "aside{overflow-y:visible!important;height:auto!important;}main{overflow-y:visible!important;height:auto!important;}")
READ = ("() => (typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta) ? "
        "{boxes:VIEWS.l1.meta.boxes, summary:VIEWS.l1.meta.summary} : null")
DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")

results = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1800})
    for tf in TFS:
        rec = {"tf": tf}
        try:
            for key, wv in WINDOWS:
                pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
                pg.select_option("#inst_select", "HG"); pg.wait_for_timeout(1200)
                pg.select_option("#tf_select", tf); pg.wait_for_timeout(1500)
                pg.select_option("#l1_window", wv); pg.wait_for_timeout(400)
                pg.click("#run")
                pg.wait_for_function(DONE, timeout=600000)
                m = pg.evaluate(READ) or {}
                rec[key] = {"boxes": m.get("boxes", {}), "summary": m.get("summary", {})}
                if key == "full":
                    try: pg.click(".segctl button[data-view='l1']", timeout=3000)
                    except Exception: pass
                    pg.add_style_tag(content=UNCLIP); pg.wait_for_timeout(700)
                    pg.screenshot(path=os.path.join(SNAP, f"HG_{tf}.png"), full_page=True)
            bx = rec["full"]["boxes"]; oo = rec["oos2026"]["summary"]
            print(f"HG {tf:3}: on-screen full P/L=${bx.get('pnl',0):,.0f}  DD=${bx.get('max_dd',0):,.0f}  "
                  f"win={bx.get('win')}%  n={bx.get('n_taken')}  |  2026 OOS=${oo.get('pnl',0):,.0f} (n={oo.get('n_taken')})", flush=True)
        except Exception as e:
            rec["err"] = str(e)[:160]; print(f"HG {tf}: ERR {rec['err']}", flush=True)
        results.append(rec)
    b.close()
json.dump(results, open(OUT, "w"), indent=1)
print(f"\nDONE: {len(results)} HG champions verified -> {OUT}", flush=True)
