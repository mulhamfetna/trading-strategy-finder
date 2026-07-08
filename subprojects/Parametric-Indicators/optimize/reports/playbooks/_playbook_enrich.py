"""Path-B enrichment (v2): drive the real dashboard UI for EVERY champion (6 insts x 6 tfs = 36) and record,
for window=full AND window=2026 (OOS):
  - cards  : the RENDERED on-screen metric cards (the user's source-of-truth; the 'Total P/L' card is NOT
             payload.summary.pnl -- e.g. GC 4h card=+$57,570 vs summary.pnl=56,480).
  - summary: the full /api/backtest summary object (richer detail: avg_win/avg_loss, hold-times, no-entry
             streaks, pnl_2025/pnl_2026) for the deeper tearsheet.
  - params : the exact champion params the UI sent.
Heavy 2m/5m run here on the server. Output: ~/Mulham/wsg-i/playbook_metrics.json"""
import json, os
from playwright.sync_api import sync_playwright

INSTS = ["NQ", "ES", "GC", "SI", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
WINDOWS = [("full", "full"), ("oos2026", "2026")]
OUT = os.path.expanduser("~/Mulham/wsg-i/playbook_metrics.json")

READ_CARDS = ("""()=>{const o={};document.querySelectorAll('#cards .card').forEach(c=>{"""
              """const k=c.querySelector('.k'),v=c.querySelector('.v');"""
              """if(k&&v)o[k.innerText.trim().toLowerCase()]=v.innerText.trim();});return o;}""")

# Read the L1 payload straight from the frontend's JS state (VIEWS.l1) once the run finishes — no network
# intercept, so heavy-TF payloads can't race to a silent None. A failed heavy run leaves VIEWS.l1 null and
# is caught as a timeout (recorded as an error), not a blank.
# VIEWS is a top-level `const` (lexical global) — reachable as a bare identifier, NOT as window.VIEWS.
READ_META = ("() => (typeof VIEWS !== 'undefined' && VIEWS.l1 && VIEWS.l1.meta) ? "
             "{boxes:VIEWS.l1.meta.boxes, summary:VIEWS.l1.meta.summary, params:VIEWS.l1.meta.params, "
             "split_ts:VIEWS.l1.meta.split_ts} : null")
RUN_DONE = ("() => typeof VIEWS !== 'undefined' && VIEWS.l1 && VIEWS.l1.meta && "
            "document.querySelector('#run') && !document.querySelector('#run').disabled")

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1500, "height": 1800}, device_scale_factor=1)

    for inst in INSTS:
        for tf in TFS:
            rec = {"inst": inst, "tf": tf}
            try:
                for key, wval in WINDOWS:
                    # fresh page load per window: VIEWS.l1 resets to null, so RUN_DONE is a clean per-run signal
                    page.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
                    page.select_option("#inst_select", inst); page.wait_for_timeout(1200)
                    page.select_option("#tf_select", tf); page.wait_for_timeout(1200)
                    try: page.select_option("#l1_window", wval)
                    except Exception as e: rec[key + "_werr"] = str(e)[:80]
                    page.wait_for_timeout(400)
                    page.click("#run")
                    page.wait_for_function(RUN_DONE, timeout=600000)  # heavy 2m/5m ok; failed run => timeout
                    meta = page.evaluate(READ_META) or {}
                    rec[key] = {
                        "boxes": meta.get("boxes", {}),      # ON-SCREEN truth (window-independent)
                        "summary": meta.get("summary", {}),  # window-aware (+pnl_2025/pnl_2026, avg_win/loss, holds)
                        "params": meta.get("params", {}),
                        "split_ts": meta.get("split_ts"),
                    }
                    bx, sm = rec[key]["boxes"], rec[key]["summary"]
                    print(f"{inst} {tf} [{key}]: boxes.pnl={bx.get('pnl')} (on-screen)  summary.pnl={sm.get('pnl')}  summary.2026={sm.get('pnl_2026')}", flush=True)
            except Exception as e:
                rec["err"] = str(e)[:160]
                print(f"{inst} {tf}: ERR {rec['err']}", flush=True)
            results.append(rec)
    browser.close()

json.dump(results, open(OUT, "w"), indent=1)
ok = sum(1 for r in results if r.get("full") and r.get("oos2026"))
print(f"\nDONE: {len(results)} slots · {ok} with both full+OOS · -> {OUT}", flush=True)
