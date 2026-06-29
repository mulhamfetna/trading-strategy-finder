"""Headless-browser E2E for the combined dashboard's INSTRUMENT selector.
Run: python3 server.py --port 8231 &  ;  PORT=8231 python3 tests/e2e_dashboard_instrument.py"""
import os, sys, json
from playwright.sync_api import sync_playwright

PORT = os.environ.get("PORT", "8231"); BASE = f"http://localhost:{PORT}/"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), "-", name, extra)
    if not cond: fails.append(name)

def grab(posts, r):
    if r.method == "POST" and (r.url.endswith("/api/causal_backtest") or r.url.endswith("/api/backtest_causal")):
        try: posts.append({"url": r.url.rsplit("/", 1)[-1], "body": json.loads(r.post_data)})
        except Exception: pass

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
    pg = br.new_page(); posts = []
    pg.on("request", lambda r: grab(posts, r))
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#inst_select", state="attached")
    pg.wait_for_function("() => { const e=document.querySelector('#l1_sl_soft'); return e && e.value!==''; }", timeout=60000)
    val = lambda sel: pg.eval_on_selector(sel, "e => e.value")

    check("init: inst == NQ", val("#inst_select") == "NQ", f"(got {val('#inst_select')!r})")
    nq_slsoft = float(val("#l1_sl_soft"))
    check("init: NQ sl_soft == 149.8", abs(nq_slsoft - 149.8) < 1e-6, f"(got {nq_slsoft})")

    pg.select_option("#inst_select", "ES")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to ES')", timeout=60000)
    es_slsoft = float(val("#l1_sl_soft"))
    check("switch ES: sl_soft scaled down (< NQ)", 0 < es_slsoft < nq_slsoft, f"(got {es_slsoft})")

    posts.clear(); pg.click("#run")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('done')", timeout=120000)
    insts = [pp["body"].get("instrument") for pp in posts]
    check("run ES: all 3 POSTs carry instrument=ES", insts == ["ES", "ES", "ES"], f"(got {insts})")
    br.close()

print("\n" + ("ALL E2E CHECKS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
