"""Generate the 37 champion preset JSONs for the shareable bundle, from the captured collectLayer objects
(exact UI-sent params) merged with the per-instrument constants (pv, dd_cap, retrace, gen). Numbers for the
labels come from the same live-dashboard capture used for the playbooks. Writes champions/<name>.json + a
MANIFEST.json for the README."""
import json, os

BASE = os.path.expanduser("~/Mulham/wsg-i")
CHDIR = os.path.join(BASE, "playbooks_backtester", "champions")
os.makedirs(CHDIR, exist_ok=True)

PV = {"NQ": 20.0, "ES": 50.0, "GC": 100.0, "SI": 5000.0, "RTY": 50.0, "YM": 5.0}
FULLNAME = {"NQ": "Nasdaq-100", "ES": "S&P 500", "GC": "Gold", "SI": "Silver", "RTY": "Russell 2000", "YM": "Dow"}

presets = json.load(open(os.path.join(BASE, "presets_raw.json")))
metrics = {(r["inst"], r["tf"]): r for r in json.load(open(os.path.join(BASE, "playbook_metrics.json")))}
variant = json.load(open(os.path.join(BASE, "gc4h_ind4h.json")))[0]

def money(v):
    if v is None: return "n/a"
    return ("+" if v >= 0 else "-") + "$" + f"{abs(v):,.0f}"

manifest = []
for pr in presets:
    inst, tf, is_v = pr["inst"], pr["tf"], pr.get("ind4h", False)
    cl = pr["collect"]
    preset = dict(cl)
    preset.update(timeframe=tf, window="full", pv=PV[inst], dd_cap=5000.0,
                  retrace_amount=0, retrace_unit="atr_mult", wait_bars=0,
                  gen={"swing_l": 2, "golf_n": 3})
    # headline numbers (same basis as the playbooks): full = on-screen boxes; OOS = window-2026 (deployed) /
    # full-run 2026 attribution (the 4h-frame variant, matching the comparison report)
    if is_v:
        full_pnl = variant["full"]["boxes"]["pnl"]; dd = variant["full"]["boxes"]["max_dd"]
        win = variant["full"]["boxes"]["win"]; oos = variant["full"]["summary"]["pnl_2026"]
        name = f"{inst}_{tf}_ind4h"
        frame = "4h-decision-frame indicators (ind_1min=false)"
    else:
        mr = metrics[(inst, tf)]
        full_pnl = mr["full"]["boxes"]["pnl"]; dd = mr["full"]["boxes"]["max_dd"]
        win = mr["full"]["boxes"]["win"]; oos = mr["oos2026"]["summary"]["pnl"]
        name = f"{inst}_{tf}"
        frame = "1-minute-frame indicators (ind_1min=true)"
    nind = sum(1 for s in cl["indicators"] if s.get("enabled"))
    cap = f"cap={int(cl['cap_1min'])}{'/'+cl['cap_mode'] if cl['cap_1min'] else ' off'}"
    label = (f"{FULLNAME[inst]} ({inst}) {tf}{' · 4h-indicator variant' if is_v else ''} · "
             f"box + {nind}-indicator gate · {cap} · {frame} — "
             f"${full_pnl:,.0f} full / ${dd:,.0f} DD / {win:.1f}% win · OOS-2026 {money(oos)}")
    champ = {"id": name, "instrument": inst, "timeframe": tf, "label": label, "preset": preset}
    json.dump(champ, open(os.path.join(CHDIR, f"{name}.json"), "w"), indent=1)
    manifest.append({"name": name, "inst": inst, "tf": tf, "variant": is_v,
                     "full": round(full_pnl), "dd": round(dd), "win": round(win, 1),
                     "oos": round(oos) if oos is not None else None, "n_ind": nind,
                     "cap_1min": int(cl["cap_1min"]), "flip": cl["flip"], "k": cl["k"], "label": label})

json.dump(manifest, open(os.path.join(BASE, "playbooks_backtester", "MANIFEST.json"), "w"), indent=1)
print(f"wrote {len(manifest)} champions -> {CHDIR}")
dep = sum(1 for m in manifest if not m["variant"])
print(f"  {dep} deployed + {len(manifest)-dep} variant")
