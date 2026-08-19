"""WS-DEPLOY D3 (#127) — the qty scaling study: 5 / 10 / 20 contracts, NEWS LAYER ONLY.

Owner-approved (2026-08-17) for the same isolated branch, with its own verifications,
pre-registered before this first ran:

  V1  ARITHMETIC — per-event dollars at each qty must equal qty x (qty=1) TO THE CENT, every
      event, both instruments; per-contract points qty-invariant.
  V2  THE MARKET SIDE, measured from data — 1-second files carry per-second traded VOLUME:
      for every event, the volume of the ENTRY second (release-300s, the quiet side) and of the
      EXIT-FILL second (stop/TP, usually the violent side); participation = qty / second-volume.
      What bars cannot see (book depth, queue position) remains a declared blind spot.
  V3  FALSIFIER — exit-fill-second volume must be MATERIALLY higher than entry-second volume
      (the release volume explosion is physics; if absent, the volume alignment is broken: VOID).

    WSH_DATA_BASE=... python3 -m src.deploy.scaling_study --instrument NQ \
        --bars-1s /path/NQ_1s.csv [--floor-year 2024]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .release_executor import (PV, COST_PER_LEG, LEAD_S, Leg, run_bracket,
                               load_1s_windows)
from .schedule import load as load_schedule, DEFAULT_SCHEDULE

QTYS = [1, 5, 10, 20]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=list(PV))
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--schedule", default=str(DEFAULT_SCHEDULE))
    ap.add_argument("--floor-year", type=int, default=2024)
    ap.add_argument("--series", default="",
                    help="comma-separated schedule titles this leg rides (empty = all; "
                         "ES/YM scale on 'Inflation Rate MoM' only — RQ-1/RQ-9, #141/#150)")
    ap.add_argument("--out-dir", default="deploy_out_d3")
    a = ap.parse_args()
    inst = a.instrument
    cost1 = COST_PER_LEG[inst]["stressed"]

    sched = load_schedule(Path(a.schedule))
    ev = sched[(sched.status == "confirmed")
               & (sched.et.dt.year >= a.floor_year)].reset_index(drop=True)
    series = [x.strip() for x in a.series.split(",") if x.strip()]
    if series:                       # RQ-1/RQ-9: a leg may scale on a SUBSET of the schedule
        ev = ev[ev.title.isin(series)].reset_index(drop=True)
    print(f"D3 scaling study · {inst} · {len(ev)} releases {a.floor_year}+ · qty grid {QTYS} · "
          f"stressed cost/leg ${cost1:.2f} (leads, per policy)")

    windows = [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=905))
               for t in ev.et]
    bars = load_1s_windows(Path(a.bars_1s), windows, keep_volume=True)
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    vol = bars["Volume"].to_numpy(float)

    # ---- base replay (qty=1) + fill-second volumes ------------------------------------------------
    rows = []
    for _, r in ev.iterrows():
        f = run_bracket(idx, op, hi, lo, cl, pd.Timestamp(r.et), Leg("long", 1), PV[inst], r.title)
        if f is None:
            continue
        t_rel = np.datetime64(pd.Timestamp(r.et))
        i_ent = int(np.searchsorted(idx, t_rel - np.timedelta64(LEAD_S, "s"), "right")) - 1
        t_exit = t_rel + np.timedelta64(int(round(f.exit_s_from_release)), "s")
        i_exit = int(np.searchsorted(idx, t_exit, "right")) - 1
        rows.append({"et": f.et, "outcome": f.outcome, "pnl_usd_q1": f.pnl_usd,
                     "pnl_points": f.pnl_points, "entry": f.entry,
                     "entry_sec_volume": float(vol[i_ent]),
                     "exit_sec_volume": float(vol[i_exit])})
    d = pd.DataFrame(rows)

    # ---- V1 · arithmetic linearity at every qty, every event, to the cent -------------------------
    v1_bad = 0
    for q in QTYS[1:]:
        got = np.array([run_bracket(idx, op, hi, lo, cl, pd.Timestamp(r.et), Leg("long", q),
                                    PV[inst], r.title).pnl_usd
                        for _, r in ev.iterrows()
                        if run_bracket(idx, op, hi, lo, cl, pd.Timestamp(r.et), Leg("long", q),
                                       PV[inst], r.title) is not None])
        want = d.pnl_usd_q1.to_numpy() * q
        v1_bad += int((np.abs(got - want) > 0.005).sum())
    print(f"\nV1 · linearity: {len(d)} events x qtys {QTYS[1:]} -> "
          f"{v1_bad} mismatches -> {'PASS (to the cent)' if v1_bad == 0 else 'FAIL'}")

    # ---- V3 first (it gates V2's meaning) ---------------------------------------------------------
    med_entry = float(d.entry_sec_volume.median())
    post = d[d.outcome.isin(["tp", "stopped_post"])]
    med_exit = float(post.exit_sec_volume.median())
    v3_ratio = med_exit / med_entry if med_entry > 0 else float("inf")
    v3_pass = v3_ratio > 3.0
    print(f"V3 · volume physics: median entry-second vol {med_entry:.0f} vs median post-release "
          f"fill-second vol {med_exit:.0f} -> {v3_ratio:.1f}x "
          f"-> {'PASS (alignment sane)' if v3_pass else 'FAIL — VOID, volume alignment broken'}")

    # ---- V2 · participation at scale --------------------------------------------------------------
    out_rows = []
    print(f"\nV2 · participation = qty / traded volume in the fill second "
          f"(entry = the quiet side; exit = the violent side)")
    print(f"  {'qty':>4} {'entry p50':>10} {'entry p95':>10} {'exit p50':>9} {'exit p95':>9} "
          f"{'entry>25% share':>16} {'exit>25% share':>15}")
    for q in QTYS:
        pe = q / d.entry_sec_volume.replace(0, np.nan)
        px = q / post.exit_sec_volume.replace(0, np.nan)
        row = {"qty": q,
               "entry_particip_p50": float(pe.median()), "entry_particip_p95": float(pe.quantile(.95)),
               "exit_particip_p50": float(px.median()), "exit_particip_p95": float(px.quantile(.95)),
               "entry_over25pct_share": float((pe > 0.25).mean()),
               "exit_over25pct_share": float((px > 0.25).mean())}
        out_rows.append(row)
        print(f"  {q:>4} {row['entry_particip_p50']:>9.1%} {row['entry_particip_p95']:>9.1%} "
              f"{row['exit_particip_p50']:>8.1%} {row['exit_particip_p95']:>8.1%} "
              f"{row['entry_over25pct_share']:>15.1%} {row['exit_over25pct_share']:>14.1%}")

    # ---- economics & risk at scale (stressed costs lead) ------------------------------------------
    print(f"\nECONOMICS & RISK AT SCALE ({a.floor_year}+, net = stressed ${cost1:.2f}/contract-event)")
    print(f"  {'qty':>4} {'net mean/event':>14} {'net total':>12} {'worst event':>12} "
          f"{'-2R budget/event':>16}")
    econ = []
    med_1r = float((d.entry * 0.0010 * PV[inst]).median())   # nominal 1R $ per contract
    for q in QTYS:
        net = d.pnl_usd_q1 * q - cost1 * q
        worst = float(d.pnl_usd_q1.min() * q - cost1 * q)
        two_r = -2 * med_1r * q                              # the measured-slippage budget rule
        econ.append({"qty": q, "net_mean": float(net.mean()), "net_total": float(net.sum()),
                     "worst_event": worst, "minus_2R_budget": two_r})
        print(f"  {q:>4} {net.mean():>+14.2f} {net.sum():>+12,.0f} {worst:>+12,.0f} {two_r:>+16,.0f}")

    dest = Path(a.out_dir); dest.mkdir(parents=True, exist_ok=True)
    d.to_csv(dest / f"d3_events_{inst}.csv", index=False)
    (dest / f"d3_result_{inst}.json").write_text(json.dumps(
        {"instrument": inst, "floor_year": a.floor_year, "n_events": int(len(d)),
         "qtys": QTYS, "v1_mismatches": v1_bad, "v1_pass": v1_bad == 0,
         "v3_exit_over_entry_volume": v3_ratio, "v3_pass": bool(v3_pass),
         "participation": out_rows, "economics": econ,
         "blind_spot": "book depth and queue position are invisible to bar data; participation "
                       "ratios are the measurable proxy, not a fill guarantee"}, indent=1))
    print(f"\nwrote {dest}/d3_events_{inst}.csv, d3_result_{inst}.json")
    return 0 if (v1_bad == 0 and v3_pass) else 1


if __name__ == "__main__":
    raise SystemExit(main())
