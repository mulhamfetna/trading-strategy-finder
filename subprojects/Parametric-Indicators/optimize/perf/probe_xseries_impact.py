"""Issue #75 — quantify what the wiring fix actually CHANGES, on real data.

The fix is a behaviour change wherever a `--reference` is supplied, so the point of this script is to
put a number on it rather than assert that it is small. Three questions:

  A  NO REFERENCE — the golden-gated path. Old and new must be byte-identical. If this moves, the fix
     is not contained and must not ship.
  B  WITH A REFERENCE, a cross-series indicator enabled — how much did the K-rule starvation cost?
     Runs the deployed 4h champion plus one cross-series CONFIRM indicator at k+1, once with the
     reference reaching the 1-minute context (fixed) and once without (the old behaviour), and diffs
     entries / P&L / drawdown.
  C  COST — cross-series votes are never cached, so a live cross-series indicator is paid on every
     trial. Report the per-call wall-clock so the search-space decision is informed.

Run (server):
  WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data \
    /home/dev/Mulham/.venv/bin/python3 -m optimize.perf.probe_xseries_impact --tf 4h --reference ES
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from optimize import core, data as data_mod, timeframes as TF
from indicators import library
from optimize.l2.payload import l1_default_params

XS_KEYS = ("rolling_corr", "rolling_beta", "cointegration", "pca_factor")
_METRICS = ("pnl", "max_dd", "n_taken", "win_rate", "profit_factor")


def _summary(m):
    return {k: (round(float(m[k]), 4) if isinstance(m.get(k), (int, float, np.floating)) else m.get(k))
            for k in _METRICS if k in m}


def _n_confirmers(params):
    return sum(1 for s in (params.get("indicators") or [])
               if s.get("enabled") and s.get("mode") in ("confirm", "both"))


def _with_xs(params, key, mode=None):
    """The champion params plus one cross-series indicator, with k set so that indicator is PIVOTAL.

    ⚠️ The first version of this used `k = champion_k + 1` (= 2) and measured a difference of exactly
    zero for all four — because `k_eff = min(k, len(confirmers))` and the champion already carries 7
    confirmers, so k=2 is satisfied without the new indicator ever mattering. The comparison was
    unfalsifiable, not null. `k = n_confirmers + 1` makes the added indicator decide every entry.
    """
    p = dict(params)
    specs = [dict(s) for s in (p.get("indicators") or [])]
    spec = library.SCHEMA[key]
    # Use the indicator's NATURAL mode. Forcing a veto-only indicator (`rolling_corr`) into "confirm"
    # makes it a confirmer that structurally cannot confirm, which would look like the starvation bug
    # while actually being an artefact of the harness.
    specs.append({"key": key, "enabled": True, "mode": mode or spec["mode"],
                  "params": {q["name"]: q["default"] for q in spec.get("params", [])}})
    p["indicators"] = specs
    p["k"] = _n_confirmers(p)          # counts the new one iff it is confirm-capable
    return p


def _prefix_activity(monkey_on: bool):
    """Restore the PRE-FIX activity rule (`ref_df is not None`) so the bug can be measured, not just
    described. Post-fix the rule reads the vote-producing context instead."""
    from indicators import runner
    if monkey_on:
        if not hasattr(runner, "_reference_reaches_fixed"):
            runner._reference_reaches_fixed = runner._reference_reaches
        runner._reference_reaches = lambda src, ref_df: ref_df is not None
    elif hasattr(runner, "_reference_reaches_fixed"):
        runner._reference_reaches = runner._reference_reaches_fixed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--instrument", default="NQ")
    ap.add_argument("--reference", default="ES")
    ap.add_argument("--out", default="optimize/perf/results/xseries_wiring_impact.json")
    args = ap.parse_args()

    def log(m):
        print(m, flush=True)

    tf = TF.get(args.tf)
    df_dec, df1, box, vf, n_split = data_mod.load_inputs(args.tf, args.instrument)
    ref_dec, ref_1m, *_ = data_mod.load_inputs(args.tf, args.reference)
    base = l1_default_params(args.tf)
    base["ind_1min"] = True                                    # the production path
    log(f"[impact] {args.instrument} {args.tf}: {len(df_dec):,} decision bars / {len(df1):,} 1-min | "
        f"reference {args.reference} | champion k={base.get('k')} "
        f"indicators={[s['key'] for s in (base.get('indicators') or []) if s.get('enabled')]}")

    res = {"tf": args.tf, "instrument": args.instrument, "reference": args.reference}

    # ---- A: the golden-gated path must not move --------------------------------------------------
    log("\n[impact] A — NO reference (the golden-gated path): must be byte-identical")
    core._clear_caches()
    a_old = core.backtest_metrics(df_dec, df1, box, vf, n_split, dict(base), tf.bar_td)
    core._clear_caches()
    a_new = core.backtest_metrics(df_dec, df1, box, vf, n_split, dict(base), tf.bar_td, ref_df1=None)
    same = _summary(a_old) == _summary(a_new)
    log(f"    {_summary(a_old)}")
    log(f"    identical with ref_df1=None: {same}")
    res["a_no_reference_identical"] = bool(same)
    res["a_summary"] = _summary(a_old)

    # ---- CONTROL: can this measurement see a confirm-gate change at all? -------------------------
    n_conf = _n_confirmers(base)
    core._clear_caches()
    ctrl = core.backtest_metrics(df_dec, df1, box, vf, n_split, dict(base, k=99), tf.bar_td)
    log(f"\n[impact] CONTROL — k=99 with {n_conf} confirmers: entries "
        f"{int(a_old['n_taken'])} -> {int(ctrl['n_taken'])}")
    res["control_k99"] = _summary(ctrl)
    res["control_detects_gate"] = bool(int(ctrl["n_taken"]) != int(a_old["n_taken"]))
    if not res["control_detects_gate"]:
        log("    !! the confirm gate is NOT detectable here — phase B below would be meaningless")

    # ---- B: what the fix changes when a reference IS supplied ------------------------------------
    log(f"\n[impact] B — champion + one cross-series CONFIRM indicator, k = {n_conf + 1} "
        f"(so the added indicator is PIVOTAL)")
    log("    pre_fix      = the shipped bug: counted as a confirmer, reference never reaches it")
    log("    post_unwired = fixed rule, no reference supplied ⇒ correctly inert, k_eff drops back")
    log("    post_wired   = fixed rule, reference wired ⇒ genuinely votes")
    rows = []
    for key in XS_KEYS:
        p = _with_xs(base, key)
        _prefix_activity(True)
        core._clear_caches()
        pre = core.backtest_metrics(df_dec, df1, box, vf, n_split, dict(p), tf.bar_td,
                                    ref_df=ref_dec, ref_df1=None)
        _prefix_activity(False)
        core._clear_caches()
        unwired = core.backtest_metrics(df_dec, df1, box, vf, n_split, dict(p), tf.bar_td,
                                        ref_df=ref_dec, ref_df1=None)
        core._clear_caches()
        wired = core.backtest_metrics(df_dec, df1, box, vf, n_split, dict(p), tf.bar_td,
                                      ref_df=ref_dec, ref_df1=ref_1m)
        row = {"key": key, "k": p["k"], "mode": library.SCHEMA[key]["mode"],
               "confirm_capable": library.SCHEMA[key]["mode"] in ("confirm", "both"),
               "pre_fix": _summary(pre),
               "post_unwired": _summary(unwired), "post_wired": _summary(wired)}
        rows.append(row)
        log(f"    {key:16s} [{library.SCHEMA[key]['mode']:>7s}] entries  pre_fix {int(pre.get('n_taken', 0)):>4d} | "
            f"post_unwired {int(unwired.get('n_taken', 0)):>4d} | "
            f"post_wired {int(wired.get('n_taken', 0)):>4d}   "
            f"P/L ${float(pre.get('pnl', 0)):>10,.0f} | ${float(unwired.get('pnl', 0)):>10,.0f} | "
            f"${float(wired.get('pnl', 0)):>10,.0f}")
    res["b_impact"] = rows
    # Starvation is a CONFIRM-path bug: a vetoer that never vetoes changes nothing, so only the
    # confirm-capable indicators are expected to show it.
    res["b_starvation_confirmed"] = all(
        int(r["pre_fix"].get("n_taken", 0)) < int(r["post_unwired"].get("n_taken", 0))
        for r in rows if r["confirm_capable"])

    # ---- C: what a live cross-series indicator costs per trial ------------------------------------
    log("\n[impact] C — per-call cost of a live cross-series indicator (never cached ⇒ every trial)")
    from indicators import runner
    src = runner.indicator_source_1min(df_dec, df1, tf.bar_td, ref_1m)
    cost = []
    for key in XS_KEYS:
        spec = library.SCHEMA[key]
        ind = library.from_specs([{"key": key, "enabled": True, "mode": spec["mode"],
                                   "params": {q["name"]: q["default"] for q in spec.get("params", [])}}])[0]
        ind.directions(src[0])                                          # warm-up (JIT), NOT timed
        t0 = time.perf_counter()
        ind.directions(src[0])
        secs = time.perf_counter() - t0
        cost.append({"key": key, "seconds": round(secs, 4)})
        log(f"    {key:16s} {secs:6.3f}s per compute on the full 1-minute frame")
    res["c_cost_per_call_s"] = cost
    res["c_total_if_all_four_enabled_s"] = round(sum(c["seconds"] for c in cost), 3)
    log(f"    all four together: {res['c_total_if_all_four_enabled_s']}s per trial (uncached)")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2))
    log(f"\n[impact] WROTE {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
