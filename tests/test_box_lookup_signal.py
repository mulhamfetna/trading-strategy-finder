"""Tests for BoxLookup signal logic.

FIX-21 + FIX-20: get_signal_detail must expose a `conflict` flag when
weekly and monthly fire opposite directions. The aggregate `signal`
uses weekly-priority (existing behaviour, see box_lookup.get_signal).
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategy.box_lookup import BoxLookup


def _weekly_csv(path, **levels) -> None:
    """Build a weekly box CSV with only the named columns set."""
    cols = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
            'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
            'WTLU', 'WTLD', 'WTL1', 'WTL2']
    row = {c: levels.get(c) for c in cols}
    pd.DataFrame({'Date': ['2025-01-01'], **{c: [v] for c, v in row.items()}}).to_csv(path, index=False)


def _monthly_csv(path, **levels) -> None:
    cols = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
            'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
            'MTLU', 'MTLD', 'MTL1', 'MTL2']
    row = {c: levels.get(c) for c in cols}
    pd.DataFrame({'Date': ['2025-01-01'], **{c: [v] for c, v in row.items()}}).to_csv(path, index=False)


def test_no_signal_inside_active_box(tmp_path):
    # Both boxes cover the same range so close=102 sits inside both
    # (neither side fires; conflict flag must be False).
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv', MRHU=105.0, MRHD=100.0)
    lookup = BoxLookup(week_path=str(tmp_path / 'w.csv'), month_path=str(tmp_path / 'm.csv'), tick_threshold=0.75, weekly_window_days=7, monthly_window_days=30)
    detail = lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03'))
    assert detail['signal'] is None
    assert detail['conflict'] is False


def test_weekly_long_no_monthly(tmp_path):
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv', MRHU=205.0, MRHD=200.0)
    lookup = BoxLookup(week_path=str(tmp_path / 'w.csv'), month_path=str(tmp_path / 'm.csv'), tick_threshold=0.75, weekly_window_days=7, monthly_window_days=30)
    # close=106 > weekly RHU+0.75 → weekly LONG.
    # close=106 is between MRHU=205 and MRHD=200? No, 106 < 200. Below monthly box.
    # close < MRHD-0.75 (199.25)? Yes → monthly SHORT (not what we want here).
    # Pick monthly RHD below 106 to avoid the monthly short firing:
    _monthly_csv(tmp_path / 'm.csv', MRHU=205.0, MRHD=10.0)
    lookup = BoxLookup(week_path=str(tmp_path / 'w.csv'), month_path=str(tmp_path / 'm.csv'), tick_threshold=0.75, weekly_window_days=7, monthly_window_days=30)
    detail = lookup.get_signal_detail(close=106.0, ts=pd.Timestamp('2025-01-03'))
    assert detail['weekly_signal'] == 'long'
    assert detail['monthly_signal'] is None
    assert detail['conflict'] is False
    assert detail['signal'] == 'long'


def test_conflict_when_close_triggers_opposite_sides(tmp_path):
    """Construct a fixture where weekly fires LONG but monthly fires SHORT for
    the SAME close, then assert `conflict` is True."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=50.0, WRHD=45.0)       # weekly LONG above 50
    _monthly_csv(tmp_path / 'm.csv', MRLU=100.0, MRLD=95.0)     # monthly SHORT below 95
    lookup = BoxLookup(week_path=str(tmp_path / 'w.csv'), month_path=str(tmp_path / 'm.csv'), tick_threshold=0.75, weekly_window_days=7, monthly_window_days=30)

    # close=60: above weekly RHU=50+0.75 → weekly LONG;
    # below monthly RLD=95-0.75 → monthly SHORT.
    detail = lookup.get_signal_detail(close=60.0, ts=pd.Timestamp('2025-01-03'))
    assert detail['weekly_signal'] == 'long'
    assert detail['monthly_signal'] == 'short'
    assert detail['conflict'] is True
    # Aggregate still resolves via weekly-priority.
    assert detail['signal'] == 'long'
