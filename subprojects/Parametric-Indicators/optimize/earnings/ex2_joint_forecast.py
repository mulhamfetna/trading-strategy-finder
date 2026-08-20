#!/usr/bin/env python3
"""E-X2 — the joint two-calendar forecast. Implements docs/EX2-PREREGISTRATION.md (frozen).

One model, both calendars: HAR-LS + (m_dummy, m_power, e_dummy, e_power) vs the deployed
HAR, HAR-LS, and each single-calendar fused model — scored on macro bars, earnings bars,
their union, and overall.

    WSH_16Y_ROOT=... python3 optimize/earnings/ex2_joint_forecast.py --instrument NQ
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

import p2_power_model as p2                                    # noqa: E402
from p1_ride_through import load_tv_events                     # noqa: E402
from extended_data import load_1m_extended                     # noqa: E402
from volatility import compute_rv_pts                          # noqa: E402
from optimize.fundamentals.fu11_stage1 import (                # noqa: E402
    qlike, build_frame, har_regressors, deployed_har, ols_predict, event_features, EPS)

TRAIN_END = pd.Timestamp("2024-01-01")
N_BOOT, SEED, MINUTES = 2000, 20260820, 60


def macro_terms(inst: str, df1: pd.DataFrame, starts: np.ndarray):
    raw = load_tv_events(inst)
    ev = pd.concat([raw.reset_index(drop=True),
                    p2.realized_moves(df1, pd.DatetimeIndex(raw.et))], axis=1)
    ev = ev.dropna(subset=["jump_pct"]).sort_values("et").reset_index(drop=True)
    ev["et"] = pd.to_datetime(ev.et)
    ev["pred_exp"] = p2.build_predictions(ev, ev.title, trailing=0)
    sc = ev.dropna(subset=["pred_exp"]).reset_index(drop=True)
    return event_features(sc, starts, MINUTES, sc["pred_exp"])


def earn_terms(inst: str, starts: np.ndarray):
    ev = pd.read_csv(HERE / "data" / f"ep1_events_{inst}.csv", parse_dates=["event_et"])
    ev = ev.dropna(subset=["pred"]).rename(columns={"event_et": "et"}).reset_index(drop=True)
    return event_features(ev, starts, MINUTES, ev["pred"])


def run(inst: str, out_dir: Path) -> dict:
    print(f"[E-X2] instrument={inst} TRAIN_END={TRAIN_END.date()} N_BOOT={N_BOOT} "
          f"SEED={SEED}", flush=True)
    df1 = load_1m_extended(inst).sort_values("Date").reset_index(drop=True)
    frame = build_frame(df1, MINUTES)
    rv = pd.Series(compute_rv_pts(frame, df1, bar_minutes=MINUTES)).ffill().bfill().to_numpy()
    dates = frame["Date"]
    starts = frame["Date"].to_numpy()
    m_dum, m_pw = macro_terms(inst, df1, starts)
    e_dum, e_pw = earn_terms(inst, starts)

    y = rv
    Xh = har_regressors(rv)
    valid = np.isfinite(Xh).all(1) & np.isfinite(y)
    train = valid & (dates < TRAIN_END).to_numpy()
    test = valid & (dates >= TRAIN_END).to_numpy()
    mbar = test & (m_dum > 0)
    ebar = test & (e_dum > 0)
    ubar = test & ((m_dum > 0) | (e_dum > 0))
    print(f"[E-X2] test bars={test.sum():,} macro={mbar.sum()} earnings={ebar.sum()} "
          f"union={ubar.sum()} (overlap={int((mbar & ebar).sum())})", flush=True)

    pA = np.maximum(deployed_har(rv), EPS)
    pB, _ = ols_predict(Xh, y, train)
    pCm, _ = ols_predict(np.c_[Xh, m_dum, m_pw], y, train)
    pCe, _ = ols_predict(np.c_[Xh, e_dum, e_pw], y, train)
    pCj, bJ = ols_predict(np.c_[Xh, m_dum, m_pw, e_dum, e_pw], y, train)
    print(f"[E-X2] joint betas (m_dummy,m_pw,e_dummy,e_pw) = "
          f"{np.round(bJ[-4:], 4).tolist()}", flush=True)

    def sc(pred, m):
        return float(np.mean(qlike(y[m], pred[m]))) if m.sum() else float("nan")

    S = {}
    for name, p_ in (("A", pA), ("B", pB), ("Cm", pCm), ("Ce", pCe), ("Cj", pCj)):
        S[name] = {"macro": sc(p_, mbar), "earn": sc(p_, ebar),
                   "union": sc(p_, ubar), "overall": sc(p_, test)}

    dloss = qlike(y[ubar], pB[ubar]) - qlike(y[ubar], pCj[ubar])
    rng = np.random.default_rng(SEED)
    n = len(dloss)
    boots = np.array([np.mean(dloss[rng.integers(0, n, n)]) for _ in range(N_BOOT)])
    ci = (float(np.percentile(boots, 5)), float(np.percentile(boots, 95)))

    lines = {
        "1_no_macro_degradation": bool(S["Cj"]["macro"] <= 1.001 * S["Cm"]["macro"]),
        "2_no_earn_degradation": bool(S["Cj"]["earn"] <= 1.001 * S["Ce"]["earn"]),
        "3_union_ci": bool(np.mean(dloss) > 0 and ci[0] > 0),
        "4_overall_single_best": bool(S["Cj"]["overall"] <= 1.001 * min(
            S["B"]["overall"], S["Cm"]["overall"], S["Ce"]["overall"])),
    }
    sd = float(np.std(dloss, ddof=1)) if n > 1 else float("nan")
    res = {"instrument": inst,
           "n_bars": {"macro": int(mbar.sum()), "earn": int(ebar.sum()),
                      "union": int(ubar.sum()), "overlap": int((mbar & ebar).sum())},
           "scores": S,
           "decision_union": {"mean_diff_B_minus_Cj": float(np.mean(dloss)),
                              "boot90_ci": ci},
           "lines": lines,
           "power": {"sd_diff": sd,
                     "mde": float(1.645 * sd / np.sqrt(n)) if n > 1 else None}}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"ex2_result_{inst}.json").write_text(json.dumps(res, indent=2))
    print(f"[E-X2] {inst} macro-bar QLIKE: Cm={S['Cm']['macro']:.4f} Cj={S['Cj']['macro']:.4f} | "
          f"earn-bar: Ce={S['Ce']['earn']:.4f} Cj={S['Cj']['earn']:.4f} | union diff "
          f"{np.mean(dloss):+.4f} CI90={ci} | overall B={S['B']['overall']:.4f} "
          f"Cj={S['Cj']['overall']:.4f}", flush=True)
    print(f"[E-X2] {inst}: lines={lines}", flush=True)
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
