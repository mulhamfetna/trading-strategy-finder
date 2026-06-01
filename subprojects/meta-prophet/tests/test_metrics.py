"""Verify metric formulas. Hand-computed expected values."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.metrics import (
    compute_all, hit_rate, lift_vs_naive, mae, mape, rmse,
)


def test_rmse_basic():
    y_true = np.array([100.0, 200.0, 300.0])
    y_hat  = np.array([110.0, 190.0, 305.0])
    assert rmse(y_true, y_hat) == pytest.approx(np.sqrt((100 + 100 + 25) / 3))


def test_mae_basic():
    y_true = np.array([100.0, 200.0, 300.0])
    y_hat  = np.array([110.0, 190.0, 305.0])
    assert mae(y_true, y_hat) == pytest.approx((10 + 10 + 5) / 3)


def test_mape_basic_percent():
    y_true = np.array([100.0, 200.0])
    y_hat  = np.array([110.0, 190.0])
    assert mape(y_true, y_hat) == pytest.approx(7.5)


def test_hit_rate_directional():
    y_true_ret = np.array([0.01, -0.005, 0.002, -0.003])
    y_hat_ret  = np.array([0.02, -0.001, -0.004, 0.001])
    assert hit_rate(y_true_ret, y_hat_ret) == pytest.approx(50.0)


def test_lift_vs_naive_positive_means_model_better():
    assert lift_vs_naive(rmse_model=80.0, rmse_naive=100.0) == pytest.approx(20.0)


def test_lift_vs_naive_negative_when_worse():
    assert lift_vs_naive(rmse_model=120.0, rmse_naive=100.0) == pytest.approx(-20.0)


def test_compute_all_returns_dict_with_expected_keys():
    y_true_price = np.array([100.0, 200.0, 300.0])
    y_hat_price  = np.array([110.0, 190.0, 305.0])
    y_true_ret   = np.array([0.01, -0.005, 0.002])
    y_hat_ret    = np.array([0.02, -0.001, -0.004])
    out = compute_all(y_true_price, y_hat_price, y_true_ret, y_hat_ret, rmse_naive=10.0)
    assert set(out.keys()) == {"rmse", "mae", "mape", "hit_rate", "lift_vs_naive"}
    assert out["rmse"] == pytest.approx(np.sqrt((100 + 100 + 25) / 3))
