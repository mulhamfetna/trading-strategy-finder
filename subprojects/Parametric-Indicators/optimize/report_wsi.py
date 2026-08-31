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

import math
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
from optimize import optimizer as OPT  # noqa: E402  — searchable_indicators: the ONE scope resolver
from optimize import storage  # noqa: E402  — the ONE module that knows Optuna's private table names

# Stable, full list of every indicator's internal param column: "<key>_<param>" across all
# registered indicators (rectangular — present for every row, filled only when that indicator is
# enabled, blank otherwise). Lets each Pareto row be a complete, directly-applyable spec.
# Recovery switch for studies optimized with --force-eod BEFORE the optimizer began recording cap_mode as
# a user_attr. Such a run pins en_cap_eod ON without suggesting it, so it never reaches trial.params and a
# re-derivation would read the end-of-day close as OFF. Set WSI_FORCE_EOD=1 to extract those studies.
# Never set it for a study that actually SEARCHED en_cap_eod — the recorded value wins there anyway.
_FORCED_EOD = os.getenv("WSI_FORCE_EOD", "").strip().lower() in ("1", "true", "yes", "on")

_IND_PARAM_COLS = [f"{key}_{p['name']}" for key in library.REGISTRY
                   for p in library.SCHEMA[key].get("params", [])]

_DB = _HERE / "studies" / "wsh.db"                     # legacy SHARED store (back-compat)
_PREFIX = os.environ.get("WSI_STUDY_PREFIX", "wsh3")   # study name prefix (wsh3 = WS-I.10 regime)
_INSTRUMENT = os.environ.get("WSI_INSTRUMENT", "NQ")   # NQ (default) or ES; non-NQ → suffixed artifacts
_SUF = "" if _INSTRUMENT == "NQ" else f"_{_INSTRUMENT}"


def _study_in(db_path: Path, study_name: str) -> bool:
    """True iff an Optuna study named `study_name` already lives in the SQLite file `db_path`.

    Delegates to storage.study_exists so Optuna's PRIVATE table names live in exactly one module —
    this was one of six places that open-coded `SELECT ... FROM studies`."""
    return storage.study_exists(db_path, study_name)


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
DD_CAP = float(os.environ.get("WSH_DD_CAP", "0.25"))   # feasibility gate (full_dd ≤ DD_CAP·full_pnl); env-relaxable


def _feasible(t) -> bool:
    fp = t.user_attrs.get("full_pnl"); fd = t.user_attrs.get("full_dd")
    return fp is not None and fp > 0 and fd is not None and fd <= DD_CAP * fp


def _enabled_inds(p: dict) -> list[str]:
    """Enabled INDICATORS only. Must be pinned to the registry: the search also carries non-indicator
    `en_*` switches (en_cap_bars / en_cap_eod), and a bare startswith("en_") would harvest those as
    phantom indicators named "cap_bars"/"cap_eod" — corrupting n_indicators and the rebuilt champion."""
    return [k[3:] for k, v in p.items() if k.startswith("en_") and v and k[3:] in library.REGISTRY]


def _cap_mode_of(pr: dict, ua: dict | None = None) -> str:
    """The exit rule this trial was actually SCORED with. Three sources, in strict order of trust:

    1. The user_attr recorded by the optimizer at trial time — AUTHORITATIVE. It is the exact string that
       was handed to the scorer, so it cannot drift from what was measured. Always prefer it.

    2. Re-derived from the searched switches (studies that ran before we recorded (1)).
       ⚠️ en_cap_eod is ABSENT from trial.params whenever the run PINNED it with --force-eod: Optuna only
       stores params it was asked to SUGGEST, and a pinned value is never suggested. Re-deriving therefore
       reads it as OFF and silently strips the end-of-day close off every champion of a forced-EOD run —
       the strategy written to disk would hold overnight while the one that actually won closed at the
       bell. Set WSI_FORCE_EOD=1 when extracting such a study to recover the truth.

    3. Legacy studies (wsh4/hg1/cl1/ng1 …) predate both switches entirely; a non-zero cap_1min there
       always meant a bars cap.
    """
    if ua:                                                              # (1) recorded, not guessed
        m = str(ua.get("cap_mode") or "").strip()
        if m in ("none", "bars", "eod", "both"):
            return m
    if "en_cap_bars" in pr or "en_cap_eod" in pr:                       # (2) re-derive from the switches
        bars = bool(pr.get("en_cap_bars"))
        # absent ⇒ it was PINNED, not searched. Only WSI_FORCE_EOD can tell us to what.
        eod = bool(pr["en_cap_eod"]) if "en_cap_eod" in pr else _FORCED_EOD
        return ("both" if (bars and eod) else "bars" if bars else "eod" if eod else "none")
    return "bars" if int(pr.get("cap_1min", 0) or 0) > 0 else "none"    # (3) legacy


