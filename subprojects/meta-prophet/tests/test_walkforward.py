"""Verify the walk-forward harness contract: causality + retrain cadence + output shape."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return
from scripts.common.walkforward import Forecaster, walk_forward


class ConstantReturnModel(Forecaster):
    def __init__(self) -> None:
        self._mean: float = 0.0
        self.fit_calls = 0

    def fit(self, history: pd.DataFrame) -> None:
        self.fit_calls += 1
        self._mean = float(history["log_return"].dropna().mean())

    def predict_one(self, target_row: pd.Series) -> float:
        return self._mean


def _toy(n: int) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    close = 100.0 + np.cumsum(rng.normal(0, 0.5, n))
    return add_log_return(pd.DataFrame({
        "datetime": pd.date_range("2025-01-01", periods=n, freq="4h"),
        "open": close, "high": close, "low": close, "close": close, "volume": 1e4,
    }))


def test_walk_forward_output_shape():
    train = _toy(50)
    evalp = _toy(20); evalp["datetime"] = pd.date_range("2025-02-01", periods=20, freq="4h")
    model = ConstantReturnModel()
    preds = walk_forward(train, evalp, lambda: model, retrain_every=5)
    assert len(preds) == 20
    assert list(preds.columns) == ["datetime", "y_true_price", "y_hat_price", "y_true_return", "y_hat_return"]


def test_walk_forward_retrains_at_expected_cadence():
    train = _toy(50)
    evalp = _toy(20); evalp["datetime"] = pd.date_range("2025-02-01", periods=20, freq="4h")
    fit_calls_total = [0]
    def factory():
        m = ConstantReturnModel()
        original_fit = m.fit
        def counting_fit(history):
            fit_calls_total[0] += 1
            original_fit(history)
        m.fit = counting_fit  # type: ignore
        return m
    walk_forward(train, evalp, factory, retrain_every=5)
    # 20 eval bars, retrain at i=0,5,10,15 -> exactly 4 retrains
    assert fit_calls_total[0] == 4


def test_walk_forward_first_prediction_uses_train_only():
    train = _toy(50)
    evalp = _toy(20); evalp["datetime"] = pd.date_range("2025-02-01", periods=20, freq="4h")
    seen_dates: list[pd.Timestamp] = []
    class Spy(Forecaster):
        def fit(self, history: pd.DataFrame) -> None:
            seen_dates.append(history["datetime"].max())
        def predict_one(self, target_row): return 0.0
    walk_forward(train, evalp, Spy, retrain_every=5)
    # first fit must see only train (last date = train's last)
    assert seen_dates[0] == train["datetime"].iloc[-1]


def test_walk_forward_price_reconstruction():
    train = _toy(50)
    evalp = _toy(20); evalp["datetime"] = pd.date_range("2025-02-01", periods=20, freq="4h")
    model = ConstantReturnModel()
    preds = walk_forward(train, evalp, lambda: model, retrain_every=20)
    expected_first = train["close"].iloc[-1] * np.exp(preds["y_hat_return"].iloc[0])
    assert preds["y_hat_price"].iloc[0] == pytest.approx(expected_first)
    expected_second = evalp["close"].iloc[0] * np.exp(preds["y_hat_return"].iloc[1])
    assert preds["y_hat_price"].iloc[1] == pytest.approx(expected_second)
