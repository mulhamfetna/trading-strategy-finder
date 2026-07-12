"""The honest head-to-head: re-decide every slot on CORRECTED out-of-sample numbers.

Both sides recomputed on the fixed engine (build_payload now honors the time caps, so the 2026 window is
no longer measured with the cap switched off). Decision rule, unchanged:

  1. A champion that loses money in-sample OR out-of-sample is rejected.
  2. Otherwise the higher 2026 out-of-sample wins.
  3. Within 5% => the lower drawdown wins.
"""
import json
import os
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.expanduser("~/.claude/jobs/b835c01f/tmp/honest_compare.json")
rows = [r for r in json.load(open(SRC)) if r.get("old") and r.get("new")]

INST_ORDER = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TF_ORDER = {t: i for i, t in enumerate(["4h", "2h", "1h", "15m", "5m", "2m"])}
rows.sort(key=lambda r: (INST_ORDER.index(r["inst"]), TF_ORDER[r["tf"]]))

CAPL = {"none": "none", "bars": "bars", "eod": "eod", "both": "both"}


def m(v):
    return ("+" if v >= 0 else "−") + "$" + f"{abs(v):,.0f}"


new_wins, old_holds, rejects = [], [], []
print(f"{'slot':9} | {'OLD (corrected)':>24} | {'NEW (corrected)':>24} | cap    | verdict")
print(f"{'':9} | {'full':>11} {'2026':>11} | {'full':>11} {'2026':>11} |        |")
print("-" * 96)
cur = None
for r in rows:
    o, n = r["old"], r["new"]
    slot = f"{r['inst']}_{r['tf']}"
    if cur and cur != r["inst"]:
        print("-" * 96)
    cur = r["inst"]

    if n["pnl"] <= 0 or n["oos"] <= 0:
        v, pick = "❌ REJECT new", "old"
        rejects.append(slot)
    elif n["oos"] > o["oos"] * 1.05:
        v, pick = "✅ NEW", "new"
        new_wins.append(slot)
    elif o["oos"] > n["oos"] * 1.05:
        v, pick = "old holds", "old"
        old_holds.append(slot)
    else:
        pick = "new" if n["dd"] < o["dd"] else "old"
        v = f"tie → {pick} (lower DD)"
        (new_wins if pick == "new" else old_holds).append(slot)

    cap = CAPL.get(n["cap_mode"], "?")
    if n["cap_mode"] in ("bars", "both") and n["cap_1min"]:
        cap += f"/{n['cap_1min']}"
    print(f"{slot:9} | {m(o['pnl']):>11} {m(o['oos']):>11} | {m(n['pnl']):>11} {m(n['oos']):>11} "
          f"| {cap:6} | {v}")

dep = sum(r["old"]["oos"] for r in rows)
fin = 0.0
for r in rows:
    o, n = r["old"], r["new"]
    slot = f"{r['inst']}_{r['tf']}"
    fin += n["oos"] if slot in new_wins else o["oos"]

print("\n" + "=" * 96)
print(f"NEW adopted : {len(new_wins):2d}")
print(f"OLD held    : {len(old_holds):2d}")
print(f"NEW rejected: {len(rejects):2d}   {rejects}")
print(f"\n2026 OOS (CORRECTED):  deployed {m(dep)}  →  best-of-both {m(fin)}   "
      f"gain {m(fin - dep)} ({100 * (fin - dep) / abs(dep):.0f}%)")

json.dump({"new_wins": new_wins, "old_holds": old_holds, "rejects": rejects,
           "oos_deployed": dep, "oos_final": fin},
          open(os.path.expanduser("~/.claude/jobs/b835c01f/tmp/honest_verdict.json"), "w"), indent=1)
