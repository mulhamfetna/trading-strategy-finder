"""Workstream A — GARCH/HAR volatility tournament on 1-min data.

Benchmarks the classical volatility families against the C2 deep-learning results, on the
SAME target (next-bar range) and SAME 20k-bar test tail, scored with RMSE + QLIKE — so we get
one apples-to-apples leaderboard: naive / EWMA / HAR-range / GARCH / GJR-GARCH / EGARCH (and
the C2 DL numbers slotted in by the report).

Every model emits a next-bar RANGE forecast:
  - naive / EWMA / HAR operate on range directly.
  - GARCH-family model the conditional volatility of RETURNS (σ_t); we map σ_t → range with a
    single train-fit scale c (range ≈ c·σ), so they compete on the same range metric. Params
    are fit on TRAIN only, then applied causally over the test tail via arch's .fix()+forecast
    (no look-ahead, no per-bar refit).

CPU. Run on the server venv (has statsmodels; arch installed by setup). Usage:
    python 43_vol_garch_har.py --csv data/NQ_1m.csv --test-bars 20000 --out runs/wsa_vol
"""
from __future__ import annotations

import argparse
import json
import os
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")


def rmse(y, p): return float(np.sqrt(np.mean((y - p) ** 2)))


def qlike(y, p, eps=1e-6):
    vt = np.maximum(y, eps) ** 2; vp = np.maximum(p, eps) ** 2
    return float(np.mean(vt / vp - np.log(vt / vp) - 1))


def har_features(x):
    """HAR regressors: [lag1, mean of last 6, mean of last 30] — all causal (shifted)."""
    s = pd.Series(x)
    return np.column_stack([
        s.shift(1).to_numpy(),
        s.shift(1).rolling(6).mean().to_numpy(),
        s.shift(1).rolling(30).mean().to_numpy(),
    ])


def garch_range_forecast(r_pct, split, vol, p=1, o=0, q=1):
    """Fit a GARCH-family model on TRAIN returns, return causal 1-step cond-vol over ALL bars."""
    from arch import arch_model
    am_tr = arch_model(r_pct[:split], mean="Zero", vol=vol, p=p, o=o, q=q, dist="normal")
    res_tr = am_tr.fit(disp="off")
    am_full = arch_model(r_pct, mean="Zero", vol=vol, p=p, o=o, q=q, dist="normal")
    res_fix = am_full.fix(res_tr.params)
    cv = np.asarray(res_fix.conditional_volatility, float)   # σ_t in pct units, causal
    return cv, res_tr.params.to_dict()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--test-bars", type=int, default=20000)
    ap.add_argument("--ewma-span", type=int, default=60)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    df = pd.read_csv(a.csv, usecols=["high", "low", "close"])
    hi, lo, cl = (df[c].astype(float).to_numpy() for c in ("high", "low", "close"))
    rng = (hi - lo) / cl
    r_pct = np.concatenate([[0.0], np.diff(np.log(cl))]) * 100.0   # returns in %, aligned to bars
    n = len(rng); split = n - a.test_bars
    test = np.arange(split, n)
    ytrue = rng[test]
    print(f"[wsA] bars={n:,} train={split:,} test={a.test_bars}", flush=True)

    preds = {}
    preds["naive"] = rng[test - 1]
    preds["ewma"] = pd.Series(rng).ewm(span=a.ewma_span, adjust=False).mean().to_numpy()[test - 1]

    # HAR on range (linear LS on train, causal features)
    X = har_features(rng); ok = np.isfinite(X).all(1)
    tr_mask = ok.copy(); tr_mask[split:] = False
    beta, *_ = np.linalg.lstsq(np.c_[np.ones(tr_mask.sum()), X[tr_mask]], rng[tr_mask], rcond=None)
    har_all = np.c_[np.ones(n), np.nan_to_num(X)] @ beta
    preds["har_range"] = np.maximum(har_all[test], 1e-9)

    # GARCH family: σ (pct) -> range via train-fit scale c (range ≈ c·σ)
    for label, (vol, o) in {"garch": ("Garch", 0), "gjr_garch": ("Garch", 1),
                            "egarch": ("EGARCH", 0)}.items():
        try:
            cv, params = garch_range_forecast(r_pct, split, vol, p=1, o=o, q=1)
            sig_tr = cv[:split]; rng_tr = rng[:split]
            c = float(np.sum(sig_tr * rng_tr) / np.sum(sig_tr * sig_tr))   # LS scale, no intercept
            preds[label] = np.maximum(c * cv[test], 1e-9)
            print(f"[wsA] {label} fit ok (scale c={c:.3e})", flush=True)
        except Exception as e:
            print(f"[wsA] {label} FAILED: {e}", flush=True)

    rows = []
    for name, p in preds.items():
        rows.append(dict(model=name, rmse=rmse(ytrue, p), qlike=qlike(ytrue, p)))
    lb = pd.DataFrame(rows).sort_values("rmse").reset_index(drop=True)
    lb.to_csv(Path(a.out) / "leaderboard.csv", index=False)
    pd.DataFrame({"idx": test, "y_true_range": ytrue, **preds}).to_csv(
        Path(a.out) / "preds.csv", index=False)

    base = lb.loc[lb.model == "naive", "rmse"].iloc[0]
    lb["lift_vs_naive_pct"] = (base - lb["rmse"]) / base * 100
    with open(Path(a.out) / "result.json", "w") as f:
        json.dump({"leaderboard": lb.to_dict("records"), "wall_s": round(time.time()-t0, 1),
                   "n_test": int(a.test_bars)}, f, indent=2)

    print(f"\n[wsA] VOLATILITY LEADERBOARD (range target, {a.test_bars} test bars):", flush=True)
    print(lb.to_string(index=False, float_format=lambda v: f"{v:.6f}"), flush=True)
    print(f"[wsA] done in {time.time()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