def _exact(v):
    """Persist a searched price parameter EXACTLY. No rounding, at any scale.

    History, because this bug got 'fixed' twice and came back both times:
      * `round(x, 1)` destroyed silver (tp 0.04 -> 0.0, a zero-width target).
      * So it became `round(x, 4)` — which fixed silver and destroyed natural gas instead
        (sl 0.00080919 -> 0.0008, a 1.1% shift that flipped NG 5m from +$38,079 to -$1,714).
      * So it became round-to-12-SIGNIFICANT-digits, which is scale-free and ~10 orders of magnitude
        safer — but its docstring claimed to "round-trip a float64 losslessly", and that was simply
        FALSE. Measured: 12 significant digits reproduces the searched float exactly ~0.01% of the
        time. float64 needs 17 significant digits in the worst case.

    Each fix repaired the market that had just broken and left a smaller version of the same flaw. The
    pattern only ends by removing the rounding, not by choosing a better amount of it.

    There is no cost to exactness here. csv.DictWriter formats a float with str(), which in Python 3 is
    the SHORTEST string that round-trips exactly (repr). So writing the raw float is simultaneously the
    most precise option and the most compact honest one — measured at 10,000/10,000 exact round-trips
    across NG-to-YM price scales, versus 1/10,000 for the 12-digit version.

    This function is deliberately near-identity: it exists so the persistence path has ONE named place
    that documents why nothing is rounded, and so a future 'let's just round it a bit' has somewhere
    obvious to be rejected.
    """
    if v is None:
        return None
    return float(v)


