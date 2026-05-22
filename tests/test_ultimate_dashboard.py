import os
import sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main.ultimate_dashboard import apply_rsi_entry_filters, generate_html, run_backtest_15min


def test_apply_rsi_entry_filters_keeps_valid_longs_and_shorts():
    signals = np.array([1, -1, -1, 1, 0])
    rsi_values = np.array([20.0, 76.0, 70.0, 30.0, 80.0])

    filtered = apply_rsi_entry_filters(signals, rsi_values, oversold=25, overbought=75)

    assert filtered.tolist() == [1, -1, 0, 0, 0]


def test_generate_html_has_single_total_fees_label(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    os.makedirs('docs', exist_ok=True)

    data = {
        'metrics': {
            'net_profit': 100.0,
            'final_capital': 10100.0,
            'total_fees': 20.0,
            'profit_factor': 1.5,
            'total_trades': 2,
            'sharpe_ratio': 0.2,
            'win_rate': 50.0,
            'max_drawdown': 1.0,
            'avg_profit': 60.0,
            'avg_loss': -20.0,
            'expected_value': 20.0,
            'max_consecutive_losses': 1,
            'gross_profit': 120.0
        },
        'trades': [],
        'logs': [],
        'insights': {'key_findings': [], 'recommendations': []},
        'chart_data': {
            'dates': [],
            'opens': [],
            'highs': [],
            'lows': [],
            'closes': [],
            'volumes': [],
            'ema_5': [],
            'ema_15': [],
            'rsi': [],
            'volume_spike': [],
            'trade_markers': []
        },
        'params': {
            'rsi_period': 5,
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'ema_fast': 5,
            'ema_slow': 15,
            'volume_threshold': 1.0,
            'stop_loss': 0.6,
            'take_profit': 2.4
        },
        'final_capital': 10100.0,
        'total_return': 1.0
    }

    generate_html(data)

    html = (tmp_path / 'docs' / 'ultimate_trading_dashboard.html').read_text(encoding='utf-8')
    assert html.count('>Total Fees<') == 1
    assert '>Total Trades<' in html


def test_generate_html_uses_candlestick_chart(tmp_path, monkeypatch):
    """Iter 1 (TODO item 3): main chart must be a candlestick (not a close-line)
    and the dashboard body must surface latest open/close/high/low values."""
    monkeypatch.chdir(tmp_path)
    os.makedirs('docs', exist_ok=True)

    data = {
        'metrics': {
            'net_profit': 100.0,
            'final_capital': 10100.0,
            'total_fees': 20.0,
            'profit_factor': 1.5,
            'total_trades': 2,
            'sharpe_ratio': 0.2,
            'win_rate': 50.0,
            'max_drawdown': 1.0,
            'avg_profit': 60.0,
            'avg_loss': -20.0,
            'expected_value': 20.0,
            'max_consecutive_losses': 1,
            'gross_profit': 120.0
        },
        'trades': [],
        'logs': [],
        'insights': {'key_findings': [], 'recommendations': []},
        'chart_data': {
            'dates': ['2025-09-01 09:30:00'],
            'opens': [100.0],
            'highs': [101.0],
            'lows': [99.5],
            'closes': [100.5],
            'volumes': [1000],
            'ema_5': [100.25],
            'ema_15': [100.1],
            'rsi': [50.0],
            'volume_spike': [False],
            'trade_markers': []
        },
        'params': {
            'rsi_period': 5,
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'ema_fast': 5,
            'ema_slow': 15,
            'volume_threshold': 1.0,
            'stop_loss': 0.6,
            'take_profit': 2.4
        },
        'final_capital': 10100.0,
        'total_return': 1.0
    }

    generate_html(data)

    html = (tmp_path / 'docs' / 'ultimate_trading_dashboard.html').read_text(encoding='utf-8')

    # Chart must be a candlestick trace, not a scatter/line trace
    assert "type: 'candlestick'" in html, "main chart should use Plotly candlestick"
    # Candlestick traces require open/high/low/close arrays
    assert 'chartData.opens' in html
    assert 'chartData.highs' in html
    assert 'chartData.lows' in html
    assert 'chartData.closes' in html
    # Body must surface latest OHLC values for quick inspection
    assert 'Latest Open' in html
    assert 'Latest Close' in html


def test_run_backtest_15min_uses_nq_point_value_for_pnl():
    signals = np.array([1, 0])
    closes = np.array([20000.0, 20500.0])

    trades, final_capital = run_backtest_15min(
        signals=signals,
        closes=closes,
        df=None,
        initial_capital=10000.0,
        stop_loss=0.6,
        take_profit=2.4,
        fee_per_trade=10.0
    )

    assert len(trades) == 1
    assert trades[0]['direction'] == 'long'
    assert trades[0]['profit_dollars'] == 990.0
    assert final_capital == 10990.0
