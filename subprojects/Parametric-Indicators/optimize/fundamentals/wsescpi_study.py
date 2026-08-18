#!/usr/bin/env python3
"""WS-ESCPI (#139) — the ES CPI-alone ride: YM-holdout confirmation + ES robustness.

Implements `docs/WS-ESCPI-PREREGISTRATION.md` (commit 051ff07, filed BEFORE the YM 1-second
file was ever opened). Machinery imported from the parity-proven executor and the N2/N3
runners — nothing re-implemented.

    python3 wsescpi_study.py --instrument YM --bars-1s .../YM_1s.csv     # the holdout
    python3 wsescpi_study.py --instrument ES --bars-1s .../ES_1s.csv     # robustness battery

Outputs: wsescpi_blocks_{INST}.csv · wsescpi_events_{INST}.csv · wsescpi_result_{INST}.json
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

from src.deploy.release_executor import LEAD_S, EXIT_S, load_1s_windows  # noqa: E402
import tv_calendar                                                        # noqa: E402
from news4_premium_scan import (                                          # noqa: E402
    MIN_YEAR, N_PLACEBO, NOISE_PCTL, SEED, JUMP_RATIO,
    control_days, mde_usd, minute_jump, ride_all, t_test_mean,
)
from news4_n3_deepdive import block_moments                               # noqa: E402

ALPHA = 0.01                    # pre-registered, two-sided, primary YM test
MDE_LINE_USD = 150.0
PV_X = {"YM": 5.0, "ES": 50.0}
COST_X = {"YM": 22.50, "ES": 52.50}     # 2.50 + 4 * tick_usd (YM tick $5, ES $12.50)
COVERAGE_MIN_SECONDS = 150      # data-quality gate: traded seconds required in [rel-300, rel)
COVERAGE_MIN_FRAC = 0.70


def cpi_schedule_events(data_end: pd.Timestamp) -> list[pd.Timestamp]:
    """The SAME 116 CPI events the ES observation was measured on: the deployed schedule's
    confirmed 'Inflation Rate MoM' rows (>=2016, within data)."""
    sched = pd.read_csv(REPO / "src" / "deploy" / "data" / "release_schedule.csv")
    sched = sched[(sched.status == "confirmed") & (sched.title == "Inflation Rate MoM")]
    sched["et"] = pd.to_datetime(sched.et)
    return sorted(sched[(sched.et.dt.year >= MIN_YEAR) & (sched.et <= data_end)].et)


def coverage(idx, moments) -> tuple[float, int]:
    """Fraction of events whose pre-release window [rel-300, rel) has >= COVERAGE_MIN_SECONDS
    traded seconds (the 0-byte-1m YM warning made this gate mandatory)."""
    good = total = 0
    for t in moments:
        t0 = np.datetime64(t)
        i0 = int(np.searchsorted(idx, t0 - np.timedelta64(LEAD_S, "s"), side="left"))
        i1 = int(np.searchsorted(idx, t0, side="left"))
        total += 1
        if i1 - i0 >= COVERAGE_MIN_SECONDS:
            good += 1
    return (good / total if total else 0.0), total


def battery(idx, op, hi, lo, cl, moments, pv, cost, ctrl_ride, ctrl_jump, rng, tag):
    """The full pre-registered gate battery for one block. Returns (row, events_df)."""
    ev = ride_all(idx, op, hi, lo, cl, moments, pv, tag)
    if not len(ev):
        return {"block": tag, "n_filled": 0, "verdict": "NO-DATA"}, ev
    g = ev.pnl_usd.to_numpy()
    net = g - cost
    t_stat, p = t_test_mean(net)
    half = len(ev) // 2
    h1, h2 = g[:half].mean(), g[half:].mean()
    mde = mde_usd(net, ALPHA)

    ej = minute_jump(idx, op, cl, moments)
    jump_ratio = (np.median(ej) / np.median(ctrl_jump)) \
        if len(ctrl_jump) and len(ej) and np.median(ctrl_jump) > 0 else np.nan
    jump_ok = bool(np.isfinite(jump_ratio) and jump_ratio > JUMP_RATIO)

    ctrl_net = (ctrl_ride.pnl_usd.to_numpy() - cost) if len(ctrl_ride) else np.array([])
    _, ctrl_p = t_test_mean(ctrl_net) if len(ctrl_net) > 2 else (0.0, 1.0)
    ctrl_mean = float(ctrl_net.mean()) if len(ctrl_net) else np.nan
    ctrl_is_positive = bool(len(ctrl_net) and ctrl_p < ALPHA and ctrl_net.mean() > 0)
    floor_ok = bool(len(ctrl_net) and net.mean() > ctrl_mean and not ctrl_is_positive)

    noise_p = np.nan
    if len(ctrl_net) >= 30:
        sims = np.array([ctrl_net[rng.integers(0, len(ctrl_net), len(net))].mean()
                         for _ in range(N_PLACEBO)])
        noise_p = float((sims >= net.mean()).mean())
    noise_ok = bool(np.isfinite(noise_p) and noise_p < (1 - NOISE_PCTL / 100))

    if not jump_ok:
        verdict = "VOID-TIMESTAMP"
    elif p < ALPHA and net.mean() > 0 and h1 > 0 and h2 > 0 and floor_ok and noise_ok:
        verdict = "PASS"
    elif p >= ALPHA and mde <= MDE_LINE_USD:
        verdict = "POWERED-NULL"
    elif p >= ALPHA:
        verdict = "UNDERPOWERED"
    else:
        verdict = f"SIGNIFICANT-{'POSITIVE-FAILED-GATES' if net.mean() > 0 else 'NEGATIVE'} (p={p:.2g})"

    row = {"block": tag, "n_filled": len(ev), "gross_mean": g.mean(),
           "net_stressed_mean": net.mean(), "t": t_stat, "p": p,
           "half1_gross": h1, "half2_gross": h2, "mde_usd": mde,
           "jump_ratio": jump_ratio, "jump_ok": jump_ok,
           "ctrl_mean_net": ctrl_mean, "ctrl_p": ctrl_p, "floor_ok": floor_ok,
           "noise_p": noise_p, "noise_ok": noise_ok, "verdict": verdict}
    ev = ev.assign(block=tag)
    return row, ev


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=list(PV_X))
    ap.add_argument("--bars-1s", required=True)
    ap.add_argument("--out-dir", default=str(HERE))
    a = ap.parse_args()
    inst, bars_path = a.instrument, Path(a.bars_1s)
    pv, cost = PV_X[inst], COST_X[inst]

    with bars_path.open("rb") as f:
        f.seek(-4096, 2)
        data_end = pd.Timestamp(f.read().splitlines()[-1].split(b",")[0].decode())
    print(f"WS-ESCPI {inst}: bars end {data_end}; pv {pv}; stressed ${cost}/event; "
          f"alpha {ALPHA}; pre-reg 051ff07")

    cal = tv_calendar.load()
    cpi = cpi_schedule_events(data_end)
    retail = block_moments(cal, "Retail Sales MoM", data_end)   # the YM falsifier
    print(f"  CPI events (schedule, >=2016): {len(cpi)} · Retail-alone minutes: {len(retail)}")

    ctrl_days = control_days(cal, "08:30", data_end)
    windows = [(t - pd.Timedelta(seconds=LEAD_S + 60), t + pd.Timedelta(seconds=EXIT_S + 5))
               for t in (cpi + retail + ctrl_days)]
    bars = load_1s_windows(bars_path, windows)
    print(f"  1s bars loaded: {len(bars):,}")
    idx = bars["Date"].to_numpy()
    op, hi, lo, cl = (bars[c].to_numpy(float) for c in ("Open", "High", "Low", "Close"))

    # data-quality gate — pre-registered FOR YM specifically (the degenerate-file guard);
    # for ES it is REPORTED, not gating (the ES arm is a robustness battery on known-good
    # data: N3 filled 116 events with a 20x jump ratio there).
    cov, n_cov = coverage(idx, cpi)
    print(f"  pre-release coverage: {cov:.1%} of {n_cov} CPI windows have "
          f">={COVERAGE_MIN_SECONDS} traded seconds")
    if inst == "YM" and cov < COVERAGE_MIN_FRAC:
        manifest = {"instrument": inst, "verdict": "VOID-DATA", "coverage": cov,
                    "prereg_commit": "051ff07"}
        (Path(a.out_dir) / f"wsescpi_result_{inst}.json").write_text(json.dumps(manifest, indent=2))
        print("VOID-DATA — no premium verdict claimable either way (pre-registered gate)")
        return 0

    ctrl_ride = ride_all(idx, op, hi, lo, cl, ctrl_days, pv, "CTRL@08:30")
    ctrl_jump = minute_jump(idx, op, cl, ctrl_days)
    print(f"  control 08:30: rides {len(ctrl_ride)} · jump n {len(ctrl_jump)}")
    rng = np.random.default_rng(SEED)

    rows, frames = [], []
    r_cpi, ev_cpi = battery(idx, op, hi, lo, cl, cpi, pv, cost, ctrl_ride, ctrl_jump, rng,
                            "CPI-alone")
    rows.append(r_cpi)
    frames.append(ev_cpi)
    print(f"  CPI-alone: n={r_cpi.get('n_filled', 0)} net ${r_cpi.get('net_stressed_mean', 0):+.2f} "
          f"p={r_cpi.get('p', 1):.3g} jump {r_cpi.get('jump_ratio', float('nan')):.2f} "
          f"-> {r_cpi['verdict']}")

    r_ret, ev_ret = battery(idx, op, hi, lo, cl, retail, pv, cost, ctrl_ride, ctrl_jump, rng,
                            "Retail-falsifier")
    rows.append(r_ret)
    frames.append(ev_ret)
    print(f"  Retail-falsifier: n={r_ret.get('n_filled', 0)} "
          f"gross ${r_ret.get('gross_mean', 0):+.2f} -> {r_ret['verdict']} "
          f"(pipeline is broken if this is a PASS)")

    # per-year table incl. the owner's 2024->2026 verification window
    ev = ev_cpi.copy()
    ev["year"] = pd.to_datetime(ev.et).dt.year
    per_year = ev.groupby("year").pnl_usd.agg(["count", "mean"]).round(2)
    per_year["net_mean"] = (per_year["mean"] - cost).round(2)
    print("  per-year CPI-alone ($/event):")
    print(per_year.to_string())
    w = ev[ev.year >= 2024]
    w_net = w.pnl_usd - cost
    print(f"  2024->2026 window: n={len(w)} gross ${w.pnl_usd.mean():+.2f} "
          f"net ${w_net.mean():+.2f} total net ${w_net.sum():+,.2f}")

    out = Path(a.out_dir)
    pd.DataFrame(rows).to_csv(out / f"wsescpi_blocks_{inst}.csv", index=False)
    pd.concat(frames).to_csv(out / f"wsescpi_events_{inst}.csv", index=False)
    manifest = {"instrument": inst, "prereg_commit": "051ff07", "seed": SEED,
                "pv": pv, "cost_stressed": cost, "alpha": ALPHA, "coverage": cov,
                "data_end": str(data_end),
                "cpi_verdict": r_cpi["verdict"], "retail_falsifier": r_ret["verdict"],
                "per_year": {str(y): {"n": int(r["count"]), "net_mean": float(r["net_mean"])}
                             for y, r in per_year.iterrows()},
                "window_2024_2026": {"n": int(len(w)), "net_mean": float(w_net.mean()),
                                     "net_total": float(w_net.sum())} if len(w) else {}}
    (out / f"wsescpi_result_{inst}.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({"cpi": r_cpi["verdict"], "retail_falsifier": r_ret["verdict"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
