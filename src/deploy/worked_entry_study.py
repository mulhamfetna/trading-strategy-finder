"""WS-DEPLOY D4 (#132) — worked-entry validation: does the qty 10/20 economics survive a VWAP
entry over the pre-release window?

D3 (#131) measured the wall: the single ENTRY second trades ~7 contracts (NQ median) while a
worked entry over the whole 300s window is 1.31% participation even at qty=20. This study replaces
the entry model and measures what that does to the trade — pre-registered on #132 before this ran.

THE WORKED-ENTRY MODEL (fixed in the registration):
    entry price = VWAP of all traded seconds in [release-300s, release-5s)
    bracket (stop 0.10% / TP 0.40% off the WORKED entry, tie=>STOP, GAP-01, timed +900s)
    ACTIVE from release-5s  — the build window is unprotected (an explicit property, reported)

VERIFICATIONS:
    V1  bridge: run_bracket with the OLD definition must equal the parity-proven results
        byte-identically (enforced by the existing battery + replay parity); VWAP re-derived by an
        independent path (pandas groupby vs numpy dot) must match per event.
    V2  the worked-vs-single effect must be consistent in direction/scale on RTY.
    V3  falsifier: the entry window shifted +360s (INTO the release) must change the result
        dramatically — else the window anchoring is broken and the study is VOID.

    WSH_DATA_BASE=... python3 -m src.deploy.worked_entry_study --instrument NQ --bars-1s ...
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .release_executor import (PV, COST_PER_LEG, LEAD_S, Leg, run_bracket, load_1s_windows)
from .schedule import load as load_schedule, DEFAULT_SCHEDULE

QTYS = [1, 5, 10, 20]
BUILD_END_S = 5                     # the worked order must be DONE 5s before the print


def vwap_and_start(idx, cl, vol, t_rel, shift_s: int = 0):
    """VWAP over [t_rel-300s+shift, t_rel-5s+shift) and the first bar index >= t_rel-5s."""
    t0 = np.datetime64(t_rel)
    a = int(np.searchsorted(idx, t0 - np.timedelta64(LEAD_S - shift_s, "s"), "left"))
    b = int(np.searchsorted(idx, t0 - np.timedelta64(BUILD_END_S - shift_s, "s"), "left"))
    if b <= a:
        return None, None, None
    v = vol[a:b]
    if v.sum() <= 0:
        return None, None, None
    vw = float(np.dot(cl[a:b], v) / v.sum())
    i_active = int(np.searchsorted(idx, t0 - np.timedelta64(BUILD_END_S, "s"), "left"))
    # V1 (independent path): pandas re-derivation of the same VWAP
    vw_alt = float((pd.Series(cl[a:b]) * pd.Series(v)).sum() / pd.Series(v).sum())
    return vw, i_active, vw_alt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=list(PV))
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--schedule", default=str(DEFAULT_SCHEDULE))
    ap.add_argument("--floor-year", type=int, default=2024)
    ap.add_argument("--series", default="",
                    help="comma-separated schedule titles this leg rides (empty = all; "
                         "ES/YM scale on 'Inflation Rate MoM' only — RQ-1/RQ-9, #141/#150)")
    ap.add_argument("--out-dir", default="deploy_out_d4")
    a = ap.parse_args()
    inst = a.instrument
    cost1 = COST_PER_LEG[inst]["stressed"]
    pv = PV[inst]

    sched = load_schedule(Path(a.schedule))
    ev = sched[(sched.status == "confirmed")
               & (sched.et.dt.year >= a.floor_year)].reset_index(drop=True)
    series = [x.strip() for x in a.series.split(",") if x.strip()]
    if series:                       # RQ-1/RQ-9: a leg may scale on a SUBSET of the schedule
        ev = ev[ev.title.isin(series)].reset_index(drop=True)
    print(f"D4 worked-entry study · {inst} · {len(ev)} releases {a.floor_year}+ · "
          f"entry = VWAP[rel-300s, rel-5s) · bracket active from rel-5s · stressed ${cost1:.2f}")

    bars = load_1s_windows(Path(a.bars_1s),
                           [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=905))
                            for t in ev.et], keep_volume=True)
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    vol = bars["Volume"].to_numpy(float)

    rows, v1_bad = [], 0
    for _, r in ev.iterrows():
        t = pd.Timestamp(r.et)
        single = run_bracket(idx, op, hi, lo, cl, t, Leg("long", 1), pv, r.title)
        vw, i_act, vw_alt = vwap_and_start(idx, cl, vol, t)
        if single is None or vw is None:
            continue
        if abs(vw - vw_alt) > 1e-9:
            v1_bad += 1
        worked = run_bracket(idx, op, hi, lo, cl, t, Leg("long", 1), pv, r.title,
                             entry_price=vw, walk_from=i_act)
        if worked is None:
            continue
        rows.append({"et": single.et, "title": r.title,
                     "single_entry": single.entry, "worked_entry": vw,
                     "entry_delta_usd": (vw - single.entry) * pv,
                     "single_pnl": single.pnl_usd, "worked_pnl": worked.pnl_usd,
                     "single_outcome": single.outcome, "worked_outcome": worked.outcome})
    d = pd.DataFrame(rows)
    print(f"\nV1 · VWAP independent-path mismatches: {v1_bad} -> "
          f"{'PASS' if v1_bad == 0 else 'FAIL'} (bridge: existing battery + replay parity "
          f"prove the default path unchanged)")

    # ---- V3 falsifier: window shifted +360s must change things dramatically ----------------------
    sh = []
    for _, r in ev.iterrows():
        t = pd.Timestamp(r.et)
        vw, i_act, _ = vwap_and_start(idx, cl, vol, t, shift_s=360)
        if vw is None:
            continue
        w = run_bracket(idx, op, hi, lo, cl, t, Leg("long", 1), pv, r.title,
                        entry_price=vw, walk_from=i_act)
        if w is not None:
            sh.append(w.pnl_usd)
    shifted_mean = float(np.mean(sh)) if sh else float("nan")
    delta_vs_worked = abs(shifted_mean - d.worked_pnl.mean())
    v3_pass = delta_vs_worked > 100.0
    print(f"V3 · shifted-window (+360s, INTO the release) mean ${shifted_mean:+.2f} vs worked "
          f"${d.worked_pnl.mean():+.2f} -> |Δ| ${delta_vs_worked:.2f} -> "
          f"{'PASS (anchoring real)' if v3_pass else 'FAIL — VOID'}")

    # ---- the comparison ---------------------------------------------------------------------------
    print(f"\nWORKED vs SINGLE (qty=1 per contract, {a.floor_year}+):")
    print(f"  entry delta (worked − single): mean ${d.entry_delta_usd.mean():+.2f} · "
          f"median ${d.entry_delta_usd.median():+.2f} · p5 ${d.entry_delta_usd.quantile(.05):+.2f} "
          f"· p95 ${d.entry_delta_usd.quantile(.95):+.2f}")
    for name, col in (("SINGLE", "single_pnl"), ("WORKED", "worked_pnl")):
        x = d[col]
        print(f"  {name:>7}: n={len(x)} gross mean ${x.mean():+.2f} · net(stressed) "
              f"${x.mean() - cost1:+.2f} · total ${x.sum():+,.0f} · win {(x > 0).mean():.1%}")
    give_up = d.single_pnl.mean() - d.worked_pnl.mean()
    print(f"  cost of working the entry: ${give_up:+.2f}/event "
          f"({100 * give_up / d.single_pnl.mean():+.1f}% of the single-entry edge)")
    changed = (d.single_outcome != d.worked_outcome)
    pre_avoided = ((d.single_outcome == "stopped_pre") & (d.worked_outcome != "stopped_pre")).sum()
    print(f"  outcome changes: {int(changed.sum())}/{len(d)} events · "
          f"pre-release stop-outs avoided by the unprotected build: {int(pre_avoided)}")

    print(f"\nECONOMICS RE-STATED UNDER THE WORKED ENTRY (net stressed):")
    print(f"  {'qty':>4} {'net mean/event':>14} {'net total':>12} {'vs single-entry total':>22}")
    econ = []
    for q in QTYS:
        net_w = d.worked_pnl * q - cost1 * q
        net_s = d.single_pnl * q - cost1 * q
        econ.append({"qty": q, "worked_net_mean": float(net_w.mean()),
                     "worked_net_total": float(net_w.sum()),
                     "single_net_total": float(net_s.sum())})
        print(f"  {q:>4} {net_w.mean():>+14.2f} {net_w.sum():>+12,.0f} {net_s.sum():>+22,.0f}")

    dest = Path(a.out_dir); dest.mkdir(parents=True, exist_ok=True)
    d.to_csv(dest / f"d4_events_{inst}.csv", index=False)
    (dest / f"d4_result_{inst}.json").write_text(json.dumps(
        {"instrument": inst, "floor_year": a.floor_year, "n_events": int(len(d)),
         "v1_vwap_mismatches": v1_bad, "v3_shifted_mean": shifted_mean,
         "v3_delta": delta_vs_worked, "v3_pass": bool(v3_pass),
         "entry_delta_mean": float(d.entry_delta_usd.mean()),
         "single_gross_mean": float(d.single_pnl.mean()),
         "worked_gross_mean": float(d.worked_pnl.mean()),
         "cost_of_working_per_event": float(give_up),
         "outcome_changes": int(changed.sum()), "pre_stops_avoided": int(pre_avoided),
         "economics": econ,
         "model_note": "build window unprotected by design (reported, not netted); bracket "
                       "active from release-5s; entry = window VWAP"}, indent=1))
    print(f"\nwrote {dest}/d4_events_{inst}.csv, d4_result_{inst}.json")
    return 0 if (v1_bad == 0 and v3_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
