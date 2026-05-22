import os
import sys
from pathlib import Path

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


def test_ultimate_dashboard_template_file_exists_with_named_slots():
    """Iter 2 (TODO item 4): the dashboard HTML shell must live in a
    real template file with named slot placeholders - not be inlined in
    Python source."""
    repo_root = Path(__file__).resolve().parents[1]
    tpl_path = repo_root / 'templates' / 'ultimate_dashboard.html.tpl'

    assert tpl_path.exists(), f"Template file missing: {tpl_path}"

    content = tpl_path.read_text(encoding='utf-8')

    # The template must contain the static HTML shell.
    assert '<!DOCTYPE html>' in content
    assert '<html' in content
    assert '<head>' in content
    assert '<style>' in content

    # The template must use named slot placeholders, not be a single
    # {{BODY}} wrapper.
    required_slots = [
        '{{TITLE}}',
        '{{FINAL_CAPITAL}}',
        '{{TOTAL_RETURN}}',
        '{{METRICS_BLOCK}}',
        '{{OHLC_SUMMARY}}',
        '{{TRADES_HTML}}',
        '{{LOGS_HTML}}',
        '{{FINDINGS_HTML}}',
        '{{RECOMMENDATIONS_HTML}}',
        '{{CHART_JSON}}',
        '{{PARAMS_BLOCK}}',
    ]
    for slot in required_slots:
        assert slot in content, f"Missing slot {slot!r} in template"


def test_generate_html_python_source_does_not_inline_html_shell():
    """Iter 2 (TODO item 4): the giant HTML shell must not live in the
    Python module any more - the doctype/head/body skeleton should come
    from the template file."""
    src_path = Path(__file__).resolve().parents[1] / 'src' / 'main' / 'ultimate_dashboard.py'
    source = src_path.read_text(encoding='utf-8')

    # If the doctype shows up in Python source we haven't actually
    # extracted the template.
    assert '<!DOCTYPE html>' not in source, (
        "ultimate_dashboard.py still inlines the HTML doctype; "
        "the shell should be in templates/ultimate_dashboard.html.tpl"
    )


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
