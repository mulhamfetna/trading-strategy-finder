"""CSV loading + log-return transform + train/eval split for the tournament."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_4h_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def add_log_return(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    out = df.copy()
    out["log_return"] = np.log(out[price_col] / out[price_col].shift(1))
    return out


def train_eval_split(
    df_train_pool: pd.DataFrame,
    df_eval_pool: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df_train_pool.sort_values("datetime").reset_index(drop=True)
    evalp = df_eval_pool.sort_values("datetime").reset_index(drop=True)
    if train["datetime"].max() >= evalp["datetime"].min():
        raise ValueError("train_eval_split: train pool overlaps eval pool")
    return train, evalp


def split_by_cutoff(df: pd.DataFrame, cutoff: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a single dataframe into (rows <= cutoff, rows > cutoff). Preserves order, resets index."""
    df = df.sort_values("datetime").reset_index(drop=True)
    train = df[df["datetime"] <= cutoff].reset_index(drop=True)
    evalp = df[df["datetime"] >  cutoff].reset_index(drop=True)
    return train, evalp
