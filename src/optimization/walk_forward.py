"""Walk-forward fold splitter.

Splits a 4h DataFrame into N equal-calendar-time-span folds. Each fold is a
contiguous slice of the input (no overlap, no gaps within the input range).

Per the no-fallback rule, every argument is required and inputs that
can't support the requested fold count raise ConfigurationError with a
structured code + system_status payload.
"""
from __future__ import annotations

from typing import List

import pandas as pd

from src.exceptions import ConfigurationError


# Minimum bars per fold for the optimiser to have any chance of running.
# Operational floor; not a strategy decision. Documented; not user-tunable.
_MIN_BARS_PER_FOLD = 30


def split_folds(df: pd.DataFrame, fold_count: int) -> List[pd.DataFrame]:
    """Split `df` into `fold_count` equal-time-span folds.

    Args:
        df: DataFrame with a 'Date' column (pandas Timestamps), already
            sorted ascending.
        fold_count: Number of folds. Must be >= 2.

    Returns:
        A list of `fold_count` DataFrames. Each fold's bars are reset-indexed.
        Folds are time-disjoint; their union equals `df` (modulo row order).

    Raises:
        ConfigurationError(code='invalid-fold-count') when `fold_count` < 2.
        ConfigurationError(code='insufficient-data-window') when the input
            has fewer than `fold_count * _MIN_BARS_PER_FOLD` bars.
    """
    if fold_count < 2:
        raise ConfigurationError(
            f'fold_count must be >= 2, got {fold_count}.',
            code='invalid-fold-count',
            system_status={'fold_count': fold_count, 'min_required': 2},
        )
    min_required_bars = fold_count * _MIN_BARS_PER_FOLD
    if len(df) < min_required_bars:
        raise ConfigurationError(
            f'Insufficient data window: {len(df)} bars for {fold_count} '
            f'folds (need at least {min_required_bars}).',
            code='insufficient-data-window',
            system_status={
                'bars': len(df),
                'fold_count': fold_count,
                'min_bars_per_fold': _MIN_BARS_PER_FOLD,
                'min_required_total': min_required_bars,
            },
        )

    df = df.sort_values('Date').reset_index(drop=True)
    start_ts = df['Date'].iloc[0]
    end_ts   = df['Date'].iloc[-1]
    total_span = end_ts - start_ts
    fold_span = total_span / fold_count

    folds: List[pd.DataFrame] = []
    for i in range(fold_count):
        lo = start_ts + fold_span * i
        if i < fold_count - 1:
            hi = start_ts + fold_span * (i + 1)
            mask = (df['Date'] >= lo) & (df['Date'] < hi)
        else:
            # Last fold is inclusive of end_ts so the final bar is captured.
            mask = (df['Date'] >= lo) & (df['Date'] <= end_ts)
        folds.append(df[mask].reset_index(drop=True))
    return folds
