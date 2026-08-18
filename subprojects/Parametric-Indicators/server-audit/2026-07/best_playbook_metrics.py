"""Assemble the DEPLOYED (best-per-slot) set's playbook metrics — from the PRECISION-CORRECTED numbers.

⚠️ Reads precise_metrics.json / precise_decision.json ONLY.

The earlier files (honest_metrics.json, eod_forced.json, eod1_verified.json) were all measured on champions
whose stops had been rounded to four decimal places. That is a 1-2% distortion in the four lowest-priced
markets — it flipped NG 5m from +$38,079 to -$1,714 — and it got 10 of the 54 head-to-head verdicts wrong.
Using them here would silently reintroduce the whole bug into the shipped bundle.

Each slot takes the numbers of whichever candidate WON it (29 incumbent · 24 forced-EOD · 1 bolt-on).
Presets come from the live dashboard with the `best` set selected, so what a reader is told to load is
exactly what the dashboard serves.
"""
import json
import os
from collections import Counter

BASE = os.path.expanduser("~/Mulham/wsg-i")

met = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/precise_metrics.json")) if not r.get("err")}
dec = json.load(open(f"{BASE}/precise_decision.json"))
pres = {(p["inst"], p["tf"]): p["collect"] for p in json.load(open(f"{BASE}/presets_raw_best.json"))}

out, bad = [], []
for d in dec:
    k, w = (d["inst"], d["tf"]), d["winner"]
    m = met.get(k)
    if not m:
        bad.append(f"{k[0]}_{k[1]}: no measurement")
        continue
    if k not in pres:
        bad.append(f"{k[0]}_{k[1]}: no captured preset — cannot tell the reader what to load")
        continue
    if w not in m:
        bad.append(f"{k[0]}_{k[1]}: winner {w!r} has no measurement")
        continue

    full, oos = m[w]["full"], m[w]["oos2026"]
    for win, x in (("full", full), ("2026", oos)):
        if x.get("pnl") is None:
            bad.append(f"{k[0]}_{k[1]} {win}: no measurement")
        elif (x.get("n_taken") or 0) == 0 and abs(x.get("pnl") or 0) > 1:
            bad.append(f"{k[0]}_{k[1]} {win}: ${x['pnl']:,.0f} across 0 trades — fabricated")

    out.append({"inst": d["inst"], "tf": d["tf"], "source": w,
                "full": {"boxes": full, "summary": full, "params": pres[k], "split_ts": None},
                "oos2026": {"boxes": oos, "summary": oos, "params": pres[k], "split_ts": None}})

if bad or len(out) != 54:
    print(f"REFUSING TO BUILD — {len(bad)} problem(s), {len(out)}/54 usable:")
    for b in bad[:20]:
        print("   ", b)
    raise SystemExit(1)

json.dump(out, open(f"{BASE}/playbook_metrics_best.json", "w"), indent=1)
c = Counter(o["source"] for o in out)
print(f"playbook_metrics_best.json — 54 champions "
      f"(incumbent {c['deployed']} · forced-EOD {c['eod1']} · bolt-on {c['bolt-on']})")

# prove the corrected numbers really are the ones going into the PDFs
ng = next(o for o in out if (o["inst"], o["tf"]) == ("NG", "5m"))
print(f"  NG 5m (the slot the rounding flipped): full ${ng['full']['boxes']['pnl']:,.0f} · "
      f"2026 ${ng['oos2026']['boxes']['pnl']:,.0f}")
assert ng["full"]["boxes"]["pnl"] > 0, "NG 5m is still negative — the corrupted numbers leaked back in"
