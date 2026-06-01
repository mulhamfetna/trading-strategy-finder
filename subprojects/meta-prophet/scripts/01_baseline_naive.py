"""Naive baseline: yhat_return = 0 ⇒ yhat_price = previous_close.

Writes outputs/01_naive.csv with the standard per-bar prediction schema.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward


class NaiveModel(Forecaster):
    def fit(self, history: pd.DataFrame) -> None:
        pass

    def predict_one(self, target_row: pd.Series) -> float:
        return 0.0


def main() -> None:
    df_25 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2025.csv"))
    df_26 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2026.csv"))
    train, evalp = train_eval_split(df_25, df_26)

    preds = walk_forward(train, evalp, NaiveModel, retrain_every=20)

    out_path = ROOT / "outputs" / "01_naive.csv"
    preds.to_csv(out_path, index=False)
    print(f"wrote {out_path}  ({len(preds)} rows)")

    rmse_self = rmse(preds["y_true_price"].to_numpy(), preds["y_hat_price"].to_numpy())
    metrics = compute_all(
        y_true_price=preds["y_true_price"].to_numpy(),
        y_hat_price=preds["y_hat_price"].to_numpy(),
        y_true_ret=preds["y_true_return"].to_numpy(),
        y_hat_ret=preds["y_hat_return"].to_numpy(),
        rmse_naive=rmse_self,
    )
    print("metrics:")
    for k, v in metrics.items():
        print(f"  {k:<14} {v:>10.4f}")


if __name__ == "__main__":
    main()
