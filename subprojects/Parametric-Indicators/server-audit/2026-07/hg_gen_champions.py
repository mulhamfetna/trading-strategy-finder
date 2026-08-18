"""Add HG (Copper) to the shareable bundle: build champions/HG_<tf>.json from the captured collectLayer
presets + the UI-verified numbers (labels). Matches the format of the existing 37 champions."""
import json, os

BASE = os.path.expanduser("~/Mulham/wsg-i")
CHDIR = os.path.join(BASE, "playbooks_backtester", "champions")
presets = json.load(open(os.path.join(BASE, "hg_presets_raw.json")))
verify = {r["tf"]: r for r in json.load(open(os.path.join(BASE, "hg_verify.json")))}  # on-screen numbers

def money(v):
    if v is None: return "n/a"
    return ("+" if v >= 0 else "-") + "$" + f"{abs(v):,.0f}"

added = []
for pr in presets:
    tf, cl = pr["tf"], pr["collect"]
    preset = dict(cl)
    preset.update(timeframe=tf, window="full", pv=25000.0, dd_cap=5000.0,
                  retrace_amount=0, retrace_unit="atr_mult", wait_bars=0, gen={"swing_l": 2, "golf_n": 3})
    v = verify.get(tf, {})
    bx = v.get("full", {}).get("boxes", {}); oo = v.get("oos2026", {}).get("summary", {})
    full_pnl = bx.get("pnl", 0); dd = bx.get("max_dd", 0); win = bx.get("win", 0); oos = oo.get("pnl", 0)
    nind = sum(1 for s in cl["indicators"] if s.get("enabled"))
    cap = f"cap={int(cl['cap_1min'])}/{cl['cap_mode']}" if cl["cap_1min"] else "cap off"
    label = (f"Copper (HG) {tf} · box + {nind}-indicator gate · {cap} · 1-minute-frame indicators (ind_1min=true) — "
             f"${full_pnl:,.0f} full / ${dd:,.0f} DD / {win:.1f}% win · OOS-2026 {money(oos)}")
    champ = {"id": f"HG_{tf}", "instrument": "HG", "timeframe": tf, "label": label, "preset": preset}
    json.dump(champ, open(os.path.join(CHDIR, f"HG_{tf}.json"), "w"), indent=1)
    added.append((f"HG_{tf}", full_pnl, oos))
    print(f"wrote champions/HG_{tf}.json  (full ${full_pnl:,.0f} · OOS {money(oos)})", flush=True)
print(f"\nDONE: {len(added)} HG champions added · total champions now {len(os.listdir(CHDIR))}", flush=True)
