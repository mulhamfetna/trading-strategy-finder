"""Phase F1 — forecast next-bar RANGE (high-low, in points) on 4h data.

Models: naive-range, EWMA-range, HAR-range, GARCH(1,1). All scored on the same range target
with RMSE / MAE / lift-over-naive / QLIKE / correlation. Walk-forward on 2026.

This is the 'magnitude' pivot from notes/23 — the first target with real autocorrelation (0.56).
Classical lightweight models only (no torch) → no OOM risk.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from arch import arch_model

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split

warnings.filterwarnings("ignore")


# ----- metrics ---------------------------------------------------------------
def rmse(a, p): a, p = np.asarray(a, float), np.asarray(p, float); return float(np.sqrt(np.mean((a - p) ** 2)))
def mae(a, p):  a, p = np.asarray(a, float), np.asarray(p, float); return float(np.mean(np.abs(a - p)))
def corr(a, p): return float(np.corrcoef(a, p)[0, 1])

def qlike(actual, pred):
    """QLIKE loss on variance: mean( a/p - ln(a/p) - 1 ). Lower is better. Uses variances (range²)."""
    a = np.asarray(actual, float) ** 2
    p = np.asarray(pred, float) ** 2
    p = np.clip(p, 1e-9, None)
    ratio = a / p
    return float(np.mean(ratio - np.log(np.clip(ratio, 1e-9, None)) - 1))


# ----- models (walk-forward) -------------------------------------------------
def run_models(train, evalp):
    tr_range = (train["high"] - train["low"]).to_numpy(float)
    ev_range = (evalp["high"] - evalp["low"]).to_numpy(float)
    # full concatenated range history for recursive updates
    hist = list(tr_range)
    n = len(ev_range)

    preds = {k: np.empty(n) for k in ["naive", "ewma", "har", "garch"]}

    # EWMA state (RiskMetrics λ=0.94) on range
    lam = 0.94
    ewma = np.mean(tr_range[-50:])
    for v in tr_range:
        ewma = lam * ewma + (1 - lam) * v

    # GARCH: fit on returns, refit every 20 bars; scale sigma→range by c
    full_ret = add_log_return(pd.concat([train, evalp], ignore_index=True))["log_return"].to_numpy(float)
    n_tr = len(train)
    c_scale = np.nanmean(tr_range) / np.nanmean(np.abs(full_ret[1:n_tr]))  # range per unit |ret|
    garch_sigma = None

    def fit_garch(ret_hist):
        am = arch_model(ret_hist * 100, mean="Zero", vol="GARCH", p=1, q=1, dist="normal")
        res = am.fit(disp="off")
        f = res.forecast(horizon=1, reindex=False)
        return float(np.sqrt(f.variance.values[-1, 0]) / 100.0)

    ewma_state = ewma
    for i in range(n):
        # naive
        preds["naive"][i] = hist[-1]
        # ewma
        preds["ewma"][i] = ewma_state
        # HAR: average of last 1, 6, 30 ranges
        h = np.array(hist)
        preds["har"][i] = 0.5 * h[-1] + 0.3 * h[-6:].mean() + 0.2 * h[-30:].mean()
        # garch: refit every 20 bars
        if i % 20 == 0:
            try:
                ret_so_far = full_ret[1:n_tr + i]
                garch_sigma = fit_garch(ret_so_far[-750:])  # cap history for speed
            except Exception:
                garch_sigma = np.abs(full_ret[n_tr + i - 1]) if (n_tr + i - 1) < len(full_ret) else h[-1] / c_scale
        preds["garch"][i] = garch_sigma * c_scale

        # advance state with realised range
        realised = ev_range[i]
        hist.append(realised)
        ewma_state = lam * ewma_state + (1 - lam) * realised

    return ev_range, preds


def main() -> None:
    d25 = load_4h_csv(ROOT / "NQ_4h_2025.csv")
    d26 = load_4h_csv(ROOT / "NQ_4h_2026.csv")
    train, evalp = train_eval_split(d25, d26)

    actual, preds = run_models(train, evalp)

    # per-bar output
    out = pd.DataFrame({"datetime": evalp["datetime"], "actual_range": actual,
                        **{f"pred_{k}": v for k, v in preds.items()}})
    out.to_csv(ROOT / "outputs" / "15_range_forecast.csv", index=False)

    rmse_naive = rmse(actual, preds["naive"])
    rows = []
    for k, p in preds.items():
        rows.append({
            "model": f"range-{k}",
            "rmse_pts": rmse(actual, p),
            "mae_pts": mae(actual, p),
            "lift_vs_naive_%": (rmse_naive - rmse(actual, p)) / rmse_naive * 100,
            "qlike": qlike(actual, p),
            "corr": corr(actual, p),
        })
    lb = pd.DataFrame(rows).sort_values("rmse_pts")
    lb.to_csv(ROOT / "outputs" / "range_leaderboard.csv", index=False)
    print("=== RANGE-FORECAST LEADERBOARD (2026 walk-forward) ===")
    print(lb.to_string(index=False))
    print(f"\nmean actual range: {actual.mean():.1f} pts  (naive RMSE {rmse_naive:.1f} pts)")


if __name__ == "__main__":
    main()
