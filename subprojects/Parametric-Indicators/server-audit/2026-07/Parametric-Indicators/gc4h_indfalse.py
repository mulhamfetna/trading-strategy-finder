"""One-off: GC 4h with indicators on the 4h DECISION frame (ind_1min=false) — the stronger 4h-indicator
variant from the 1-min-vs-4h comparison report. Captures meta.boxes + summary (full + 2026) AND a fresh
full-page snapshot on this frame. Output: ~/Mulham/wsg-i/gc4h_indfalse.json + snapshots/GC_4h_ind4h.png"""
import json, os
from playwright.sync_api import sync_playwright

OUT = os.path.expanduser("~/Mulham/wsg-i/gc4h_indfalse.json")
SHOT = os.path.expanduser("~/Mulham/wsg-i/snapshots/GC_4h_ind4h.png")
UNCLIP = ("html,body{height:auto!important;min-height:0!important;}"
          ".body{overflow:visible!important;height:auto!important;}"
          "aside{overflow-y:visible!important;height:auto!important;}"
          "main{overflow-y:visible!important;height:auto!important;}")
READ_META = ("() => (typeof VIEWS !== 'undefined' && VIEWS.l1 && VIEWS.l1.meta) ? "
             "{boxes:VIEWS.l1.meta.boxes, summary:VIEWS.l1.meta.summary, params:VIEWS.l1.meta.params, "
             "split_ts:VIEWS.l1.meta.split_ts} : null")
RUN_DONE = ("() => typeof VIEWS !== 'undefined' && VIEWS.l1 && VIEWS.l1.meta && "
            "document.querySelector('#run') && !document.querySelector('#run').disabled")

rec = {"inst": "GC", "tf": "4h", "ind_1min": False}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1500, "height": 1800}, device_scale_factor=1)
    for key, wval in [("full", "full"), ("oos2026", "2026")]:
        page.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
        page.select_option("#inst_select", "GC"); page.wait_for_timeout(1200)
        page.select_option("#tf_select", "4h"); page.wait_for_timeout(1200)
        page.select_option("#l1_ind_1min", "false")          # indicators on the 4h decision frame
        page.select_option("#l1_window", wval); page.wait_for_timeout(400)
        page.click("#run")
        page.wait_for_function(RUN_DONE, timeout=600000)
        meta = page.evaluate(READ_META) or {}
        rec[key] = {"boxes": meta.get("boxes", {}), "summary": meta.get("summary", {}),
                    "params": meta.get("params", {}), "split_ts": meta.get("split_ts")}
        bx, sm = rec[key]["boxes"], rec[key]["summary"]
        print(f"GC 4h ind4h [{key}]: boxes.pnl={bx.get('pnl')}  summary.pnl={sm.get('pnl')}  win={bx.get('win')}", flush=True)
        if key == "full":
            page.add_style_tag(content=UNCLIP); page.wait_for_timeout(800)
            page.screenshot(path=SHOT, full_page=True)
            print(f"snapshot -> {SHOT}", flush=True)
    b.close()
json.dump([rec], open(OUT, "w"), indent=1)
print(f"DONE -> {OUT}", flush=True)
