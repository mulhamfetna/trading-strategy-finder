import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.loader import load_data
from src.data.splitter import filter_2025, filter_by_date_range, split_train_test
from src.data.resampler import resample_to_timeframe


def test_load_1min_data():
    df = load_data('1min.csv')
    assert 'Date' in df.columns
    assert 'Open' in df.columns
    assert len(df) > 0


def test_load_15min_data():
    df = load_data('NQ_15min_processed.csv')
    assert 'Open' in df.columns
    assert 'High' in df.columns


def test_filter_2025_data():
    df = load_data('1min.csv')
    df_2025 = filter_2025(df)
    assert df_2025['Date'].min() >= pd.Timestamp('2025-01-01')
    assert df_2025['Date'].max() <= pd.Timestamp('2025-09-30')


def test_split_train_test():
    df = load_data('1min.csv')
    df_2025 = filter_2025(df)
    train, test = split_train_test(df_2025, '2025-06-30')
    assert train['Date'].max() <= pd.Timestamp('2025-06-30')
    assert test['Date'].min() >= pd.Timestamp('2025-07-01')


def test_resample_1min_to_5min():
    df = load_data('1min.csv')
    df_2025 = filter_2025(df)
    df_5min = resample_to_timeframe(df_2025, '5min')
    assert len(df_5min) < len(df_2025)
    assert 'Open' in df_5min.columns


def test_resample_1min_to_15min():
    df = load_data('1min.csv')
    df_2025 = filter_2025(df)
    df_15min = resample_to_timeframe(df_2025, '15min')
    assert len(df_15min) < len(df_2025)


# --- Iter 5 (TODO item 9): generalized date-range filter ---

def _synth_daily_df(start_date: str, days: int) -> pd.DataFrame:
    """Build a synthetic daily DataFrame with a Date column."""
    dates = pd.date_range(start=start_date, periods=days, freq='D')
    return pd.DataFrame({
        'Date': dates,
        'Open': [100.0] * days,
        'High': [101.0] * days,
        'Low':  [99.0] * days,
        'Close': [100.5] * days,
        'Volume': [1000] * days,
    })


def test_filter_by_date_range_inclusive_boundaries():
    df = _synth_daily_df('2025-09-01', days=30)

    out = filter_by_date_range(df, start='2025-09-10', end='2025-09-20')

    assert out['Date'].min() == pd.Timestamp('2025-09-10')
    assert out['Date'].max() == pd.Timestamp('2025-09-20')
    assert len(out) == 11  # 10..20 inclusive


def test_filter_by_date_range_excludes_outside_rows():
    df = _synth_daily_df('2025-08-01', days=120)

    out = filter_by_date_range(df, start='2025-09-01', end='2025-12-31')

    assert (out['Date'] >= pd.Timestamp('2025-09-01')).all()
    assert (out['Date'] <= pd.Timestamp('2025-12-31')).all()


def test_filter_by_date_range_crosses_year_boundary():
    """A range spanning 2025-09 to 2026-06 must keep all the days in
    between (this is exactly TODO item 9's intended use case)."""
    df = _synth_daily_df('2025-08-01', days=400)

    out = filter_by_date_range(df, start='2025-09-01', end='2026-06-30')

    # Range covers both 2025 and 2026 dates
    has_2025 = (out['Date'].dt.year == 2025).any()
    has_2026 = (out['Date'].dt.year == 2026).any()
    assert has_2025 and has_2026
    # Out-of-range dates excluded
    assert out['Date'].min() == pd.Timestamp('2025-09-01')
    assert out['Date'].max() == pd.Timestamp('2026-06-30')


def test_filter_by_date_range_works_with_timestamps_column():
    """Some CSVs use 'timestamps' instead of 'Date'. Both must work."""
    df = _synth_daily_df('2025-09-01', days=10)
    df = df.rename(columns={'Date': 'timestamps'})

    out = filter_by_date_range(df, start='2025-09-03', end='2025-09-07')

    assert len(out) == 5
    assert 'Date' in out.columns or 'timestamps' in out.columns


def test_filter_2025_still_works_as_before():
    """Backwards compatibility: filter_2025 still produces the Jan-Sep
    2025 slice (it now delegates to filter_by_date_range)."""
    df = load_data('1min.csv')
    df_2025 = filter_2025(df)
    assert df_2025['Date'].min() >= pd.Timestamp('2025-01-01')
    assert df_2025['Date'].max() <= pd.Timestamp('2025-09-30')