"""Assemble playbook_metrics_eod1.json — the PDF builder's input — from MEASURED numbers only.

Sources, both real:
    eod1_verified.json     causal engine, window-aware, BOTH windows (build_view_payload)
    presets_raw_eod1.json  collectLayer('l1') straight off the dashboard — the exact settings to load

Shape the builder wants: [{inst, tf, full:{boxes,summary,params,split_ts}, oos2026:{...}}]
It reads .boxes for the headline and .summary for the tearsheet; we put the SAME measured dict in both, so
the PDF cannot print one number in the headline and a different one in the table.

THE GUARD. The last playbook build shipped FABRICATED metrics — the OOS trade count was hardcoded to 0 and
pf/payoff/avg_win/avg_loss/exposure were invented, so PDFs literally read "still profitable (+$37,286)
across 0 trades". Nothing here is allowed to be a placeholder: a slot that claims profit with no trades, or
whose numbers are missing, ABORTS the build rather than printing a plausible lie.
"""
import json
import os

BASE = os.path.expanduser("~/Mulham/wsg-i")
ver = json.load(open(f"{BASE}/eod1_verified.json"))
pres = {(p["inst"], p["tf"]): p["collect"] for p in json.load(open(f"{BASE}/presets_raw_eod1.json"))}

out, bad = [], []
for r in ver:
    k = (r["inst"], r["tf"])
    if r.get("err") or not r.get("eod1"):
        bad.append(f"{k[0]}_{k[1]}: measurement failed ({r.get('err')})")
        continue
    if k not in pres:
        bad.append(f"{k[0]}_{k[1]}: no captured preset — cannot tell the reader what to load")
        continue
    m = r["eod1"]
    for w in ("full", "oos2026"):
        d = m.get(w) or {}
        if not d or d.get("pnl") is None:
            bad.append(f"{k[0]}_{k[1]} {w}: no measurement")
        elif (d.get("n_taken") or 0) == 0 and abs(d.get("pnl") or 0) > 1:
            bad.append(f"{k[0]}_{k[1]} {w}: ${d['pnl']:,.0f} across 0 trades — fabricated")
    cap = (pres[k].get("cap_mode") or "none")
    if cap not in ("eod", "both"):
        bad.append(f"{k[0]}_{k[1]}: cap_mode={cap!r} — does not close at the bell")
    out.append({
        "inst": r["inst"], "tf": r["tf"],
        "full": {"boxes": m["full"], "summary": m["full"], "params": pres[k], "split_ts": None},
        "oos2026": {"boxes": m["oos2026"], "summary": m["oos2026"], "params": pres[k], "split_ts": None},
    })

if bad or len(out) != 54:
    print(f"REFUSING TO BUILD — {len(bad)} problem(s), {len(out)}/54 slots usable:")
    for b in bad[:20]:
        print("   ", b)
    raise SystemExit(1)

json.dump(out, open(f"{BASE}/playbook_metrics_eod1.json", "w"), indent=1)
print(f"playbook_metrics_eod1.json — {len(out)} champions, every number measured, none fabricated")
print()
print(f"{'slot':9} {'full P/L':>10} {'DD':>9} {'trades':>7} | {'2026 P/L':>9} {'trades':>7}  exit")
print("-" * 68)
for o in out:
    f, s = o["full"]["boxes"], o["oos2026"]["boxes"]
    print(f"{o['inst'] + '_' + o['tf']:9} {f['pnl']:>10,.0f} {f['max_dd']:>9,.0f} {f['n_taken']:>7} | "
          f"{s['pnl']:>9,.0f} {s['n_taken']:>7}  {o['full']['params']['cap_mode']}")
