"""Build the FINAL champion set: per slot, keep whichever champion actually won on 2026 out-of-sample.

Inputs (both sides UI-verified, so this is apples-to-apples):
  new      -> cap_verify.json          + nq4h_verify.json (NQ 4h, which the dashboard cannot serve)
  deployed -> the backed-up wsh4_champions_full*.json (currently swapped OUT)
  new defs -> cap1_champions/cap1_champions_<INST>.json

Writes the merged set back into results/wsh4_champions_full*.json — the dashboard's defaults — so that
what ships is, slot by slot, the champion that demonstrably held up on the held-out year.
"""
import json
import os
from pathlib import Path

WSI = Path(os.path.expanduser("~/Mulham/wsg-i"))
RES = WSI / "Parametric-Indicators" / "optimize" / "results"
BAK = WSI / "deployed_champions_backup"
CAP = WSI / "cap1_champions"

MAN = json.load(open(WSI / "manifest_deployed.json"))     # deployed verified numbers
dep_num = {(m["inst"], m["tf"]): m for m in MAN if not m["variant"]}

new = {(r["inst"], r["tf"]): r for r in json.load(open(WSI / "cap_verify.json")) if "full" in r}

# NQ 4h: verified separately (payload hardcodes the 4h anchor, so the UI pass could not test it)
nq4 = json.load(open(WSI / "nq4h_verify.json"))

TFS = ["4h", "2h", "1h", "15m", "5m", "2m"]
INSTS = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]

report, n_new, n_old, n_rej = [], 0, 0, 0

for inst in INSTS:
    suf = "" if inst == "NQ" else f"_{inst}"
    deployed = json.loads((BAK / f"wsh4_champions_full{suf}.json").read_text())
    challenger = json.loads((CAP / f"cap1_champions_{inst}.json").read_text())
    merged = dict(deployed)

    for tf in TFS:
        if tf not in challenger:
            continue

        if inst == "NQ" and tf == "4h":
            n_pnl, n_dd, n_oos = nq4["pnl"], nq4["dd"], nq4["oos"]
        else:
            r = new.get((inst, tf))
            if not r:
                continue
            n_pnl = r["full"]["boxes"].get("pnl", 0)
            n_dd = r["full"]["boxes"].get("max_dd", 0)
            n_oos = r["oos2026"]["summary"].get("pnl", 0)

        d = dep_num.get((inst, tf))
        o_oos = (d or {}).get("oos")
        o_pnl = (d or {}).get("full")

        # 1) never ship a champion that loses money in- or out-of-sample
        if n_pnl <= 0 or n_oos <= 0:
            pick, why = "old", f"REJECT new (in ${n_pnl:,.0f} / oos ${n_oos:,.0f})"
            n_rej += 1
        elif o_oos is None:
            pick, why = "new", "no incumbent"
            n_new += 1
        elif n_oos > o_oos * 1.05:
            pick, why = "new", f"OOS {n_oos:,.0f} > {o_oos:,.0f}"
            n_new += 1
        elif o_oos > n_oos * 1.05:
            pick, why = "old", f"OOS {o_oos:,.0f} > {n_oos:,.0f}"
            n_old += 1
        else:
            pick = "new" if n_dd < (d or {}).get("dd", 1e18) else "old"
            why = "tie on OOS → lower drawdown"
            (n_new if pick == "new" else n_old)
            if pick == "new":
                n_new += 1
            else:
                n_old += 1

        if pick == "new":
            merged[tf] = challenger[tf]

        report.append((inst, tf, pick, o_pnl, o_oos, n_pnl, n_oos, why))

    (RES / f"wsh4_champions_full{suf}.json").write_text(json.dumps(merged, indent=1))
    print(f"wrote wsh4_champions_full{suf}.json", flush=True)

print(f"\n{'slot':9} {'pick':5} {'old OOS':>10} {'new OOS':>10}  why")
print("-" * 78)
for inst, tf, pick, op, oo, np_, no, why in report:
    tag = "NEW" if pick == "new" else "old"
    print(f"{inst+'_'+tf:9} {tag:5} {('$'+format(int(oo or 0),',')):>10} {('$'+format(int(no),',')):>10}  {why}")

print(f"\nNEW adopted: {n_new}   OLD held: {n_old}   (rejected new: {n_rej})")
best = sum(max(no if no > 0 else 0, oo or 0) for _, _, _, _, oo, _, no, _ in report)
depl = sum((oo or 0) for _, _, _, _, oo, _, _, _ in report)
print(f"2026 OOS:  deployed ${depl:,.0f}  →  final ${best:,.0f}   (+${best-depl:,.0f})")
print("MERGE_DONE")
