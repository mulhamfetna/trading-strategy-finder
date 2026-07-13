"""Rebuild the playbook metrics with REAL numbers — no fabricated placeholders.

THE BUG THIS FIXES. The previous metrics file was assembled by hand from a comparison run that had only
captured P/L, drawdown, win-rate and the FULL-window trade count. Everything else was invented:

    2026 trade count  -> hardcoded 0      => playbooks literally read
                                             "still profitable (+$37,286) across 0 trades"
    profit factor     -> None
    payoff            -> None
    avg win / loss    -> 0
    exposure          -> 100.0

So the tearsheets were printing placeholders as if they were measurements. eod_forced.json now carries the
COMPLETE metric set for both windows, straight from the causal on-screen engine, so we can build the file
honestly.
"""
import json
import os

BASE = os.path.expanduser("~/Mulham/wsg-i")
rows = [r for r in json.load(open(f"{BASE}/eod_forced.json")) if r.get("as_deployed")]

out = []
for r in rows:
    m = r["as_deployed"]          # the champion AS DEPLOYED (the EOD-forced variant is a separate study)
    full, oos = m["full"], m["oos2026"]

    # sanity: refuse to emit a slot that claims profit with no trades — the exact defect we are fixing
    for w, d in (("full", full), ("2026", oos)):
        if d.get("n_taken") in (None, 0) and abs(d.get("pnl") or 0) > 1:
            raise SystemExit(f"{r['inst']}_{r['tf']} {w}: ${d['pnl']:,.0f} with n_taken={d.get('n_taken')} "
                             f"— that is the bug, not a champion")

    out.append({
        "inst": r["inst"], "tf": r["tf"],
        "full": {"boxes": full, "summary": full},
        "oos2026": {"boxes": oos, "summary": oos},
    })

json.dump(out, open(f"{BASE}/honest_metrics.json", "w"), indent=1)
print(f"wrote honest_metrics.json — {len(out)} champions, full metric set on both windows")
print()
print(f"{'slot':9} {'full P/L':>10} {'trades':>7} {'pf':>5} {'payoff':>7} | "
      f"{'2026 P/L':>9} {'trades':>7} {'exposure':>9}")
print("-" * 74)
for o in out[:6]:
    f, s = o["full"]["boxes"], o["oos2026"]["boxes"]
    print(f"{o['inst']+'_'+o['tf']:9} {f['pnl']:>10,.0f} {f['n_taken']:>7} {str(f.get('pf')):>5} "
          f"{str(f.get('payoff')):>7} | {s['pnl']:>9,.0f} {s['n_taken']:>7} {str(s.get('exposure')):>9}")
print("  ... (all 54 written)")
