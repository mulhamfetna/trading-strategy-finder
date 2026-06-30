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
    pg.wait_for_function("() => { const e=document.querySelector('#l1_sl_soft'); return e && e.value!==''; }", timeout=60000)
    val = lambda sel: pg.eval_on_selector(sel, "e => e.value")
    visible = lambda sel: pg.is_visible(sel)

    pg.click("#tab_l2")                          # reveal the L2 settings pane (#pane_l2)
    check("init: L2 mode == residual", val("#l2_mode") == "residual", f"(got {val('#l2_mode')!r})")
    check("init: L2 timeframe picker hidden (residual)", not visible("#l2_tf_fld"))

    pg.select_option("#l2_mode", "independent")
    check("independent: L2 timeframe picker revealed", visible("#l2_tf_fld"))

    pg.select_option("#tf_select", "1h")        # primary = 1h (finer)
    pg.select_option("#l2_tf", "4h")            # secondary = 4h (coarser)
    posts.clear(); pg.click("#run")
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
