"""GC 4h with the 4h-DECISION-FRAME champion (ind_1min=false) from the 1-min-vs-4h comparison report
(4h_wsi_pareto_GC.csv row 0, full_pnl ~$97,889). The dashboard doesn't serve this champion, so we inject
its exact params into the L1 form via setLayer(), set ind_1min=false, run full + 2026, read meta.boxes/
summary, and snapshot. Output: ~/Mulham/wsg-i/gc4h_ind4h.json + snapshots/GC_4h_ind4h.png"""
import json, os, sys
sys.path.insert(0, os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators"))
from indicators import library
from playwright.sync_api import sync_playwright

CH = json.load(open("/tmp/gc_wsi_ind4h.json"))["4h"]
# FULL spec list: applySpecsTo needs .length AND only touches keys it's given — so include EVERY indicator,
# champion's set enabled (with its tuned params + fixed library mode), all others explicitly disabled.
champ_inds = CH["indicators"]
specs = []
for key in library.REGISTRY:
    meta = library.SCHEMA[key]
    en = key in champ_inds
    params = dict(champ_inds[key]) if en else {p["name"]: p["default"] for p in meta.get("params", [])}
    specs.append({"key": key, "enabled": en, "mode": meta["mode"], "params": params})
P = dict(CH["box"]); P["ind_1min"] = False; P["indicators"] = specs
OUT = os.path.expanduser("~/Mulham/wsg-i/gc4h_ind4h.json")
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

rec = {"inst": "GC", "tf": "4h", "ind_1min": False, "champion": CH}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1500, "height": 1800}, device_scale_factor=1)
    for key, wval in [("full", "full"), ("oos2026", "2026")]:
        page.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
        page.select_option("#inst_select", "GC"); page.wait_for_timeout(1200)
        page.select_option("#tf_select", "4h"); page.wait_for_timeout(1500)   # builds indicator panel + default
        page.evaluate("(P) => setLayer('l1', P)", P)                          # inject the 4h-frame champion
        page.wait_for_timeout(400)
        page.select_option("#l1_ind_1min", "false")                          # belt-and-suspenders
        page.select_option("#l1_window", wval); page.wait_for_timeout(400)
        page.click("#run")
        page.wait_for_function(RUN_DONE, timeout=600000)
        meta = page.evaluate(READ_META) or {}
        rec[key] = {"boxes": meta.get("boxes", {}), "summary": meta.get("summary", {}),
                    "params": meta.get("params", {}), "split_ts": meta.get("split_ts")}
        bx, sm = rec[key]["boxes"], rec[key]["summary"]
        print(f"GC 4h ind4h-champion [{key}]: boxes.pnl={bx.get('pnl')}  summary.pnl={sm.get('pnl')}  win={bx.get('win')}  n={bx.get('n_taken')}", flush=True)
        if key == "full":
            page.add_style_tag(content=UNCLIP); page.wait_for_timeout(800)
            page.screenshot(path=SHOT, full_page=True)
            print(f"snapshot -> {SHOT}", flush=True)
    b.close()
json.dump([rec], open(OUT, "w"), indent=1)
print(f"DONE -> {OUT}", flush=True)
