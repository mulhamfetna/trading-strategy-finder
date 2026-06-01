"""Internal: shared Darts model-runner template.

Each of scripts/09_darts_*.py through 14_darts_*.py imports `run_darts_model` from here
and calls it with model_class + kwargs + use_regressors flag. Keeps the 6 driver scripts to
~20 lines each.
"""
from __future__ import annotations

import os
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import sys
import warnings
import logging
from pathlib import Path
from typing import Type

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
logging.getLogger().setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, split_by_cutoff
from scripts.common.darts_helpers import (PL_TRAINER_KWARGS, to_covariate_series, to_target_series)
from scripts.common.features import REGRESSOR_COLUMNS, build_features, usable_regressors
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward


def _load_data(use_features: bool):
    if use_features:
        df_25 = load_4h_csv(ROOT / "NQ_4h_2025.csv")
        df_26 = load_4h_csv(ROOT / "NQ_4h_2026.csv")
        full = pd.concat([df_25, df_26], ignore_index=True).sort_values("datetime").reset_index(drop=True)
        full = build_features(add_log_return(full))
        return split_by_cutoff(full, df_25["datetime"].max())
    else:
        df_25 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2025.csv"))
        df_26 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2026.csv"))
        from scripts.common.data import train_eval_split
        return train_eval_split(df_25, df_26)


def make_darts_forecaster(model_class: Type, model_kwargs: dict, regressors: list[str] | None):
    """Build a Forecaster that wraps a Darts model. regressors=None ⇒ no covariates."""

    class _Wrap(Forecaster):
        def __init__(self) -> None:
            self._model = None

        def fit(self, history: pd.DataFrame) -> None:
            y = to_target_series(history)
            self._model = model_class(**model_kwargs)
            if regressors:
                cov = to_covariate_series(history, regressors)
                # past_covariates: model sees them at lag-1 implicitly
                self._model.fit(y, past_covariates=cov)
                self._last_cov = cov
            else:
                self._model.fit(y)
            self._last_y = y

        def predict_one(self, target_row: pd.Series) -> float:
            assert self._model is not None
            if regressors:
                # Extend covariate series with the target row's regressors (bar-open-known).
                new_cov_vals = np.array([[float(target_row[c]) for c in regressors]])
                cov_ext = self._last_cov.append_values(new_cov_vals)
                preds = self._model.predict(n=1, series=self._last_y, past_covariates=cov_ext)
            else:
                preds = self._model.predict(n=1, series=self._last_y)
            return float(preds.values()[0, 0])

    return _Wrap


def run_darts_model(*, name: str, model_class: Type, model_kwargs: dict, use_regressors: bool,
                    output_filename: str, retrain_every: int = 20) -> None:
    train, evalp = _load_data(use_features=use_regressors)
    if use_regressors:
        regressors = usable_regressors(train)
        print(f"  {len(regressors)} usable regressors")
    else:
        regressors = None

    factory = make_darts_forecaster(model_class, model_kwargs, regressors)
    print(f"Phase D — {name} walk-forward (retrain every {retrain_every}) ...")
    preds = walk_forward(train, evalp, factory, retrain_every=retrain_every)

    out_path = ROOT / "outputs" / output_filename
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
