"""Build the shareable champion set for the FORCED END-OF-DAY bundle.

preset  <- presets_raw_eod1.json      exactly what the dashboard sends (collectLayer('l1'))
numbers <- eod1_verified.json         the causal engine, both windows — NOT the optimizer's claims

Every slot ships, including the bad ones, FLAGGED. The standalone backtester reproduces their bad numbers
too, and that is the point: a champion set you can only trust when it flatters you is not a champion set.
"""
import json
import os
import shutil

BASE = os.path.expanduser("~/Mulham/wsg-i")
SRC = os.path.join(BASE, "playbooks_backtester")            # the proven scaffold (code, loader, data)
DST = os.path.join(BASE, "playbooks_backtester_best")
CHDIR = os.path.join(DST, "champions")

# ⚠️ point values. The shim once carried only 6 markets behind a .get(inst, 20.0) default, so copper, oil
# and gas were all priced as the NASDAQ — Copper 15m reported $33 instead of $41,588, a 1,250x error.
# Raise on anything unknown; never default.
PV = {"NQ": 20.0, "ES": 50.0, "GC": 100.0, "SI": 5000.0, "HG": 25000.0,
      "CL": 1000.0, "NG": 10000.0, "RTY": 50.0, "YM": 5.0}
NAME = {"NQ": "Nasdaq-100 (NQ)", "ES": "S&P 500 (ES)", "GC": "Gold (GC)", "SI": "Silver (SI)",
        "HG": "Copper (HG)", "CL": "Crude Oil (CL)", "NG": "Natural Gas (NG)",
        "RTY": "Russell 2000 (RTY)", "YM": "Dow (YM)"}
CAP_TXT = {"none": "no time cap", "bars": "max-hold {n} bars",
           "eod": "end-of-day exit (never holds overnight)",
           "both": "max-hold {n} bars OR end-of-day — whichever fires first"}

SRC_TXT = {"deployed": "incumbent (held — no challenger beat it out-of-sample)",
           "eod1": "cold-start re-optimization with the end-of-day close FORCED",
           "bolt-on": "incumbent + end-of-day close switched on (not re-tuned)"}

presets = json.load(open(f"{BASE}/presets_raw_best.json"))
met = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/playbook_metrics_best.json"))}

if os.path.isdir(DST):
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
shutil.rmtree(CHDIR, ignore_errors=True)
os.makedirs(CHDIR, exist_ok=True)


def money(v):
    return "n/a" if v is None else ("+" if v >= 0 else "-") + "$" + f"{abs(v):,.0f}"


added, weak = [], []
for pr in presets:
    inst, tf, cl = pr["inst"], pr["tf"], pr["collect"]
    slot = f"{inst}_{tf}"
    if inst not in PV:
        raise SystemExit(f"{slot}: no point value for {inst!r} — refusing to guess (this shipped a 1,250x bug once)")
    m = met.get((inst, tf))
    if not m:
        raise SystemExit(f"{slot}: no causal measurement — refusing to ship an unmeasured champion")

    f, o = m["full"]["boxes"], m["oos2026"]["boxes"]
    src = m["source"]
    pnl, dd, win, oos = f["pnl"], f["max_dd"], f["win"], o["pnl"]
    if (f.get("n_taken") or 0) == 0 and abs(pnl) > 1:
        raise SystemExit(f"{slot}: ${pnl:,.0f} across 0 trades — that is the fabrication bug, not a champion")

    cm = cl.get("cap_mode", "none")
    if cm not in CAP_TXT:
        raise SystemExit(f"{slot}: unknown cap_mode={cm!r}")

    preset = dict(cl)
    preset.update(timeframe=tf, window="full", pv=PV[inst], dd_cap=5000.0,
                  retrace_amount=0, retrace_unit="atr_mult", wait_bars=0,
                  gen={"swing_l": 2, "golf_n": 3})

    cap = CAP_TXT[cm].format(n=int(cl.get("cap_1min") or 0))
    nind = sum(1 for s in cl["indicators"] if s.get("enabled"))

    warn = ""
    if pnl <= 0 or oos <= 0:
        warn = "  ** DO NOT TRADE — "
        warn += "loses money in-sample" if pnl <= 0 else "negative out-of-sample"
        if pnl <= 0 and oos <= 0:
            warn = "  ** DO NOT TRADE — loses money in-sample AND out-of-sample"
        weak.append(slot)

    label = (f"{NAME[inst]} {tf} · box + {nind}-indicator gate · {cap} · 1-minute-frame indicators — "
             f"{money(pnl)} full / ${dd:,.0f} DD / {win:.1f}% win · OOS-2026 {money(oos)} · "
             f"{SRC_TXT[src]}{warn}")

    json.dump({"id": slot, "instrument": inst, "timeframe": tf, "label": label, "preset": preset},
              open(os.path.join(CHDIR, f"{slot}.json"), "w"), indent=1)
    added.append(slot)

print(f"wrote {len(added)} champion files -> {CHDIR}")
if weak:
    print(f"FLAGGED as DO-NOT-TRADE ({len(weak)}): {', '.join(weak)}")
else:
    print("no slot is negative in-sample or out-of-sample")
