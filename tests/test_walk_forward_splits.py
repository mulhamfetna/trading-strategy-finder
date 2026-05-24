"""Fold-splitter correctness tests.

The splitter must:
1. Produce exactly `fold_count` non-overlapping DataFrames whose union == input.
2. Use equal calendar-time spans (not equal candle counts).
3. Raise ConfigurationError with code='invalid-fold-count' if N < 2.
4. Raise ConfigurationError with code='insufficient-data-window' if the
   input is too small for the requested fold count.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.exceptions import ConfigurationError
from src.optimization.walk_forward import split_folds


def _synth_4h(n_bars: int) -> pd.DataFrame:
    timestamps = pd.date_range(start='2025-01-01', periods=n_bars, freq='4h')
    return pd.DataFrame({
        'Date':   timestamps,
        'Open':   [20000.0] * n_bars,
        'High':   [20010.0] * n_bars,
        'Low':    [19990.0] * n_bars,
        'Close':  [20005.0] * n_bars,
        'Volume': [1000] * n_bars,
    })


def test_three_folds_cover_full_range_with_no_overlap():
    df = _synth_4h(300)   # 50 calendar days @ 4h bars
    folds = split_folds(df, fold_count=3)
    assert len(folds) == 3
    # Union: every bar must appear in exactly one fold.
    total = sum(len(f) for f in folds)
    assert total == len(df)
    # No overlap: bar-set intersections are empty.
    seen = set()
    for f in folds:
        idxs = set(f['Date'].astype(str))
        assert not (idxs & seen)
        seen |= idxs


def test_five_folds_equal_time_spans():
    df = _synth_4h(500)
    folds = split_folds(df, fold_count=5)
    assert len(folds) == 5
    spans = [(f['Date'].iloc[-1] - f['Date'].iloc[0]) for f in folds if len(f) > 0]
    # Spans should be within a tolerance equal to one 4h bar gap.
    bar_gap = pd.Timedelta(hours=4)
    for s in spans:
        for t in spans:
            assert abs((s - t).total_seconds()) <= bar_gap.total_seconds() + 1


def test_rejects_fold_count_below_two():
    df = _synth_4h(100)
    with pytest.raises(ConfigurationError) as exc:
        split_folds(df, fold_count=1)
    assert exc.value.code == 'invalid-fold-count'


def test_rejects_insufficient_data_window():
    df = _synth_4h(20)    # very small input
    with pytest.raises(ConfigurationError) as exc:
        split_folds(df, fold_count=3)
    assert exc.value.code == 'insufficient-data-window'
    assert exc.value.system_status['bars'] == 20
