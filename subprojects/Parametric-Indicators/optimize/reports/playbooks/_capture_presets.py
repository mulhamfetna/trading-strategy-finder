"""Capture the EXACT param object the dashboard sends per champion — collectLayer('l1') — for all 36
deployed slots + the GC 4h 4h-indicator variant. This is a fast FORM read (no backtest): selecting an
instrument+timeframe auto-loads that champion into the L1 form, and collectLayer serialises it verbatim
(box knobs + full indicator spec list + cap_1min/cap_mode/ind_1min/flip that meta.params drops).
Output: ~/Mulham/wsg-i/presets_raw.json  (list of {inst, tf, ind4h?, collect})"""
import json, os, sys
sys.path.insert(0, os.path.expanduser("~/Mulham/wsg-i/Parametric-Indicators"))
from indicators import library
from playwright.sync_api import sync_playwright

INSTS = ["NQ", "ES", "GC", "SI", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
OUT = os.path.expanduser("~/Mulham/wsg-i/presets_raw.json")

# variant champion (GC 4h, ind_1min=false) spec, same reconstruction as the playbook
CH = json.load(open("/tmp/gc_wsi_ind4h.json"))["4h"]
_champ_inds = CH["indicators"]
_variant_specs = []
for key in library.REGISTRY:
    meta = library.SCHEMA[key]
    en = key in _champ_inds
    params = dict(_champ_inds[key]) if en else {p["name"]: p["default"] for p in meta.get("params", [])}
    _variant_specs.append({"key": key, "enabled": en, "mode": meta["mode"], "params": params})
_VP = dict(CH["box"]); _VP["ind_1min"] = False; _VP["indicators"] = _variant_specs

COLLECT = "() => collectLayer('l1')"
results = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width": 1500, "height": 1800})
    for inst in INSTS:
        for tf in TFS:
            page.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
            page.select_option("#inst_select", inst); page.wait_for_timeout(1200)
            page.select_option("#tf_select", tf); page.wait_for_timeout(1500)  # champion auto-loads into form
            cl = page.evaluate(COLLECT)
            results.append({"inst": inst, "tf": tf, "collect": cl})
            en = [s["key"] for s in cl["indicators"] if s.get("enabled")]
            print(f"{inst} {tf}: k={cl['k']} flip={cl['flip']} ind_1min={cl['ind_1min']} cap={cl['cap_1min']}/{cl['cap_mode']} inds={en}", flush=True)
    # variant
    page.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
    page.select_option("#inst_select", "GC"); page.wait_for_timeout(1200)
    page.select_option("#tf_select", "4h"); page.wait_for_timeout(1500)
    page.evaluate("(P)=>setLayer('l1',P)", _VP); page.wait_for_timeout(300)
    page.select_option("#l1_ind_1min", "false")
    cl = page.evaluate(COLLECT)
    results.append({"inst": "GC", "tf": "4h", "ind4h": True, "collect": cl})
    en = [s["key"] for s in cl["indicators"] if s.get("enabled")]
    print(f"GC 4h [ind4h variant]: k={cl['k']} flip={cl['flip']} ind_1min={cl['ind_1min']} cap={cl['cap_1min']}/{cl['cap_mode']} inds={en}", flush=True)
    b.close()
json.dump(results, open(OUT, "w"), indent=1)
print(f"\nDONE: {len(results)} presets -> {OUT}", flush=True)
