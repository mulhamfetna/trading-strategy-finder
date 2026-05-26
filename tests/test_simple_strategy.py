"""Tests for SimpleStrategy — Stage 1 entry + 1-min SL/TP exit.

Synthetic tests pin the engine's per-rule behaviour; the real-data lock
pins counts against `data/full_data/NQ_4h.csv` + `NQ_1m.csv` for
sl=100, tp=150. Skipped automatically if data files are missing.
"""
from __future__ import annotations

import os

import pandas as pd
import pytest

from src.strategy.simple_strategy import (
    SimpleStrategy,
    SimpleStrategyParams,
    _stage1_candle_signal,
    _exit_check_close_past,
)


_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_4H  = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_4h.csv')
_1M  = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_1m.csv')
_BOX = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_full_data.csv')


# ---------- Helpers ------------------------------------------------------

def _candle(dt, o, h, l, c):
    return pd.Series({
        'Date': pd.Timestamp(dt),
        'Open': o, 'High': h, 'Low': l, 'Close': c,
        'Volume': 0,
    })

def _box_row_one_pair(upper: float, lower: float, upper_col: str = 'WRHU', lower_col: str = 'WRHD'):
    """Build a one-row box Series with a single level pair. Defaults to W-RH."""
    return pd.Series({upper_col: upper, lower_col: lower})

def _params(sl=100, tp=150, scope='both'):
    return SimpleStrategyParams(
        sl_points=sl, tp_points=tp,
        data_path_4h='/dev/null', data_path_1min='/dev/null',
        box_data_path='/dev/null',
        direction_scope=scope,
    )


# ---------- Stage 1 candle-level signal helper ---------------------------

def test_stage1_signal_long_when_green_breaks_upper():
    c = _candle('2025-01-01 10:00:00', o=100, h=110, l=99, c=105)  # green, touched
    box = _box_row_one_pair(upper=103, lower=98)
    assert _stage1_candle_signal(c, box) == 'long'  # close 105 > BU 103


def test_stage1_signal_short_when_red_breaks_lower():
    c = _candle('2025-01-01 10:00:00', o=110, h=112, l=95, c=99)  # red, touched
    box = _box_row_one_pair(upper=108, lower=100)
    assert _stage1_candle_signal(c, box) == 'short'  # close 99 < BL 100


def test_stage1_signal_hold_when_not_touched():
    c = _candle('2025-01-01 10:00:00', o=100, h=101, l=99, c=100.5)
    box = _box_row_one_pair(upper=200, lower=150)  # way above
    assert _stage1_candle_signal(c, box) == 'hold'


def test_stage1_signal_hold_when_doji():
    c = _candle('2025-01-01 10:00:00', o=100, h=110, l=90, c=100)  # close == open
    box = _box_row_one_pair(upper=99, lower=95)
    assert _stage1_candle_signal(c, box) == 'hold'


def test_stage1_signal_hold_when_close_on_edge():
    c = _candle('2025-01-01 10:00:00', o=100, h=110, l=99, c=103)  # close == BU
    box = _box_row_one_pair(upper=103, lower=98)
    assert _stage1_candle_signal(c, box) == 'hold'  # strict > rule


def test_stage1_signal_hold_when_no_box_row():
    c = _candle('2025-01-01 10:00:00', o=100, h=110, l=99, c=105)
    assert _stage1_candle_signal(c, None) == 'hold'


# ---------- Exit check helper -------------------------------------------

def test_exit_check_long_take_profit():
    assert _exit_check_close_past('long', tp_line=110, sl_line=90, one_min_close=110.0) == 'TAKE_PROFIT'
    assert _exit_check_close_past('long', tp_line=110, sl_line=90, one_min_close=109.99) is None


def test_exit_check_long_stop_loss():
    assert _exit_check_close_past('long', tp_line=110, sl_line=90, one_min_close=90.0) == 'STOP_LOSS'
    assert _exit_check_close_past('long', tp_line=110, sl_line=90, one_min_close=90.01) is None


def test_exit_check_short_take_profit():
    assert _exit_check_close_past('short', tp_line=90, sl_line=110, one_min_close=90.0) == 'TAKE_PROFIT'
    assert _exit_check_close_past('short', tp_line=90, sl_line=110, one_min_close=90.01) is None


