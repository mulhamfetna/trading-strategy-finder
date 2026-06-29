"""Headless-browser E2E for the combined dashboard's TIMEFRAME SELECTOR.
Drives the REAL frontend/dashboard.html in google-chrome via Playwright and validates the
full switch flow a user performs:
  - on load        : tf_select = 4h, L1 form holds the 4h lean champion (sl_soft 149.8)
  - on TF change   : status says "switched to <tf>", the L1 form repopulates with THAT TF's
                     wsh4 champion (sl_soft changes), without a manual reload
  - on Run         : the three POSTs (/api/backtest_causal + 2x /api/causal_backtest) all carry
                     the selected TF, and the run completes ("done")

Run:
    pip install --break-system-packages playwright   # one-time (module already present here)
    python3 server.py --port 8231 &                  # start the dashboard
    PORT=8231 python3 tests/e2e_dashboard_tf_selector.py

Set CHROME=/path/to/chrome to override the browser binary. Exits non-zero if any check fails.
"""
import os, sys, json
from playwright.sync_api import sync_playwright

PORT = os.environ.get("PORT", "8231")
BASE = f"http://localhost:{PORT}/"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")

# expected L1-champion sl_soft per TF (4h = lean champion; others = wsh4 champions)
EXPECT_SLSOFT = {"4h": 149.8, "2h": 78.5, "15m": 21.6}

fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), "-", name, extra)
    if not cond: fails.append(name)


def grab_post(posts, r):
    if r.method != "POST":
        return
    if r.url.endswith("/api/causal_backtest") or r.url.endswith("/api/backtest_causal"):
        try:
            posts.append({"url": r.url.rsplit("/", 1)[-1], "body": json.loads(r.post_data)})
        except Exception:
            pass


with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
    pg = br.new_page()
    posts = []
    pg.on("request", lambda r: grab_post(posts, r))
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#tf_select", state="attached")
    # loadConfig(4h) populated the L1 form (setLayer wrote l1_sl_soft)
    pg.wait_for_function("() => { const e=document.querySelector('#l1_sl_soft'); return e && e.value!==''; }",
                         timeout=60000)

    val = lambda sel: pg.eval_on_selector(sel, "e => e.value")
    fnum = lambda sel: float(val(sel))

    # ---- 1. initial state: 4h selected, 4h lean champion loaded ----
    check("init: tf_select == 4h", val("#tf_select") == "4h", f"(got {val('#tf_select')!r})")
    check("init: L1 sl_soft == 149.8 (4h lean champion)", abs(fnum("#l1_sl_soft") - EXPECT_SLSOFT["4h"]) < 1e-6,
          f"(got {val('#l1_sl_soft')!r})")

    # ---- 2. switch to 2h: status updates + L1 form repopulates with the 2h champion (no reload) ----
    pg.select_option("#tf_select", "2h")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to 2h')",
                         timeout=60000)
    check("switch 2h: status says 'switched to 2h'",
          "switched to 2h" in pg.eval_on_selector("#status", "e=>e.textContent"))
    check("switch 2h: L1 sl_soft repopulated to 78.5 (2h champion, not 149.8)",
          abs(fnum("#l1_sl_soft") - EXPECT_SLSOFT["2h"]) < 1e-6, f"(got {val('#l1_sl_soft')!r})")

    # ---- 3. Run at 2h: all three POSTs carry tf=2h, run completes ----
    posts.clear()
    pg.click("#run")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('done')", timeout=120000)
    by_url = {pp["url"]: pp["body"] for pp in posts}
    check("run 2h: 3 POSTs captured", len(posts) == 3, f"(got {len(posts)}: {[p['url'] for p in posts]})")
    check("run 2h: /api/backtest_causal timeframe == 2h",
          by_url.get("backtest_causal", {}).get("timeframe") == "2h",
          f"(got {by_url.get('backtest_causal', {}).get('timeframe')!r})")
    causal_tfs = [pp["body"].get("tf") for pp in posts if pp["url"] == "causal_backtest"]
    check("run 2h: both /api/causal_backtest carry tf=2h", causal_tfs == ["2h", "2h"], f"(got {causal_tfs})")
    views = sorted(pp["body"].get("view") for pp in posts if pp["url"] == "causal_backtest")
    check("run 2h: causal views are l2 + combined", views == ["combined", "l2"], f"(got {views})")

    # ---- 4. switch to 15m: champion changes again ----
    pg.select_option("#tf_select", "15m")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('switched to 15m')",
                         timeout=60000)
    check("switch 15m: L1 sl_soft repopulated to 21.6 (15m champion)",
          abs(fnum("#l1_sl_soft") - EXPECT_SLSOFT["15m"]) < 1e-6, f"(got {val('#l1_sl_soft')!r})")

    br.close()

print("\n" + ("ALL E2E CHECKS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
