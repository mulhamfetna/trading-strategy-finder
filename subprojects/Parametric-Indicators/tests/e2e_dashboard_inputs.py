"""Headless-browser E2E for the backtester dashboard input round-trip.
Drives the REAL page in google-chrome via Playwright, captures the actual POST body
sent to /api/backtest, and asserts the form reflects user edits AFTER a run
(the reset-to-default bug) — for both shared and split SL/TP modes.

Run:
    pip install --break-system-packages playwright   # one-time
    python3 server.py --port 8231 &                  # start the dashboard
    PORT=8231 python3 tests/e2e_dashboard_inputs.py   # then drive it

Requires a Chromium/Chrome binary (Playwright's bundled browser is unavailable on some
distros); set CHROME=/path/to/chrome to override. Exits non-zero if any check fails.
"""
import os, sys, json
from playwright.sync_api import sync_playwright

PORT = os.environ.get("PORT", "8231")
BASE = f"http://localhost:{PORT}/"
CHROME = os.environ.get("CHROME", "/usr/bin/google-chrome")
fails = []
def check(name, cond, extra=""):
    print(("PASS" if cond else "FAIL"), "-", name, extra)
    if not cond: fails.append(name)

with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
    pg = br.new_page()
    posts = []
    pg.on("request", lambda r: posts.append(json.loads(r.post_data)) if r.url.endswith("/api/backtest") and r.method == "POST" else None)
    pg.goto(BASE, wait_until="networkidle")
    pg.wait_for_selector("#sl_soft", state="attached")
    pg.wait_for_function("() => document.querySelector('#indpanel .ind') !== null")  # schema loaded

    val = lambda sel: pg.eval_on_selector(sel, "e => e.value")
    disp = lambda sel: pg.eval_on_selector(sel, "e => getComputedStyle(e).display")

    # ---- 1. SHARED mode: edit sl_soft, run, confirm POST got it AND form keeps it ----
    pg.fill("#sl_soft", "33"); pg.fill("#sl_hard", "44"); pg.fill("#tp", "55")
    pg.eval_on_selector("#sl_soft", "e=>e.blur()")
    posts.clear()
    pg.click("#run")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('done')", timeout=60000)
    sent = posts[-1]
    check("shared: POST sl_soft=33", sent["sl_soft"] == 33, f"(got {sent['sl_soft']})")
    check("shared: POST sl_hard=44", sent["sl_hard"] == 44, f"(got {sent['sl_hard']})")
    check("shared: POST tp=55", sent["tp"] == 55, f"(got {sent['tp']})")
    check("shared: split keys null", all(sent[k] is None for k in
          ("long_sl_soft","long_sl_hard","long_tp","short_sl_soft","short_sl_hard","short_tp")))
    check("shared: form KEEPS sl_soft=33 after run (not reset)", val("#sl_soft") == "33", f"(form shows {val('#sl_soft')!r})")
    check("shared: mode still 'shared'", val("#sltp_mode") == "shared")

    # ---- 2. SPLIT mode: switch dropdown, shared boxes hidden, edit per-side, run ----
    pg.select_option("#sltp_mode", "split")
    check("split: #sharedbox hidden", disp("#sharedbox") == "none", f"(display={disp('#sharedbox')})")
    check("split: #splitbox visible", disp("#splitbox") != "none")
    check("split: long_sl_soft prefilled from shared(33)", val("#long_sl_soft") == "33", f"(got {val('#long_sl_soft')!r})")
    pg.fill("#long_sl_soft", "120"); pg.fill("#long_sl_hard", "140"); pg.fill("#long_tp", "100")
    pg.fill("#short_sl_soft", "160"); pg.fill("#short_sl_hard", "180"); pg.fill("#short_tp", "130")
    pg.eval_on_selector("#short_tp", "e=>e.blur()")
    posts.clear()
    pg.click("#run")
    pg.wait_for_function("() => document.getElementById('status').textContent.includes('done')", timeout=60000)
    sent = posts[-1]
    check("split: POST long_sl_soft=120", sent["long_sl_soft"] == 120, f"(got {sent['long_sl_soft']})")
    check("split: POST short_tp=130", sent["short_tp"] == 130, f"(got {sent['short_tp']})")
    # THE BUG: after a split run the form must STAY in split mode with the per-side values
    check("split: mode STILL 'split' after run (not reset)", val("#sltp_mode") == "split", f"(mode={val('#sltp_mode')!r})")
    check("split: #splitbox STILL visible after run", disp("#splitbox") != "none", f"(display={disp('#splitbox')})")
    check("split: long_sl_soft STILL 120 after run", val("#long_sl_soft") == "120", f"(got {val('#long_sl_soft')!r})")
    check("split: short_tp STILL 130 after run", val("#short_tp") == "130", f"(got {val('#short_tp')!r})")

    # ---- 3. separator present between SL/TP boxes and direction ----
    check("separator hr.sep exists in Entry/exit group", pg.locator("#splitbox ~ hr.sep, hr.sep").count() >= 1)

    br.close()

print("\n" + ("ALL E2E CHECKS PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
