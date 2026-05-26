"""Tests for SimpleStrategy — Stage 1 entry + dual-SL/TP exit.

Synthetic tests pin the engine's per-rule behaviour; the real-data lock
pins counts against `data/full_data/NQ_4h.csv` + `NQ_1m.csv` for
sl_soft=100, sl_hard=200, tp=150. Skipped automatically if data files
are missing.
"""
from __future__ import annotations

import os

import pandas as pd
import pytest

from src.strategy.simple_strategy import (
    SimpleStrategy,
    SimpleStrategyParams,
    _stage1_candle_signal,
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
    return pd.Series({upper_col: upper, lower_col: lower})

def _params(ss=100, sh=200, tp=150, scope='both'):
    return SimpleStrategyParams(
        sl_soft_points=ss, sl_hard_points=sh, tp_points=tp,
        data_path_4h='/dev/null', data_path_1min='/dev/null',
        box_data_path='/dev/null',
        direction_scope=scope,
    )


# ---------- Construction / validation ------------------------------------

def test_params_reject_hard_below_soft():
    with pytest.raises(ValueError):
        SimpleStrategy(_params(ss=200, sh=100, tp=150))


def test_params_accept_hard_equal_soft():
    SimpleStrategy(_params(ss=100, sh=100, tp=150))


def test_params_reject_non_positive():
    with pytest.raises(ValueError):
        SimpleStrategy(_params(ss=0, sh=200, tp=150))
    with pytest.raises(ValueError):
        SimpleStrategy(_params(ss=100, sh=200, tp=-1))


# ---------- Stage 1 candle-level signal helper ---------------------------

def test_stage1_signal_long_when_green_breaks_upper():
    c = _candle('2025-01-01 10:00:00', o=100, h=110, l=99, c=105)
    box = _box_row_one_pair(upper=103, lower=98)
    assert _stage1_candle_signal(c, box) == 'long'


def test_stage1_signal_short_when_red_breaks_lower():
    c = _candle('2025-01-01 10:00:00', o=110, h=112, l=95, c=99)
    box = _box_row_one_pair(upper=108, lower=100)
    assert _stage1_candle_signal(c, box) == 'short'


def test_stage1_signal_hold_when_not_touched():
    c = _candle('2025-01-01 10:00:00', o=100, h=101, l=99, c=100.5)
    box = _box_row_one_pair(upper=200, lower=150)
    assert _stage1_candle_signal(c, box) == 'hold'


def test_stage1_signal_hold_when_doji():
    c = _candle('2025-01-01 10:00:00', o=100, h=110, l=90, c=100)
    box = _box_row_one_pair(upper=99, lower=95)
    assert _stage1_candle_signal(c, box) == 'hold'


def test_stage1_signal_hold_when_close_on_edge():
    c = _candle('2025-01-01 10:00:00', o=100, h=110, l=99, c=103)
    box = _box_row_one_pair(upper=103, lower=98)
    assert _stage1_candle_signal(c, box) == 'hold'


def test_stage1_signal_hold_when_no_box_row():
    c = _candle('2025-01-01 10:00:00', o=100, h=110, l=99, c=105)
    assert _stage1_candle_signal(c, None) == 'hold'


# ---------- Backtest engine — synthetic ---------------------------------

def _box_indexed(upper, lower, upper_col='WRHU', lower_col='WRHD', date='2025-01-01'):
    df = pd.DataFrame([{
        'Date': pd.Timestamp(date),
        upper_col: upper,
        lower_col: lower,
    }])
    df['Date'] = pd.to_datetime(df['Date']).dt.normalize()
    return df.set_index('Date', drop=False)


def test_backtest_empty_returns_no_trades():
    strat = SimpleStrategy(_params())
    trades, state = strat.backtest(
        pd.DataFrame(columns=['Date','Open','High','Low','Close']),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert trades == []
    assert state == {'open_trade': None}


def test_backtest_hard_sl_long_touch_fills_at_line():
    """Long position; 1-min low touches hard SL → exit at hard SL line.

    No-look-ahead timing: bar 0 (06:00) fires the long signal (green,
    touched, close > BU). Bar 1 (10:00) is the entry-window — 1-min low
    touches hard SL.
    """
    df_4h = pd.DataFrame([
        # signal bar: green, touched, close=105 > BU=103 → fires LONG at close
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
        # entry bar: 1-min stream below triggers exits
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low':  95, 'Close': 100, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low': 95, 'Close': 100, 'Volume': 0},
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(ss=5, sh=8, tp=10))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 1
    t = trades[0]
    assert t['direction']    == 'long'
    assert t['signal_idx']   == 0          # bar 06:00 fired the signal
    assert t['entry_idx']    == 1          # entry at bar 10:00's start
    assert t['entry_time']   == pd.Timestamp('2025-01-01 10:00:00')
    assert t['entry_price']  == 105        # = bar 0 close
    assert t['exit_reason']  == 'STOP_LOSS_HARD'
    assert t['exit_price']   == 97         # hard SL line (105 - 8)
    assert t['pnl_points']   == -8


def test_backtest_tp_long_touch_fills_at_line():
    """Long position; 1-min high touches TP → exit at TP line."""
    df_4h = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 121, 'Low': 104, 'Close': 110, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 120, 'Low': 104, 'Close': 110, 'Volume': 0},
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(ss=5, sh=8, tp=10))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 1
    t = trades[0]
    assert t['exit_reason']  == 'TAKE_PROFIT'
    assert t['exit_price']   == 115        # tp line (105 + 10)
    assert t['pnl_points']   == 10


