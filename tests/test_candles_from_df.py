"""Regression tests for `_candles_from_df` in src/api/app.py.

BUG-016: when the Date column is a parsed `Timestamp` and a separate
Time column exists, the old code produced
`"2025-07-28 00:00:00T18:21:00"` — the exact BUG-003 corruption pattern.
The fix normalises Date via `dt.strftime('%Y-%m-%d')` before concat.

All emitted timestamps must match `^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}$`.
"""

import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.app import _candles_from_df  # noqa: E402


TS_PATTERN = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$')


def _ohlcv(timestamps):
    """Build a synthetic OHLCV frame given any timestamp column shape."""
    # row count = length of the first value in `timestamps`
    n = len(next(iter(timestamps.values()))) if timestamps else 0
    base = {
        'Open': [20000.0] * n,
        'High': [20010.0] * n,
        'Low':  [19990.0] * n,
        'Close':[20005.0] * n,
        'Volume':[1000] * n,
    }
    return pd.DataFrame({**timestamps, **base})


def test_candles_with_string_date_only():
    df = _ohlcv({'Date': ['2025-01-01T09:30:00', '2025-01-01T09:45:00']})
    candles = _candles_from_df(df)
    assert len(candles) == 2
    for c in candles:
        assert TS_PATTERN.match(c.t), f"bad timestamp: {c.t!r}"


def test_candles_with_parsed_timestamp_date_only():
    # Date parsed to pandas Timestamp (no Time column).
    df = _ohlcv({'Date': pd.to_datetime([
        '2025-01-01 09:30:00', '2025-01-01 09:45:00',
    ])})
    candles = _candles_from_df(df)
    assert len(candles) == 2
    for c in candles:
        assert TS_PATTERN.match(c.t), f"bad timestamp: {c.t!r}"


# Canonical BUG-016 scenario: Date is a Timestamp AND Time exists.
def test_candles_with_timestamp_date_and_time_columns():
    df = _ohlcv({
        'Date': pd.to_datetime(['2025-07-28', '2025-07-28']),
        'Time': ['18:21:00', '18:22:00'],
    })
    candles = _candles_from_df(df)
    assert len(candles) == 2
    for c in candles:
        assert TS_PATTERN.match(c.t), f"BUG-016 reproduced: {c.t!r}"
    # Specifically: NOT `"2025-07-28 00:00:00T18:21:00"`
    assert candles[0].t == '2025-07-28T18:21:00'
    assert candles[1].t == '2025-07-28T18:22:00'


def test_candles_with_string_date_string_time():
    df = _ohlcv({
        'Date': ['2025-07-28', '2025-07-28'],
        'Time': ['18:21:00', '18:22:00'],
    })
    candles = _candles_from_df(df)
    for c in candles:
        assert TS_PATTERN.match(c.t)
    assert candles[0].t == '2025-07-28T18:21:00'


def test_empty_df_returns_empty_list():
    df = _ohlcv({'Date': []})
    assert _candles_from_df(df) == []


def test_missing_volume_column_raises_configuration_error():
    """No-fallback rule: a CSV missing the Volume column must NOT silently
    substitute zeros — it must raise ConfigurationError so the caller can
    show the user a concrete data-quality error."""
    import pytest
    from src.exceptions import ConfigurationError

    df = pd.DataFrame({
        'Date': pd.to_datetime(['2025-01-01 09:30:00']),
        'Open': [20000.0],
        'High': [20010.0],
        'Low':  [19990.0],
        'Close': [20005.0],
        # NOTE: no Volume column
    })
    with pytest.raises(ConfigurationError) as exc:
        _candles_from_df(df)
    assert exc.value.code == 'missing-candle-columns'
    assert 'Volume' in exc.value.system_status['missing_columns']
