"""Path-B enrichment (v2): drive the real dashboard UI for EVERY champion (6 insts x 6 tfs = 36) and record,
for window=full AND window=2026 (OOS):
  - cards  : the RENDERED on-screen metric cards (the user's source-of-truth; the 'Total P/L' card is NOT
             payload.summary.pnl -- e.g. GC 4h card=+$57,570 vs summary.pnl=56,480).
  - summary: the full /api/backtest summary object (richer detail: avg_win/avg_loss, hold-times, no-entry
             streaks, pnl_2025/pnl_2026) for the deeper tearsheet.
  - params : the exact champion params the UI sent.
Heavy 2m/5m run here on the server. Output: ~/Mulham/wsg-i/playbook_validate.json"""
import json, os
from playwright.sync_api import sync_playwright

INSTS = ["NQ","GC"]
TFS = ["1h"]
WINDOWS = [("full", "full"), ("oos2026", "2026")]
OUT = os.path.expanduser("~/Mulham/wsg-i/playbook_validate.json")

READ_CARDS = ("""()=>{const o={};document.querySelectorAll('#cards .card').forEach(c=>{"""
              """const k=c.querySelector('.k'),v=c.querySelector('.v');"""
              """if(k&&v)o[k.innerText.trim().toLowerCase()]=v.innerText.trim();});return o;}""")

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1500, "height": 1800}, device_scale_factor=1)
    cap = {"p": None}

    def _safe_json(r):
        try: return r.json()
        except Exception: return cap["p"]

    page.on("response", lambda r: cap.__setitem__("p", _safe_json(r))
            if ("/api/backtest" in r.url and r.request.method == "POST") else None)

    for inst in INSTS:
        for tf in TFS:
            rec = {"inst": inst, "tf": tf}
            try:
                for key, wval in WINDOWS:
                    # fresh page load per window so leftover cards from the prior run can't be misread
                    page.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
                    page.select_option("#inst_select", inst); page.wait_for_timeout(1200)
                    page.select_option("#tf_select", tf); page.wait_for_timeout(1200)
                    try: page.select_option("#l1_window", wval)
                    except Exception as e: rec[key + "_werr"] = str(e)[:80]
                    page.wait_for_timeout(400)
                    cap["p"] = None
                    page.click("#run")
                    # wait for THIS run's /api/backtest response to land (fresh page => no stale cards)
                    for _ in range(4000):  # up to ~600s: heavy 2m/5m
                        if cap["p"] is not None: break
                        page.wait_for_timeout(150)
                    page.wait_for_function(
                        "document.querySelector('#cards') && document.querySelectorAll('#cards .card').length>0",
                        timeout=600000)
                    try: page.click(".segctl button[data-view='l1']", timeout=4000)
                    except Exception: pass
                    page.wait_for_timeout(1500)  # let cards render the fresh response
                    pl = cap["p"] or {}
                    rec[key] = {
                        "cards": page.evaluate(READ_CARDS),
                        "summary": pl.get("meta", {}).get("summary", {}),
                        "params": pl.get("meta", {}).get("params", {}),
                        "split_ts": pl.get("meta", {}).get("split_ts"),
                    }
                    tp = next((rec[key]["cards"][k] for k in rec[key]["cards"] if k.startswith("total p/l")), None)
                    print(f"{inst} {tf} [{key}]: card Total P/L = {tp}  (summary.pnl {rec[key]['summary'].get('pnl')})", flush=True)
            except Exception as e:
                rec["err"] = str(e)[:160]
                print(f"{inst} {tf}: ERR {rec['err']}", flush=True)
            results.append(rec)
    browser.close()

json.dump(results, open(OUT, "w"), indent=1)
ok = sum(1 for r in results if r.get("full") and r.get("oos2026"))
print(f"\nDONE: {len(results)} slots · {ok} with both full+OOS · -> {OUT}", flush=True)
