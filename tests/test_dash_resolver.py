"""Iter 8 (TODO items 7+8): native Dash app with resolver controls.

Replaces the iframe-only viewer with native Dash components driven by
the Strategy/Backtester classes from iter 7. The controls let the user
pick a date range, a dataset (train/test), a timeframe, and an
intra-candle TP/SL resolution mode (iter 4), then re-run the pipeline
on demand.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.dashboard.dash_app import build_app, on_apply


def _write_synth_15min_csv(path, n_rows=200):
    """Synthetic OHLCV CSV. Same shape as the runner test."""
    dates = pd.date_range(start='2025-09-01 09:30:00', periods=n_rows, freq='15min')
    df = pd.DataFrame({
        'Date': dates.strftime('%Y-%m-%d'),
        'Time': dates.strftime('%H:%M:%S'),
        'Open':   [20000.0 + i * 0.5 for i in range(n_rows)],
        'High':   [20002.0 + i * 0.5 for i in range(n_rows)],
        'Low':    [19998.0 + i * 0.5 for i in range(n_rows)],
        'Close':  [20001.0 + i * 0.5 for i in range(n_rows)],
        'Volume': [1000 + i for i in range(n_rows)],
    })
    df.to_csv(path, index=False)


# ---- layout / structure ----

def test_build_app_returns_dash_instance():
    app = build_app(data_path='1min.csv')  # path need not exist for layout
    assert hasattr(app, 'server')
    assert hasattr(app, 'layout')


def test_layout_has_resolver_controls():
    """The new layout must have: dataset radio, start/end date pickers,
    timeframe dropdown, tp-sl-resolution dropdown, apply button."""
    app = build_app(data_path='1min.csv')
    layout_str = str(app.layout)

    required_ids = [
        'dataset-radio',
        'start-date',
        'end-date',
        'timeframe-dropdown',
        'tp-sl-resolution-dropdown',
        'apply-btn',
    ]
    for rid in required_ids:
        assert rid in layout_str, f"missing control id {rid!r}"


def test_layout_has_output_components():
    """Output components: candlestick chart, metric cards container,
    trade list container, error panel."""
    app = build_app(data_path='1min.csv')
    layout_str = str(app.layout)

    required_ids = [
        'candlestick-chart',
        'metric-cards',
        'trade-list',
        'error-panel',
    ]
    for rid in required_ids:
        assert rid in layout_str, f"missing output id {rid!r}"


def test_layout_does_not_use_iframes():
    """Iter 8: replaces the iframe-only preview with native components.
    No <Iframe> should remain in the new layout."""
    app = build_app(data_path='1min.csv')
    layout_str = str(app.layout)
    assert 'Iframe' not in layout_str


# ---- on_apply callback logic ----

def test_on_apply_rejects_inverted_date_range(tmp_path):
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=100)

    figure, metrics_html, trades_html, error = on_apply(
        n_clicks=1,
        dataset='test',
        start='2025-09-10',
        end='2025-09-05',  # before start
        timeframe='15min',
        tp_sl_resolution='conservative',
        data_path=str(csv),
    )

    assert error  # non-empty error message
    assert 'start' in error.lower() or 'before' in error.lower() or 'invalid' in error.lower()


def test_on_apply_handles_empty_range(tmp_path):
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=100)

    # Range entirely outside the synthetic data window
    figure, metrics_html, trades_html, error = on_apply(
        n_clicks=1,
        dataset='test',
        start='2030-01-01',
        end='2030-12-31',
        timeframe='15min',
        tp_sl_resolution='conservative',
        data_path=str(csv),
    )

    assert error  # tells the user no data
    assert 'no data' in error.lower() or 'empty' in error.lower()


def test_on_apply_handles_missing_csv():
    figure, metrics_html, trades_html, error = on_apply(
        n_clicks=1,
        dataset='test',
        start='2025-09-01',
        end='2025-09-30',
        timeframe='15min',
        tp_sl_resolution='conservative',
        data_path='/tmp/opencode/does-not-exist.csv',
    )

    assert error
    assert 'not found' in error.lower() or 'missing' in error.lower()


def test_on_apply_valid_range_returns_chart_and_metrics(tmp_path):
    """Happy path: synthetic CSV + valid range -> figure with candlestick,
    metric cards, trade list (possibly empty), no error."""
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    figure, metrics_html, trades_html, error = on_apply(
        n_clicks=1,
        dataset='test',
        start='2025-09-01',
        end='2025-12-31',
        timeframe='15min',
        tp_sl_resolution='conservative',
        data_path=str(csv),
    )

    assert error == ''  # no error
    # figure is a Plotly Figure dict
    assert isinstance(figure, dict)
    assert 'data' in figure
    # Candlestick trace present
    types = [trace.get('type') for trace in figure['data']]
    assert 'candlestick' in types
    # Metrics cards rendered (Dash html.Div children = list)
    assert metrics_html is not None
    # Trade list rendered (may be empty list)
    assert trades_html is not None


def test_on_apply_no_clicks_returns_empty_state(tmp_path):
    """Before the user clicks Apply for the first time, the callback
    should return an empty/placeholder state - not run the pipeline."""
    figure, metrics_html, trades_html, error = on_apply(
        n_clicks=None,  # or 0
        dataset='test',
        start='2025-09-01',
        end='2025-12-31',
        timeframe='15min',
        tp_sl_resolution='conservative',
        data_path='1min.csv',
    )

    # No error and no data yet - placeholder state
    assert error == ''


def test_on_apply_passes_tp_sl_resolution_through(tmp_path):
    """The resolution mode is wired through to Backtester."""
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    # Run with each mode; results should be valid (no error).
    for mode in ('conservative', 'optimistic', 'direction-proxy'):
        figure, _m, _t, error = on_apply(
            n_clicks=1,
            dataset='test',
            start='2025-09-01',
            end='2025-12-31',
            timeframe='15min',
            tp_sl_resolution=mode,
            data_path=str(csv),
        )
        assert error == '', f"unexpected error with mode={mode!r}: {error}"