def test_backtest_soft_sl_needs_two_consecutive_closes():
    df_4h = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low':  97, 'Close': 98,  'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low': 98, 'Close': 99, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:01:00'), 'Open': 99,  'High': 100, 'Low': 97, 'Close': 98, 'Volume': 0},
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(ss=5, sh=20, tp=50))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 1
    t = trades[0]
    assert t['exit_reason']  == 'STOP_LOSS_SOFT'
    assert t['exit_price']   == 98          # 2nd close, not the line
    assert t['pnl_points']   == -7          # 98 - 105


def test_backtest_soft_sl_counter_resets_on_recovery():
    df_4h = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low': 99, 'Close': 99,  'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 106, 'Low': 99, 'Close': 99,  'Volume': 0},  # counter=1
        {'Date': pd.Timestamp('2025-01-01 10:01:00'), 'Open': 99,  'High': 105, 'Low': 99, 'Close': 101, 'Volume': 0},  # counter=0
        {'Date': pd.Timestamp('2025-01-01 10:02:00'), 'Open': 101, 'High': 102, 'Low': 99, 'Close': 99,  'Volume': 0},  # counter=1
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(ss=5, sh=50, tp=100))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 1
    assert trades[0]['exit_reason'] == 'OPEN'


def test_backtest_hard_sl_beats_tp_in_same_bar():
    """Hard SL > TP > soft SL priority. If a single bar's low touches hard
    SL AND its high touches TP, hard SL wins."""
    df_4h = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 120, 'Low': 90, 'Close': 110, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        # bar spans 90..120: low touches hard SL=97; high touches TP=115. Hard SL wins.
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 120, 'Low': 90, 'Close': 110, 'Volume': 0},
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(ss=5, sh=8, tp=10))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert trades[0]['exit_reason'] == 'STOP_LOSS_HARD'
    assert trades[0]['exit_price']  == 97


