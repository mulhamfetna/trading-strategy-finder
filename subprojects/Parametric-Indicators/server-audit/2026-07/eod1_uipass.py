"""ONE browser sweep over all 54 forced-EOD champions that produces EVERYTHING the bundle needs.

The old pipeline drove the dashboard THREE separate times (metrics, then snapshots, then presets). That is
three full backtest sweeps including the heavy 2m/5m frames. This does all three per slot in a single visit:

    cards   : the RENDERED on-screen metric cards — the user's source of truth. NOT payload.summary:
              the on-screen Total P/L is meta.boxes.pnl (causal), and summary.pnl can differ.
    summary : the full /api/backtest summary (avg win/loss, hold times, pnl_2025/2026) for the tearsheet.
    params  : collectLayer('l1') — the EXACT object the dashboard sends, which the shareable backtester
              replays. meta.params drops cap_1min/cap_mode/ind_1min/flip, so it cannot be used here.
    snapshot: full-page screenshot of the FULL-window run, embedded in the PDF.

Champion set is selected in the UI (champ_set=eod1), so what is captured is exactly what a user sees.
Runs ON THE SERVER against its own dashboard. Heavy timeframes are fine here; never locally.
"""
import json
import os
import time

from playwright.sync_api import sync_playwright

BASE = os.path.expanduser("~/Mulham/wsg-i")
SNAP = os.path.join(BASE, "snapshots_eod1")
OUT = os.path.join(BASE, "playbook_metrics_eod1.json")
PRESETS = os.path.join(BASE, "presets_raw_eod1.json")
os.makedirs(SNAP, exist_ok=True)

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
URL = "http://localhost:8200/"

READ_CARDS = ("()=>{const o={};document.querySelectorAll('#cards .card').forEach(c=>{"
              "const k=c.querySelector('.k'),v=c.querySelector('.v');"
              "if(k&&v)o[k.innerText.trim().toLowerCase()]=v.innerText.trim();});return o;}")
READ_ALL = ("()=>({boxes: VIEWS.l1.meta.boxes, summary: VIEWS.l1.meta.summary, "
            "collect: collectLayer('l1'), split_ts: (VIEWS.l1.meta.split_ts||null)})")
DONE = ("() => typeof VIEWS!=='undefined' && VIEWS.l1 && VIEWS.l1.meta && "
        "document.querySelector('#run') && !document.querySelector('#run').disabled")
UNCLIP = ("html,body{height:auto!important;min-height:0!important;}"
          ".body{overflow:visible!important;height:auto!important;}"
          "aside{overflow-y:visible!important;height:auto!important;}"
          "main{overflow-y:visible!important;height:auto!important;}")

rows, presets, t0, n = [], [], time.time(), 0
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1500, "height": 1800})
    for inst in INSTS:
        for tf in TFS:
            n += 1
            rec = {"inst": inst, "tf": tf}
            try:
                for key, win in (("full", "full"), ("oos2026", "2026")):
                    pg.goto(URL, wait_until="networkidle", timeout=60000)
                    pg.select_option("#inst_select", inst); pg.wait_for_timeout(900)
                    pg.select_option("#tf_select", tf); pg.wait_for_timeout(1100)
                    pg.select_option("#champ_set", "eod1")
                    # ⚠️ RACE — this cost a full 30-minute sweep. Changing instrument / timeframe /
                    # champion-set fires an ASYNC reload, and its setLayer() REWRITES the window field from
                    # the champion defaults (always "full"). Setting the window and then sleeping loses that
                    # race: the first run of this script asked for 2026 on all 54 slots, silently got the
                    # FULL-window result back, and the out-of-sample column came out an exact copy of the
                    # in-sample one. Every number looked perfectly plausible.
                    # So: let the reload settle, set the window, then ASSERT the form really holds it at the
                    # instant we press Run. No assertion, no run.
                    pg.wait_for_load_state("networkidle"); pg.wait_for_timeout(800)
                    pg.select_option("#l1_window", win)
                    pg.wait_for_function(f"() => collectLayer('l1').window === '{win}'", timeout=30000)
                    pg.click("#run")
                    pg.wait_for_function(DONE, timeout=2400000)
                    d = pg.evaluate(READ_ALL)
                    got = (d["collect"] or {}).get("window")          # what the form ACTUALLY ran
                    if got != win:
                        raise ValueError(f"asked for window={win!r} but the form ran {got!r}")
                    rec[key] = {"cards": pg.evaluate(READ_CARDS), "boxes": d["boxes"],
                                "summary": d["summary"], "params": d["collect"],
                                "split_ts": d["split_ts"]}
                    if key == "full":
                        presets.append({"inst": inst, "tf": tf, "collect": d["collect"]})
                        try:
                            pg.click(".segctl button[data-view='l1']", timeout=3000)
                        except Exception:
                            pass
                        pg.add_style_tag(content=UNCLIP); pg.wait_for_timeout(600)
                        pg.screenshot(path=os.path.join(SNAP, f"{inst}_{tf}.png"), full_page=True)
                f, o = rec["full"]["boxes"], rec["oos2026"]["boxes"]
                # the fabrication guard: profit across zero trades is the bug we shipped once already
                for w, d in (("full", f), ("2026", o)):
                    if (d.get("n_taken") or 0) == 0 and abs(d.get("pnl") or 0) > 1:
                        raise ValueError(f"{w}: ${d['pnl']:,.0f} across 0 trades")
                # the bug's signature: if the window never applied, both windows return the same run
                if f["n_taken"] and (f["pnl"], f["n_taken"]) == (o["pnl"], o["n_taken"]):
                    raise ValueError("full and 2026 are IDENTICAL — the window never applied")
                cap = rec["full"]["params"].get("cap_mode")
                if cap not in ("eod", "both"):
                    raise ValueError(f"cap_mode={cap!r} — this slot does NOT close at the bell")
                print(f"[{n:2d}/54] {inst:3} {tf:3} {cap:4} full ${f['pnl']:>9,.0f} DD ${f['max_dd']:>7,.0f} "
                      f"n={f['n_taken']:>5} | 2026 ${o['pnl']:>8,.0f} n={o['n_taken']:>4}", flush=True)
            except Exception as e:
                rec["err"] = str(e)[:160]
                print(f"[{n:2d}/54] {inst:3} {tf:3}  ERROR {rec['err']}", flush=True)
            rows.append(rec)
            json.dump(rows, open(OUT, "w"), indent=1)
            json.dump(presets, open(PRESETS, "w"), indent=1)
            el = time.time() - t0
            print(f"PROGRESS {n}/54  elapsed {el/60:.1f}m  ETA {(el/n)*(54-n)/60:.1f}m", flush=True)
    b.close()
print("UIPASS_DONE", flush=True)
