"""UI-verify the DEPLOYED best-per-slot set through the real browser.

For every slot the deploy CHANGED (22 of them), select the market + timeframe with ZERO manual edits, press
Run, and require the ON-SCREEN number (meta.boxes — the causal engine, what the user actually sees) to equal
the number we recorded when we decided the head-to-head. A mismatch means the dashboard is serving something
other than what we measured, which is the failure mode that has bitten this project hardest.

Also spot-checks 6 KEPT slots: the deploy must not have disturbed them.
"""
import json
import os

from playwright.sync_api import sync_playwright

BASE = os.path.expanduser("~/Mulham/wsg-i")
dec = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/precise_decision.json"))}

# expected on-screen full-window P/L = whatever the WINNING candidate measured
checks = []
for (inst, tf), r in dec.items():
    w = r["winner"]
    exp = (r["c"].get(w) or {}).get("full", {}).get("pnl")
    if exp is None:
        continue
    checks.append((inst, tf, exp, w))
changed = [c for c in checks if c[3] != "deployed"]
kept = [c for c in checks if c[3] == "deployed"][:6]
todo = changed + kept

DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")
READ = ("() => ({pnl: VIEWS.l1.meta.boxes.pnl, dd: VIEWS.l1.meta.boxes.max_dd, "
        "n: VIEWS.l1.meta.boxes.n_taken, cap: collectLayer('l1').cap_mode, "
        "capn: collectLayer('l1').cap_1min, set: (document.getElementById('champ_set')||{}).value})")

ok = bad = 0
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1200})
    for i, (inst, tf, exp, src) in enumerate(todo, 1):
        try:
            pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
            pg.select_option("#inst_select", inst); pg.wait_for_timeout(900)
            pg.select_option("#tf_select", tf); pg.wait_for_timeout(1300)
            pg.click("#run")                                   # ZERO manual modification
            pg.wait_for_function(DONE, timeout=2400000)
            m = pg.evaluate(READ)
            good = abs(m["pnl"] - exp) < 1.0
            ok += good; bad += (not good)
            tag = "kept" if src == "deployed" else src.upper()
            print(f"[{i:2d}/{len(todo)}] {inst:3} {tf:3} {tag:8} on-screen ${m['pnl']:>10,.0f}  "
                  f"recorded ${exp:>10,.0f}  cap={m['cap']}/{m['capn']}  set={m['set']}  "
                  f"{'OK' if good else '*** MISMATCH ***'}", flush=True)
        except Exception as e:
            bad += 1
            print(f"[{i:2d}/{len(todo)}] {inst:3} {tf:3}  ERROR {str(e)[:110]}", flush=True)
    b.close()

print(f"\nDEPLOY VERIFY: {ok}/{len(todo)} reproduce the recorded number on screen, zero manual changes")
print("DEPLOYVERIFY_DONE" if bad == 0 else f"*** {bad} FAILED ***")
