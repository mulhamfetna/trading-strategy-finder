#!/usr/bin/env python3
"""FU-8 (#160) — the Retail short. Implements docs/FU8-PREREGISTRATION.md (frozen).

Frozen mirrored spec (SHORT rel−300s, S 0.10 worse-of, TP 0.40 better-of, tie⇒STOP,
exit +900s) on Retail events (FU-9 frozen list) over NQ/RTY/ES/YM; LONG parity anchor vs
FU-9's stored rides; pooled NQ+RTY decision, era halves, ES/YM sign witnesses.

    python3 optimize/fundamentals/fu8_retail_short.py
"""
from __future__ import annotations

import os

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PI_ROOT = HERE.parents[1]
REPO = PI_ROOT.parents[1]
for p_ in (str(PI_ROOT), str(HERE), str(REPO)):
    sys.path.insert(0, p_)

from src.deploy.release_executor import (COST_PER_LEG, PV, Leg,    # noqa: E402
                                         load_1s_windows, run_bracket, LEAD_S, EXIT_S)

INSTS = ["NQ", "RTY", "ES", "YM"]
RETAIL = "Retail Sales MoM"
N_BOOT, SEED = 10000, 20260820
BARS_1S = os.environ.get("WSH_16Y_ROOT", "") + "/{i}_Continuous_Data/{i}_1s.csv"


def retail_events(inst: str) -> pd.DataFrame:
    d = pd.read_csv(HERE / f"fu9_event_state_{inst}.csv", parse_dates=["et"],
                    usecols=["et", "title", "ride_pnl_usd"])
    return d[d.title == RETAIL].sort_values("et").reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    print(f"[FU-8] pre-reg docs/FU8-PREREGISTRATION.md · frozen mirrored spec · "
          f"insts {INSTS} · N_BOOT={N_BOOT} SEED={SEED}", flush=True)
    rng = np.random.default_rng(SEED)
    per = {}
    prim = []          # pooled NQ+RTY per-event short net
    prim_et = []
    for inst in INSTS:
        ev = retail_events(inst)
        windows = [(t - pd.Timedelta(seconds=LEAD_S + 60),
                    t + pd.Timedelta(seconds=EXIT_S + 5)) for t in ev.et]
        bars = load_1s_windows(Path(BARS_1S.format(i=inst)), windows)
        idx = bars["Date"].to_numpy()
        op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))
        longs = np.full(len(ev), np.nan)
        shorts = np.full(len(ev), np.nan)
        for i, r in ev.iterrows():
            fl = run_bracket(idx, op, hi, lo, cl, pd.Timestamp(r.et), Leg("long", 1),
                             PV[inst], r.title)
            fs = run_bracket(idx, op, hi, lo, cl, pd.Timestamp(r.et), Leg("short", 1),
                             PV[inst], r.title)
            if fl is not None:
                longs[i] = fl.pnl_usd
            if fs is not None:
                shorts[i] = fs.pnl_usd
        # parity anchor: LONG must equal FU-9's stored ride to the cent
        stored = ev.ride_pnl_usd.to_numpy(float)
        both = np.isfinite(longs) & np.isfinite(stored)
        mx = float(np.nanmax(np.abs(longs[both] - stored[both]))) if both.any() else np.inf
        if not (both.sum() and mx < 0.01):
            print(f"[FU-8] ABORT {inst}: LONG parity vs FU-9 broken (n={both.sum()}, "
                  f"max|Δ| {mx})", flush=True)
            return 1
        oks = np.isfinite(shorts)
        net = shorts[oks] - COST_PER_LEG[inst]["stressed"]
        gross_mean = float(np.mean(shorts[oks]))
        per[inst] = {"events": int(oks.sum()), "parity_n": int(both.sum()),
                     "short_gross_mean": round(gross_mean, 2),
                     "short_net_mean": round(float(np.mean(net)), 2),
                     "short_net_total": round(float(np.sum(net)), 2),
                     "long_gross_mean": round(float(np.mean(longs[oks])), 2)}
        print(f"[FU-8] {inst}: parity PASS ({both.sum()}ev) · short gross/ev "
              f"{gross_mean:+,.2f} net/ev {per[inst]['short_net_mean']:+,.2f} "
              f"total {per[inst]['short_net_total']:+,.0f} · (long gross/ev "
              f"{per[inst]['long_gross_mean']:+,.2f})", flush=True)
        if inst in ("NQ", "RTY"):
            prim.extend(net.tolist())
            prim_et.extend(ev.et.to_numpy()[oks].tolist())

    prim = np.array(prim)
    order = np.argsort(np.array(prim_et))
    prim_sorted = prim[order]
    ets_sorted = np.array(prim_et)[order]
    mean = float(prim.mean())
    boots = np.array([prim[rng.integers(0, len(prim), len(prim))].mean()
                      for _ in range(N_BOOT)])
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))
    mid = ets_sorted[len(ets_sorted) // 2]
    eras = {"h1": round(float(prim_sorted[ets_sorted < mid].mean()), 2),
            "h2": round(float(prim_sorted[ets_sorted >= mid].mean()), 2),
            "split": str(pd.Timestamp(mid).date())}
    sd = float(prim.std(ddof=1))
    mde = float(1.645 * sd / np.sqrt(len(prim)))
    witnesses_pos = all(per[i]["short_net_mean"] > 0 for i in ("ES", "YM"))
    if mean > 0 and ci[0] > 0 and eras["h1"] > 0 and eras["h2"] > 0 and witnesses_pos:
        verdict = "ARMED-FORWARD"
    else:
        verdict = "CLOSED"
    res = {"per_instrument": per,
           "primary_pool_nq_rty": {"n": int(len(prim)), "net_mean": round(mean, 2),
                                   "boot90_ci": [round(ci[0], 2), round(ci[1], 2)],
                                   "eras": eras},
           "power": {"sd_event_net": round(sd, 2), "mde_mean": round(mde, 2)},
           "witnesses_es_ym_positive": bool(witnesses_pos),
           "forward_protocol": {"events": 12, "rule": "pooled NQ+RTY net>0 AND >=7/12 "
                                "events with the descriptive mean's sign"},
           "verdict": verdict}
    (Path(a.out) / "fu8_result.json").write_text(json.dumps(res, indent=2))
    print(f"[FU-8] PRIMARY NQ+RTY net/ev {mean:+,.2f} CI90 [{ci[0]:,.2f},{ci[1]:,.2f}] "
          f"(n={len(prim)}) eras {eras} · ES/YM positive: {witnesses_pos} · MDE "
          f"{mde:,.2f} -> VERDICT {verdict}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
