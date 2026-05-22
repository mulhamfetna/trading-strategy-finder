"""Date filtering and train/test splitting (iter 5: generalized API)."""

from __future__ import annotations

from typing import Tuple, Union

import pandas as pd


def _ensure_date_only(df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """Add a 'Date_only' column derived from Date or timestamps. Returns
    the augmented df and the name of the date column to filter on."""
    df = df.copy()
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        # Use normalize (day truncation) when the timestamps look daily,
        # otherwise keep .dt.date for sub-daily data.
        if df['Date'].dt.hour.min() == 0 and df['Date'].dt.minute.min() == 0:
            df['Date_only'] = df['Date'].dt.normalize()
        else:
            df['Date_only'] = pd.to_datetime(df['Date'].dt.date)
        return df, 'Date_only'
    if 'timestamps' in df.columns:
        df['timestamps'] = pd.to_datetime(df['timestamps'])
        df['Date_only'] = df['timestamps'].dt.normalize()
        df['Time'] = df['timestamps'].dt.strftime('%H:%M:%S')
        return df, 'Date_only'
    raise ValueError("No Date or timestamps column found")


def filter_by_date_range(
    df: pd.DataFrame,
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
) -> pd.DataFrame:
    """Return rows whose date falls in the inclusive range [start, end].

    Iter 5 (TODO item 9): generalized replacement for filter_2025. Works
    with 'Date' or 'timestamps' columns. Inclusive on both ends so
    callers can pass a calendar quarter like ('2025-09-01', '2025-12-31')
    or a partial month without losing the boundary day.
    """
    df, date_col = _ensure_date_only(df)
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if start_ts > end_ts:
        raise ValueError(
            f"start ({start_ts.date()}) is after end ({end_ts.date()})"
        )
    return df[(df[date_col] >= start_ts) & (df[date_col] <= end_ts)]


def filter_2025(df: pd.DataFrame) -> pd.DataFrame:
    """Backwards-compatible Jan-Sep 2025 slice (kept for existing callers).

    New code should call ``filter_by_date_range`` directly.
    """
    return filter_by_date_range(df, '2025-01-01', '2025-09-30')


def split_train_test(df: pd.DataFrame, split_date: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split DataFrame into training and test sets based on a date.

    Args:
        df: DataFrame with a 'Date' or 'timestamps' column.
        split_date: Date string in 'YYYY-MM-DD' format (inclusive for train).

    Returns:
        Tuple of (train_df, test_df) where train contains dates <= split_date.
    """
    df, date_col = _ensure_date_only(df)
    split = pd.Timestamp(split_date)
    train = df[df[date_col] <= split]
    test = df[df[date_col] > split]
    return train, test
