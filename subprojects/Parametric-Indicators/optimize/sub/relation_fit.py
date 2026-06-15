"""Stage-0bis analysis — can market state PREDICT the best SL/TP (absolutely, or as a band ± error margin)?

Loads the per-window tables from fixed_window_subopt.py and asks, for each target (best SL/TP and the
near-best BAND center):
  1. ABSOLUTE map: linear regression target ~ features. Report in-sample R² AND leave-one-window-out (LOWO)
     out-of-sample skill vs the only honest baseline — "just use the global mean" (= the fixed value).
       skill = 1 - SSE(model) / SSE(predict-global-mean).  >0 ⇒ features help OOS; ≤0 ⇒ they don't.
  2. PROBABILISTIC: the predictive error margin = std of LOWO residuals. Compare to the UNCONDITIONAL std
     (spread of the target itself). If conditional σ is NOT smaller, conditioning on features buys NO
     certainty — you can always quote "value ± margin", but the margin isn't tighter than the global mean ±
     its own spread, so the features are uninformative.
Features: price_change_pct, range_pct, atr_mean, harv_mean, price_mean. CPU only, no look-ahead concern
(this is a property of the labels). Usage: python3 optimize/sub/relation_fit.py [fixed|rolling]
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent / "results"
FEATURES = ["price_change_pct", "range_pct", "atr_mean", "harv_mean", "price_mean"]
TARGETS = ["best_sl_soft", "best_sl_hard", "best_tp", "sl_soft_mean", "tp_mean"]


def lowo(X, y):
    """Leave-one-window-out predictions for OLS with intercept. Returns yhat (per row)."""
    n = len(y); yhat = np.empty(n)
    Xi = np.column_stack([np.ones(n), X])
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        beta, *_ = np.linalg.lstsq(Xi[m], y[m], rcond=None)
        yhat[i] = Xi[i] @ beta
    return yhat


def main() -> int:
    which = sys.argv[1] if len(sys.argv) > 1 else "fixed"
    path = HERE / ("fixed_window_subopt.csv" if which == "fixed" else "rolling_band_subopt.csv")
    df = pd.read_csv(path)
    df = df[df["n_trades"] > 0].reset_index(drop=True)
    print(f"\n=== {which.upper()} windows: {len(df)} · features={FEATURES} ===")
    X = df[FEATURES].to_numpy(float)
    # standardize features (numerical stability; price_mean is ~1e4)
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)

    print(f"{'target':14s} {'uncond.σ':>9s} {'OOSresid.σ':>10s} {'σ ratio':>8s} {'OOS skill':>10s} {'verdict':>22s}")
    for t in TARGETS:
        if t not in df:
            continue
        y = df[t].to_numpy(float)
        uncond = y.std(ddof=1)
        yhat = lowo(Xs, y)
        resid = y - yhat
        oos_sigma = resid.std(ddof=1)
        sse_model = float((resid ** 2).sum())
        sse_base = float(((y - y.mean()) ** 2).sum())          # predict the global mean (= the fixed value)
        skill = 1 - sse_model / sse_base if sse_base > 0 else float("nan")
        ratio = oos_sigma / uncond if uncond else float("nan")
        verdict = "features HELP" if skill > 0.05 else ("marginal" if skill > 0 else "NO gain (use fixed)")
        print(f"{t:14s} {uncond:9.1f} {oos_sigma:10.1f} {ratio:8.2f} {skill:10.2f} {verdict:>22s}")

    # Feature↔target correlations (which single signal, if any, tracks the optimum)
    print(f"\nPearson r (feature vs target):")
    print(f"{'':14s}" + "".join(f"{f[:10]:>11s}" for f in FEATURES))
    for t in TARGETS:
        if t not in df:
            continue
        rs = [np.corrcoef(df[f], df[t])[0, 1] for f in FEATURES]
        print(f"{t:14s}" + "".join(f"{r:>+11.2f}" for r in rs))

    print("\nReading: OOS skill ≤ 0 ⇒ a feature-driven SL/TP map does NOT beat just using the global fixed "
          "value out-of-sample. σ ratio ≈ 1 ⇒ conditioning on features does not shrink the error margin "
          "(no 'certainty' gain). >0 skill AND ratio<1 ⇒ a usable probabilistic mapping exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