def _row(t) -> dict:
    p = t.user_attrs; pr = t.params
    enabled = set(_enabled_inds(pr))
    row = dict(
        median_pnl=round(t.values[0], 1), worst_dd=round(-t.values[1], 1), win=round(t.values[2], 1),
        full_pnl=round(p.get("full_pnl", 0.0), 1), full_dd=round(p.get("full_dd", 0.0), 1),
        dd_pct_of_pnl=round(100 * p.get("full_dd", 0.0) / p.get("full_pnl", 1e-9), 1),
        # ⚠️ SIGNIFICANT DIGITS, NEVER DECIMAL PLACES. Price scales here span four orders of magnitude —
        # the Dow trades at $44,452 and natural gas at $3.57 — so a stop is ~10 points on YM and ~0.0008 on
        # NG. Any FIXED number of decimals is therefore right for one market and destroys another:
        #   1 dp  killed silver     (tp 0.04  -> 0.0     — a degenerate zero-width target)
        #   4 dp  killed nat gas    (sl 0.00080919 -> 0.0008 — a 1.1% shift in the stop)
        #         and copper too    (its stops start at 0.0013 — two significant digits survive)
        # The 4-dp version looked safe because it fixed the market that had just broken. It did not: on NG 5m
        # it moved the champion's P/L by $39,793 and FLIPPED ITS SIGN (+$38,079 measured -> -$1,714 shipped),
        # and we spent a day blaming the optimizer's fast engine for "lying". The engine was right every time.
        # Significant digits are scale-free: 12 of them round-trip float64 losslessly at any price level.
        sl_soft=_exact(pr["sl_soft"]), sl_hard=_exact(pr["sl_soft"] + pr["sl_hard_delta"]),
        tp=_exact(pr["tp"]), gate_pct=_exact(pr["gate_pct"]),
               # dd_limit/cooldown RETIRED from the search 2026-08-01 (optimizer runs them fixed at 0):
               # post-retirement studies have no such params — read what the trial actually ran with.
               dd_limit=_exact(pr.get("dd_limit", 0.0)),
        cooldown=pr.get("cooldown", 0), flip=pr["flip"], k=pr["k"],
        # Time caps. BOTH are searched, so both must round-trip or the rebuilt champion mis-exits.
        # cap_1min is only meaningful when a BAR cap is armed — zero it otherwise so a stale "how many
        # bars" value cannot be mistaken for an active cap downstream.
        #
        # ⚠️ DERIVE "is the bar cap armed?" FROM _cap_mode_of(), NEVER from `pr.get("en_cap_bars")`.
        # LEGACY studies (wsh4/hg1/cl1/ng1 …) predate the two cap switches and carry NO en_cap_bars param,
        # so a truthiness test on it is False for every one of them — which silently STRIPS THE CAP off
        # every legacy champion (cap_1min 9 → 0). That corrupted the deployed CL/NG champions when their
        # pareto CSVs were regenerated. _cap_mode_of() already handles the legacy fallback (a non-zero
        # cap_1min with no switches always meant a bars cap).
        cap_1min=(int(p.get("cap_1min", pr.get("cap_1min", 0)) or 0)
                  if _cap_mode_of(pr, p) in ("bars", "both") else 0),
        cap_mode=_cap_mode_of(pr, p),                    # none | bars | eod | both
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
    # Tier 1 — honor WSH_STORAGE_URL (else per-TF sqlite); Tier 2 — WSH_JOURNAL_DIR ⇒ per-study journal.
    from optimize import storage as study_storage
    try:
        study = optuna.load_study(study_name=study_name,
                                  storage=study_storage.make_storage(db_path, study_name))
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
            "sl_soft", "sl_hard", "tp", "gate_pct", "dd_limit", "cooldown", "flip", "k",
            "cap_1min", "cap_mode",
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


def _scope_sentence() -> str:
    """Describe the indicator scope this run ACTUALLY searched, rather than asserting a number.

    The header used to read "all 15 indicators" — a literal from when the registry held 15. It stayed
    put through 18 and then 165, and it survived onto every generated report including campaigns that
    deliberately restricted the search: the rescued wshgap4 report claims "all 15" for a run that
    searched the original 18 under --only-indicators (#89 sweep). A generated report that hardcodes a
    fact about the search is a report that eventually lies about it.
    """
    only = tuple(x for x in os.environ.get("WSH_ONLY", "").split(",") if x)
    excl = tuple(x for x in os.environ.get("WSH_EXCLUDE", "").split(",") if x)
    total = len(library.REGISTRY)
    if not only and not excl:
        return f"all {total} indicators in the registry"
    n = len(OPT.searchable_indicators(only, excl))
    how = []
    if only:
        how.append(f"--only-indicators {','.join(only)}")
    if excl:
        how.append(f"--exclude-indicators {','.join(excl)}")
    return f"{n} of {total} indicators (scoped by `{'` `'.join(how)}`)"


def _write_md(summ):
    lines = ["---", "name: ws-i-results-report",
             "description: WS-I.10 results — per-TF NSGA-III indicator search (feasible Pareto fronts; "
             "DD≤25%·P/L constraint) + cross-TF champion combos.",
             "type: report", "status: complete", "workstream: WS-I", "---", "",
             "# WS-I.10 — All-timeframe indicator search: results", "",
             "NSGA-III, 3 objectives (median fold P/L ↑, worst-fold maxDD ↓, median win-rate ↑), "
             "feasibility = full-period maxDD ≤ 25% of full-period P/L. Search = box params + "
             f"{_scope_sentence()} on/off + their params + K. "
             "Champion per TF = max median fold P/L among feasible.", "",
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
