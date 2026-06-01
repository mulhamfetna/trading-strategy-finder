"""RMSE / MAE / MAPE / directional-hit-rate / lift-vs-naive."""
from __future__ import annotations

from typing import Mapping

import numpy as np


def rmse(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    err = np.asarray(y_true, dtype=float) - np.asarray(y_hat, dtype=float)
    return float(np.sqrt(np.mean(err ** 2)))


def mae(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    err = np.asarray(y_true, dtype=float) - np.asarray(y_hat, dtype=float)
    return float(np.mean(np.abs(err)))


def mape(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    yt = np.asarray(y_true, dtype=float)
    yh = np.asarray(y_hat, dtype=float)
    return float(np.mean(np.abs((yt - yh) / yt)) * 100.0)


def hit_rate(y_true_ret: np.ndarray, y_hat_ret: np.ndarray) -> float:
    yt = np.sign(np.asarray(y_true_ret, dtype=float))
    yh = np.sign(np.asarray(y_hat_ret, dtype=float))
    return float(np.mean(yt == yh) * 100.0)


def lift_vs_naive(rmse_model: float, rmse_naive: float) -> float:
    return float((rmse_naive - rmse_model) / rmse_naive * 100.0)


def compute_all(
    y_true_price: np.ndarray,
    y_hat_price: np.ndarray,
    y_true_ret: np.ndarray,
    y_hat_ret: np.ndarray,
    rmse_naive: float,
) -> Mapping[str, float]:
    rmse_v = rmse(y_true_price, y_hat_price)
    return {
        "rmse":          rmse_v,
        "mae":           mae(y_true_price, y_hat_price),
        "mape":          mape(y_true_price, y_hat_price),
        "hit_rate":      hit_rate(y_true_ret, y_hat_ret),
        "lift_vs_naive": lift_vs_naive(rmse_v, rmse_naive),
    }