def test_exit_check_short_stop_loss():
    assert _exit_check_close_past('short', tp_line=90, sl_line=110, one_min_close=110.0) == 'STOP_LOSS'


def test_exit_check_no_action_inside_band():
    assert _exit_check_close_past('long', tp_line=110, sl_line=90, one_min_close=100.0) is None
    assert _exit_check_close_past('short', tp_line=90, sl_line=110, one_min_close=100.0) is None


# ---------- Backtest engine — synthetic ---------------------------------

def _box_indexed(upper, lower, upper_col='WRHU', lower_col='WRHD', date='2025-01-01'):
    """Build a single-row box DataFrame indexed on `Date`. Defaults to W-RH."""
    df = pd.DataFrame([{
        'Date': pd.Timestamp(date),
        upper_col: upper,
        lower_col: lower,
    }])
    df['Date'] = pd.to_datetime(df['Date']).dt.normalize()
    return df.set_index('Date', drop=False)


def test_backtest_empty_returns_no_trades():
    strat = SimpleStrategy(_params())
    trades, state = strat.backtest(pd.DataFrame(columns=['Date','Open','High','Low','Close']), pd.DataFrame(), pd.DataFrame())
    assert trades == []
    assert state == {'open_trade': None}


def test_backtest_long_take_profit():
    """Green 4h candle breaks the box upper → long signal → TP fires when
    a 1-min close crosses entry_close + tp_points."""
    df_4h = pd.DataFrame([
        # entry: green, touched, close > BU=103 → long
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
    ])
    # 1-min data: a few flat bars then a TP hit at 105 + 150 = 255 (use tp=5 instead)
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low': 105, 'Close': 105.5, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:01:00'), 'Open': 105.5, 'High': 112, 'Low': 105, 'Close': 110.5, 'Volume': 0},
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(sl=10, tp=5))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 1
    t = trades[0]
    assert t['direction'] == 'long'
    assert t['exit_reason'] == 'TAKE_PROFIT'
    assert t['entry_price'] == 105
    assert t['tp_line'] == 110
    assert t['exit_time'] == pd.Timestamp('2025-01-01 10:01:00')
    assert t['exit_price'] == 110.5         # close-past fill
    assert t['pnl_points'] == 5.5            # 110.5 - 105


def test_backtest_short_stop_loss():
    """Red 4h candle breaks the box lower → short signal → SL fires."""
    df_4h = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 110, 'High': 112, 'Low': 95, 'Close': 99, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 99,    'High': 100,  'Low': 98.5,  'Close': 99.5, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:01:00'), 'Open': 99.5,  'High': 105,  'Low': 99,    'Close': 104,  'Volume': 0},
    ])
    box = _box_indexed(upper=108, lower=100)
    strat = SimpleStrategy(_params(sl=4, tp=5))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 1
    t = trades[0]
    assert t['direction'] == 'short'
    assert t['exit_reason'] == 'STOP_LOSS'
    assert t['entry_price'] == 99
    assert t['sl_line'] == 103
    assert t['exit_time'] == pd.Timestamp('2025-01-01 10:01:00')
    assert t['exit_price'] == 104           # close-past fill
    assert t['pnl_points'] == -5            # short pnl: 99 - 104 = -5


def test_backtest_reentry_gate_blocks_partial_4h():
    """After exit mid-4h, the next 4h candle must START strictly after
    the exit_time. Same 4h as the entry → blocked (exit_time is inside it,
    so its start ≤ exit_time)."""
    df_4h = pd.DataFrame([
        # bar 0 (18:00-22:00): triggers long, TP fires inside
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
        # bar 1 (14:00 — eligible: start > prev exit_time 10:01)
        # touches box (low 99 <= BU 103) and closes above → long signal
        {'Date': pd.Timestamp('2025-01-01 14:00:00'), 'Open': 110, 'High': 120, 'Low': 99, 'Close': 115, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        # 1-min bars for bar 0: TP at 18:01
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low': 105, 'Close': 105.5, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:01:00'), 'Open': 105.5, 'High': 112, 'Low': 105, 'Close': 110.5, 'Volume': 0},
        # 1-min bars for bar 1: held, TP at 22:30
        {'Date': pd.Timestamp('2025-01-01 14:00:00'), 'Open': 115, 'High': 116, 'Low': 114, 'Close': 115, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 14:30:00'), 'Open': 115, 'High': 125, 'Low': 115, 'Close': 121, 'Volume': 0},
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(sl=10, tp=5))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 2
    assert trades[0]['entry_time']  == pd.Timestamp('2025-01-01 10:00:00')
    assert trades[0]['exit_time']   == pd.Timestamp('2025-01-01 10:01:00')
    assert trades[1]['entry_time']  == pd.Timestamp('2025-01-01 14:00:00')
    # bar 1 closes at 115, tp_line = 115 + 5 = 120; 22:30 closes at 121 → TP
    assert trades[1]['exit_reason'] == 'TAKE_PROFIT'


def test_backtest_open_at_eof():
    """A trade still open at EOF emits with exit_reason='OPEN'."""
    df_4h = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        # 1-min bars that never reach TP (105+100=205) or SL (105-100=5)
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low': 104, 'Close': 105.5, 'Volume': 0},
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(sl=100, tp=100))
    trades, state = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 1
    assert trades[0]['exit_reason'] == 'OPEN'
    assert trades[0]['exit_time']   is None
    assert trades[0]['pnl_points']  is None
    assert state['open_trade'] is not None


