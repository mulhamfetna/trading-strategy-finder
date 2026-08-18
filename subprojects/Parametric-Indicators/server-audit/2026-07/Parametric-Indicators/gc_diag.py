import json, os
from playwright.sync_api import sync_playwright
cap={"p":None}
with sync_playwright() as p:
    b=p.chromium.launch(headless=True)
    pg=b.new_page(viewport={"width":1500,"height":1800})
    pg.on("response", lambda r: cap.__setitem__("p", r.json()) if ("/api/backtest" in r.url and r.request.method=="POST") else None)
    # --- Run A: EXACT snapshot sequence (no window touch) ---
    pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
    pg.select_option("#inst_select","GC"); pg.wait_for_timeout(1200)
    pg.select_option("#tf_select","4h"); pg.wait_for_timeout(1200)
    cap["p"]=None
    pg.click("#run")
    pg.wait_for_function("document.querySelectorAll('#cards .card').length>0", timeout=600000)
    pg.wait_for_timeout(1500)
    card=pg.evaluate("""()=>{const o={};document.querySelectorAll('#cards .card').forEach(c=>{const k=c.querySelector('.k'),v=c.querySelector('.v');if(k&&v)o[k.innerText.trim().toLowerCase()]=v.innerText.trim();});return o;}""")
    pl=cap["p"]
    tp=next((card[k] for k in card if k.startswith("total p/l")),None)
    pr=pl["meta"]["params"]
    print("RUN A (snapshot-exact, no window touch):")
    print("  card Total P/L =", tp)
    print("  payload summary.pnl =", pl["meta"]["summary"]["pnl"])
    print("  params sent: ind_1min=%s flip=%s k=%s cap_1min=%s cooldown=%s window=%s sl=%s/%s tp=%s gate=%s dd=%s"%(
        pr.get("ind_1min"),pr.get("flip"),pr.get("k"),pr.get("cap_1min"),pr.get("cooldown"),pr.get("window"),
        pr.get("sl_soft"),pr.get("sl_hard"),pr.get("tp"),pr.get("gate_pct"),pr.get("dd_limit")))
    print("  #indicators in params:", len([k for k in pr if isinstance(pr.get(k),dict)]), "| has 'indicators' key:", "indicators" in pr)
    # --- Run B: same but explicitly select window=full first ---
    pg.select_option("#l1_window","full"); pg.wait_for_timeout(400)
    cap["p"]=None
    pg.click("#run")
    pg.wait_for_function("document.querySelectorAll('#cards .card').length>0", timeout=600000)
    pg.wait_for_timeout(1200)
    card2=pg.evaluate("""()=>{const o={};document.querySelectorAll('#cards .card').forEach(c=>{const k=c.querySelector('.k'),v=c.querySelector('.v');if(k&&v)o[k.innerText.trim().toLowerCase()]=v.innerText.trim();});return o;}""")
    tp2=next((card2[k] for k in card2 if k.startswith("total p/l")),None)
    print("RUN B (window=full explicit):")
    print("  card Total P/L =", tp2, "| payload pnl =", cap["p"]["meta"]["summary"]["pnl"])
    b.close()
