"""Rolling-origin walk-forward harness. Identical for every model in the tournament."""
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np
import pandas as pd


class Forecaster(Protocol):
    def fit(self, history: pd.DataFrame) -> None: ...
    def predict_one(self, target_row: pd.Series) -> float: ...


def walk_forward(
    train_pool: pd.DataFrame,
    eval_pool: pd.DataFrame,
    model_factory: Callable[[], Forecaster],
    retrain_every: int = 20,
) -> pd.DataFrame:
    """Walk forward through eval_pool, retraining every `retrain_every` bars.

    At each eval bar t:
      1. The model has been fit on history containing all bars with datetime <= prev eval bar's datetime
         (it has NOT seen bar t's close).
      2. predict_one receives the full eval row for t (datetime + bar-open-known regressors)
         and returns the log-return forecast for bar t.
      3. y_hat_price[t] = close[t-1] * exp(yhat_return[t]) where close[t-1] is the realised
         previous-bar close (train-pool last for the first eval bar; eval-bar i-1 for i >= 1).
      4. After recording, the realised bar t is appended to history.
    """
    if retrain_every < 1:
        raise ValueError("retrain_every must be >= 1")

    history = train_pool.copy()
    records: list[dict] = []
    model: Forecaster | None = None

    for i in range(len(eval_pool)):
        if i % retrain_every == 0:
            model = model_factory()
            model.fit(history)
        assert model is not None

        target = eval_pool.iloc[i]
        yhat_return = float(model.predict_one(target))

        prev_close = float(history["close"].iloc[-1])
        yhat_price = prev_close * float(np.exp(yhat_return))
        y_true_price = float(target["close"])
        y_true_return = float(np.log(y_true_price / prev_close))

        records.append({
            "datetime":      target["datetime"],
            "y_true_price":  y_true_price,
            "y_hat_price":   yhat_price,
            "y_true_return": y_true_return,
            "y_hat_return":  yhat_return,
        })

        new_row = target.copy()
        if "log_return" in history.columns:
            new_row["log_return"] = y_true_return
        history = pd.concat([history, new_row.to_frame().T], ignore_index=True)

    return pd.DataFrame.from_records(records)
