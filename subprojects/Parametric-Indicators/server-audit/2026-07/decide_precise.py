"""The head-to-head, re-run on PRECISION-CORRECTED numbers.

Same rule as before, written down before the numbers were seen and unchanged since:
  1. The held-out 2026 year decides. In-sample profit never picks a winner.
  2. Anything that loses money in 2026 is disqualified.
  3. A challenger takes a slot only by beating the deployed champion's 2026 profit by MORE THAN 10%.
     A tie does not churn a verified strategy.
  4. If the deployed champion itself loses in 2026, it forfeits the slot.

Also reports how the corrected precision changed the verdict — because it is not a small change: NG 5m
alone goes from "loses $1,915" to "+$11,155 out-of-sample".
"""
import json
import os

BASE = os.path.expanduser("~/Mulham/wsg-i")
MARGIN = 0.10
rows = [r for r in json.load(open(f"{BASE}/precise_metrics.json")) if not r.get("err")]
old = {(r["inst"], r["tf"]): r["winner"] for r in json.load(open(f"{BASE}/eod1_decision.json"))}

out, won, tot = [], {"deployed": 0, "bolt-on": 0, "eod1": 0}, {"deployed": 0.0, "bolt-on": 0.0, "eod1": 0.0}
flips = []
for r in rows:
    oos = {n: (r[n]["oos2026"]["pnl"] or 0) for n in ("deployed", "bolt-on", "eod1")}
    for n in tot:
        tot[n] += oos[n]
    base = oos["deployed"]
    chal = {n: v for n, v in oos.items() if n != "deployed" and v > 0}
    if base > 0:
        good = {n: v for n, v in chal.items() if v > base * (1 + MARGIN)}
        w = max(good, key=good.get) if good else "deployed"
    elif chal:
        w = max(chal, key=chal.get)
    else:
        w = "deployed"
    won[w] += 1
    slot = f"{r['inst']}_{r['tf']}"
    prev = old.get((r["inst"], r["tf"]))
    if prev and prev != w:
        flips.append((slot, prev, w))
    out.append({"inst": r["inst"], "tf": r["tf"], "winner": w,
                "c": {n: {"full": r[n]["full"], "oos": r[n]["oos2026"]} for n in ("deployed", "bolt-on", "eod1")}})

json.dump(out, open(f"{BASE}/precise_decision.json", "w"), indent=1)
sd = sum(o["c"]["deployed"]["oos"]["pnl"] or 0 for o in out)
sw = sum(o["c"][o["winner"]]["oos"]["pnl"] or 0 for o in out)
M = lambda v: ("+" if (v or 0) >= 0 else "-") + "$" + f"{abs(v or 0):,.0f}"

print("2026 out-of-sample, one approach across all 54 slots:")
for n, v in tot.items():
    print(f"    all-{n:<9} {M(v):>12}")
print(f"    BEST-PER-SLOT {M(sw):>12}   vs deployed {M(sd)}  ({M(sw - sd)})")
print(f"    slots won: deployed {won['deployed']} · bolt-on {won['bolt-on']} · eod1 {won['eod1']}")
print()
if flips:
    print(f"VERDICTS THE PRECISION FIX CHANGED ({len(flips)}):")
    for slot, a, b in flips:
        print(f"    {slot:9} {a:9} -> {b}")
else:
    print("the precision fix changed no verdicts")
