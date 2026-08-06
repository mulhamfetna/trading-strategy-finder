"""WS-EARN Stage 4 (#113) — H1: index aggregation lag, on 1-SECOND bars.

PRE-REGISTERED IN #113 BEFORE THIS FILE RAN. The eight cells below are the whole search.

THE HYPOTHESIS
    After a mega-cap earnings release, does NQ keep moving in the direction already established in the
    first few seconds, by enough to pay for the trade?

    Christensen, Timmermann & Veliyev (2025, JFE 167) show on 89+ billion after-hours quotes that price
    discovery on the ANNOUNCING STOCK completes in milliseconds to seconds, and that a post-announcement
    strategy there is insignificant or negative after 2016 once spreads or a 5-second delay apply. They
    document that the market index co-jumps — but never test an INDEX-level strategy.

    The announcing stock has one price to discover. The index has to aggregate one constituent's news
    into a 100-name basket. If a lag exists anywhere in this question, that is where it is.

⚠️ WHY 1-SECOND AND NOT 1-MINUTE. The effect is smaller than one 1-minute bar. By the time a 1-minute
   bar closes the event is over — and a 1-minute OHLC cannot even tell you the ORDER of what happened
   inside it (this project already hit that: the 2025-03-07 payrolls bar went DOWN 46 points and UP 141
   points within the same minute).

🚫 NO PARAMETER OUTSIDE THE PRE-REGISTERED TABLE IS TRIED. Adding one later would silently enlarge the
   search and invalidate the Bonferroni threshold that makes the result meaningful.

    WSH_DATA_BASE=/home/dev/Mulham/wsg-i python3 optimize/earnings/stage4_aggregation_lag.py
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

PV = 20.0                                   # NQ dollars per index point
DELAYS = [5, 10, 30, 60]                    # seconds — pre-registered
HOLDS = [60, 300]                           # seconds — pre-registered
N_CELLS = len(DELAYS) * len(HOLDS)          # 8

COSTS = {"optimistic": 4.50, "realistic": 9.50, "stressed": 14.50}
ALPHA = 0.05
# Bonferroni over the 8 pre-registered cells: alpha/8 = 0.00625 two-sided => |t| > 2.734
BONFERRONI_T = 2.734

PRE = 30                                    # seconds of context loaded before t0
POST = max(DELAYS) + max(HOLDS) + 30        # seconds after t0


def effective_n(times, horizon_s: int) -> int:
    """Events whose [t, t+horizon] ranges overlap are ONE observation (S4-C5)."""
    ts = sorted(times)
    if not ts:
        return 0
    n, end = 1, ts[0]
    for t in ts[1:]:
        if (t - end).total_seconds() > horizon_s:
            n += 1
            end = t
        else:
            end = max(end, t)
    return n


def run_cells(px, events, label, out_rows):
    """px: dict event_index -> pd.Series of 1-second closes indexed by timestamp."""
    import numpy as np

    print(f"\n{'='*100}\n{label}\n{'='*100}")
    print(f"  {'delay':>6} {'hold':>6} {'n':>5} {'n_eff':>6} {'mean $':>10} {'net $':>9} "
          f"{'t':>7} {'pass?':>7}   {'win%':>6}")
    for D in DELAYS:
        for H in HOLDS:
            pnl, keep_t = [], []
            for i, (t0, s) in px.items():
                if s is None or len(s) == 0:
                    continue
                try:
                    p0 = s.asof(t0)
                    pd_ = s.asof(t0 + np.timedelta64(D, "s"))
                    p1 = s.asof(t0 + np.timedelta64(D + H, "s"))
                except Exception:
                    continue
                if any(x != x for x in (p0, pd_, p1)):        # NaN check
                    continue
                sign = 1.0 if pd_ > p0 else (-1.0 if pd_ < p0 else 0.0)
                if sign == 0.0:
                    continue
                pnl.append(sign * (p1 - pd_) * PV)
                keep_t.append(t0)
            if len(pnl) < 10:
                print(f"  {D:>5}s {H:>5}s {len(pnl):>5}      -          -         -       -   too few")
                continue
            a = np.array(pnl, float)
            n_eff = effective_n([__import__("pandas").Timestamp(x) for x in keep_t], D + H)
            gross = a.mean()
            net = gross - COSTS["realistic"]
            t = net / (a.std(ddof=1) / math.sqrt(n_eff)) if a.std(ddof=1) > 0 else 0.0
            ok = (net > 0) and (abs(t) > BONFERRONI_T)
            win = float((a > 0).mean())
            print(f"  {D:>5}s {H:>5}s {len(a):>5} {n_eff:>6} {gross:>10.2f} {net:>9.2f} "
                  f"{t:>7.2f} {'PASS' if ok else 'fail':>7}   {win:>5.1%}")
            out_rows.append({"set": label, "delay_s": D, "hold_s": H, "n": int(len(a)),
                             "n_eff": int(n_eff), "mean_gross_usd": float(gross),
                             "mean_net_usd": float(net), "t": float(t), "pass": bool(ok),
                             "win_rate": win, "sd_usd": float(a.std(ddof=1)),
                             "net_stressed": float(gross - COSTS["stressed"]),
                             "net_optimistic": float(gross - COSTS["optimistic"])})


def main() -> int:
    import numpy as np
    import pandas as pd
    from optimize.fundamentals.extended_data import load_1s_windows

    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=str(DATA / "earnings_timestamps_STUDY12.csv"))
    ap.add_argument("--out", default=str(DATA / "stage4_results.json"))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    df = pd.read_csv(a.events, parse_dates=["event_et"]).sort_values("event_et")
    if a.limit:
        df = df.head(a.limit)

    print("=" * 100)
    print("WS-EARN STAGE 4 (#113) — H1 index aggregation lag, 1-second bars")
    print("=" * 100)
    print(f"  events file      : {Path(a.events).name}  ({len(df)} events)")
    print(f"  pre-registered   : delays {DELAYS}s x holds {HOLDS}s = {N_CELLS} cells (THE WHOLE SEARCH)")
    print(f"  cost (headline)  : ${COSTS['realistic']:.2f} round trip")
    print(f"  threshold        : Bonferroni {N_CELLS} tests, alpha={ALPHA} -> |t| > {BONFERRONI_T}")
    print(f"  prediction filed : ALL EIGHT CELLS FAIL")

    windows = [(t - pd.Timedelta(seconds=PRE), t + pd.Timedelta(seconds=POST))
               for t in df.event_et]
    print(f"\n  loading 1-second bars for {len(windows)} windows "
          f"(-{PRE}s .. +{POST}s each) — one pass over the 7.8 GB archive...")
    sec = load_1s_windows(windows, instrument="NQ", verbose=True)
    print(f"  got {len(sec):,} 1-second bars")

    s_all = pd.Series(sec["Close"].to_numpy(float), index=pd.DatetimeIndex(sec["Date"])).sort_index()

    px = {}
    for i, (_, r) in enumerate(df.iterrows()):
        t0 = pd.Timestamp(r.event_et)
        seg = s_all.loc[t0 - pd.Timedelta(seconds=PRE): t0 + pd.Timedelta(seconds=POST)]
        px[i] = (t0, seg if len(seg) else None)
    covered = sum(1 for v in px.values() if v[1] is not None)
    print(f"  events with 1-second coverage: {covered} / {len(df)}")

    rows: list[dict] = []
    run_cells(px, df, "ALL EVENTS", rows)

    # ---- dumb control (S4-C4): same rule, non-announcement days, matched time-of-day --------------
    rng = np.random.default_rng(20260806)
    real_days = set(pd.DatetimeIndex(df.event_et).normalize())
    # ⚠️ Bound by the ARCHIVE span, not by the span of the loaded event windows. Using the latter
    # rejected almost every candidate for the earliest events (they fall before the first loaded
    # window), which silently shrank the control to a handful of late-dated draws — a control that
    # is not matched to the real sample is not a control.
    span_lo, span_hi = pd.Timestamp("2010-06-07"), pd.Timestamp("2026-07-11")
    ctrl = []
    for t in df.event_et:
        for _ in range(60):
            shift = int(rng.integers(3, 400)) * (1 if rng.random() < 0.5 else -1)
            cand = pd.Timestamp(t) - pd.Timedelta(days=shift)
            if cand.normalize() in real_days or cand < span_lo or cand > span_hi:
                continue
            if cand.weekday() >= 5:                      # markets shut; the real events never are
                continue
            ctrl.append(cand)
            break
    if ctrl:
        cwin = [(t - pd.Timedelta(seconds=PRE), t + pd.Timedelta(seconds=POST)) for t in ctrl]
        print(f"\n  loading control windows ({len(cwin)})...")
        csec = load_1s_windows(cwin, instrument="NQ", verbose=False)
        c_all = pd.Series(csec["Close"].to_numpy(float),
                          index=pd.DatetimeIndex(csec["Date"])).sort_index()
        cpx = {}
        for i, t0 in enumerate(ctrl):
            seg = c_all.loc[t0 - pd.Timedelta(seconds=PRE): t0 + pd.Timedelta(seconds=POST)]
            cpx[i] = (t0, seg if len(seg) else None)
        run_cells(cpx, None, "DUMB CONTROL (non-announcement, time-of-day matched)", rows)

    # ---- era split (validity check, NOT a hypothesis, NOT counted in the 8 cells) -----------------
    for lo, hi, name in ((2010, 2015, "ERA 2010-2015 (paper: edge existed)"),
                         (2016, 2026, "ERA 2016-2026 (paper: edge closed)")):
        sub = {i: v for i, v in px.items() if lo <= v[0].year <= hi}
        if len(sub) >= 20:
            run_cells(sub, None, f"VALIDITY CHECK — {name}", rows)

    Path(a.out).write_text(json.dumps({
        "preregistered": {"delays_s": DELAYS, "holds_s": HOLDS, "cells": N_CELLS,
                          "bonferroni_t": BONFERRONI_T, "costs_usd": COSTS,
                          "prediction": "all eight cells fail"},
        "results": rows,
    }, indent=1))

    main_cells = [r for r in rows if r["set"] == "ALL EVENTS"]
    passed = [r for r in main_cells if r["pass"]]
    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    print(f"  cells passing S4-C1 + S4-C2 : {len(passed)} of {len(main_cells)}")
    if not passed:
        print("  => H1 REJECTED. Null result, as predicted in #113.")
    else:
        print("  => cells passed; S4-C3 (stressed cost) and S4-C4 (control) decide:")
        for r in passed:
            print(f"     delay {r['delay_s']}s hold {r['hold_s']}s  net ${r['mean_net_usd']:.2f} "
                  f"t={r['t']:.2f}  stressed ${r['net_stressed']:.2f}")
    print(f"\nwrote -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
