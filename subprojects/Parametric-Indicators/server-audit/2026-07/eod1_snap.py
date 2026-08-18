"""Browser pass for the forced-EOD bundle: dashboard SNAPSHOT + exact PRESET, per slot. Full window only.

Deliberately does NOT switch the window. Through the dashboard, meta.boxes is computed over the whole
dataset regardless of the window selector (window-independent), so driving the UI to "2026" and reading the
boxes silently returns the FULL-window run — an earlier attempt did exactly that and produced 54 slots whose
out-of-sample column was an exact copy of the in-sample one. The window-aware numbers come from the API pass
(build_view_payload with window=...), which is how every corrected OOS number in this project was measured.

What this captures, per slot, in one visit:
    presets_raw_eod1.json  — collectLayer('l1'): the EXACT object the dashboard sends. The shareable
                             backtester replays this. meta.params drops cap_1min/cap_mode/ind_1min/flip,
                             so it cannot be used in its place.
    snapshots_eod1/*.png   — full-page screenshot of that champion's run, embedded in its playbook PDF.
                             (The shipped PDFs once carried 07-07 screenshots of STALE champions beside
                             correct text — worse than no screenshot, because the reader trusts the picture.)
"""
import json
import os
import time

from playwright.sync_api import sync_playwright

BASE = os.path.expanduser("~/Mulham/wsg-i")
SNAP = os.path.join(BASE, "snapshots_eod1")
PRESETS = os.path.join(BASE, "presets_raw_eod1.json")
os.makedirs(SNAP, exist_ok=True)

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
URL = "http://localhost:8200/"

READ = "()=>({boxes: VIEWS.l1.meta.boxes, collect: collectLayer('l1')})"
DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")
UNCLIP = ("html,body{height:auto!important;min-height:0!important;}"
          ".body{overflow:visible!important;height:auto!important;}"
          "aside{overflow-y:visible!important;height:auto!important;}"
          "main{overflow-y:visible!important;height:auto!important;}")

presets, t0, n = [], time.time(), 0
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1800})
    for inst in INSTS:
        for tf in TFS:
            n += 1
            try:
                pg.goto(URL, wait_until="networkidle", timeout=60000)
                pg.select_option("#inst_select", inst); pg.wait_for_timeout(900)
                pg.select_option("#tf_select", tf); pg.wait_for_timeout(1100)
                pg.select_option("#champ_set", "eod1")
                # the champion-set change fires an async reload; let it fully settle, then ASSERT the form
                # really holds this set's champion before running (a stale form would snapshot the wrong one)
                pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(900)
                pg.wait_for_function("() => ['eod','both'].includes(collectLayer('l1').cap_mode)", timeout=30000)
                pg.click("#run")
                pg.wait_for_function(DONE, timeout=2400000)
                d = pg.evaluate(READ)
                c, bx = d["collect"], d["boxes"]
                if c.get("cap_mode") not in ("eod", "both"):
                    raise ValueError(f"cap_mode={c.get('cap_mode')!r} — this slot does not close at the bell")
                presets.append({"inst": inst, "tf": tf, "collect": c})
                try:
                    pg.click(".segctl button[data-view='l1']", timeout=3000)
                except Exception:
                    pass
                pg.add_style_tag(content=UNCLIP); pg.wait_for_timeout(600)
                pg.screenshot(path=os.path.join(SNAP, f"{inst}_{tf}.png"), full_page=True)
                print(f"[{n:2d}/54] {inst:3} {tf:3} {c['cap_mode']:4} on-screen ${bx['pnl']:>10,.0f} "
                      f"DD ${bx['max_dd']:>8,.0f} n={bx['n_taken']:>5}  snapshot+preset OK", flush=True)
            except Exception as e:
                print(f"[{n:2d}/54] {inst:3} {tf:3}  ERROR {str(e)[:130]}", flush=True)
            json.dump(presets, open(PRESETS, "w"), indent=1)
            el = time.time() - t0
            print(f"PROGRESS {n}/54  elapsed {el/60:.1f}m  ETA {(el/n)*(54-n)/60:.1f}m", flush=True)
    b.close()
print("SNAPPASS_DONE", flush=True)
