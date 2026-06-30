"""Headless-Chrome UI test: the optimized ES champions reproduce in the dashboard.
Loads ES/4h (auto-loads the 4h champion incl. cap_1min), runs, and asserts the L1 rich-engine P/L matches
the optimizer's full_pnl (~$38.7k ± rounding); checks the cap field loaded; checks profile-import populates.
Run: python3 server.py --port 8260 &  ;  PORT=8260 python3 tests/e2e_dashboard_es_champions.py"""
import os, sys, json
from playwright.sync_api import sync_playwright

PORT = os.environ.get("PORT", "8260"); BASE = f"http://localhost:{PORT}/"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), "-", name, extra)
    if not cond: fails.append(name)

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
    pg = br.new_page()
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#inst_select", state="attached")
    pg.wait_for_function("() => { const e=document.querySelector('#l1_sl_soft'); return e && e.value!==''; }", timeout=60000)
    val = lambda s: pg.eval_on_selector(s, "e => e.value")
    fnum = lambda s: float(val(s))

    # switch to ES (4h default) → auto-loads the 4h champion
    pg.select_option("#inst_select", "ES")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to ES 4h')", timeout=60000)
    check("ES/4h champion loaded: sl_soft ~25.6", abs(fnum("#l1_sl_soft") - 25.6) < 0.5, f"(got {val('#l1_sl_soft')})")
    check("ES/4h cap_1min loaded = 871", abs(fnum("#l1_cap_1min") - 871) < 1, f"(got {val('#l1_cap_1min')})")
    check("ES/4h cap_mode = bars", val("#l1_cap_mode") == "bars", f"(got {val('#l1_cap_mode')!r})")
    # the champion default appears in the L1 profile dropdown labelled as a champion (not 'permissive')
    label = pg.evaluate("() => { const o=document.querySelector('#l1_strategy').options; return o.length?o[0].textContent:''; }")
    check("ES/4h L1 label says champion (not permissive)", "champion" in label.lower() and "permissive" not in label.lower(), f"(got {label!r})")

    # run → capture the L1 rich-engine P/L
    # ES 4h champion runs 10 indicators incl. slow SMC (ifvg/cisd) on the 487k-bar 1-min frame × 3 views,
    # interactive + uncached → a few minutes. Capture the L1 (backtest_causal) response directly.
    with pg.expect_response(lambda r: r.url.endswith("/api/backtest_causal") and r.request.method == "POST",
                            timeout=420000) as ri:
        pg.click("#run")
    body = ri.value.json()
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('done')", timeout=60000)
    # the DISPLAYED L1 P/L = log-derived boxes (causal, capped) — meta.boxes.pnl
    pnl = body.get("meta", {}).get("boxes", {}).get("pnl")
    check("ES/4h run: L1 P/L reproduces optimizer full_pnl (~$38.7k)",
          pnl is not None and 35000 <= pnl <= 43000, f"(got {pnl})")

    # profile import: pick the 1h champion profile from the dropdown → form repopulates (sl_soft 25.6 → ~8.4)
    picked = pg.evaluate("""() => { const s=document.querySelector('#l1_strategy');
        const o=[...s.options].find(x=>x.textContent.includes('ES 1h champion'));
        if(!o) return false; s.value=o.value; s.dispatchEvent(new Event('change',{bubbles:true})); return true; }""")
    check("profile dropdown has 'ES 1h champion'", picked is True)
    pg.wait_for_function("() => Math.abs(parseFloat(document.querySelector('#l1_sl_soft').value) - 8.4) < 0.6", timeout=15000)
    check("profile import: 'ES 1h champion' populates sl_soft ~8.4", abs(fnum("#l1_sl_soft") - 8.4) < 0.6, f"(got {val('#l1_sl_soft')})")

    br.close()

print("\n" + ("ALL ES-CHAMPION UI CHECKS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
