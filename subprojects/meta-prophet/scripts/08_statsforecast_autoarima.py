"""Phase C — Nixtla StatsForecast AutoARIMA.

Comparison library for our pmdarima auto_arima result (Phase 3) on the same data.
Tests whether a different ARIMA-selection implementation lands at the same RMSE.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsforecast.models import AutoARIMA

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward

warnings.filterwarnings("ignore")


class StatsForecastAutoARIMA(Forecaster):
    def __init__(self) -> None:
        self._model = None

    def fit(self, history: pd.DataFrame) -> None:
        y = history["log_return"].dropna().astype(float).to_numpy()
        # AutoARIMA from statsforecast.models. Set d=0 (returns stationary), no seasonality.
        self._model = AutoARIMA(max_p=5, max_q=5, d=0, max_d=0, seasonal=False, stepwise=True)
        self._model.fit(y)

    def predict_one(self, target_row: pd.Series) -> float:
        assert self._model is not None
        out = self._model.predict(h=1)
        # statsforecast returns dict-like with "mean"; some versions return array
        if isinstance(out, dict):
            return float(out["mean"][0])
        return float(np.asarray(out).reshape(-1)[0])


def main() -> None:
    df_25 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2025.csv"))
    df_26 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2026.csv"))
    train, evalp = train_eval_split(df_25, df_26)

    print("Phase C — Nixtla StatsForecast AutoARIMA, walk-forward retrain_every=20 ...")
    preds = walk_forward(train, evalp, StatsForecastAutoARIMA, retrain_every=20)
    out_path = ROOT / "outputs" / "08_statsforecast_autoarima.csv"
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
    for k, v in metrics.items():
        print(f"  {k:<14} {v:>10.4f}")


if __name__ == "__main__":
    main()
