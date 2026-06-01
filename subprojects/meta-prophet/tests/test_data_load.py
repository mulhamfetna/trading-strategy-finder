"""Verify CSV loading + log-return computation."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split


def test_load_4h_csv_returns_typed_frame():
    df = load_4h_csv(ROOT / "NQ_4h_2025.csv")
    assert list(df.columns) == ["datetime", "open", "high", "low", "close", "volume"]
    assert df["datetime"].dtype == "datetime64[ns]"
    assert df["close"].dtype == float
    assert len(df) == 1534
    assert df["datetime"].is_monotonic_increasing


def test_add_log_return_first_row_is_nan():
    df = pd.DataFrame({"close": [100.0, 101.0, 102.0]})
    out = add_log_return(df)
    assert np.isnan(out["log_return"].iloc[0])
    assert out["log_return"].iloc[1] == pytest.approx(np.log(101 / 100))
    assert out["log_return"].iloc[2] == pytest.approx(np.log(102 / 101))


def test_train_eval_split_disjoint_and_complete():
    df_25 = load_4h_csv(ROOT / "NQ_4h_2025.csv")
    df_26 = load_4h_csv(ROOT / "NQ_4h_2026.csv")
    train, evalp = train_eval_split(df_25, df_26)
    assert len(train) == 1534
    assert len(evalp) == 585
    assert train["datetime"].max() < evalp["datetime"].min()
    assert train["datetime"].is_monotonic_increasing
    assert evalp["datetime"].is_monotonic_increasing
