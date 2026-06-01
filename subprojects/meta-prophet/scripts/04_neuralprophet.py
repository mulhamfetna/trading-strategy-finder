"""Phase 4 — NeuralProphet (DEAD REFERENCE — DO NOT RUN).

This script is preserved as the canonical record of seven distinct NeuralProphet 0.8 +
torch 2.12 + Python 3.14 + CME-futures-data incompatibilities we hit while attempting
to add NeuralProphet to the tournament.

The dominant root cause (structural, not fixable) is documented in:
    notes/07_phase4_neuralprophet_BLOCKED.md  (initial dependency-chain failures)
    notes/09_neuralprophet_root_cause_report.md  (deep investigation with citations)

NeuralProphet expects uniform-cadence time series; our NQ 4h data has CME weekend
closures (52h Friday→Sunday, every week) which NP synthesizes as NaN slots, then
either errors (drop_missing=False) or drops every sample whose lookback crosses
a gap (drop_missing=True). At n_lags=30 exactly 0% of samples survive.

This is upstream issue ourownstory/neural_prophet#1521 — confirmed by maintainer,
no fix in pipeline (project marked Inactive on Snyk).

The expansion plan (notes/10_expansion_plan.md) replaces this script's role with
scripts/06-14 (SARIMAX + StatsForecast + Darts), all of which natively support
irregular timestamps.

DO NOT RUN. DO NOT REVIVE without first reading notes/09_neuralprophet_root_cause_report.md.
"""
from __future__ import annotations

import functools
import itertools
import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

# NeuralProphet 0.8 + torch 2.6+ incompatibility: torch.load now defaults to weights_only=True,
# which rejects NP's internal config classes during checkpoint reload after fit. Patch before import.
import torch
torch.load = functools.partial(torch.load, weights_only=False)  # type: ignore[assignment]

# NeuralProphet's auto_normalization_setting raises on any sub-window where a regressor has
# <2 unique values (happens with lagged copies of binary or low-variance columns). Patch to
# downgrade to "off" instead of raising — the model still trains, just without normalising
# that sub-window's stats.
import neuralprophet.df_utils as _np_df_utils
_orig_auto_norm = _np_df_utils.auto_normalization_setting
def _safe_auto_norm(array):
    import numpy as _np
    try:
        return _orig_auto_norm(array)
    except ValueError:
        if len(_np.unique(array)) < 2:
            return "minmax"  # singular -> pretend it's binary; downstream handles 1-value case
        raise
_np_df_utils.auto_normalization_setting = _safe_auto_norm

from neuralprophet import NeuralProphet, set_log_level

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, split_by_cutoff
from scripts.common.features import REGRESSOR_COLUMNS, build_features, usable_regressors

_REGRESSORS: list[str] = list(REGRESSOR_COLUMNS)
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward

set_log_level("ERROR")
logging.getLogger("NP").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")


GRID = {
    "n_lags":        [10, 15, 20],
    "learning_rate": [1e-3, 1e-2],
    "ar_layers":     [[], [16]],
}


def _to_np_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={"datetime": "ds", "log_return": "y"}).copy()
    return out[["ds", "y"]].dropna(subset=["y"]).reset_index(drop=True)


def _build_np(params: dict) -> NeuralProphet:
    # No lagged regressors — pure AR-Net on log-returns. NeuralProphet 0.8 + torch 2.12 +
    # Python 3.14 hit too many singular-window edge cases with lagged regressors enabled.
    # The naked AR-Net is still a valid test of "does autoregression help?".
    m = NeuralProphet(
        n_lags=params["n_lags"],
        n_forecasts=1,
        ar_layers=params["ar_layers"],
        learning_rate=params["learning_rate"],
        epochs=50,
        daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=False,
        growth="off",
        normalize="standardize",
        impute_missing=True,
        drop_missing=True,
    )
    return m


def tier1_search(df_train_feat: pd.DataFrame) -> dict:
    pf = _to_np_frame(df_train_feat)
    cut = int(0.8 * len(pf))
    tr, va = pf.iloc[:cut].reset_index(drop=True), pf.iloc[cut:].reset_index(drop=True)
    best = (np.inf, None); results = []
    for n_lags, lr, ar_layers in itertools.product(GRID["n_lags"], GRID["learning_rate"], GRID["ar_layers"]):
        params = {"n_lags": n_lags, "learning_rate": lr, "ar_layers": ar_layers}
        try:
            m = _build_np(params)
            m.fit(tr, freq="4h", progress=None)
            future = m.make_future_dataframe(tr, periods=len(va), n_historic_predictions=False)
            fc = m.predict(future)
            yhat = fc["yhat1"].to_numpy()[-len(va):]
            y    = va["y"].to_numpy()
            mask = ~(np.isnan(yhat) | np.isnan(y))
            score = float(np.sqrt(np.mean((y[mask] - yhat[mask]) ** 2)))
        except Exception as e:
            print(f"  n_lags={n_lags:<3} lr={lr:<6} ar_layers={ar_layers}  -> FAIL {e!r}")
            continue
        results.append({**params, "rmse_val": score})
        if score < best[0]: best = (score, params)
        print(f"  n_lags={n_lags:<3} lr={lr:<6} ar_layers={ar_layers}  -> rmse_val={score:.6f}")
    if best[1] is None:
        raise RuntimeError("tier1 search produced no successful configs")
    return best[1] | {"_search_results": results, "_winner_rmse_val": best[0]}


class NPForecaster(Forecaster):
    def __init__(self, params: dict) -> None:
        self.params = params
        self._model: NeuralProphet | None = None
        self._history_np: pd.DataFrame | None = None

    def fit(self, history: pd.DataFrame) -> None:
        self._history_np = _to_np_frame(history)
        self._model = _build_np(self.params)
        self._model.fit(self._history_np, freq="4h", progress=None)

    def predict_one(self, target_row: pd.Series) -> float:
        assert self._model is not None and self._history_np is not None
        fc_df = self._model.make_future_dataframe(self._history_np, periods=1,
                                                   n_historic_predictions=False)
        fc = self._model.predict(fc_df)
        return float(fc["yhat1"].iloc[-1])


def main() -> None:
    df_25_raw = load_4h_csv(ROOT / "NQ_4h_2025.csv")
    df_26_raw = load_4h_csv(ROOT / "NQ_4h_2026.csv")
    full = pd.concat([df_25_raw, df_26_raw], ignore_index=True).sort_values("datetime").reset_index(drop=True)
    full = build_features(add_log_return(full))
    cutoff = df_25_raw["datetime"].max()
    train, evalp = split_by_cutoff(full, cutoff)

    print("  NeuralProphet running in no-regressor mode (AR-Net only); "
          "see 07_phase4_neuralprophet_BLOCKED.md for the trail of incompatibilities that forced this.")

    print("Tier 1: hyperparam search on 2025 (80/20 split) ...")
    locked = tier1_search(train)
    print(f"\nLocked params: {locked}")
    with open(ROOT / "outputs" / "04_neuralprophet_search.json", "w") as f:
        json.dump(locked, f, indent=2, default=str)

    print("\nTier 2: walk-forward on 2026 ...")
    locked_runtime = {k: locked[k] for k in ("n_lags", "learning_rate", "ar_layers")}
    preds = walk_forward(train, evalp, lambda: NPForecaster(locked_runtime), retrain_every=20)
    out_path = ROOT / "outputs" / "04_neuralprophet.csv"
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
    for k, v in metrics.items(): print(f"  {k:<14} {v:>10.4f}")


if __name__ == "__main__":
    main()