def test_backtest_direction_scope_long_only():
    """direction_scope='long_only' skips short signals."""
    df_4h = pd.DataFrame([
        # red 4h that would fire short
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 110, 'High': 112, 'Low': 95, 'Close': 99, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 99, 'High': 100, 'Low': 98, 'Close': 99.5, 'Volume': 0},
    ])
    box = _box_indexed(upper=108, lower=100)
    strat = SimpleStrategy(_params(scope='long_only'))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert trades == []


# ---------- Real-data lock (skipped if files absent) --------------------

pytestmark_realdata = pytest.mark.skipif(
    not (os.path.exists(_4H) and os.path.exists(_1M) and os.path.exists(_BOX)),
    reason='Real-data CSVs not present.',
)


@pytest.fixture(scope='module')
def real_trades():
    from src.data.loader import load_data
    df_4h = load_data(_4H)
    df_1m = load_data(_1M)
    box = pd.read_csv(_BOX)
    box['Date'] = pd.to_datetime(box['Date']).dt.normalize()
    box = box.set_index('Date', drop=False)
    p = SimpleStrategyParams(
        sl_points=100, tp_points=150,
        data_path_4h=_4H, data_path_1min=_1M, box_data_path=_BOX,
    )
    return SimpleStrategy(p).backtest(df_4h, df_1m, box)


@pytestmark_realdata
def test_real_data_lock_counts(real_trades):
    trades, _ = real_trades
    import collections
    by_reason = dict(collections.Counter(t['exit_reason'] for t in trades))
    assert len(trades) == 604
    assert by_reason == {'STOP_LOSS': 516, 'TAKE_PROFIT': 87, 'OPEN': 1}


@pytestmark_realdata
def test_real_data_lock_first_trade(real_trades):
    trades, _ = real_trades
    t = trades[0]
    assert t['entry_time']  == pd.Timestamp('2025-01-01 18:00:00')
    assert t['direction']   == 'long'
    assert t['entry_price'] == 21322.25
    assert t['exit_time']   == pd.Timestamp('2025-01-01 19:10:00')
    assert t['exit_reason'] == 'STOP_LOSS'
    assert t['pnl_points']  == pytest.approx(-104.5)


@pytestmark_realdata
def test_real_data_lock_directions(real_trades):
    trades, _ = real_trades
    import collections
    by_dir = dict(collections.Counter(t['direction'] for t in trades))
    assert by_dir == {'long': 312, 'short': 292}


@pytestmark_realdata
def test_real_data_lock_total_pnl(real_trades):
    trades, _ = real_trades
    total = sum(t['pnl_dollars'] for t in trades if t['pnl_dollars'] is not None)
    assert total == pytest.approx(-1455105.0)


@pytestmark_realdata
def test_real_data_reentry_gate_holds(real_trades):
    """After an exit at T, the next trade's entry_time must be > T."""
    trades, _ = real_trades
    for i in range(1, len(trades)):
        prev = trades[i - 1]
        cur  = trades[i]
        if prev['exit_time'] is None:
            continue  # last trade was OPEN; should be the final one
        assert cur['entry_time'] > prev['exit_time'], (
            f"trade {i} entered at {cur['entry_time']} but prev exited at {prev['exit_time']}"
        )
