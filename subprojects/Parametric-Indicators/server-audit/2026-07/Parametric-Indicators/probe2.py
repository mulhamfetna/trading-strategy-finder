import json
from playwright.sync_api import sync_playwright
cap={"p":None}
def grab(pl):
    m=pl.get("meta",{})
    return {"boxes_pnl":m.get("boxes",{}).get("pnl"),"boxes_dd":m.get("boxes",{}).get("max_dd"),
            "boxes_win":m.get("boxes",{}).get("win"),"boxes_n":m.get("boxes",{}).get("n_taken"),
            "sum_pnl":m.get("summary",{}).get("pnl"),"sum_2025":m.get("summary",{}).get("pnl_2025"),
            "sum_2026":m.get("summary",{}).get("pnl_2026"),"sum_n":m.get("summary",{}).get("n_taken"),
            "sum_win":m.get("summary",{}).get("win"),"boxes_keys":sorted(m.get("boxes",{}).keys())}
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); pg=b.new_page(viewport={"width":1500,"height":1800})
    pg.on("response", lambda r: cap.__setitem__("p", r.json()) if ("/api/backtest" in r.url and r.request.method=="POST") else None)
    for wv in ["full","2026"]:
        pg.goto("http://localhost:8200/", wait_until="networkidle", timeout=60000)
        pg.select_option("#inst_select","GC"); pg.wait_for_timeout(1200)
        pg.select_option("#tf_select","4h"); pg.wait_for_timeout(1200)
        pg.select_option("#l1_window",wv); pg.wait_for_timeout(400)
        cap["p"]=None; pg.click("#run")
        for _ in range(4000):
            if cap["p"] is not None: break
            pg.wait_for_timeout(150)
        g=grab(cap["p"])
        print(f"[GC 4h window={wv}] boxes.pnl={g['boxes_pnl']} boxes.dd={g['boxes_dd']} boxes.win={g['boxes_win']} boxes.n={g['boxes_n']} | sum.pnl={g['sum_pnl']} sum.2025={g['sum_2025']} sum.2026={g['sum_2026']} sum.n={g['sum_n']} sum.win={g['sum_win']}")
        if wv=="full": print("  boxes keys:", g["boxes_keys"])
    b.close()
