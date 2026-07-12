"""Deploy the FINAL champion set: per slot, whichever champion won on CORRECTED 2026 out-of-sample.

Sources:
  incumbents  -> deployed_champions_backup/  (restored from git ff79770 — caps intact)
  challengers -> cap1_champions/
  decisions   -> honest_verdict.json (36 new / 16 old / 2 rejected)
"""
import json
import os
from pathlib import Path

WSI = Path(os.path.expanduser("~/Mulham/wsg-i"))
RES = WSI / "Parametric-Indicators" / "optimize" / "results"
BAK = WSI / "deployed_champions_backup"
CAP = WSI / "cap1_champions"

v = json.load(open(WSI / "honest_verdict.json"))
new_wins = set(v["new_wins"])

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]

n_new = n_old = 0
for inst in INSTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    incumbent = json.loads((BAK / f"wsh4_champions_full{suf}.json").read_text())
    challenger = json.loads((CAP / f"cap1_champions_{inst}.json").read_text())

    merged = dict(incumbent)
    picks = []
    for tf in TFS:
        slot = f"{inst}_{tf}"
        if slot in new_wins and tf in challenger:
            merged[tf] = challenger[tf]
            picks.append(f"{tf}:NEW")
            n_new += 1
        else:
            picks.append(f"{tf}:old")
            n_old += 1

    (RES / f"wsh4_champions_full{suf}.json").write_text(json.dumps(merged, indent=1))

    caps = {tf: (merged[tf]["box"].get("cap_mode"), merged[tf]["box"].get("cap_1min"))
            for tf in TFS if tf in merged}
    print(f"{inst:4} {' '.join(picks)}")
    print(f"      caps: {caps}", flush=True)

print(f"\nDEPLOYED: {n_new} new · {n_old} old")

# sanity: no capped champion may have lost its cap
bad = []
for inst in INSTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    d = json.loads((RES / f"wsh4_champions_full{suf}.json").read_text())
    for tf, e in d.items():
        b = e["box"]
        if b.get("cap_mode") in ("bars", "both") and not int(b.get("cap_1min") or 0):
            bad.append(f"{inst}_{tf} (mode={b.get('cap_mode')} but cap_1min=0)")
print("cap sanity:", "OK" if not bad else f"BROKEN -> {bad}")
print("FINALSET_DONE")
