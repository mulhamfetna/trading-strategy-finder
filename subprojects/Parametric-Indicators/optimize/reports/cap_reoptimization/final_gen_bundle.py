"""Rebuild the shareable bundle's champion set from the DEPLOYED champions + CORRECTED numbers.

preset  <- final_presets_raw.json   (exactly what the dashboard sends: collectLayer('l1'))
numbers <- honest_compare.json      (both sides recomputed on the fixed engine — caps honored)

Weak/negative slots ship FLAGGED, not hidden: the engine reproduces their bad numbers exactly, and that
is the point.
"""
import json
import os

BASE = os.path.expanduser("~/Mulham/wsg-i")
CHDIR = os.path.join(BASE, "playbooks_backtester", "champions")
os.makedirs(CHDIR, exist_ok=True)

PV = {"NQ": 20.0, "ES": 50.0, "GC": 100.0, "SI": 5000.0, "HG": 25000.0,
      "CL": 1000.0, "NG": 10000.0, "RTY": 50.0, "YM": 5.0}
NAME = {"NQ": "Nasdaq-100 (NQ)", "ES": "S&P 500 (ES)", "GC": "Gold (GC)", "SI": "Silver (SI)",
        "HG": "Copper (HG)", "CL": "Crude Oil (CL)", "NG": "Natural Gas (NG)",
        "RTY": "Russell 2000 (RTY)", "YM": "Dow (YM)"}
CAP_TXT = {"none": "no time cap", "bars": "max-hold {n} bars", "eod": "end-of-day exit",
           "both": "max-hold {n} bars OR end-of-day — whichever first"}

presets = json.load(open(f"{BASE}/final_presets_raw.json"))
verdict = json.load(open(f"{BASE}/honest_verdict.json"))
new_wins = set(verdict["new_wins"])
cmp_rows = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/honest_compare.json"))
            if r.get("old") and r.get("new")}


def money(v):
    if v is None:
        return "n/a"
    return ("+" if v >= 0 else "-") + "$" + f"{abs(v):,.0f}"


added, weak = [], []
for pr in presets:
    inst, tf, cl = pr["inst"], pr["tf"], pr["collect"]
    slot = f"{inst}_{tf}"

    preset = dict(cl)
    preset.update(timeframe=tf, window="full", pv=PV[inst], dd_cap=5000.0,
                  retrace_amount=0, retrace_unit="atr_mult", wait_bars=0,
                  gen={"swing_l": 2, "golf_n": 3})

    row = cmp_rows.get((inst, tf))
    side = "new" if slot in new_wins else "old"
    m = (row or {}).get(side, {})
    pnl, dd, win, oos = m.get("pnl", 0), m.get("dd", 0), m.get("win", 0), m.get("oos", 0)

    cm = cl.get("cap_mode", "none")
    cap = CAP_TXT[cm].format(n=int(cl.get("cap_1min") or 0))
    nind = sum(1 for s in cl["indicators"] if s.get("enabled"))
    src = "cold-start re-optimization (time-cap model)" if side == "new" else "incumbent (held — beat the challenger out-of-sample)"

    warn = ""
    if pnl <= 0 or oos <= 0:
        warn = "  ** DO NOT TRADE — "
        warn += "loses money in-sample" if pnl <= 0 else "negative out-of-sample"
        if pnl <= 0 and oos <= 0:
            warn += " AND out-of-sample"
        weak.append(slot)

    label = (f"{NAME[inst]} {tf} · box + {nind}-indicator gate · {cap} · 1-minute-frame indicators — "
             f"{money(pnl)} full / ${dd:,.0f} DD / {win:.1f}% win · OOS-2026 {money(oos)} · {src}{warn}")

    json.dump({"id": slot, "instrument": inst, "timeframe": tf, "label": label, "preset": preset},
              open(os.path.join(CHDIR, f"{slot}.json"), "w"), indent=1)
    added.append(slot)
    print(f"  {slot:9} {cm:5} {money(pnl):>10} / OOS {money(oos):>9}  [{side}]{warn}", flush=True)

print(f"\nDONE: {len(added)} champions written · {len(weak)} flagged weak: {weak}")
print(f"total in champions/: {len(os.listdir(CHDIR))}")
print("GENBUNDLE_DONE")
