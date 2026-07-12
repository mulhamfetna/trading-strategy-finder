"""Build the playbook metrics file for the 54 DEPLOYED champions, from the CORRECTED measurements.

build_playbooks.py expects: [{inst, tf, full:{boxes, summary}, oos2026:{boxes, summary}}]
We have honest_compare.json (both sides, corrected) + honest_verdict.json (who won each slot).
"""
import json
import os

BASE = os.path.expanduser("~/Mulham/wsg-i")
rows = {(r["inst"], r["tf"]): r for r in json.load(open(f"{BASE}/honest_compare.json"))
        if r.get("old") and r.get("new")}
new_wins = set(json.load(open(f"{BASE}/honest_verdict.json"))["new_wins"])

out = []
for (inst, tf), r in rows.items():
    side = "new" if f"{inst}_{tf}" in new_wins else "old"
    m = r[side]
    boxes = {"pnl": m["pnl"], "max_dd": m["dd"], "win": m["win"], "n_taken": m["n"],
             "n_candidates": m["n"], "pf": None, "payoff": None, "exposure": 100.0, "n_locks": 0}
    out.append({
        "inst": inst, "tf": tf,
        "full": {"boxes": boxes, "summary": {"pnl": m["pnl"], "max_dd": m["dd"],
                                             "avg_win": 0, "avg_loss": 0}},
        "oos2026": {"boxes": {"pnl": m["oos"], "n_taken": 0},
                    "summary": {"pnl": m["oos"], "n_taken": 0}},
    })

json.dump(out, open(f"{BASE}/final_metrics.json", "w"), indent=1)
n_new = sum(1 for o in out if (o["inst"] + "_" + o["tf"]) in new_wins)
print(f"wrote final_metrics.json — {len(out)} deployed champions "
      f"({n_new} new / {len(out) - n_new} old)")
