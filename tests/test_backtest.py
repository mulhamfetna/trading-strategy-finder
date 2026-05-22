import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.loader import load_data
from src.data.splitter import filter_2025
from src.backtest.engine import run_backtest, calculate_max_drawdown
from src.backtest.metrics import calculate_metrics, calculate_max_drawdown_from_trades


def _both_hit_df():
    """Build a 2-candle DataFrame where the second candle's range hits both
    the TP and SL for a long entry at close=100 with TP=10% and SL=1%:

    - Entry candle: signal=1, Close=100, OHL trivial
    - Trigger candle: High=120 (>=110 = TP), Low=85 (<=99 = SL), Close varies
    """
    df = pd.DataFrame({
        'Date':   ['2025-09-01', '2025-09-02'],
        'Open':   [100.0, 100.0],
        'High':   [100.0, 120.0],
        'Low':    [100.0, 85.0],
        'Close':  [100.0, 100.0],  # close-only logic would NOT trigger an exit
        'signal': [1, 0],
    })
    return df


def test_run_backtest_conservative_resolution_assumes_sl_first():
    """Iter 4 (TODO item 10): when High >= TP AND Low <= SL in the same
    candle, conservative mode assumes SL hit first (worst case)."""
    df = _both_hit_df()

    trades, _ = run_backtest(
        df, initial_capital=10000, stop_loss=1.0, take_profit=10.0,
        slippage_pct=0.0, fee_per_trade=0.0,
        tp_sl_resolution='conservative',
    )

    assert len(trades) == 1
    assert trades[0]['exit_reason'] == 'STOP LOSS'
    assert trades[0]['profit_pct'] < 0


def test_run_backtest_optimistic_resolution_assumes_tp_first():
    """Optimistic mode assumes TP was reached first when both hit."""
    df = _both_hit_df()

    trades, _ = run_backtest(
        df, initial_capital=10000, stop_loss=1.0, take_profit=10.0,
        slippage_pct=0.0, fee_per_trade=0.0,
        tp_sl_resolution='optimistic',
    )

    assert len(trades) == 1
    assert trades[0]['exit_reason'] == 'TAKE PROFIT'
    assert trades[0]['profit_pct'] > 0


def test_run_backtest_direction_proxy_uses_candle_close_vs_open():
    """Direction-proxy mode uses the trigger candle's Close vs Open as a
    tiebreaker: green candle (Close > Open) -> TP first; red (Close < Open)
    -> SL first."""
    # Green candle case -> TP wins
    df = _both_hit_df()
    df.loc[1, 'Open'] = 90.0
    df.loc[1, 'Close'] = 115.0  # closed above open -> green

    trades, _ = run_backtest(
        df, initial_capital=10000, stop_loss=1.0, take_profit=10.0,
        slippage_pct=0.0, fee_per_trade=0.0,
        tp_sl_resolution='direction-proxy',
    )
    assert trades[0]['exit_reason'] == 'TAKE PROFIT'

    # Red candle case -> SL wins
    df = _both_hit_df()
    df.loc[1, 'Open'] = 115.0
    df.loc[1, 'Close'] = 90.0  # closed below open -> red

    trades, _ = run_backtest(
        df, initial_capital=10000, stop_loss=1.0, take_profit=10.0,
        slippage_pct=0.0, fee_per_trade=0.0,
        tp_sl_resolution='direction-proxy',
    )
    assert trades[0]['exit_reason'] == 'STOP LOSS'


def test_run_backtest_uses_high_low_for_single_side_hits():
    """When only ONE of TP/SL is hit (in any mode), the exit triggers on
    that side regardless of Close. This catches cases where the close-only
    legacy logic would miss intra-candle moves."""
    df = pd.DataFrame({
        'Date':  ['2025-09-01', '2025-09-02'],
        'Open':  [100.0, 100.0],
        'High':  [100.0, 115.0],  # hits TP=110
        'Low':   [100.0, 99.5],   # does NOT hit SL=99
        'Close': [100.0, 100.0],  # close-only logic would NOT trigger
        'signal': [1, 0],
    })

    trades, _ = run_backtest(
        df, initial_capital=10000, stop_loss=1.0, take_profit=10.0,
        slippage_pct=0.0, fee_per_trade=0.0,
    )

    assert len(trades) == 1
    assert trades[0]['exit_reason'] == 'TAKE PROFIT'


def test_run_backtest_resolution_default_is_conservative():
    """The default mode (no tp_sl_resolution arg) must be 'conservative'
    so existing callers get the safer behavior automatically."""
    df = _both_hit_df()

    trades, _ = run_backtest(
        df, initial_capital=10000, stop_loss=1.0, take_profit=10.0,
        slippage_pct=0.0, fee_per_trade=0.0,
        # no tp_sl_resolution arg
    )

    assert trades[0]['exit_reason'] == 'STOP LOSS'


def test_backtest_single_trade():
    df = load_data('NQ_15min_processed.csv')
    df = df.head(50).copy()
    df = df.reset_index(drop=True)
    if 'timestamps' in df.columns:
        df['Date'] = pd.to_datetime(df['timestamps'])
    df['signal'] = 0
    df.iloc[10, df.columns.get_loc('signal')] = 1
    
    trades, final_capital = run_backtest(df, initial_capital=10000, stop_loss=1.0, take_profit=2.0)
    assert isinstance(trades, list)
    assert isinstance(final_capital, (int, float))


def test_backtest_stop_loss():
    df = load_data('NQ_15min_processed.csv')
    df = df.head(50).copy()
    df = df.reset_index(drop=True)
    if 'timestamps' in df.columns:
        df['Date'] = pd.to_datetime(df['timestamps'])
    df['signal'] = 0
    df.iloc[10, df.columns.get_loc('signal')] = 1
    
    trades, _ = run_backtest(df, initial_capital=10000, stop_loss=0.5, take_profit=2.0)


def test_calculate_all_metrics():
    trades = [
        {'profit_pct': 1.5, 'profit_dollars': 150, 'capital_after': 10150},
        {'profit_pct': -0.5, 'profit_dollars': -50, 'capital_after': 10100},
        {'profit_pct': 2.0, 'profit_dollars': 200, 'capital_after': 10300},
    ]
    
    metrics = calculate_metrics(trades, 10000)
    
    assert 'total_profit' in metrics
    assert 'profit_factor' in metrics
    assert 'win_rate' in metrics
    assert 'sharpe_ratio' in metrics
    assert 'max_drawdown' in metrics
    assert metrics['total_profit'] == 300
    assert abs(metrics['win_rate'] - 66.67) < 1