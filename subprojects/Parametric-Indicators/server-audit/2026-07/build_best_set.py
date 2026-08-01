"""Build the BEST-PER-SLOT champion set from the three-way head-to-head, and install it as a new set.

    32 slots  keep the DEPLOYED champion   (the challengers did not clear the 10% margin on 2026)
    19 slots  take the eod1 champion       (cold-start, re-tuned with the bell close forced)
     3 slots  take the BOLT-ON             (deployed champion, bell close switched on, nothing re-tuned)

Written as a NEW set (best_champions_full*.json) rather than overwriting wsh4 in place: the deployed set
stays intact and selectable in the dashboard, so this deploy is reversible by changing one dropdown.

The bolt-on entries are SYNTHESISED here — deployed box + the bell close armed — using the same mapping the
measurement used, so what ships is exactly what was measured:
    none -> eod        (no cap at all      -> close at the bell)
    bars -> both       (keep the bar cap   -> AND close at the bell, whichever fires first)
"""
import json
import os
import shutil

BASE = os.path.expanduser("~/Mulham/wsg-i")
RES = f"{BASE}/Parametric-Indicators/optimize/results"
BAK = f"{BASE}/champions_backup_pre_best"
os.makedirs(BAK, exist_ok=True)

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
FORCE = {"none": "eod", "bars": "both", "eod": "eod", "both": "both"}

dec = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/eod1_decision.json"))}

changed, kept = [], []
for inst in INSTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    dep_p, new_p = f"{RES}/wsh4_champions_full{suf}.json", f"{RES}/eod1_champions_full{suf}.json"
    shutil.copy(dep_p, f"{BAK}/wsh4_champions_full{suf}.json")           # never destroy the verified set
    dep, new = json.loads(open(dep_p).read()), json.loads(open(new_p).read())

    out = {}
    for tf in TFS:
        w = dec[(inst, tf)]["winner"]
        slot = f"{inst}_{tf}"
        if w == "eod1":
            out[tf] = new[tf]
            changed.append((slot, "eod1"))
        elif w == "bolt-on":
            e = json.loads(json.dumps(dep[tf]))                          # deep copy — do not mutate the source
            # ⚠️ USE THE *VALIDATED* CAP, NEVER THE RAW BOX VALUE. validate_params carries a back-compat
            # rule — a champion with cap_mode "none"/absent but a non-zero cap_1min really runs as "bars"
            # (that is how every pre-2026-07-11 champion encodes a bar cap). ES 1h is exactly that: its box
            # says None/696 but the engine runs it as bars/696. Reading the raw value mapped it none->eod
            # and SILENTLY DROPPED the 696-bar cap, deploying a strategy that was never measured — the UI
            # verification caught it at $58,440 against a recorded $60,595.
            cm = str(e["box"].get("cap_mode") or "none")
            if cm == "none" and int(e["box"].get("cap_1min") or 0) > 0:
                cm = "bars"
            e["box"]["cap_mode"] = FORCE[cm]
            e["box"].setdefault("eod_margin_min", 15)
            out[tf] = e
            changed.append((slot, f"bolt-on ({cm}->{FORCE[cm]})"))
        else:
            out[tf] = dep[tf]
            kept.append(slot)
    json.dump(out, open(f"{RES}/best_champions_full{suf}.json", "w"), indent=1)

print(f"backed up the deployed set -> {BAK}")
print(f"wrote 9 files: best_champions_full*.json   ({len(kept)} kept, {len(changed)} changed)")
print()
print("CHANGED SLOTS:")
for slot, how in changed:
    print(f"   {slot:9} <- {how}")
