"""Drive the real dashboard UI on the server for EVERY champion (ALL instruments x ALL timeframes = 36),
read the on-screen L1 values, screenshot the full dashboard, and record match-vs-recorded plus whether the
red error banner appears (proves the Math.max-spread recursion fix). Heavy 2m/5m run here because the server
has the RAM the laptop doesn't. Output: snapshots/<inst>_<tf>.png + ui_snapshot_results.json."""
import json, os
from playwright.sync_api import sync_playwright

INSTS = ["NQ", "ES", "GC", "SI", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
# un-clip the app-shell so full_page captures the WHOLE dashboard (main scrolls internally otherwise -> crop)
UNCLIP = ("html,body{height:auto!important;min-height:0!important;}"
          ".body{overflow:visible!important;height:auto!important;}"
          "aside{overflow-y:visible!important;height:auto!important;}"
          "main{overflow-y:visible!important;height:auto!important;}")
OUTDIR = os.path.expanduser("~/Mulham/wsg-i/snapshots")
os.makedirs(OUTDIR, exist_ok=True)
REC = json.load(open(os.path.expanduser("~/Mulham/wsg-i/recorded.json"))) if os.path.exists(
    os.path.expanduser("~/Mulham/wsg-i/recorded.json")) else {}

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1500, "height": 1800}, device_scale_factor=1)
    for inst in INSTS:
        for tf in TFS:
            rec = {"inst": inst, "tf": tf}
            try:
                page.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
                page.select_option("#inst_select", inst); page.wait_for_timeout(1200)
                page.select_option("#tf_select", tf); page.wait_for_timeout(1200)
                page.click("#run")
                page.wait_for_function(
                    "document.querySelector('#cards') && document.querySelectorAll('#cards .card').length>0",
                    timeout=600000)
                try:
                    page.click(".segctl button[data-view='l1']", timeout=4000)
                except Exception:
                    pass
                page.wait_for_timeout(1500)
                cards = page.evaluate("""() => {const o={};document.querySelectorAll('#cards .card').forEach(c=>{
                    const k=c.querySelector('.k'),v=c.querySelector('.v');if(k&&v)o[k.innerText.trim().toLowerCase()]=v.innerText.trim();});return o;}""")
                def g(sub):
                    return next((cards[k] for k in cards if k.startswith(sub)), None)
                rec["onscreen_pnl"] = g("total p/l"); rec["max_dd"] = g("max drawdown")
                rec["win"] = g("win rate"); rec["pf"] = g("profit factor")
                rec["payoff"] = g("payoff"); rec["trades"] = g("l1 entries")
                rec["err_banner"] = page.evaluate(
                    "() => {const e=document.querySelector('#err'); return !!(e && getComputedStyle(e).display!=='none' && e.offsetParent!==null);}")
                page.add_style_tag(content=UNCLIP)   # expand shell so nothing is cropped
                page.wait_for_timeout(800)
                shot = os.path.join(OUTDIR, f"{inst}_{tf}.png")
                page.screenshot(path=shot, full_page=True)
                rec["snapshot"] = os.path.basename(shot)
                r = REC.get(inst, {}).get(tf, {}).get("pnl")
                if r is not None and rec["onscreen_pnl"]:
                    onnum = float(rec["onscreen_pnl"].replace("+", "").replace("−", "-").replace("$", "").replace(",", ""))
                    rec["recorded_pnl"] = round(r)
                    rec["match"] = abs(onnum - r) <= max(2.0, 0.01 * abs(r))
                print(f"{inst} {tf}: onscreen={rec.get('onscreen_pnl')} recorded=${rec.get('recorded_pnl')} match={rec.get('match')} banner={rec.get('err_banner')}", flush=True)
            except Exception as e:
                rec["err"] = str(e)[:120]
                print(f"{inst} {tf}: ERR {rec['err']}", flush=True)
            results.append(rec)
    browser.close()
json.dump(results, open(os.path.expanduser("~/Mulham/wsg-i/ui_snapshot_results.json"), "w"), indent=1)
ok = sum(1 for r in results if r.get("match"))
banners = sum(1 for r in results if r.get("err_banner"))
print(f"\nDONE: {len(results)} champions · {ok} recorded-matches · {banners} error-banners · snapshots in {OUTDIR}")
