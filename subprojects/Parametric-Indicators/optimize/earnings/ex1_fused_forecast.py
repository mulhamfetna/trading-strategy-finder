#!/usr/bin/env python3
"""E-X1 — earnings × the fused forecast. Implements docs/EX1-PREREGISTRATION.md (frozen).

FU-11 Stage-1 machinery verbatim with the earnings calendar swapped in: does adding
(earn_dummy, earn_power) to the live engine's HAR family beat it on earnings bars?

    WSH_16Y_ROOT=... python3 optimize/earnings/ex1_fused_forecast.py --instrument NQ
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PI_ROOT = HERE.parents[1]
FUND = PI_ROOT / "optimize" / "fundamentals"
for p_ in (str(PI_ROOT), str(FUND)):
    sys.path.insert(0, p_)

from extended_data import load_1m_extended                     # noqa: E402
from volatility import compute_rv_pts                          # noqa: E402
from optimize.fundamentals.fu11_stage1 import (                # noqa: E402
    qlike, build_frame, har_regressors, deployed_har, ols_predict, EPS)

TRAIN_END = pd.Timestamp("2024-01-01")
N_BOOT, N_SHUFFLE, SEED, MINUTES = 2000, 20, 20260820, 60


def earnings_features(inst: str, starts: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    ev = pd.read_csv(HERE / "data" / f"ep1_events_{inst}.csv", parse_dates=["event_et"])
    ev = ev.dropna(subset=["pred"]).reset_index(drop=True)
    n = len(starts)
    dummy = np.zeros(n)
    pw = np.zeros(n)
    et = ev.event_et.to_numpy()
    idx = np.searchsorted(starts, et, side="right") - 1
    dur = np.timedelta64(MINUTES, "m")
    for k, (i, p_) in enumerate(zip(idx, ev.pred.to_numpy(float))):
        if i >= 0 and et[k] < starts[i] + dur and np.isfinite(p_):
            dummy[i] = 1.0
            pw[i] = max(pw[i], p_)
    return dummy, pw, len(ev)


def run(inst: str, out_dir: Path) -> dict:
    print(f"[E-X1] instrument={inst} TRAIN_END={TRAIN_END.date()} N_BOOT={N_BOOT} "
          f"N_SHUFFLE={N_SHUFFLE} SEED={SEED}", flush=True)
    df1 = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    frame = build_frame(df1, MINUTES)
    rv = pd.Series(compute_rv_pts(frame, df1, bar_minutes=MINUTES)).ffill().bfill().to_numpy()
    dates = frame["Date"]
    starts = frame["Date"].to_numpy()
    dummy, pw, n_ev = earnings_features(inst, starts)
    print(f"[E-X1] bars={len(frame):,} scored earnings events={n_ev} "
          f"event bars={int(dummy.sum())}", flush=True)

    y = rv
    Xh = har_regressors(rv)
    valid = np.isfinite(Xh).all(1) & np.isfinite(y)
    train = valid & (dates < TRAIN_END).to_numpy()
    test = valid & (dates >= TRAIN_END).to_numpy()
    evt = test & (dummy > 0)
    print(f"[E-X1] train={train.sum():,} test={test.sum():,} test EARNINGS bars={evt.sum()}",
          flush=True)

    pA = np.maximum(deployed_har(rv), EPS)
    pB, _ = ols_predict(Xh, y, train)
    pC, bC = ols_predict(np.c_[Xh, dummy, pw], y, train)
    pD, _ = ols_predict(np.c_[Xh, dummy], y, train)
    print(f"[E-X1] betas C tail (dummy, power) = {np.round(bC[-2:], 4).tolist()}", flush=True)

    def sc(pred, m):
        return float(np.mean(qlike(y[m], pred[m])))

    scores = {k: {"event": sc(p_, evt), "overall": sc(p_, test)}
              for k, p_ in (("A", pA), ("B", pB), ("C", pC), ("D", pD))}
    dloss = qlike(y[evt], pB[evt]) - qlike(y[evt], pC[evt])
    rng = np.random.default_rng(SEED)
    n = len(dloss)
    boots = np.array([np.mean(dloss[rng.integers(0, n, n)]) for _ in range(N_BOOT)])
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))
    dAC = float(np.mean(qlike(y[evt], pA[evt]) - qlike(y[evt], pC[evt])))

    ev = pd.read_csv(HERE / "data" / f"ep1_events_{inst}.csv", parse_dates=["event_et"])
    ev = ev.dropna(subset=["pred"]).reset_index(drop=True)
    placebo = []
    for s in range(N_SHUFFLE):
        r2 = np.random.default_rng(SEED + 1 + s)
        ev2 = ev.copy()
        ev2["pred"] = r2.permutation(ev.pred.to_numpy())
        et = ev2.event_et.to_numpy()
        idx = np.searchsorted(starts, et, side="right") - 1
        pw_sh = np.zeros(len(starts))
        dur = np.timedelta64(MINUTES, "m")
        for k, (i, p_) in enumerate(zip(idx, ev2.pred.to_numpy(float))):
            if i >= 0 and et[k] < starts[i] + dur and np.isfinite(p_):
                pw_sh[i] = max(pw_sh[i], p_)
        pS, _ = ols_predict(np.c_[Xh, dummy, pw_sh], y, train)
        placebo.append(sc(pS, evt))
    q_pl = float(np.median(placebo))

    gain_C_over_D = scores["D"]["event"] - scores["C"]["event"]
    placebo_gain = scores["D"]["event"] - q_pl
    lines = {
        "1_primary_ci": bool(np.mean(dloss) > 0 and ci[0] > 0 and dAC > 0),
        "3_no_harm": bool(scores["C"]["overall"] <= 1.001 * scores["B"]["overall"]),
        "4_placebo": bool(gain_C_over_D <= 0 or placebo_gain <= 0.5 * gain_C_over_D),
    }
    sd = float(np.std(dloss, ddof=1)) if n > 1 else float("nan")
    res = {"instrument": inst, "n_test_event_bars": int(n), "scores": scores,
           "decision": {"mean_diff_B_minus_C": float(np.mean(dloss)), "boot90_ci": ci,
                        "mean_diff_A_minus_C": dAC},
           "decomposition": {"gain_C_over_D": gain_C_over_D,
                             "placebo_median": q_pl, "placebo_gain_over_D": placebo_gain},
           "lines": lines,
           "power": {"sd_diff": sd,
                     "mde": float(1.645 * sd / np.sqrt(n)) if n > 1 else None}}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"ex1_result_{inst}.json").write_text(json.dumps(res, indent=2))
    print(f"[E-X1] {inst}: event QLIKE A={scores['A']['event']:.4f} B={scores['B']['event']:.4f} "
          f"C={scores['C']['event']:.4f} D={scores['D']['event']:.4f} placebo={q_pl:.4f}",
          flush=True)
    print(f"[E-X1] {inst}: diff(B−C)={np.mean(dloss):+.4f} CI90={ci} lines={lines}", flush=True)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", required=True, choices=["NQ", "ES"])
    ap.add_argument("--out", default=str(HERE / "data"))
    a = ap.parse_args()
    run(a.instrument, Path(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
