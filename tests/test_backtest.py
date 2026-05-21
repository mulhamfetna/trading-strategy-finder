import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.loader import load_data
from src.data.splitter import filter_2025
from src.backtest.engine import run_backtest, calculate_max_drawdown
from src.backtest.metrics import calculate_metrics, calculate_max_drawdown_from_trades


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


def test_run_period_backtest_reports_requested_vs_actual_coverage():
    import pandas as pd
    from src.main.backtest_runner import compute_coverage_metadata

    df = pd.DataFrame(
        {
            'Date': pd.to_datetime(['2025-09-05', '2025-09-06']),
            'Open': [1, 1],
            'High': [1, 1],
            'Low': [1, 1],
            'Close': [1, 1],
            'Volume': [1, 1],
        }
    )

    coverage = compute_coverage_metadata(
        df=df,
        requested_start='2025-09-01',
        requested_end='2025-12-31',
    )

    assert coverage['requested_start'] == '2025-09-01'
    assert coverage['requested_end'] == '2025-12-31'
    assert coverage['actual_start'] == '2025-09-05'
    assert coverage['actual_end'] == '2025-09-06'
    assert coverage['has_gap'] is True


def test_run_period_backtest_returns_metrics_trades_and_coverage():
    import pandas as pd
    from src.main.backtest_runner import run_period_backtest

    df = pd.DataFrame(
        {
            'Date': pd.to_datetime(['2025-09-05', '2025-09-06', '2025-09-07']),
            'Time': ['10:00:00', '10:15:00', '10:30:00'],
            'Open': [100, 100, 100],
            'High': [101, 101, 101],
            'Low': [99, 99, 99],
            'Close': [100, 100.5, 100.2],
            'Volume': [10, 10, 10],
        }
    )

    result = run_period_backtest(
        df=df,
        requested_start='2025-09-01',
        requested_end='2025-12-31'
    )

    assert 'metrics' in result
    assert 'trades' in result
    assert 'coverage' in result