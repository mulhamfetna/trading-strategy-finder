"""Head-to-head: the 54 NEW cap1 champions vs the DEPLOYED (already-verified) ones.

Both sides are UI-verified on-screen numbers, so this is apples-to-apples:
  • new       -> cap_verify.json          (this campaign, verified through the dashboard today)
  • deployed  -> MANIFEST.json            (the shipped 55-champion bundle, UI-verified previously)

DECISION RULE — 2026 out-of-sample wins, not in-sample profit.
The whole point of the held-out year is that in-sample gains can be overfitting. We already saw it:
ES 2h earns MORE in-sample ($104k vs $76k) and LESS out-of-sample ($12.7k vs $19.6k). So:

  1. A champion that LOSES money in-sample or out-of-sample is rejected outright.
  2. Otherwise the winner is the one with the higher 2026 OOS.
  3. Ties (within 5%) go to the LOWER drawdown.
"""
import json
import os
import sys
from pathlib import Path

NEW = json.load(open(os.path.expanduser("~/.claude/jobs/b835c01f/tmp/cap_verify.json")
                     if len(sys.argv) < 2 else sys.argv[1]))
MAN = json.load(open(sys.argv[2] if len(sys.argv) > 2 else
                     "/mnt/data/projects/trading/subprojects/Parametric-Indicators/"
                     "shareable/playbooks_backtester/MANIFEST.json"))

dep = {(m["inst"], m["tf"]): m for m in MAN if not m["variant"]}

TF_ORDER = {t: i for i, t in enumerate(["4h", "2h", "1h", "15m", "5m", "2m"])}
INST_ORDER = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]


def money(v):
    if v is None:
        return "n/a"
    return ("+" if v >= 0 else "−") + "$" + f"{abs(v):,.0f}"


rows, keep_new, keep_old, rejected = [], [], [], []

for r in NEW:
    if "full" not in r:
        continue
    inst, tf = r["inst"], r["tf"]
    bx = r["full"]["boxes"]
    oo = r["oos2026"]["summary"]
    n_pnl, n_dd, n_oos = bx.get("pnl", 0), bx.get("max_dd", 0), oo.get("pnl", 0)

    d = dep.get((inst, tf))
    o_pnl = d["full"] if d else None
    o_dd = d["dd"] if d else None
    o_oos = d["oos"] if d else None

    # 1. reject outright if the NEW one is not profitable both in- and out-of-sample
    if n_pnl <= 0 or n_oos <= 0:
        verdict = "REJECT new"
        rejected.append(f"{inst}_{tf}")
        winner = "old"
    elif o_oos is None:
        verdict = "NEW (no incumbent)"
        winner = "new"
    elif n_oos > o_oos * 1.05:
        verdict = "NEW wins"
        winner = "new"
    elif o_oos > n_oos * 1.05:
        verdict = "OLD wins"
        winner = "old"
    else:                                   # within 5% => lower drawdown wins
        winner = "new" if n_dd < (o_dd or 1e18) else "old"
        verdict = f"tie → {winner} (lower DD)"

    (keep_new if winner == "new" else keep_old).append(f"{inst}_{tf}")
    rows.append((inst, tf, o_pnl, o_dd, o_oos, n_pnl, n_dd, n_oos, verdict))

rows.sort(key=lambda r: (INST_ORDER.index(r[0]), TF_ORDER[r[1]]))

print(f"{'slot':9} | {'DEPLOYED (verified)':>34} | {'NEW cap1 (verified)':>34} | verdict")
print(f"{'':9} | {'full':>11} {'DD':>9} {'2026':>11} | {'full':>11} {'DD':>9} {'2026':>11} |")
print("-" * 105)
cur = None
for inst, tf, op, od, oo_, np_, nd, no, v in rows:
    if cur and cur != inst:
        print("-" * 105)
    cur = inst
    print(f"{inst+'_'+tf:9} | {money(op):>11} {('$'+format(od,',')) if od is not None else 'n/a':>9} "
          f"{money(oo_):>11} | {money(np_):>11} {'$'+format(int(nd),','):>9} {money(no):>11} | {v}")

print("\n" + "=" * 105)
print(f"NEW champion wins : {len(keep_new):2d}  {sorted(keep_new)}")
print(f"OLD champion held : {len(keep_old):2d}  {sorted(keep_old)}")
print(f"NEW rejected      : {len(rejected):2d}  {sorted(rejected)}")

tot_old_oos = sum(d["oos"] or 0 for d in dep.values())
best_oos = 0
for inst, tf, op, od, oo_, np_, nd, no, v in rows:
    best_oos += max(no if no > 0 else 0, oo_ or 0)
print(f"\n2026 OOS across the suite:  deployed {money(tot_old_oos)}  →  best-of-both {money(best_oos)}")
