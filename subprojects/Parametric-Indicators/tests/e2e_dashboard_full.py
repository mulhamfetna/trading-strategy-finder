"""Comprehensive headless-Chrome UI test of the dashboard: Market group placement, instrument switching,
all 6 timeframes, the instrument x timeframe matrix, running backtests, and all three view tabs rendering.

Run: python3 server.py --port 8236 &  ;  PORT=8236 python3 tests/e2e_dashboard_full.py
Set CHROME=/path/to/chrome to override the browser binary. Exits non-zero if any check fails."""
import os, sys, json
from playwright.sync_api import sync_playwright

PORT = os.environ.get("PORT", "8236"); BASE = f"http://localhost:{PORT}/"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")

# expected NQ per-TF champion sl_soft (4h=lean, others=wsh4)
NQ_SLSOFT = {"4h": 149.8, "2h": 78.5, "1h": 49.6, "15m": 21.6, "5m": 21.9, "2m": 12.3}

fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), "-", name, extra)
    if not cond: fails.append(name)

def grab(posts, r):
    if r.method == "POST" and (r.url.endswith("/api/causal_backtest") or r.url.endswith("/api/backtest_causal")):
        try: posts.append({"u": r.url.rsplit("/", 1)[-1], "b": json.loads(r.post_data)})
        except Exception: pass

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
    pg = br.new_page(viewport={"width": 1500, "height": 950}); posts = []
    pg.on("request", lambda r: grab(posts, r))
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#inst_select", state="attached")
    pg.wait_for_function("() => { const e=document.querySelector('#l1_sl_soft'); return e && e.value!==''; }", timeout=60000)
    val = lambda s: pg.eval_on_selector(s, "e => e.value")
    txt = lambda s: pg.eval_on_selector(s, "e => e.textContent")
    fnum = lambda s: float(val(s))

    # ---- 1. Market group: both selectors live INSIDE the settings panel (aside), not the header ----
    check("Market group: inst_select is inside <aside>",
          pg.eval_on_selector("#inst_select", "e => !!e.closest('aside')"))
    check("Market group: tf_select is inside <aside>",
          pg.eval_on_selector("#tf_select", "e => !!e.closest('aside')"))
    check("Market group: NOT in header .hdr-right",
          pg.eval_on_selector("#inst_select", "e => !e.closest('.hdr-right')"))
    check("Market group: heading present",
          pg.locator("aside .sgroup h3", has_text="Market").count() >= 1)

    # ---- 2. defaults: NQ + 4h lean champion ----
    check("default inst NQ", val("#inst_select") == "NQ")
    check("default tf 4h", val("#tf_select") == "4h")
    check("NQ 4h sl_soft 149.8", abs(fnum("#l1_sl_soft") - 149.8) < 1e-6, f"(got {val('#l1_sl_soft')})")

    # ---- 3. NQ: sweep all 6 timeframes, each loads its champion ----
    for tf, exp in NQ_SLSOFT.items():
        pg.select_option("#tf_select", tf)
        pg.wait_for_function(f"() => document.getElementById('status').textContent.includes('switched to NQ {tf}') "
                             f"|| document.getElementById('l1_sl_soft').value==='{exp}'", timeout=60000)
        check(f"NQ {tf}: champion sl_soft {exp}", abs(fnum("#l1_sl_soft") - exp) < 1e-6, f"(got {val('#l1_sl_soft')})")

    # ---- 4. instrument x timeframe matrix: ES at every TF loads a scaled (smaller) sl_soft ----
    pg.select_option("#tf_select", "4h")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to NQ 4h')", timeout=60000)
    pg.select_option("#inst_select", "ES")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to ES 4h')", timeout=60000)
    for tf in ("4h", "2h", "1h", "15m", "5m", "2m"):
        pg.select_option("#tf_select", tf)
        pg.wait_for_function(f"() => document.getElementById('status').textContent.includes('switched to ES {tf}')", timeout=60000)
        es_ss = fnum("#l1_sl_soft")
        check(f"ES {tf}: sl_soft scaled (< NQ 4h 149.8, > 0)", 0 < es_ss < 149.8, f"(got {es_ss})")

    # ---- 5. RUN at ES/2h → 3 POSTs carry ES+2h, all three view tabs render ----
    pg.select_option("#tf_select", "2h")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to ES 2h')", timeout=60000)
    posts.clear(); pg.click("#run")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('done')", timeout=120000)
    insts = sorted(set(pp["b"].get("instrument") for pp in posts))
    tfs = sorted(set(pp["b"].get("tf", pp["b"].get("timeframe")) for pp in posts))
    check("ES/2h run: all POSTs instrument=ES", insts == ["ES"], f"(got {insts})")
    check("ES/2h run: all POSTs tf=2h", tfs == ["2h"], f"(got {tfs})")
    for view, vid in (("Combined", "combined"), ("L1", "l1"), ("L2", "l2")):
        pg.eval_on_selector(f"#viewtabs button[data-view='{vid}']", "b => b.click()")
        pg.wait_for_function(f"() => document.getElementById('status').textContent.toUpperCase().includes('{view.upper()}')", timeout=30000)
        st = txt("#status")
        check(f"ES/2h view '{view}' renders (status shows counts)", view.upper() in st.upper() and "candles" in st, f"(status={st!r})")

    # ---- 6. settings L1/L2 nav-tabs toggle the panes ----
    pg.eval_on_selector("#tab_l2", "e => e.click()")
    check("L2 settings pane visible after tab click", pg.eval_on_selector("#pane_l2", "e => getComputedStyle(e).display") != "none")
    pg.eval_on_selector("#tab_l1", "e => e.click()")
    check("L1 settings pane visible after tab click", pg.eval_on_selector("#pane_l1", "e => getComputedStyle(e).display") != "none")

    # ---- 7. back to NQ/4h → lean champion restored (round-trip) ----
    pg.select_option("#inst_select", "NQ")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to NQ 2h')", timeout=60000)
    pg.select_option("#tf_select", "4h")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to NQ 4h')", timeout=60000)
    check("round-trip NQ 4h: sl_soft back to 149.8", abs(fnum("#l1_sl_soft") - 149.8) < 1e-6, f"(got {val('#l1_sl_soft')})")

    br.close()

print("\n" + ("ALL UI CHECKS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
