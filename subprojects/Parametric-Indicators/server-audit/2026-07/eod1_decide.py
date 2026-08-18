"""THE HEAD-TO-HEAD. Three candidates per slot, one winner, decided on the held-out 2026 year.

    deployed  -- today's champion. Most of these HOLD OVERNIGHT.                (honest_metrics.json)
    bolt-on   -- that exact champion with the end-of-day close switched on,
                 with NO re-tuning. Tests: "can we just turn it on?"            (eod_forced.json)
    eod1      -- cold-start, re-tuned from scratch WITH the close forced.       (eod1_verified.json)

DECISION RULE -- written down BEFORE looking at the numbers, so it cannot be fitted to them:

  1. The 2026 held-out year decides. In-sample profit is NEVER used to pick a winner: every eod1
     champion was chosen by a search that read the in-sample data, so its in-sample number is
     optimistic by construction. 2026 is the only window none of these searches ever saw.

  2. Any candidate that LOSES money in 2026 is disqualified, however good it looks in-sample.

  3. A challenger takes the slot only by beating the deployed champion's 2026 profit by more than a
     10% MARGIN. A tie does NOT churn a verified, deployed strategy: switching costs real work
     (re-verify, new playbook, a fresh chance to ship a bug), and a sub-10% edge on ONE year of
     out-of-sample data is noise, not evidence.

  4. If the deployed champion itself loses money in 2026, it has no claim on the slot -- take the best
     surviving challenger outright. If NOTHING is profitable in 2026, keep the deployed one (there is
     nothing better to switch to) and FLAG the slot.
"""
import json
import os

WSI = os.path.expanduser("~/Mulham/wsg-i")
MARGIN = 0.10

dep = {(r["inst"], r["tf"]): r for r in json.load(open(f"{WSI}/honest_metrics.json"))}
bolt = {(r["inst"], r["tf"]): r for r in json.load(open(f"{WSI}/eod_forced.json"))}
new = {(r["inst"], r["tf"]): r for r in json.load(open(f"{WSI}/eod1_verified.json"))}

INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]

rows = []
for inst in INSTS:
    for tf in TFS:
        k = (inst, tf)
        c = {}
        if dep.get(k):
            c["deployed"] = {"full": dep[k]["full"]["boxes"], "oos": dep[k]["oos2026"]["boxes"]}
        if bolt.get(k, {}).get("eod_forced"):
            c["bolt-on"] = {"full": bolt[k]["eod_forced"]["full"], "oos": bolt[k]["eod_forced"]["oos2026"]}
        if new.get(k, {}).get("eod1"):
            c["eod1"] = {"full": new[k]["eod1"]["full"], "oos": new[k]["eod1"]["oos2026"]}

        def oos(name):
            return (c.get(name) or {}).get("oos", {}).get("pnl") or 0

        base = oos("deployed")
        chal = {n: oos(n) for n in ("bolt-on", "eod1") if n in c and oos(n) > 0}   # rule 2

        flag = ""
        if base > 0:
            # rule 3: must clear deployed by the margin
            good = {n: v for n, v in chal.items() if v > base * (1 + MARGIN)}
            win = max(good, key=good.get) if good else "deployed"
        elif chal:
            win = max(chal, key=chal.get)                                          # rule 4
            flag = "deployed loses in 2026"
        else:
            win = "deployed"
            flag = "NO candidate is profitable in 2026"

        rows.append({"inst": inst, "tf": tf, "winner": win, "flag": flag,
                     "cands": {n: {"full_pnl": v["full"].get("pnl"), "full_dd": v["full"].get("max_dd"),
                                   "oos_pnl": v["oos"].get("pnl"), "oos_dd": v["oos"].get("max_dd"),
                                   "oos_n": v["oos"].get("n_taken")} for n, v in c.items()}})

json.dump(rows, open(f"{WSI}/eod1_decision.json", "w"), indent=1)

hdr = f"{'slot':8} | {'deployed 2026':>14} | {'bolt-on 2026':>14} | {'eod1 2026':>14} | winner"
print(hdr); print("-" * (len(hdr) + 14))
tot = {"deployed": 0.0, "bolt-on": 0.0, "eod1": 0.0}
won = {"deployed": 0, "bolt-on": 0, "eod1": 0}
sd = sw = 0.0
for r in rows:
    c = r["cands"]
    def f(n):
        return f"${c[n]['oos_pnl']:>13,.0f}" if c.get(n) else " " * 14
    for n in tot:
        if c.get(n):
            tot[n] += c[n]["oos_pnl"] or 0
    won[r["winner"]] += 1
    sd += (c.get("deployed") or {}).get("oos_pnl") or 0
    sw += (c.get(r["winner"]) or {}).get("oos_pnl") or 0
    mark = "  <-- CHANGE" if r["winner"] != "deployed" else ""
    if r["flag"]:
        mark += f"   [{r['flag']}]"
    print(f"{r['inst']+'_'+r['tf']:8} | {f('deployed')} | {f('bolt-on')} | {f('eod1')} | {r['winner']}{mark}")

print("-" * (len(hdr) + 14))
print("2026 SUITE TOTAL, if you ran ONE approach across all 54 slots:")
for n, v in tot.items():
    print(f"    all-{n:<10} ${v:>12,.0f}")
print()
print(f"    BEST-PER-SLOT  ${sw:>12,.0f}   (vs deployed ${sd:,.0f} = {sw - sd:+,.0f}, "
      f"{((sw / sd - 1) * 100 if sd else 0):+.1f}%)")
print(f"    slots won: deployed {won['deployed']}, bolt-on {won['bolt-on']}, eod1 {won['eod1']}")