def test_backtest_short_hard_sl():
    """Short position; 1-min high touches hard SL above entry → fire."""
    df_4h = pd.DataFrame([
        # signal bar: red, touched, close=99 < BL=100 → fires SHORT
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 110, 'High': 112, 'Low': 95, 'Close': 99, 'Volume': 0},
        # entry bar: 1-min high 110 crosses hard SL line (99+8=107) → SL_HARD
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 99,  'High': 110, 'Low': 98, 'Close': 100, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 99, 'High': 110, 'Low': 98, 'Close': 100, 'Volume': 0},
    ])
    box = _box_indexed(upper=108, lower=100)
    strat = SimpleStrategy(_params(ss=5, sh=8, tp=10))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert trades[0]['direction']   == 'short'
    assert trades[0]['exit_reason'] == 'STOP_LOSS_HARD'
    assert trades[0]['exit_price']  == 107       # hard SL line (99 + 8)
    assert trades[0]['pnl_points']  == -8


def test_backtest_open_at_eof_yields_open():
    """A trade still open at EOF emits with exit_reason='OPEN' and null pnl."""
    df_4h = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 100, 'High': 110, 'Low': 99, 'Close': 105, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 105.1, 'Low': 104.9, 'Close': 105, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 105.1, 'Low': 104.9, 'Close': 105, 'Volume': 0},
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(ss=100, sh=200, tp=100))
    trades, state = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 1
    assert trades[0]['exit_reason'] == 'OPEN'
    assert trades[0]['exit_time']   is None
    assert trades[0]['pnl_points']  is None
    assert state['open_trade'] is not None


def test_backtest_reentry_gate_blocks_until_next_4h_start():
    """After exit at T inside 4h window N, next signal-eligible 4h must
    have Date > T.

    No-look-ahead timing: bar 0 (06:00) is the warm-up signal that fires
    LONG. Trade enters at bar 1 (10:00). TP hits inside the 10:00 4h
    window. Bar 2 (14:00) also fires LONG (green, touched, close > BU)
    — re-entry gate passes because bar 2's Date is after the exit time.
    """
    df_4h = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 100, 'High': 110, 'Low':  99, 'Close': 105, 'Volume': 0},   # signal for trade 1
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 120, 'Low':  99, 'Close': 115, 'Volume': 0},   # entry bar for trade 1 + signal for trade 2 (green, touched 99≤103, 115>103)
        {'Date': pd.Timestamp('2025-01-01 14:00:00'), 'Open': 115, 'High': 125, 'Low': 114, 'Close': 120, 'Volume': 0},   # entry bar for trade 2
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 105, 'High': 120, 'Low': 104, 'Close': 110, 'Volume': 0},   # TP at 105+10=115
        {'Date': pd.Timestamp('2025-01-01 14:00:00'), 'Open': 115, 'High': 125, 'Low': 114, 'Close': 120, 'Volume': 0},   # TP at 115+10=125
    ])
    box = _box_indexed(upper=103, lower=98)
    strat = SimpleStrategy(_params(ss=5, sh=20, tp=10))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert len(trades) == 2
    assert trades[0]['entry_time']  == pd.Timestamp('2025-01-01 10:00:00')
    assert trades[1]['entry_time']  == pd.Timestamp('2025-01-01 14:00:00')
    assert trades[1]['exit_reason'] == 'TAKE_PROFIT'


def test_backtest_direction_scope_long_only():
    df_4h = pd.DataFrame([
        # signal bar: red, touched, close < BL → would fire SHORT
        {'Date': pd.Timestamp('2025-01-01 06:00:00'), 'Open': 110, 'High': 112, 'Low': 95, 'Close': 99, 'Volume': 0},
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 99,  'High': 100, 'Low': 98, 'Close': 99.5, 'Volume': 0},
    ])
    df_1m = pd.DataFrame([
        {'Date': pd.Timestamp('2025-01-01 10:00:00'), 'Open': 99, 'High': 100, 'Low': 98, 'Close': 99.5, 'Volume': 0},
    ])
    box = _box_indexed(upper=108, lower=100)
    strat = SimpleStrategy(_params(scope='long_only'))
    trades, _ = strat.backtest(df_4h, df_1m, box)
    assert trades == []   # short signal blocked by scope


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
        sl_soft_points=100, sl_hard_points=200, tp_points=150,
        data_path_4h=_4H, data_path_1min=_1M, box_data_path=_BOX,
    )
    return SimpleStrategy(p).backtest(df_4h, df_1m, box)


