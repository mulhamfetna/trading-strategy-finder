"""Path-B enrichment: drive the real dashboard UI for EVERY champion (6 insts x 6 tfs = 36) and capture
the COMPLETE /api/backtest payload the UI receives -- for window=full AND window=2026 (out-of-sample).
This is byte-identical to what the browser shows (same endpoint, same champion resolution), and adds the
structured full-metric set + the true 2026 OOS split the snapshots (taken at window=full) never carried.
Heavy 2m/5m run here on the server. Output: ~/Mulham/wsg-i/playbook_probe.json  (list of per-slot dicts,
each with .full and .oos2026 = the full payloads)."""
import json, os, time
from playwright.sync_api import sync_playwright

INSTS = ["GC"]
TFS = ["4h"]
WINDOWS = [("full", "full"), ("oos2026", "2026")]   # (key, dropdown value)
OUT = os.path.expanduser("~/Mulham/wsg-i/playbook_probe.json")

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1500, "height": 1800}, device_scale_factor=1)

    captured = {"payload": None}
    def on_response(resp):
        try:
            if "/api/backtest" in resp.url and resp.request.method == "POST":
                captured["payload"] = resp.json()
        except Exception:
            pass
    page.on("response", on_response)

    for inst in INSTS:
        for tf in TFS:
            rec = {"inst": inst, "tf": tf}
            try:
                page.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
                page.select_option("#inst_select", inst); page.wait_for_timeout(1000)
                page.select_option("#tf_select", tf); page.wait_for_timeout(1000)
                for key, wval in WINDOWS:
                    try:
                        page.select_option("#l1_window", wval)
                    except Exception as e:
                        rec[key + "_err"] = f"window-select: {str(e)[:80]}"
                    page.wait_for_timeout(400)
                    captured["payload"] = None
                    page.click("#run")
                    page.wait_for_function(
                        "document.querySelector('#cards') && document.querySelectorAll('#cards .card').length>0",
                        timeout=600000)
                    # give the response handler a beat to land the JSON
                    for _ in range(40):
                        if captured["payload"] is not None:
                            break
                        page.wait_for_timeout(150)
                    rec[key] = captured["payload"]
                    s = (captured["payload"] or {}).get("meta", {}).get("summary", {})
                    print(f"{inst} {tf} [{key}]: P/L ${s.get('pnl',0):,.0f} DD ${s.get('max_dd',0):,.0f} "
                          f"n={s.get('n_taken','?')}", flush=True)
            except Exception as e:
                rec["err"] = str(e)[:160]
                print(f"{inst} {tf}: ERR {rec['err']}", flush=True)
            results.append(rec)
    browser.close()

json.dump(results, open(OUT, "w"), indent=1)
ok = sum(1 for r in results if r.get("full") and r.get("oos2026"))
print(f"\nDONE: {len(results)} slots · {ok} with both full+OOS payloads · -> {OUT}", flush=True)
