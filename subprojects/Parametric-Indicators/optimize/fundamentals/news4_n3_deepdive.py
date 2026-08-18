#!/usr/bin/env python3
"""WS-NEWS4 / N3 (#137) — the partially-tested deep-dives.

Implements `docs/NEWS4-N3-PREREGISTRATION.md` (commit 70f29fc, filed before any run):
8 confirmatory tests at Bonferroni α = 0.05/8 — Retail anti-premium (NQ/RTY), Durables
powered-null (NQ/RTY), EIA + API at the deployed spec (CL), the deployed set on ES/GC.
All machinery (frozen ride, jump gate, controls, noise check, verdict ladder) is imported
from news4_premium_scan / the parity-proven executor — nothing re-implemented.

    python3 news4_n3_deepdive.py --instrument NQ  --bars-1s .../NQ_1s.csv
    python3 news4_n3_deepdive.py --instrument CL  --bars-1s .../CL_1s.csv
    python3 news4_n3_deepdive.py --instrument ES  --bars-1s .../ES_1s.csv   (GC likewise)

Outputs: news4_n3_blocks_{INST}.csv · news4_n3_events_{INST}.csv · news4_n3_result_{INST}.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))

from src.deploy.release_executor import LEAD_S, EXIT_S, Leg, load_1s_windows, run_bracket  # noqa: E402
import tv_calendar                                                                          # noqa: E402
from news4_premium_scan import (                                                            # noqa: E402
    MIN_YEAR, N_PLACEBO, NOISE_PCTL, SEED, WINDOW_S, DEPLOYED_TITLES, JUMP_RATIO,
    control_days, mde_usd, minute_jump, ride_all, t_test_mean,
)

ALPHA_N3 = 0.05 / 8
MDE_LINE_USD = 150.0            # declared, not derived, for ES/GC/CL (see pre-reg blind spot 1)

# per-instrument constants, the deployed formula: stressed = 2.50 + 4 * tick_usd, once per event
PV_X = {"NQ": 20.0, "RTY": 50.0, "ES": 50.0, "GC": 100.0, "CL": 1000.0}
COST_X = {"NQ": 22.50, "RTY": 22.50, "ES": 52.50, "GC": 42.50, "CL": 42.50}

# test -> (instrument, block title or DEPLOYED-SET, two_sided_negative_allowed)
TESTS = {
    "NQ": [("Retail Sales MoM", True), ("Durable Goods Orders MoM", False)],
    "RTY": [("Retail Sales MoM", True), ("Durable Goods Orders MoM", False)],
    "CL": [("EIA Crude Oil Stocks Change", False), ("API Crude Oil Stock Change", False)],
    "ES": [("DEPLOYED-SET", False)],
    "GC": [("DEPLOYED-SET", False)],
}
DESCRIPTIVE = {"ES": ["Inflation Rate MoM"], "GC": ["Inflation Rate MoM"]}


def block_moments(cal: pd.DataFrame, title: str, data_end: pd.Timestamp) -> list[pd.Timestamp]:
    """A tested-title block: its own minutes, WITHOUT the covered-minute exclusion (it IS the
    tested title) but WITH the deployed-window-overlap exclusion (pre-reg N3)."""
    cal = cal[(cal.event_et.dt.year >= MIN_YEAR) & (cal.event_et <= data_end)].copy()
    cal["minute"] = cal.event_et.dt.floor("min")
    if title == "DEPLOYED-SET":
        sched = pd.read_csv(REPO / "src" / "deploy" / "data" / "release_schedule.csv")
        sched = sched[sched.status == "confirmed"]
        sched["et"] = pd.to_datetime(sched.et)
        return sorted(sched[(sched.et.dt.year >= MIN_YEAR) & (sched.et <= data_end)].et)
    deployed_ts = np.sort(cal[cal.title.isin(DEPLOYED_TITLES)]["minute"].unique())
    out = []
    for m in sorted(set(cal[cal.title == title]["minute"])):
        i = np.searchsorted(deployed_ts, np.datetime64(m))
        near = ([deployed_ts[i - 1]] if i > 0 else []) + \
               ([deployed_ts[i]] if i < len(deployed_ts) else [])
        if any(abs((np.datetime64(m) - t) / np.timedelta64(1, "s")) < WINDOW_S for t in near):
            continue
        out.append(pd.Timestamp(m))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=list(TESTS))
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--out-dir", default=str(HERE))
    a = ap.parse_args()
    inst, bars_path = a.instrument, Path(a.bars_1s)
    pv, cost = PV_X[inst], COST_X[inst]

    with bars_path.open("rb") as f:
        f.seek(-4096, 2)
        data_end = pd.Timestamp(f.read().splitlines()[-1].split(b",")[0].decode())
    print(f"N3 {inst}: bars end {data_end}; pv {pv} stressed ${cost}/event; "
          f"alpha {ALPHA_N3}; pre-reg 70f29fc")

    cal = tv_calendar.load()
    titles = [t for t, _ in TESTS[inst]] + DESCRIPTIVE.get(inst, [])
    blocks = []
    for title in titles:
        mom = block_moments(cal, title, data_end)
        confirmatory = title in [t for t, _ in TESTS[inst]]
        blocks.append({"anchor": title, "moments": mom, "confirmatory": confirmatory,
                       "two_sided_neg": dict(TESTS[inst]).get(title, False)})
        print(f"  block {title}: {len(mom)} moments{'' if confirmatory else ' (descriptive)'}")

    clocks = {}
    for b in blocks:
        cser = pd.Series([m.strftime("%H:%M") for m in b["moments"]])
        b["clock"] = cser.value_counts().idxmax() if len(cser) else ""
    ctrl = {c: control_days(cal, c, data_end)
            for c in sorted({b["clock"] for b in blocks if b["clock"]})}

    windows = []
    for b in blocks:
        windows += [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=EXIT_S + 5))
                    for t in b["moments"]]
    for c, days in ctrl.items():
        windows += [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=EXIT_S + 5))
                    for t in days]
    bars = load_1s_windows(bars_path, windows)
    print(f"1s bars loaded: {len(bars):,}")
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))

    ctrl_ride = {c: ride_all(idx, op, hi, lo, cl, d, pv, f"CTRL@{c}") for c, d in ctrl.items()}
    ctrl_jump = {c: minute_jump(idx, op, cl, d) for c, d in ctrl.items()}

    rng = np.random.default_rng(SEED)
    rows, frames = [], []
    for b in blocks:
        ev = ride_all(idx, op, hi, lo, cl, b["moments"], pv, b["anchor"])
        if not len(ev):
            rows.append({"anchor": b["anchor"], "n_filled": 0, "verdict": "NO-DATA"})
            continue
        ev["block"] = b["anchor"]
        frames.append(ev)
        g = ev.pnl_usd.to_numpy()
        net = g - cost
        t_stat, p = t_test_mean(net)
        half = len(ev) // 2
        h1, h2 = g[:half].mean(), g[half:].mean()
        mde = mde_usd(net, ALPHA_N3)

        ej = minute_jump(idx, op, cl, b["moments"])
        cj = ctrl_jump.get(b["clock"], np.array([]))
        jump_ratio = (np.median(ej) / np.median(cj)) if len(cj) and len(ej) and np.median(cj) > 0 \
            else np.nan
        jump_ok = bool(np.isfinite(jump_ratio) and jump_ratio > JUMP_RATIO)

        cr = ctrl_ride.get(b["clock"], pd.DataFrame())
        ctrl_net = (cr.pnl_usd.to_numpy() - cost) if len(cr) else np.array([])
        _, ctrl_p = t_test_mean(ctrl_net) if len(ctrl_net) > 2 else (0.0, 1.0)
        ctrl_mean = float(ctrl_net.mean()) if len(ctrl_net) else np.nan
        ctrl_is_positive = bool(len(ctrl_net) and ctrl_p < ALPHA_N3 and ctrl_net.mean() > 0)
        floor_ok = bool(len(ctrl_net) and net.mean() > ctrl_mean and not ctrl_is_positive)

        noise_p = np.nan
        if len(ctrl_net) >= 30:
            sims = np.array([ctrl_net[rng.integers(0, len(ctrl_net), len(net))].mean()
                             for _ in range(N_PLACEBO)])
            noise_p = float((sims >= net.mean()).mean())
        noise_ok = bool(np.isfinite(noise_p) and noise_p < (1 - NOISE_PCTL / 100))

        alpha = ALPHA_N3 if b["confirmatory"] else 0.05
        if not jump_ok:
            verdict = "VOID-TIMESTAMP"
        elif p < alpha and net.mean() > 0 and h1 > 0 and h2 > 0 and floor_ok and noise_ok:
            verdict = "CONFIRMED" if b["confirmatory"] else "DESCRIPTIVE-POSITIVE"
        elif b["two_sided_neg"] and p < alpha and g.mean() < 0 and h1 < 0 and h2 < 0:
            verdict = "CONFIRMED-NEGATIVE"      # gross negative + both halves negative (pre-reg)
        elif p >= alpha and mde <= MDE_LINE_USD:
            verdict = "POWERED-NULL"
        elif p >= alpha:
            verdict = "UNDERPOWERED"
        else:
            verdict = ("FAILED-GATES" if net.mean() > 0 else "COST-DRAG-NEGATIVE"
                       if g.mean() > -cost else "SIGNIFICANT-NEGATIVE") + f" (p={p:.2g})"

        rows.append({"anchor": b["anchor"], "confirmatory": b["confirmatory"],
                     "clock": b["clock"], "n_filled": len(ev),
                     "gross_mean": g.mean(), "net_stressed_mean": net.mean(),
                     "t": t_stat, "p": p, "alpha": alpha,
                     "half1_gross": h1, "half2_gross": h2, "mde_usd": mde,
                     "jump_ratio": jump_ratio, "jump_ok": jump_ok,
                     "ctrl_mean_net": ctrl_mean, "ctrl_p": ctrl_p, "floor_ok": floor_ok,
                     "noise_p": noise_p, "noise_ok": noise_ok, "verdict": verdict})
        print(f"  {b['anchor'][:38]:<38} n={len(ev):>4} gross ${g.mean():+8.2f} "
              f"net ${net.mean():+8.2f} p={p:.3g} jump {jump_ratio:.2f} -> {verdict}")

    out = Path(a.out_dir)
    pd.DataFrame(rows).to_csv(out / f"news4_n3_blocks_{inst}.csv", index=False)
    if frames:
        pd.concat(frames).to_csv(out / f"news4_n3_events_{inst}.csv", index=False)
    manifest = {"instrument": inst, "prereg_commit": "70f29fc", "seed": SEED,
                "pv": pv, "cost_stressed": cost, "alpha": ALPHA_N3,
                "data_end": str(data_end),
                "verdicts": {r["anchor"]: r["verdict"] for r in rows}}
    (out / f"news4_n3_result_{inst}.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest["verdicts"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
