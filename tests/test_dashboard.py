import os
import sys

import pytest

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


# --- Iter 2 (TODO item 4): template renderer ---

def test_render_template_replaces_named_placeholders(tmp_path):
    tpl = tmp_path / "demo.tpl"
    tpl.write_text("Hello {{NAME}} from {{CITY}}", encoding="utf-8")

    out = render_template(tpl, {"NAME": "NQ", "CITY": "Chicago"})

    assert out == "Hello NQ from Chicago"


def test_render_template_replaces_repeated_placeholder(tmp_path):
    tpl = tmp_path / "demo.tpl"
    tpl.write_text("{{X}} and {{X}} and {{X}}", encoding="utf-8")

    out = render_template(tpl, {"X": "ok"})

    assert out == "ok and ok and ok"


def test_render_template_raises_on_unresolved_placeholder(tmp_path):
    tpl = tmp_path / "demo.tpl"
    tpl.write_text("Hi {{NAME}} from {{CITY}}", encoding="utf-8")

    with pytest.raises(KeyError):
        render_template(tpl, {"NAME": "NQ"})  # CITY missing


def test_render_template_raises_on_missing_file(tmp_path):
    missing = tmp_path / "nope.tpl"

    with pytest.raises(FileNotFoundError):
        render_template(missing, {})


def test_render_template_does_not_re_substitute_substitution_output(tmp_path):
    """If a value itself contains '{{X}}' it must NOT be re-substituted."""
    tpl = tmp_path / "demo.tpl"
    tpl.write_text("{{A}} {{B}}", encoding="utf-8")

    out = render_template(tpl, {"A": "{{B}}", "B": "safe"})

    # If we naively .replace() in a loop, A's value would be re-substituted.
    # The renderer must do a single pass.
    assert out == "{{B}} safe"