@pytestmark_realdata
def test_real_data_lock_counts(real_trades):
    trades, _ = real_trades
    import collections
    by_reason = dict(collections.Counter(t['exit_reason'] for t in trades))
    assert len(trades) == 594
    assert by_reason == {'TAKE_PROFIT': 271, 'STOP_LOSS_SOFT': 315, 'STOP_LOSS_HARD': 8}


@pytestmark_realdata
def test_real_data_lock_directions(real_trades):
    trades, _ = real_trades
    import collections
    by_dir = dict(collections.Counter(t['direction'] for t in trades))
    assert by_dir == {'long': 309, 'short': 285}


@pytestmark_realdata
def test_real_data_lock_total_pnl(real_trades):
    trades, _ = real_trades
    total = sum(t['pnl_dollars'] for t in trades if t['pnl_dollars'] is not None)
    assert total == pytest.approx(65555.0)


@pytestmark_realdata
def test_real_data_lock_first_trade(real_trades):
    """Under no-look-ahead timing: the first trade's signal comes from
    bar 0 (Date 2025-01-01 18:00); the trade enters at bar 1's start
    (Date 22:00 = bar 0's close) at price 21322.25 (= bar 0's close)."""
    trades, _ = real_trades
    t = trades[0]
    assert t['entry_idx']   == 1
    assert t['signal_idx']  == 0
    assert t['entry_time']  == pd.Timestamp('2025-01-01 22:00:00')
    assert t['direction']   == 'long'
    assert t['entry_price'] == 21322.25
    assert t['exit_reason'] == 'TAKE_PROFIT'
    assert t['exit_price']  == pytest.approx(21472.25)
    assert t['pnl_points']  == pytest.approx(150.0)


@pytestmark_realdata
def test_real_data_no_lookahead_invariant(real_trades):
    """No trade's exit can happen before its entry; entry_idx and
    signal_idx differ by exactly 1 (signal fires from the just-closed
    predecessor bar)."""
    trades, _ = real_trades
    for t in trades:
        assert t['entry_idx'] == t['signal_idx'] + 1
        if t['exit_time'] is not None:
            assert t['exit_time'] >= t['entry_time']


@pytestmark_realdata
def test_real_data_hard_sl_fills_at_line(real_trades):
    """Every hard-SL exit should fill exactly at the hard SL line."""
    trades, _ = real_trades
    for t in trades:
        if t['exit_reason'] == 'STOP_LOSS_HARD':
            assert t['exit_price'] == t['sl_hard_line']


@pytestmark_realdata
def test_real_data_tp_fills_at_line(real_trades):
    """Every TP exit should fill exactly at the TP line."""
    trades, _ = real_trades
    for t in trades:
        if t['exit_reason'] == 'TAKE_PROFIT':
            assert t['exit_price'] == t['tp_line']


@pytestmark_realdata
def test_real_data_soft_sl_pnl_is_worse_than_line(real_trades):
    """Soft SL fills at a close beyond the line, so |pnl| >= |sl_soft_points|."""
    trades, _ = real_trades
    for t in trades:
        if t['exit_reason'] == 'STOP_LOSS_SOFT':
            # pnl_points is negative; abs >= sl_soft_points (=100)
            assert -t['pnl_points'] >= 100 - 1e-9, (
                f"soft SL pnl {t['pnl_points']} not worse-or-equal to -100 at {t['entry_time']}"
            )


@pytestmark_realdata
def test_real_data_reentry_gate_holds(real_trades):
    trades, _ = real_trades
    for i in range(1, len(trades)):
        prev = trades[i - 1]
        cur  = trades[i]
        if prev['exit_time'] is None:
            continue
        assert cur['entry_time'] > prev['exit_time']
