"""Phase 2 — Prophet with log-return target, regressors, CV-tuned changepoint_prior_scale.

Tier 1: cross_validation on 2025 over hyperparam grid -> lock best config.
Tier 2: walk-forward on 2026 using locked config, retrain every 20 bars.
"""
from __future__ import annotations

import itertools
import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, split_by_cutoff
from scripts.common.features import REGRESSOR_COLUMNS, build_features, usable_regressors

# Filled in main() after we see the data; module-level placeholder.
_REGRESSORS: list[str] = list(REGRESSOR_COLUMNS)
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward

logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")


GRID = {
    "changepoint_prior_scale": [0.001, 0.01, 0.05, 0.1, 0.5],
    "seasonality_prior_scale": [0.01, 0.1, 1.0, 10.0],
    "seasonality_mode":        ["additive", "multiplicative"],
}


def _build_prophet(params: dict) -> Prophet:
    m = Prophet(
        growth="flat",
        daily_seasonality=False,
        weekly_seasonality=False,
        yearly_seasonality=False,
        changepoint_prior_scale=params["changepoint_prior_scale"],
        seasonality_prior_scale=params["seasonality_prior_scale"],
        seasonality_mode=params["seasonality_mode"],
    )
    m.add_seasonality(name="intraday_4h", period=1.0, fourier_order=4)
    m.add_seasonality(name="weekly_4h",   period=7.0, fourier_order=3)
    for col in _REGRESSORS:
        m.add_regressor(col, standardize=True)
    return m


def _to_prophet_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={"datetime": "ds", "log_return": "y"}).copy()
    keep = ["ds", "y", *_REGRESSORS]
    return out[keep].dropna(subset=["y", *_REGRESSORS]).reset_index(drop=True)


def tier1_search(df_train_feat: pd.DataFrame) -> dict:
    pf = _to_prophet_frame(df_train_feat)
    best = (np.inf, None)
    results = []
    n_configs = (len(GRID["changepoint_prior_scale"]) * len(GRID["seasonality_prior_scale"])
                 * len(GRID["seasonality_mode"]))
    print(f"  searching {n_configs} configs ...")
    for cps, sps, sm in itertools.product(GRID["changepoint_prior_scale"],
                                          GRID["seasonality_prior_scale"],
                                          GRID["seasonality_mode"]):
        params = {"changepoint_prior_scale": cps,
                  "seasonality_prior_scale": sps,
                  "seasonality_mode": sm}
        try:
            m = _build_prophet(params)
            m.fit(pf)
            cv = cross_validation(m, initial="180 days", period="14 days",
                                  horizon="4 hours", parallel=None, disable_tqdm=True)
            pm = performance_metrics(cv, rolling_window=1)
            score = float(pm["rmse"].iloc[0])
        except Exception as e:
            print(f"  cps={cps:<6} sps={sps:<6} mode={sm:<14} -> FAIL {e!r}")
            continue
        results.append({**params, "rmse_cv": score})
        if score < best[0]:
            best = (score, params)
        print(f"  cps={cps:<6} sps={sps:<6} mode={sm:<14} -> rmse_cv={score:.6f}")
    if best[1] is None:
        raise RuntimeError("tier1 search produced no successful configs")
    return best[1] | {"_search_results": results, "_winner_rmse_cv": best[0]}


class ProphetForecaster(Forecaster):
    def __init__(self, params: dict) -> None:
        self.params = params
        self._model: Prophet | None = None

    def fit(self, history: pd.DataFrame) -> None:
        pf = _to_prophet_frame(history)
        self._model = _build_prophet(self.params)
        self._model.fit(pf)

    def predict_one(self, target_row: pd.Series) -> float:
        assert self._model is not None
        future = pd.DataFrame({"ds": [target_row["datetime"]]})
        for col in _REGRESSORS:
            future[col] = float(target_row[col])
        forecast = self._model.predict(future)
        return float(forecast["yhat"].iloc[0])


def main() -> None:
    # Build features on the concatenated timeline so eval-pool features are warmed by 2025 history.
    df_25_raw = load_4h_csv(ROOT / "NQ_4h_2025.csv")
    df_26_raw = load_4h_csv(ROOT / "NQ_4h_2026.csv")
    full = pd.concat([df_25_raw, df_26_raw], ignore_index=True).sort_values("datetime").reset_index(drop=True)
    full = build_features(add_log_return(full))
    cutoff = df_25_raw["datetime"].max()
    train, evalp = split_by_cutoff(full, cutoff)

    # Filter out regressors that are singular (e.g., dow_sat — CME closed Saturdays).
    global _REGRESSORS
    _REGRESSORS = usable_regressors(train)
    dropped = [c for c in REGRESSOR_COLUMNS if c not in _REGRESSORS]
    if dropped:
        print(f"  dropping singular regressors: {dropped}")

    print("Tier 1: hyperparam search on 2025 ...")
    locked = tier1_search(train)
    print(f"\nLocked params: cps={locked['changepoint_prior_scale']}, "
          f"sps={locked['seasonality_prior_scale']}, mode={locked['seasonality_mode']}  "
          f"CV-rmse={locked['_winner_rmse_cv']:.6f}\n")

    with open(ROOT / "outputs" / "02_prophet_search.json", "w") as f:
        json.dump(locked, f, indent=2, default=str)

    print("Tier 2: walk-forward on 2026 ...")
    locked_runtime = {k: locked[k] for k in
                      ("changepoint_prior_scale", "seasonality_prior_scale", "seasonality_mode")}
    preds = walk_forward(train, evalp, lambda: ProphetForecaster(locked_runtime), retrain_every=20)
    out_path = ROOT / "outputs" / "02_prophet.csv"
    preds.to_csv(out_path, index=False)

    naive = pd.read_csv(ROOT / "outputs" / "01_naive.csv")
    rmse_naive = rmse(naive["y_true_price"].to_numpy(), naive["y_hat_price"].to_numpy())
    metrics = compute_all(
        y_true_price=preds["y_true_price"].to_numpy(),
        y_hat_price=preds["y_hat_price"].to_numpy(),
        y_true_ret=preds["y_true_return"].to_numpy(),
        y_hat_ret=preds["y_hat_return"].to_numpy(),
        rmse_naive=rmse_naive,
    )
    print(f"wrote {out_path}  ({len(preds)} rows)")
    print("metrics vs naive baseline:")
    for k, v in metrics.items():
        print(f"  {k:<14} {v:>10.4f}")


if __name__ == "__main__":
    main()
