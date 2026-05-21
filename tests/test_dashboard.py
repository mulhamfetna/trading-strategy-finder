import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.dashboard.visualizer import create_trade_chart, create_equity_curve, calculate_trade_statistics
from src.dashboard.report import generate_comparison_report, generate_error_analysis, format_metrics_for_display
from src.dashboard.template_renderer import render_template


def test_create_trade_chart():
    df = {'Close': [100, 101, 102, 103, 104]}
    trades = [{'entry_idx': 1, 'exit_idx': 3, 'entry_price': 101, 'exit_price': 103, 'direction': 'long', 'profit_pct': 2.0, 'profit_dollars': 200}]
    
    chart = create_trade_chart(df, trades, 'test_strategy')
    assert chart['strategy'] == 'test_strategy'
    assert chart['total_trades'] == 1
    assert len(chart['trades']) == 1


def test_generate_comparison_report():
    results = {
        'scalping': {'total_profit': 1000, 'win_rate': 60},
        'day_trading': {'total_profit': 1500, 'win_rate': 55},
        'intraday': {'total_profit': 800, 'win_rate': 50}
    }
    
    report = generate_comparison_report(results)
    assert 'best_strategy' in report
    assert 'recommendation' in report
    assert report['best_strategy'] == 'day_trading'


def test_generate_error_analysis():
    trades = [
        {'profit_dollars': 100},
        {'profit_dollars': -50},
        {'profit_dollars': 200},
        {'profit_dollars': -30}
    ]
    
    analysis = generate_error_analysis(trades)
    assert 'error_rate' in analysis
    assert analysis['error_rate'] == 50.0


def test_format_metrics_for_display():
    metrics = {
        'total_profit': 1500.50,
        'win_rate': 66.67,
        'max_drawdown': 5.25,
        'total_trades': 50
    }
    
    formatted = format_metrics_for_display(metrics)
    assert '$1500.50' in formatted['total_profit']
    assert '66.67%' in formatted['win_rate']
    assert '5.25%' in formatted['max_drawdown']


def test_render_template_replaces_placeholders(tmp_path):
    template_path = tmp_path / 'dashboard.tpl'
    template_path.write_text('Hello {{NAME}} from {{CITY}}', encoding='utf-8')

    rendered = render_template(template_path, {'NAME': 'NQ', 'CITY': 'Chicago'})

    assert rendered == 'Hello NQ from Chicago'


def test_render_template_raises_on_missing_placeholder(tmp_path):
    template_path = tmp_path / 'dashboard.tpl'
    template_path.write_text('Hello {{NAME}}', encoding='utf-8')

    try:
        render_template(template_path, {})
        assert False, 'Expected KeyError for unresolved placeholder'
    except KeyError:
        assert True