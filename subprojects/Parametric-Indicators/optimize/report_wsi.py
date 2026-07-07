"""WS-I.10 report — extract the FEASIBLE Pareto front from each per-TF NSGA-III study (wsh3_<tf>)
and build the cross-TF leaderboard + a results report.

Per timeframe (study wsh3_<tf>, 3 objectives + the full-period DD≤25%·P/L constraint):
  results/<tf>_wsi_pareto.csv   — every feasible Pareto-optimal config (objectives + full P/L/DD +
                                  enabled indicators + box params + K)
  results/<tf>_wsi_pareto.png   — median-P/L vs worst-DD scatter, feasible front highlighted (if mpl)
Cross-TF:
  results/wsi_leaderboard.csv   — each TF's champion (max median fold P/L among feasible) + its combo
  reports/WS-I_RESULTS.md       — summary table + per-TF champion combos + honest caveats

Run:  python3 optimize/report_wsi.py [tf ...]      (default: all 7)
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_PARENT = _HERE.parent
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

import optuna  # noqa: E402
from indicators import library  # noqa: E402

# Stable, full list of every indicator's internal param column: "<key>_<param>" across all
# registered indicators (rectangular — present for every row, filled only when that indicator is
# enabled, blank otherwise). Lets each Pareto row be a complete, directly-applyable spec.
_IND_PARAM_COLS = [f"{key}_{p['name']}" for key in library.REGISTRY
                   for p in library.SCHEMA[key].get("params", [])]

_DB = _HERE / "studies" / "wsh.db"                     # legacy SHARED store (back-compat)
_PREFIX = os.environ.get("WSI_STUDY_PREFIX", "wsh3")   # study name prefix (wsh3 = WS-I.10 regime)
_INSTRUMENT = os.environ.get("WSI_INSTRUMENT", "NQ")   # NQ (default) or ES; non-NQ → suffixed artifacts
_SUF = "" if _INSTRUMENT == "NQ" else f"_{_INSTRUMENT}"


def _study_in(db_path: Path, study_name: str) -> bool:
    """True iff an Optuna study named `study_name` already lives in the SQLite file `db_path`."""
    if not db_path.exists():
        return False
    try:
        con = sqlite3.connect(db_path)
        try:
            rows = con.execute("SELECT study_name FROM studies").fetchall()
        finally:
            con.close()
        return any(r[0] == study_name for r in rows)
    except Exception:
        return False


def _db_for(tf: str, study_name: str) -> Path:
    """Pick the SQLite file holding this timeframe's study: prefer the per-TF file (wsh_<tf>.db); if it
    is absent but the legacy shared wsh.db holds the study, fall back to the shared file with a LOUD
    warning (so the server's single-file output stays readable). See MIGRATION_per_tf_db.md."""
    per_tf = _HERE / "studies" / f"wsh_{tf}{_SUF}.db"
    if _study_in(per_tf, study_name):
        return per_tf
    if _study_in(_DB, study_name):
        print(f"  ⚠️  FALLBACK: '{per_tf.name}' has no '{study_name}' — reading the legacy SHARED "
              f"'{_DB.name}' instead.", flush=True)
        return _DB
    return per_tf                                       # neither has it → caller reports "no study"
_RESULTS = _HERE / "results"
_REPORTS = _HERE / "reports"
_RESULTS.mkdir(exist_ok=True); _REPORTS.mkdir(exist_ok=True)
TFS = ["1m", "2m", "5m", "15m", "1h", "2h", "4h"]
DD_CAP = 0.25


def _feasible(t) -> bool:
    fp = t.user_attrs.get("full_pnl"); fd = t.user_attrs.get("full_dd")
    return fp is not None and fp > 0 and fd is not None and fd <= DD_CAP * fp


def _enabled_inds(p: dict) -> list[str]:
    return [k[3:] for k, v in p.items() if k.startswith("en_") and v]


def _row(t) -> dict:
    p = t.user_attrs; pr = t.params
    enabled = set(_enabled_inds(pr))
    row = dict(
        median_pnl=round(t.values[0], 1), worst_dd=round(-t.values[1], 1), win=round(t.values[2], 1),
        full_pnl=round(p.get("full_pnl", 0.0), 1), full_dd=round(p.get("full_dd", 0.0), 1),
        dd_pct_of_pnl=round(100 * p.get("full_dd", 0.0) / p.get("full_pnl", 1e-9), 1),
        # 4-decimal precision: harmless for large-value instruments (NQ/GC/ES sl~20-135), ESSENTIAL for silver
        # whose sl/tp/dd_limit are tiny (~0.05-0.4) — rounding to 1dp turned tp=0.04→0.0 (degenerate zero-stop).
        sl_soft=round(pr["sl_soft"], 4), sl_hard=round(pr["sl_soft"] + pr["sl_hard_delta"], 4),
        tp=round(pr["tp"], 4), gate_pct=round(pr["gate_pct"], 2), dd_limit=round(pr["dd_limit"], 4),
        cooldown=pr["cooldown"], flip=pr["flip"], k=pr["k"],
        cap_1min=pr.get("cap_1min", 0),                  # max-hold (traded 1-min bars); 0 = off. SEARCHED →
                                                         # must round-trip or the rebuilt champion mis-exits.
        n_indicators=len(enabled), indicators=";".join(sorted(enabled)),
    )
    # full tuned internals: one column per indicator-param, filled only when that indicator is on
    for col in _IND_PARAM_COLS:
        ikey = next((k for k in library.REGISTRY if col.startswith(k + "_")), None)
        if ikey in enabled and col in pr:
            row[col] = round(pr[col], 4) if isinstance(pr[col], float) else pr[col]
        else:
            row[col] = ""
    return row


def export_tf(tf: str):
    study_name = f"{_PREFIX}_{tf}{_SUF}"
    db_path = _db_for(tf, study_name)
    from optimize import storage as study_storage   # Tier 1 — honor WSH_STORAGE_URL (else per-TF sqlite)
    try:
        study = optuna.load_study(study_name=study_name, storage=study_storage.storage_url(db_path))
    except Exception as e:
        print(f"  {tf}: no study ({e})"); return None
    complete = [t for t in study.trials if t.values is not None]
    feasible = [t for t in complete if _feasible(t)]
    # feasible Pareto front = non-dominated among feasible (use Optuna's front, filtered)
    front = [t for t in study.best_trials if _feasible(t)]
    if not front and feasible:                 # fall back to all feasible if best_trials empty
        front = feasible
    front = sorted(front, key=lambda t: t.values[0], reverse=True)   # by median P/L desc
    rows = [_row(t) for t in front]
    import csv
    cols = ["median_pnl", "worst_dd", "win", "full_pnl", "full_dd", "dd_pct_of_pnl",
            "sl_soft", "sl_hard", "tp", "gate_pct", "dd_limit", "cooldown", "flip", "k", "cap_1min",
            "n_indicators", "indicators"] + _IND_PARAM_COLS
    with open(_RESULTS / f"{tf}_wsi_pareto{_SUF}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    _plot(tf, complete, front)
    print(f"  {tf}: {len(complete)} complete, {len(feasible)} feasible, front {len(front)}")
    return dict(tf=tf, n_complete=len(complete), n_feasible=len(feasible), front=len(front),
                champion=(rows[0] if rows else None))


def _plot(tf, complete, front):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    if not complete:
        return
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter([-t.values[1] for t in complete], [t.values[0] for t in complete],
               s=14, c="#bbb", label="all complete")
    feas = [t for t in complete if _feasible(t)]
    ax.scatter([-t.values[1] for t in feas], [t.values[0] for t in feas],
               s=20, c="#5472d3", label="feasible")
    if front:
        ax.scatter([-t.values[1] for t in front], [t.values[0] for t in front],
                   s=40, c="#2e7d32", marker="*", label="feasible front")
    ax.set_xlabel("worst-fold maxDD ($)"); ax.set_ylabel("median fold P/L ($)")
    ax.set_title(f"WS-I {tf}: median P/L vs worst DD (feasible: DD≤25%·full P/L)")
    ax.legend(); ax.grid(alpha=0.3); fig.tight_layout()
    fig.savefig(_RESULTS / f"{tf}_wsi_pareto{_SUF}.png", dpi=110); plt.close(fig)


def main(argv):
    tfs = argv or TFS
    print("WS-I.10 report — feasible Pareto fronts per timeframe:")
    summ = [export_tf(tf) for tf in tfs]
    summ = [s for s in summ if s]
    # cross-TF leaderboard
    import csv
    lead = _RESULTS / f"wsi_leaderboard{_SUF}.csv"
    champ_cols = ["tf", "n_complete", "n_feasible", "front", "median_pnl", "worst_dd", "win",
                  "full_pnl", "dd_pct_of_pnl", "k", "n_indicators", "indicators"]
    with open(lead, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=champ_cols); w.writeheader()
        for s in summ:
            c = s["champion"] or {}
            w.writerow(dict(tf=s["tf"], n_complete=s["n_complete"], n_feasible=s["n_feasible"],
                            front=s["front"], median_pnl=c.get("median_pnl"), worst_dd=c.get("worst_dd"),
                            win=c.get("win"), full_pnl=c.get("full_pnl"),
                            dd_pct_of_pnl=c.get("dd_pct_of_pnl"), k=c.get("k"),
                            n_indicators=c.get("n_indicators"), indicators=c.get("indicators")))
    _write_md(summ)
    print(f"\nwrote {lead} + reports/WS-I_RESULTS{_SUF}.md")
    return 0


def _write_md(summ):
    lines = ["---", "name: ws-i-results-report",
             "description: WS-I.10 results — per-TF NSGA-III indicator search (feasible Pareto fronts; "
             "DD≤25%·P/L constraint) + cross-TF champion combos.",
             "type: report", "status: complete", "workstream: WS-I", "---", "",
             "# WS-I.10 — All-timeframe indicator search: results", "",
             "NSGA-III, 3 objectives (median fold P/L ↑, worst-fold maxDD ↓, median win-rate ↑), "
             "feasibility = full-period maxDD ≤ 25% of full-period P/L. Search = box params + all 15 "
             "indicators on/off + their params + K. Champion per TF = max median fold P/L among feasible.", "",
             "## Per-timeframe champion (feasible)", "",
             "| TF | complete | feasible | front | med P/L | worst DD | win% | full P/L | DD%·P/L | K | #ind | indicators |",
             "|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|---|"]
    for s in summ:
        c = s["champion"]
        if c:
            lines.append(f"| {s['tf']} | {s['n_complete']} | {s['n_feasible']} | {s['front']} | "
                         f"${c['median_pnl']:,.0f} | ${c['worst_dd']:,.0f} | {c['win']:.0f} | "
                         f"${c['full_pnl']:,.0f} | {c['dd_pct_of_pnl']:.0f}% | {c['k']} | "
                         f"{c['n_indicators']} | {c['indicators'] or '(none)'} |")
        else:
            lines.append(f"| {s['tf']} | {s['n_complete']} | {s['n_feasible']} | 0 | — | — | — | — | — | — | — | (no feasible) |")
    # full champion recipe per TF — box knobs + every enabled indicator's tuned internals,
    # so each block is a complete, directly-applyable spec (not just an on/off list).
    lines += ["", "## Full champion recipe per timeframe", "",
              "Everything needed to reproduce each per-TF best hit: the box / risk knobs **and** every "
              "enabled indicator's tuned internal parameters. (Disabled indicators omitted; `vwap` has no "
              "internal params.)", ""]
    for s in summ:
        c = s["champion"]
        if not c:
            lines += [f"### {s['tf']} — (no feasible champion)", ""]; continue
        lines += [f"### {s['tf']}  —  median fold P/L ${c['median_pnl']:,.0f}  ·  worst DD "
                  f"${c['worst_dd']:,.0f}  ·  win {c['win']:.0f}%  ·  full P/L ${c['full_pnl']:,.0f} "
                  f"({c['dd_pct_of_pnl']:.0f}% DD)", "",
                  f"- **Box / risk:** softSL `{c['sl_soft']}` · hardSL `{c['sl_hard']}` · TP `{c['tp']}` · "
                  f"vol-gate `{c['gate_pct']}%` · dd-breaker `${c['dd_limit']:,.0f}` · cooldown "
                  f"`{c['cooldown']}` · flip `{c['flip']}` · **K=`{c['k']}`**", "",
                  "| indicator | role | tuned internal params |", "|---|---|---|"]
        enabled = [x for x in (c.get("indicators") or "").split(";") if x]
        for key in enabled:
            meta = library.SCHEMA.get(key, {})
            pnames = [p["name"] for p in meta.get("params", [])]
            cells = ", ".join(f"`{pn}={c.get(f'{key}_{pn}')}`" for pn in pnames) or "_(none)_"
            lines.append(f"| **{key}** | {meta.get('mode','?')} | {cells} |")
        lines.append("")
    lines += ["## Notes / caveats",
              "- Per-TF feasible fronts + plots: `optimize/results/<tf>_wsi_pareto.{csv,png}`.",
              "- A champion is the max-median-P/L feasible point; the full **front** (the CSV) gives the "
              "P/L↔DD↔win trade-off — pick by preference, don't over-index on one row.",
              "- n=1 history (2025→2026): treat as candidate generation, not proof. Re-validate any chosen "
              "combo on the **exact dashboard engine** (retrace/wait + carry apply there).",
              "- Fine TFs (1m/2m) historically attract cost-blind flip-scalpers — sanity-check exposure + "
              "trade counts before trusting them.", ""]
    (_REPORTS / f"WS-I_RESULTS{_SUF}.md").write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
