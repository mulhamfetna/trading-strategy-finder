"""Rebuild the DEPLOYED (best-per-slot) champion set from the PRECISION-CORRECTED head-to-head.

    29 slots  keep the deployed champion (cap1p) — no challenger cleared the 10% margin on 2026
    24 slots  take the forced-end-of-day champion (eod1p)
     1 slot   takes the bolt-on: the deployed champion with the bell close switched on, not re-tuned

Sources are the *p* files — re-extracted with significant-digit precision. The previous best set was built
from champions whose stops had been rounded to 4 decimals, which got 10 of the 54 verdicts wrong.

The bolt-on is synthesised from the deployed champion's VALIDATED cap, never its raw box value: a champion
with cap_mode absent but a non-zero cap_1min really runs as "bars" (that is how every pre-2026-07-11
champion encodes a bar cap). Reading the raw field once deployed ES 1h without its 696-bar cap.
"""
import json
import os
import shutil

BASE = os.path.expanduser("~/Mulham/wsg-i")
RES = f"{BASE}/Parametric-Indicators/optimize/results"
BAK = f"{BASE}/champions_backup_pre_precise"
os.makedirs(BAK, exist_ok=True)

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
FORCE = {"none": "eod", "bars": "both", "eod": "eod", "both": "both"}

dec = {(r["inst"], r["tf"]): r["winner"] for r in json.load(open(f"{BASE}/precise_decision.json"))}

changed, kept = [], []
for inst in INSTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    for old in (f"{RES}/best_champions_full{suf}.json", f"{RES}/wsh4_champions_full{suf}.json"):
        if os.path.exists(old):
            shutil.copy(old, f"{BAK}/{os.path.basename(old)}")

    dep = json.load(open(f"{RES}/cap1p_champions_full{suf}.json"))
    new = json.load(open(f"{RES}/eod1p_champions_full{suf}.json"))

    out = {}
    for tf in TFS:
        w = dec[(inst, tf)]
        slot = f"{inst}_{tf}"
        if w == "eod1":
            out[tf] = new[tf]
            changed.append((slot, "eod1"))
        elif w == "bolt-on":
            e = json.loads(json.dumps(dep[tf]))
            cm = str(e["box"].get("cap_mode") or "none")
            if cm == "none" and int(e["box"].get("cap_1min") or 0) > 0:
                cm = "bars"                        # the VALIDATED mode, as the engine resolves it
            e["box"]["cap_mode"] = FORCE[cm]
            e["box"].setdefault("eod_margin_min", 15)
            out[tf] = e
            changed.append((slot, f"bolt-on ({cm}->{FORCE[cm]})"))
        else:
            out[tf] = dep[tf]
            kept.append(slot)
    json.dump(out, open(f"{RES}/best_champions_full{suf}.json", "w"), indent=1)

print(f"backed up the previous set -> {BAK}")
print(f"wrote 9 files  ({len(kept)} kept · {len(changed)} changed)")
print()
print("CHANGED SLOTS:")
for slot, how in changed:
    print(f"   {slot:9} <- {how}")

# prove the precision actually made it into the deployed files
ng = json.load(open(f"{RES}/best_champions_full_NG.json"))
print()
print(f"precision check — NG 5m sl_soft as DEPLOYED: {ng['5m']['box']['sl_soft']!r}")
assert len(repr(ng["5m"]["box"]["sl_soft"])) > 8, "still rounded!"
