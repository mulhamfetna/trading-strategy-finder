"""Add CL (Crude Oil) + NG (Natural Gas) to the shareable bundle: build champions/<INST>_<tf>.json from the
captured collectLayer presets + the UI-verified ON-SCREEN numbers (labels). Matches the format of the
existing 43 champions. On-screen is truth — weak/negative slots are labelled honestly, not hidden."""
import json, os

BASE = os.path.expanduser("~/Mulham/wsg-i")
CHDIR = os.path.join(BASE, "playbooks_backtester", "champions")

PV = {"CL": 1000.0, "NG": 10000.0}
NAME = {"CL": "Crude Oil (CL)", "NG": "Natural Gas (NG)"}

presets = json.load(open(os.path.join(BASE, "clng_presets_raw.json")))
verify = {(r["inst"], r["tf"]): r for r in json.load(open(os.path.join(BASE, "clng_verify.json")))}


def money(v):
    if v is None:
        return "n/a"
    return ("+" if v >= 0 else "-") + "$" + f"{abs(v):,.0f}"


added = []
for pr in presets:
    inst, tf, cl = pr["inst"], pr["tf"], pr["collect"]
    preset = dict(cl)
    preset.update(timeframe=tf, window="full", pv=PV[inst], dd_cap=5000.0,
                  retrace_amount=0, retrace_unit="atr_mult", wait_bars=0, gen={"swing_l": 2, "golf_n": 3})

    v = verify.get((inst, tf), {})
    bx = v.get("full", {}).get("boxes", {})
    oo = v.get("oos2026", {}).get("summary", {})
    full_pnl = bx.get("pnl", 0)
    dd = bx.get("max_dd", 0)
    win = bx.get("win", 0)
    oos = oo.get("pnl", 0)

    nind = sum(1 for s in cl["indicators"] if s.get("enabled"))
    cap = f"cap={int(cl['cap_1min'])}/{cl['cap_mode']}" if cl["cap_1min"] else "cap off"

    warn = ""
    if full_pnl <= 0 or oos <= 0:
        warn = "  ⚠️ DO NOT TRADE — "
        if full_pnl <= 0:
            warn += "loses money in-sample"
            if oos <= 0:
                warn += " AND out-of-sample"
        else:
            warn += "flat/negative out-of-sample (2026)"

    label = (f"{NAME[inst]} {tf} · box + {nind}-indicator gate · {cap} · 1-minute-frame indicators (ind_1min=true) — "
             f"{money(full_pnl)} full / ${dd:,.0f} DD / {win:.1f}% win · OOS-2026 {money(oos)}{warn}")

    champ = {"id": f"{inst}_{tf}", "instrument": inst, "timeframe": tf, "label": label, "preset": preset}
    json.dump(champ, open(os.path.join(CHDIR, f"{inst}_{tf}.json"), "w"), indent=1)
    added.append((f"{inst}_{tf}", full_pnl, oos))
    print(f"wrote champions/{inst}_{tf}.json  (full {money(full_pnl)} · OOS {money(oos)}){warn}", flush=True)

print(f"\nDONE: {len(added)} CL+NG champions added · total champions now {len(os.listdir(CHDIR))}", flush=True)
