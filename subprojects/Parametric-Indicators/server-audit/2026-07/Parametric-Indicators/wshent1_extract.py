#!/usr/bin/env python3
"""Entries-focused extraction for the wshent1_4h study (NQ 4h cold L1, objective=entries).
Pulls user_attrs directly via psycopg2 (avoids the optuna load_study hang), reports the
entries<->PnL<->DD trade-off, and writes namespaced artifacts (does NOT touch canonical wsh4)."""
import os, re, json, csv, psycopg2

u = os.environ["WSH_STORAGE_URL"]
usr, pw, host, port, db = re.match(r"postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(\w+)", u).groups()
c = psycopg2.connect(host=host, port=port or 5432, user=usr, password=pw, dbname=db, connect_timeout=8)
c.autocommit = True
cur = c.cursor(); cur.execute("SET statement_timeout=180000")
cur.execute("select study_id from studies where study_name=%s", ("wshent1_4h",))
sid = cur.fetchone()[0]

KEYS = ("full_pnl", "full_dd", "worst_dd", "median_pnl", "median_win", "median_entries", "constraint")
cur.execute("""select tua.trial_id, tua.key, tua.value_json
               from trial_user_attributes tua join trials t on tua.trial_id=t.trial_id
               where t.study_id=%s and t.state='COMPLETE' and tua.key = ANY(%s)""",
            (sid, list(KEYS)))
ua = {}
for tid, k, v in cur.fetchall():
    ua.setdefault(tid, {})[k] = json.loads(v)

rows = []
for tid, a in ua.items():
    if "full_pnl" not in a or "median_entries" not in a:
        continue
    con = a.get("constraint", [1.0]); con = con[0] if isinstance(con, list) else con
    rows.append(dict(tid=tid, feas=(con <= 0),
                     full_pnl=a.get("full_pnl"), full_dd=a.get("full_dd"), worst_dd=a.get("worst_dd"),
                     median_pnl=a.get("median_pnl"), median_win=a.get("median_win"),
                     median_entries=a.get("median_entries")))
feas = [r for r in rows if r["feas"]]
print(f"complete_with_attrs={len(rows)}  feasible={len(feas)}")


def topn(key, rowset=feas, n=6):
    return sorted(rowset, key=lambda r: (r[key] if r[key] is not None else -1e18), reverse=True)[:n]


def fmt(r):
    return (f"ent={r['median_entries']:.1f} medPnL=${r['median_pnl']:,.0f} fullPnL=${r['full_pnl']:,.0f} "
            f"worstDD=${r['worst_dd']:,.0f} win={r['median_win']:.0f}%")


print("\n### TOP by median-fold ENTRIES (feasible) — the objective this run maximised")
for r in topn("median_entries"):
    print("  " + fmt(r))
print("\n### TOP by full P/L (feasible)")
for r in topn("full_pnl"):
    print("  " + fmt(r))
print("\n### TOP by median-fold P/L (feasible) = report_wsi champion criterion")
for r in topn("median_pnl"):
    print("  " + fmt(r))

# distribution of entries across feasible front
ents = sorted(r["median_entries"] for r in feas)
import statistics as st
print(f"\nfeasible median_entries: min={ents[0]:.0f} p50={st.median(ents):.0f} "
      f"p90={ents[int(0.9*len(ents))]:.0f} max={ents[-1]:.0f}")

# fetch params for the two headline champions: max-entries and max-full_pnl (feasible)
def params_for(tid):
    cur.execute("select param_name, param_value from trial_params where trial_id=%s", (tid,))
    return {k: v for k, v in cur.fetchall()}

champ_entries = topn("median_entries", n=1)[0]
champ_pnl = topn("full_pnl", n=1)[0]
champ_medpnl = topn("median_pnl", n=1)[0]
out = {"study": "wshent1_4h", "objective": "entries (median-fold trade count)",
       "complete": len(rows), "feasible": len(feas),
       "champion_max_entries": {**champ_entries, "params": params_for(champ_entries["tid"])},
       "champion_max_full_pnl": {**champ_pnl, "params": params_for(champ_pnl["tid"])},
       "champion_max_median_pnl": {**champ_medpnl, "params": params_for(champ_medpnl["tid"])}}
with open("optimize/results/wshent1_4h_summary.json", "w") as f:
    json.dump(out, f, indent=2, default=float)
print("\nwrote optimize/results/wshent1_4h_summary.json")
print(f"MAX-ENTRIES champion: {fmt(champ_entries)}")
print(f"MAX-FULLPNL champion: {fmt(champ_pnl)}")
