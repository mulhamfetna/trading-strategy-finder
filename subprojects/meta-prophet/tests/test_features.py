"""Verify causal feature computation. No look-ahead allowed."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return
from scripts.common.features import build_features


def _toy(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    close = 100.0 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.1, 0.5, n)
    low = close - rng.uniform(0.1, 0.5, n)
    return pd.DataFrame({
        "datetime": pd.date_range("2025-01-01", periods=n, freq="4h"),
        "open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1e3, 1e5, n),
    })


def test_build_features_expected_columns():
    df = add_log_return(_toy())
    feats = build_features(df)
    expected = {"prior_log_return", "prior_range", "rolling_20bar_vol",
                "tod_asia", "tod_eu", "tod_rth_open", "tod_lunch", "tod_rth_close",
                "dow_mon", "dow_tue", "dow_wed", "dow_thu", "dow_fri", "dow_sat", "dow_sun"}
    assert expected.issubset(set(feats.columns))


def test_prior_log_return_is_shifted_log_return():
    df = add_log_return(_toy())
    feats = build_features(df)
    np.testing.assert_array_equal(
        feats["prior_log_return"].iloc[2:].to_numpy(),
        df["log_return"].iloc[1:-1].to_numpy(),
    )


def test_rolling_vol_uses_only_past():
    df = add_log_return(_toy())
    feats = build_features(df)
    # rolling_20bar_vol at row 25 uses log_return.shift(1) rolled over 20 bars,
    # i.e. log_return[5..24] (20 bars, all strictly before row 25)
    expected = df["log_return"].iloc[5:25].std()
    assert feats["rolling_20bar_vol"].iloc[25] == pytest.approx(expected)


def test_no_lookahead_features_dont_use_current_bar_close():
    """If we change row N's close, only features at row >= N+1 may change."""
    df = add_log_return(_toy())
    feats_orig = build_features(df)
    df_mod = df.copy()
    df_mod.loc[30, "close"] = df_mod.loc[30, "close"] * 1.1
    df_mod = add_log_return(df_mod.drop(columns=["log_return"]))
    feats_mod = build_features(df_mod)
    cols = ["prior_log_return", "prior_range", "rolling_20bar_vol"]
    for c in cols:
        v_orig = feats_orig[c].iloc[30]
        v_mod  = feats_mod[c].iloc[30]
        if np.isnan(v_orig) and np.isnan(v_mod):
            continue
        assert v_orig == pytest.approx(v_mod), f"{c} at row 30 leaked future data"


def test_tod_buckets_one_hot_per_row():
    df = add_log_return(_toy())
    feats = build_features(df)
    tod_cols = [c for c in feats.columns if c.startswith("tod_")]
    row_sums = feats[tod_cols].sum(axis=1)
    assert (row_sums == 1).all()
