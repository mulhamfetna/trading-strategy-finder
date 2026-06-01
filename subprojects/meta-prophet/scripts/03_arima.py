"""Phase 3 — auto_arima on log-returns. d=0 forced (returns are stationary)."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from pmdarima import auto_arima

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward

warnings.filterwarnings("ignore")


class ARIMAForecaster(Forecaster):
    def __init__(self) -> None:
        self._model = None

    def fit(self, history: pd.DataFrame) -> None:
        y = history["log_return"].dropna().to_numpy()
        self._model = auto_arima(
            y, start_p=0, start_q=0, max_p=5, max_q=5, d=0, max_d=0,
            seasonal=False, stepwise=True, suppress_warnings=True, error_action="ignore",
            information_criterion="aic",
        )

    def predict_one(self, target_row: pd.Series) -> float:
        assert self._model is not None
        return float(self._model.predict(n_periods=1)[0])


def main() -> None:
    df_25 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2025.csv"))
    df_26 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2026.csv"))
    train, evalp = train_eval_split(df_25, df_26)

    print("Phase 3 — ARIMA walk-forward (auto_arima refits every 20 bars) ...")
    preds = walk_forward(train, evalp, ARIMAForecaster, retrain_every=20)
    out_path = ROOT / "outputs" / "03_arima.csv"
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
