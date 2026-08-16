"""WS-NEWS3 M3 (#117, parent #124) — the release-second STRADDLE, finally tested.

The owner's proposal (recorded verbatim in #117's body): at the crazy-volatility release moment,
enter long AND short with a small stop and a big take-profit, so the move pays one leg whichever
way it goes. It was recommended against in the WS-NEWS2 closeout WITHOUT an experiment — this is
the experiment. Everything structural is pre-registered in #117 (2026-08-16) BEFORE this first ran.

WHAT M1/M2 ALREADY PIN DOWN (inherited, not re-derived):
  · the premium is LONG-side only (short legs PAY it)          -> the long-only arm exists
  · targets: CPI/NFP/FOMC on NQ+RTY; EIA on CL as the NO-PREMIUM CONTROL instrument
  · a 5-minute lead reaches the release alive (97% @0.20% NQ)  -> entry at release-300s
  · threat model: 94% of stop-outs are 1-SECOND sweeps         -> both-legs-stopped is a headline

EXECUTION MODEL (fixed in the pre-registration):
  entry   close of the 1-second bar at (release - 300s), both arms
  stop    fill = worse of (line, bar open)          [GAP-01]
  TP      resting limit: fill = better of (line, bar open)
  ⚠️ if one 1-second bar breaches BOTH a leg's stop and TP -> counts as STOPPED (pessimistic)
  exit    any leg still open at (release + 900s) closes at that bar's close
  costs   per LEG $2.50 + {1,2,4} ticks; a straddle pays TWO legs. STRESSED leads all reporting.

PRIMARY (one test): STRADDLE S=0.10% P=0.40%, NQ pooled {CPI,NFP,FOMC}, net(stressed) > 0,
one-sided t, alpha=0.05. All else descriptive; any other significance needs alpha/54 AND
sign-consistency on a chronological half split.

    WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 optimize/fundamentals/p3_straddle.py --instrument NQ
    ... --v1     # long-only S=0.20% P=inf on P1's FULL 5-series set must reproduce P1's +$84.24 (±$15)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE))

from p1_ride_through import (PV, TICK_USD, COST_SCEN, COMMISSION,  # noqa: E402
                             load_tv_events, draw_controls)

LEAD_S = 300
EXIT_S = 900
STOPS = [0.05, 0.10, 0.20]          # % of price
TPS = [0.20, 0.40, np.inf]          # % of price; inf = no take-profit
TARGET_SERIES = {"NQ": ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"],
                 "RTY": ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"],
                 "CL": ["EIA Crude Oil Stocks Change"]}
PRIMARY = dict(arm="straddle", stop=0.10, tp=0.40, instrument="NQ")


def leg_pnl(op, hi, lo, cl, i0, i_rel, i1, entry, direction, stop_lvl, tp_lvl):
    """One leg walked bar by bar. Returns (pnl_points, outcome, exit_offset_s_from_entry_bar)."""
    for b in range(i0, i1 + 1):
        if direction == "long":
            hit_sl = lo[b] <= stop_lvl
            hit_tp = np.isfinite(tp_lvl) and hi[b] >= tp_lvl
        else:
            hit_sl = hi[b] >= stop_lvl
            hit_tp = np.isfinite(tp_lvl) and lo[b] <= tp_lvl
        if hit_sl:                                    # ⚠️ both-in-one-bar -> STOP (pessimistic)
            fill = (min(op[b], stop_lvl) if direction == "long" else max(op[b], stop_lvl))
            pnl = (fill - entry) if direction == "long" else (entry - fill)
            return pnl, ("stopped_pre" if b < i_rel else "stopped_post"), b - i0
        if hit_tp:
            fill = (max(op[b], tp_lvl) if direction == "long" else min(op[b], tp_lvl))
            pnl = (fill - entry) if direction == "long" else (entry - fill)
            return pnl, "tp", b - i0
    pnl = (cl[i1] - entry) if direction == "long" else (entry - cl[i1])
    return pnl, "timed", i1 - i0


def simulate(bars: pd.DataFrame, events: pd.DataFrame, inst: str, label: str) -> pd.DataFrame:
    """Per event x (stop, tp): both single legs + the straddle, on 1-second bars."""
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
    rows = []
    for _, e in events.iterrows():
        t_rel = np.datetime64(pd.Timestamp(e.et))
        i_ent = int(np.searchsorted(idx, t_rel - np.timedelta64(LEAD_S, "s"), side="right")) - 1
        i_rel = int(np.searchsorted(idx, t_rel, side="left"))
        i_end = int(np.searchsorted(idx, t_rel + np.timedelta64(EXIT_S, "s"), side="right")) - 1
        # the entry bar must actually be near release-300s and the window must be populated
        if i_ent < 0 or i_end <= i_ent or i_rel <= i_ent or i_end >= len(idx):
            continue
        if abs((pd.Timestamp(idx[i_ent]) - (pd.Timestamp(e.et) - pd.Timedelta(seconds=LEAD_S)))
               .total_seconds()) > 60:
            continue
        entry = cl[i_ent]
        if not np.isfinite(entry) or entry <= 0:
            continue
        for S in STOPS:
            dS = entry * S / 100.0
            for P in TPS:
                dP = entry * P / 100.0 if np.isfinite(P) else np.inf
                L = leg_pnl(op, hi, lo, cl, i_ent + 1, i_rel, i_end, entry, "long",
                            entry - dS, entry + dP if np.isfinite(dP) else np.inf)
                Sh = leg_pnl(op, hi, lo, cl, i_ent + 1, i_rel, i_end, entry, "short",
                             entry + dS, entry - dP if np.isfinite(dP) else -np.inf)
                rows.append({"set": label, "instrument": inst, "et": str(e.et), "title": e.title,
                             "stop": S, "tp": (P if np.isfinite(P) else 0.0),
                             "long_usd": L[0] * PV[inst], "long_outcome": L[1], "long_t": L[2],
                             "short_usd": Sh[0] * PV[inst], "short_outcome": Sh[1], "short_t": Sh[2],
                             "straddle_usd": (L[0] + Sh[0]) * PV[inst],
                             "both_stopped": L[1].startswith("stopped") and Sh[1].startswith("stopped")})
    return pd.DataFrame(rows)


def costs(inst: str) -> dict:
    return {k: COMMISSION + t * TICK_USD[inst] for k, t in COST_SCEN.items()}


def cell_stats(x: np.ndarray, cost_per_event: float) -> dict:
    n = len(x)
    m = float(np.mean(x))
    se = float(np.std(x, ddof=1) / np.sqrt(n)) if n > 2 else np.nan
    return {"n": n, "gross": m, "ci_lo": m - 1.96 * se, "ci_hi": m + 1.96 * se,
            "net_stressed": m - cost_per_event, "mde": 2.80 * se}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", default="NQ", choices=["NQ", "RTY", "CL"])
    ap.add_argument("--v1", action="store_true",
                    help="long-only S=0.20 P=inf on P1's FULL series set; must match P1 within $15")
    a = ap.parse_args()
    inst = a.instrument

    from scipy import stats
    from optimize.fundamentals.extended_data import load_1s_windows

    ev = load_tv_events(inst)
    if not a.v1:
        ev = ev[ev.title.isin(TARGET_SERIES[inst])].reset_index(drop=True)
    print("=" * 100)
    print(f"WS-NEWS3 M3 (#117) — the release-second straddle, {inst}"
          + ("  [V1 MODE: P1 full series set]" if a.v1 else ""))
    print("=" * 100)
    print(f"  events {len(ev)} · series {sorted(ev.title.unique())} · lead {LEAD_S}s · exit +{EXIT_S}s")
    print(f"  grid stops {STOPS}% x TPs {TPS}% · costs/leg {costs(inst)} (straddle pays 2 legs)")

    ctrl = draw_controls(pd.DatetimeIndex(ev.et), pd.Timestamp("2016-01-01"),
                         pd.Timestamp("2026-07-31"), seed=20260822)
    print(f"  control timestamps: {len(ctrl)} (full-calendar-clean, same clock minute)")

    def windows(stamps):
        return [(pd.Timestamp(t) - pd.Timedelta(seconds=LEAD_S + 60),
                 pd.Timestamp(t) + pd.Timedelta(seconds=EXIT_S + 5)) for t in stamps]

    bars = load_1s_windows(windows(list(ev.et) + list(ctrl)), instrument=inst)
    print(f"  1s bars loaded: {len(bars):,}")

    E = simulate(bars, ev, inst, "RELEASES")
    C = simulate(bars, pd.DataFrame({"et": ctrl, "title": "CTRL"}), inst, "CONTROL")
    out_csv = HERE / f"p3_events_{inst}{'_v1' if a.v1 else ''}.csv"
    pd.concat([E, C]).to_csv(out_csv, index=False)

    if a.v1:
        cell = E[(E.stop == 0.20) & (E.tp == 0.0)]
        m = float(cell.long_usd.mean())
        ref = 84.24                              # P1's 1-minute pipeline, same trade, same events
        ok = abs(m - ref) <= 15.0 and m > 0
        print(f"\nV1: 1s long-only S=0.20% P=inf mean ${m:+.2f} vs P1 1m ${ref:+.2f} "
              f"-> {'PASS' if ok else 'FAIL'} (n={cell.shape[0]})")
        (HERE / f"p3_v1_{inst}.json").write_text(json.dumps(
            {"mean_1s": m, "ref_1m": ref, "n": int(cell.shape[0]), "pass": bool(ok)}, indent=1))
        return 0 if ok else 1

    ccost = costs(inst)["stressed"]
    out: dict = {"instrument": inst, "n_events": int(ev.shape[0]), "n_controls": len(ctrl),
                 "lead_s": LEAD_S, "exit_s": EXIT_S, "costs_per_leg": costs(inst), "cells": []}

    # ---- V2 — the release-second physics ---------------------------------------------------------
    idx = bars["Date"].to_numpy()
    cl_ = bars["Close"].to_numpy(float)
    fracs = []
    for t in ev.et:
        t0 = np.datetime64(pd.Timestamp(t))
        i_r = int(np.searchsorted(idx, t0, side="left")) - 1
        i60 = int(np.searchsorted(idx, t0 + np.timedelta64(60, "s"), side="right")) - 1
        i900 = int(np.searchsorted(idx, t0 + np.timedelta64(EXIT_S, "s"), side="right")) - 1
        if i_r < 0 or i900 >= len(idx) or i900 <= i60 or i60 <= i_r:
            continue
        full = abs(cl_[i900] - cl_[i_r])
        first = abs(cl_[i60] - cl_[i_r])
        if full > 0:
            fracs.append(min(first / full, 3.0))
    v2_frac = float(np.mean(fracs))
    v2_pass = v2_frac > 0.5
    out["v2_first60s_fraction"] = {"mean": v2_frac, "n": len(fracs), "pass": bool(v2_pass)}
    print(f"\n  V2 · first 60s carry {v2_frac:.2f} of the +{EXIT_S}s |move| on average "
          f"(n={len(fracs)}) -> {'PASS' if v2_pass else 'FAIL'}")

    # ---- V3 — the straddle must NOT pay at control minutes ---------------------------------------
    cc = C[(C.stop == PRIMARY["stop"]) & (C.tp == PRIMARY["tp"])]
    x = cc.straddle_usd.to_numpy()
    t3 = stats.ttest_1samp(x, 0.0)
    p3_1s = t3.pvalue / 2 if t3.statistic > 0 else 1 - t3.pvalue / 2
    v3_pass = p3_1s > 0.05
    out["v3_control_straddle"] = {"gross": float(x.mean()), "one_sided_p": float(p3_1s),
                                  "n": int(len(x)), "pass": bool(v3_pass)}
    print(f"  V3 · control straddle gross ${x.mean():+.2f} (1-sided p={p3_1s:.3f}, n={len(x)}) "
          f"-> {'PASS (no phantom pay)' if v3_pass else 'FAIL — pipeline artefact, VOID'}")

    # ---- the cells -------------------------------------------------------------------------------
    print(f"\n  {'arm':>9} {'S%':>5} {'TP%':>5} {'n':>4} {'gross':>9} {'95% CI':>20} "
          f"{'net(str.)':>10} {'bothStop':>8} {'MDE':>7}")
    half = pd.Timestamp(sorted(E.et)[len(E) // 2])
    for arm, col, cost_mult in (("straddle", "straddle_usd", 2), ("long", "long_usd", 1)):
        for S in STOPS:
            for P in [0.20, 0.40, 0.0]:
                cell = E[(E.stop == S) & (E.tp == P)]
                st = cell_stats(cell[col].to_numpy(), ccost * cost_mult)
                st.update(arm=arm, stop=S, tp=P,
                          both_stopped=float(cell.both_stopped.mean()),
                          first_half_gross=float(cell[pd.to_datetime(cell.et) < half][col].mean()),
                          second_half_gross=float(cell[pd.to_datetime(cell.et) >= half][col].mean()))
                out["cells"].append(st)
                print(f"  {arm:>9} {S:>5.2f} {P:>5.2f} {st['n']:>4} {st['gross']:>+9.2f} "
                      f"[{st['ci_lo']:>+8.2f},{st['ci_hi']:>+8.2f}] {st['net_stressed']:>+10.2f} "
                      f"{st['both_stopped']:>7.1%} {st['mde']:>7.2f}")

    # ---- the PRIMARY -----------------------------------------------------------------------------
    if inst == PRIMARY["instrument"]:
        cell = E[(E.stop == PRIMARY["stop"]) & (E.tp == PRIMARY["tp"])]
        x = cell.straddle_usd.to_numpy() - 2 * ccost
        t1 = stats.ttest_1samp(x, 0.0)
        p1s = t1.pvalue / 2 if t1.statistic > 0 else 1 - t1.pvalue / 2
        out["primary"] = {"net_stressed_mean": float(x.mean()), "t": float(t1.statistic),
                          "one_sided_p": float(p1s), "n": int(len(x)),
                          "pass": bool(p1s < 0.05 and x.mean() > 0)}
        print(f"\n  ⭐ PRIMARY (straddle S=0.10 TP=0.40, net stressed): ${x.mean():+.2f}/event "
              f"t={t1.statistic:+.2f} 1-sided p={p1s:.4f} n={len(x)} -> "
              f"{'POSITIVE — CONFIRMED' if out['primary']['pass'] else 'NOT POSITIVE'}")

    dest = HERE / f"p3_result_{inst}.json"
    dest.write_text(json.dumps(out, indent=1, default=str))
    print(f"\nwrote {out_csv.name}, {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
