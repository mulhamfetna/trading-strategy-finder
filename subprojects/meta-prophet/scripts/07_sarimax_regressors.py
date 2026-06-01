"""Phase B.2 — SARIMAX(1,0,1) on log-returns WITH exogenous regressors.

Same SARIMAX as 06_sarimax_plain.py but with the 14 bar-open-known regressors from
Phase 2 (filtered by usable_regressors to drop singular columns like dow_sat).
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, split_by_cutoff
from scripts.common.features import REGRESSOR_COLUMNS, build_features, usable_regressors
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward

warnings.filterwarnings("ignore")


ORDER = (1, 0, 1)
_REGRESSORS: list[str] = list(REGRESSOR_COLUMNS)


class SARIMAXRegressorsForecaster(Forecaster):
    def __init__(self) -> None:
        self._fitted = None

    def fit(self, history: pd.DataFrame) -> None:
        valid = history.dropna(subset=["log_return", *_REGRESSORS])
        y    = valid["log_return"].astype(float).to_numpy()
        exog = valid[list(_REGRESSORS)].astype(float).to_numpy()
        m = SARIMAX(y, exog=exog, order=ORDER, enforce_stationarity=False,
                    enforce_invertibility=False, initialization="approximate_diffuse")
        self._fitted = m.fit(disp=False, maxiter=50)

    def predict_one(self, target_row: pd.Series) -> float:
        assert self._fitted is not None
        exog_row = np.array([[float(target_row[c]) for c in _REGRESSORS]])
        return float(self._fitted.forecast(steps=1, exog=exog_row)[0])


def main() -> None:
    df_25_raw = load_4h_csv(ROOT / "NQ_4h_2025.csv")
    df_26_raw = load_4h_csv(ROOT / "NQ_4h_2026.csv")
    full = pd.concat([df_25_raw, df_26_raw], ignore_index=True).sort_values("datetime").reset_index(drop=True)
    full = build_features(add_log_return(full))
    cutoff = df_25_raw["datetime"].max()
    train, evalp = split_by_cutoff(full, cutoff)

    global _REGRESSORS
    _REGRESSORS = usable_regressors(train)
    print(f"Phase B.2 — SARIMAX{ORDER} + {len(_REGRESSORS)} exog regressors, refit every 20 ...")

    preds = walk_forward(train, evalp, SARIMAXRegressorsForecaster, retrain_every=20)
    out_path = ROOT / "outputs" / "07_sarimax_regressors.csv"
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
