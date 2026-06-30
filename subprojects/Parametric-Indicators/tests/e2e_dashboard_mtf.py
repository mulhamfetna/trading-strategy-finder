"""Headless-browser E2E for the dashboard's multi-timeframe (independent L2) mode.
Run: python3 server.py --port 8233 &  ;  PORT=8233 python3 tests/e2e_dashboard_mtf.py

Verifies: the L2 'mode' selector exists; the L2-timeframe picker is hidden in residual (default) and
revealed in independent; a 1h-primary + 4h-secondary run sends l2_mode/l2_tf on the L2 + combined POSTs
(and NOT on the L1 POST); and the combined tab renders trades."""
import os
import sys
import json
from playwright.sync_api import sync_playwright

PORT = os.environ.get("PORT", "8233"); BASE = f"http://localhost:{PORT}/"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
fails = []


def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), "-", name, extra)
    if not cond:
        fails.append(name)


def grab(posts, r):
    if r.method == "POST" and (r.url.endswith("/api/causal_backtest") or r.url.endswith("/api/backtest_causal")):
        try:
            posts.append({"url": r.url.rsplit("/", 1)[-1], "body": json.loads(r.post_data)})
        except Exception:
            pass


with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
    pg = br.new_page(); posts = []
    pg.on("request", lambda r: grab(posts, r))
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#l2_mode", state="attached")
    # wait until BOTH the L1 (primary) and L2 (secondary, loaded async) forms are populated
    pg.wait_for_function("() => { const a=document.querySelector('#l1_sl_soft'), b=document.querySelector('#l2_sl_soft');"
                         " return a && a.value!=='' && b && b.value!==''; }", timeout=60000)
    val = lambda sel: pg.eval_on_selector(sel, "e => e.value")
    visible = lambda sel: pg.is_visible(sel)

    # DEFAULTS (no interaction): the dashboard opens in the measured ES 1h-primary + 4h-secondary config
    check("default: instrument == ES", val("#inst_select") == "ES", f"(got {val('#inst_select')!r})")
    check("default: primary timeframe == 1h", val("#tf_select") == "1h", f"(got {val('#tf_select')!r})")
    check("default: L2 mode == independent", val("#l2_mode") == "independent", f"(got {val('#l2_mode')!r})")
    check("default: secondary timeframe == 4h", val("#l2_tf") == "4h", f"(got {val('#l2_tf')!r})")

    # the L1 form == the 1h champion; the L2 form == the 4h champion of the DEFAULT instrument (not PERMISSIVE)
    inst = val("#inst_select")
    ch1 = pg.evaluate(f"async () => (await (await fetch('/api/combined_config?instrument={inst}&tf=1h')).json()).l1_default.sl_soft")
    ch4 = pg.evaluate(f"async () => (await (await fetch('/api/combined_config?instrument={inst}&tf=4h')).json()).l1_default.sl_soft")
    check("default: L1 form = 1h champion", abs(float(val("#l1_sl_soft")) - float(ch1)) < 1e-6,
          f"(form {val('#l1_sl_soft')} vs champ {ch1})")
    check("default: L2 form = 4h champion (secondary)", abs(float(val("#l2_sl_soft")) - float(ch4)) < 1e-6,
          f"(form {val('#l2_sl_soft')} vs champ {ch4})")

    posts.clear(); pg.click("#run")             # Run with NO manual changes — reproduces the measured config
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('done')", timeout=120000)

    by_view = {pp["url"] + ":" + str(pp["body"].get("view", "l1")): pp["body"] for pp in posts}
    l2post = next((pp["body"] for pp in posts if pp["body"].get("view") == "l2"), None)
    combost = next((pp["body"] for pp in posts if pp["body"].get("view") == "combined"), None)
    l1post = next((pp["body"] for pp in posts if pp["url"] == "backtest_causal"), None)
    check("L2 POST carries l2_mode=independent + l2_tf=4h",
          bool(l2post) and l2post.get("l2_mode") == "independent" and l2post.get("l2_tf") == "4h",
          f"(got {l2post and {k: l2post.get(k) for k in ('l2_mode', 'l2_tf')}})")
    check("combined POST carries l2_mode=independent + l2_tf=4h",
          bool(combost) and combost.get("l2_mode") == "independent" and combost.get("l2_tf") == "4h")
    check("L1 POST does NOT carry l2_mode", bool(l1post) and "l2_mode" not in l1post)

    pg.click("button[data-view='combined']")     # result-view tab (combined is default-on, click to be sure)
    nrows = pg.eval_on_selector_all("#ledger tbody tr", "els => els.length")
    check("combined tab renders trades", nrows > 0, f"(rows={nrows})")
    br.close()

print(f"\n{'ALL PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
