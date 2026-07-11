"""UI-verify all 54 cap1 champions through the REAL dashboard.

For each (instrument, timeframe): drive the browser, read the exact on-screen L1 figures
(VIEWS.l1.meta.boxes = the number the user sees = TRUTH), then re-run window=2026 for the held-out
out-of-sample result. The optimizer's own full_pnl has LIED twice (HG 2m; NG 15m, which claimed +$7,061
and actually LOST $1,635) -- so nothing is believed until it reproduces here.

Writes progress to cap_verify.log after EVERY slot, so status.sh can show live state (no blind waiting).
Output: ~/Mulham/wsg-i/cap_verify.json  +  snapshots/cap1_<INST>_<tf>.png
"""
import json
import os
import time

from playwright.sync_api import sync_playwright

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
WINDOWS = [("full", "full"), ("oos2026", "2026")]

OUT = os.path.expanduser("~/Mulham/wsg-i/cap_verify.json")
SNAP = os.path.expanduser("~/Mulham/wsg-i/snapshots")
os.makedirs(SNAP, exist_ok=True)

READ = ("() => (typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta) ? "
        "{boxes:VIEWS.l1.meta.boxes, summary:VIEWS.l1.meta.summary, params:VIEWS.l1.meta.params} : null")
DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")

TOTAL = len(INSTS) * len(TFS)
results = []
t_start = time.time()

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1800})

    for inst in INSTS:
        for tf in TFS:
            n = len(results) + 1
            rec = {"inst": inst, "tf": tf}
            try:
                for key, wv in WINDOWS:
                    pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
                    pg.select_option("#inst_select", inst); pg.wait_for_timeout(1200)
                    pg.select_option("#tf_select", tf); pg.wait_for_timeout(1500)
                    pg.select_option("#l1_window", wv); pg.wait_for_timeout(400)
                    pg.click("#run")
                    pg.wait_for_function(DONE, timeout=1200000)
                    m = pg.evaluate(READ) or {}
                    rec[key] = {"boxes": m.get("boxes", {}), "summary": m.get("summary", {}),
                                "params": m.get("params", {})}
                    if key == "full":
                        try:
                            pg.click(".segctl button[data-view='l1']", timeout=3000)
                        except Exception:
                            pass
                        pg.screenshot(path=os.path.join(SNAP, f"cap1_{inst}_{tf}.png"), full_page=True)

                bx = rec["full"]["boxes"]
                oo = rec["oos2026"]["summary"]
                pr = rec["full"]["params"] or {}
                cap_mode = pr.get("cap_mode", "?")
                cap_n = pr.get("cap_1min", 0)
                print(f"VERIFIED [{n:2d}/{TOTAL}] {inst:3} {tf:3}  on-screen ${bx.get('pnl',0):>9,.0f}  "
                      f"DD ${bx.get('max_dd',0):>8,.0f}  win {bx.get('win','?'):>5}%  "
                      f"n={bx.get('n_taken','?'):>5}  |  2026 OOS ${oo.get('pnl',0):>9,.0f}  "
                      f"| cap={cap_mode}/{cap_n}", flush=True)
            except Exception as e:
                rec["err"] = str(e)[:150]
                print(f"ERROR    [{n:2d}/{TOTAL}] {inst:3} {tf:3}  {rec['err']}", flush=True)

            results.append(rec)
            json.dump(results, open(OUT, "w"), indent=1)          # checkpoint after EVERY slot

            el = time.time() - t_start
            eta = (el / n) * (TOTAL - n) / 3600
            print(f"PROGRESS {n}/{TOTAL} ({100*n//TOTAL}%)  elapsed {el/3600:.2f}h  ETA {eta:.2f}h", flush=True)

    b.close()

print(f"\nVERIFY_DONE: {len(results)} champions -> {OUT}", flush=True)
