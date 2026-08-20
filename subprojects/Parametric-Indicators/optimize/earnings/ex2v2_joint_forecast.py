#!/usr/bin/env python3
"""E-X2 v2 — the joint forecast under POWERED tolerances. docs/EX2V2-PREREGISTRATION.md.

Identical data/models to v1; verdict lines re-registered as paired-bootstrap CIs (the house
standard), evaluated on BOTH instruments.

    WSH_16Y_ROOT=... python3 optimize/earnings/ex2v2_joint_forecast.py --instrument NQ
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
from optimize.earnings.ex2_joint_forecast import macro_terms, earn_terms  # noqa: E402

TRAIN_END = pd.Timestamp("2024-01-01")
N_BOOT, SEED, MINUTES = 10000, 20260820, 60


def paired_ci(diff: np.ndarray, rng) -> tuple[float, list, float]:
    n = len(diff)
    boots = np.array([np.mean(diff[rng.integers(0, n, n)]) for _ in range(N_BOOT)])
    ci = [round(float(np.percentile(boots, 5)), 4),
          round(float(np.percentile(boots, 95)), 4)]
    mde = round(float(1.645 * np.std(diff, ddof=1) / np.sqrt(n)), 4)
    return float(np.mean(diff)), ci, mde


def run(inst: str, out_dir: Path) -> dict:
    print(f"[E-X2v2] instrument={inst} · powered lines (paired boot CI) · N_BOOT={N_BOOT} "
          f"SEED={SEED}", flush=True)
    rng = np.random.default_rng(SEED)
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

    pB, _ = ols_predict(Xh, y, train)
    pCm, _ = ols_predict(np.c_[Xh, m_dum, m_pw], y, train)
    pCe, _ = ols_predict(np.c_[Xh, e_dum, e_pw], y, train)
    pCj, _ = ols_predict(np.c_[Xh, m_dum, m_pw, e_dum, e_pw], y, train)

    def L(pred, m):
        return qlike(y[m], pred[m])

    res = {"instrument": inst, "n_bars": {"macro": int(mbar.sum()), "earn": int(ebar.sum()),
                                          "union": int(ubar.sum()), "test": int(test.sum())},
           "lines": {}, "detail": {}}

    # line 1: (C_m − C_j) on macro bars — fail iff CI-hi < 0
    d1, ci1, mde1 = paired_ci(L(pCm, mbar) - L(pCj, mbar), rng)
    res["detail"]["1_macro"] = {"mean": round(d1, 4), "ci90": ci1, "mde": mde1}
    res["lines"]["1_no_macro_degradation"] = bool(ci1[1] >= 0)
    # line 2: (C_e − C_j) on earnings bars
    d2, ci2, mde2 = paired_ci(L(pCe, ebar) - L(pCj, ebar), rng)
    res["detail"]["2_earn"] = {"mean": round(d2, 4), "ci90": ci2, "mde": mde2}
    res["lines"]["2_no_earn_degradation"] = bool(ci2[1] >= 0)
    # line 3: (B − C_j) on union bars — pass iff mean>0 and CI-lo>0
    d3, ci3, mde3 = paired_ci(L(pB, ubar) - L(pCj, ubar), rng)
    res["detail"]["3_union"] = {"mean": round(d3, 4), "ci90": ci3, "mde": mde3}
    res["lines"]["3_union_ci"] = bool(d3 > 0 and ci3[0] > 0)
    # line 4: no rival clear-beats C_j overall
    ok4 = True
    for rname, pR in (("B", pB), ("Cm", pCm), ("Ce", pCe)):
        dr, cir, mder = paired_ci(L(pR, test) - L(pCj, test), rng)
        res["detail"][f"4_overall_vs_{rname}"] = {"mean": round(dr, 4), "ci90": cir,
                                                  "mde": mder}
        if cir[1] < 0:
            ok4 = False
    res["lines"]["4_no_rival_overall"] = bool(ok4)

    res["all_pass"] = bool(all(res["lines"].values()))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"ex2v2_result_{inst}.json").write_text(json.dumps(res, indent=2))
    print(f"[E-X2v2] {inst}: lines={res['lines']} · L1 {res['detail']['1_macro']} · "
          f"L2 {res['detail']['2_earn']} · L3 mean {d3:+.4f} CI {ci3}", flush=True)
    print(f"[E-X2v2] {inst} ALL_PASS={res['all_pass']}", flush=True)
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
