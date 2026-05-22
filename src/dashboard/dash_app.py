"""Native Dash app with resolver controls (iter 8, TODO items 7 + 8).

Replaces the previous iframe-only preview with native Dash components.
The user picks a dataset (train/test), a date range, a timeframe, and
an intra-candle TP/SL resolution mode (iter 4), clicks Apply, and the
pipeline runs in-memory via the OOP classes from iter 7
(`ScalpingStrategy` + `Backtester`).

Architecture:

- ``build_app(data_path)``: factory that returns a Dash app instance.
  No module-level state - tests can build apps without monkey-patching.
- Module-level ``app`` is still exported so
  ``python3 -m src.dashboard.dash_app`` keeps working.
- ``on_apply(...)``: extracted as a top-level function (FP-style)
  so callback logic can be tested directly without spinning up a
  Dash server.

Refactor policy notes (from iter 7 sequencing spec):
- ``on_apply`` is a pure transform (inputs -> outputs, no state) -> FP.
- ``build_app`` is a constructor (no state, returns one object) -> FP
  too, despite returning an OOP Dash app.
- The Strategy/Backtester it instantiates internally are OOP per iter 7.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import pandas as pd
from dash import Dash, dcc, html, Input, Output, no_update

from src.data.loader import load_data
from src.data.splitter import filter_by_date_range, split_train_test
from src.strategy.scalping_strategy import ScalpingStrategy
from src.strategy.backtester import Backtester
from src.backtest.metrics import calculate_metrics


_RESOLUTION_OPTIONS = ['conservative', 'optimistic', 'direction-proxy']
_TIMEFRAME_OPTIONS = ['15min']  # v1 only - more can be added later
_DATASET_OPTIONS = ['train', 'test']

_DEFAULT_START = '2025-09-01'
_DEFAULT_END = '2025-12-31'
_DEFAULT_SPLIT = '2025-06-30'


def _empty_figure() -> dict:
    """Placeholder figure shown before the user clicks Apply."""
    return {
        'data': [],
        'layout': {
            'paper_bgcolor': '#131722',
            'plot_bgcolor': '#131722',
            'font': {'color': '#d1d4dc'},
            'annotations': [{
                'text': 'Pick a range and click Apply.',
                'showarrow': False,
                'xref': 'paper', 'yref': 'paper',
                'x': 0.5, 'y': 0.5,
            }],
            'height': 500,
        },
    }


def _candlestick_figure(df: pd.DataFrame, trades: list) -> dict:
    """Build a Plotly candlestick figure with optional trade markers."""
    candlestick = {
        'x': df['Date'].astype(str).tolist() if 'Date' in df.columns else list(range(len(df))),
        'open': df['Open'].tolist(),
        'high': df['High'].tolist(),
        'low': df['Low'].tolist(),
        'close': df['Close'].tolist(),
        'type': 'candlestick',
        'name': 'OHLC',
        'increasing': {'line': {'color': '#00c853'}, 'fillcolor': '#00c853'},
        'decreasing': {'line': {'color': '#ff5252'}, 'fillcolor': '#ff5252'},
    }

    traces = [candlestick]

    if trades:
        entry_x, entry_y, entry_color = [], [], []
        exit_x, exit_y, exit_color = [], [], []
        for t in trades:
            try:
                entry_x.append(df.iloc[t['entry_idx']]['Date'] if 'Date' in df.columns else t['entry_idx'])
                exit_x.append(df.iloc[t['exit_idx']]['Date'] if 'Date' in df.columns else t['exit_idx'])
            except (KeyError, IndexError):
                continue
            entry_y.append(t['entry_price'])
            exit_y.append(t['exit_price'])
            entry_color.append('#00c853' if t['direction'] == 'long' else '#ff5252')
            exit_color.append('#00c853' if t['profit_dollars'] > 0 else '#ff5252')

        if entry_x:
            traces.append({
                'x': entry_x, 'y': entry_y,
                'type': 'scatter', 'mode': 'markers',
                'marker': {'symbol': 'triangle-up', 'size': 10, 'color': entry_color},
                'name': 'Entry',
            })
            traces.append({
                'x': exit_x, 'y': exit_y,
                'type': 'scatter', 'mode': 'markers',
                'marker': {'symbol': 'triangle-down', 'size': 10, 'color': exit_color},
                'name': 'Exit',
            })

    return {
        'data': traces,
        'layout': {
            'paper_bgcolor': '#131722',
            'plot_bgcolor': '#131722',
            'font': {'color': '#d1d4dc'},
            'xaxis': {'gridcolor': '#363a45', 'rangeslider': {'visible': False}},
            'yaxis': {'gridcolor': '#363a45'},
            'height': 500,
        },
    }


def _metric_cards(metrics: dict) -> list:
    """Build a list of Dash html.Div metric cards."""
    cards_data = [
        ('Net Profit', f"${metrics.get('total_profit', 0):.2f}"),
        ('Win Rate', f"{metrics.get('win_rate', 0):.1f}%"),
        ('Profit Factor', f"{metrics.get('profit_factor', 0):.2f}"),
        ('Sharpe', f"{metrics.get('sharpe_ratio', 0):.2f}"),
        ('Max Drawdown', f"{metrics.get('max_drawdown', 0):.2f}%"),
        ('Total Trades', f"{metrics.get('total_trades', 0)}"),
    ]
    return [
        html.Div([
            html.Div(value, style={'fontSize': '20px', 'fontWeight': '600'}),
            html.Div(label, style={'fontSize': '12px', 'color': '#787b86', 'textTransform': 'uppercase'}),
        ], style={
            'background': '#2a2e39', 'padding': '12px', 'borderRadius': '6px',
            'textAlign': 'center', 'flex': '1', 'margin': '4px',
        })
        for label, value in cards_data
    ]


def _trade_rows(trades: list) -> list:
    """Build a Dash list of trade rows."""
    if not trades:
        return [html.Div(
            'No trades in this range.',
            style={'color': '#787b86', 'padding': '12px', 'textAlign': 'center'},
        )]
    rows = []
    for i, t in enumerate(trades[:50], start=1):  # cap at 50 for UI
        profit = t.get('profit_dollars', 0)
        color = '#00c853' if profit > 0 else '#ff5252'
        rows.append(html.Div([
            html.Span(f"#{i} ", style={'color': '#787b86'}),
            html.Span(t.get('direction', '?').upper(), style={'fontWeight': '600'}),
            html.Span(f" ${t.get('entry_price', 0):.2f} -> ${t.get('exit_price', 0):.2f}",
                      style={'marginLeft': '8px'}),
            html.Span(f" ${profit:+.2f}", style={'marginLeft': '8px', 'color': color, 'fontWeight': '600'}),
            html.Span(f" [{t.get('exit_reason', '')}]", style={'marginLeft': '8px', 'color': '#787b86', 'fontSize': '11px'}),
        ], style={'padding': '8px', 'borderBottom': '1px solid #363a45'}))
    return rows


def on_apply(
    n_clicks,
    dataset: str,
    start: str,
    end: str,
    timeframe: str,
    tp_sl_resolution: str,
    data_path: str = '1min.csv',
) -> Tuple[dict, list, list, str]:
    """Run the pipeline and return (figure, metric_cards, trade_rows, error_msg).

    Pure function - safe to unit-test without a Dash server. Returns an
    empty/placeholder state when ``n_clicks`` is falsy (before first click).
    """
    if not n_clicks:
        return _empty_figure(), [], [], ''

    # Validate dates.
    try:
        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
    except (ValueError, TypeError):
        return _empty_figure(), [], [], 'Invalid date format. Use YYYY-MM-DD.'

    if start_ts > end_ts:
        return _empty_figure(), [], [], f'Invalid range: start ({start}) is before end ({end}).'

    if not os.path.exists(data_path):
        return _empty_figure(), [], [], f'Data file not found: {data_path}'

    try:
        df = load_data(data_path)
    except Exception as exc:
        return _empty_figure(), [], [], f'Failed to load {data_path}: {exc}'

    df = filter_by_date_range(df, start=start, end=end)
    if len(df) == 0:
        return _empty_figure(), [], [], (
            f'No data in range {start} -> {end}. '
            f'Check the dataset covers this window.'
        )

    # 1min CSVs load newest-first; reverse to ascending.
    df = df.reset_index(drop=True)[::-1].reset_index(drop=True)

    # Apply train/test split based on the dataset choice.
    if dataset in ('train', 'test'):
        try:
            train_df, test_df = split_train_test(df, split_date=_DEFAULT_SPLIT)
            df = train_df if dataset == 'train' else test_df
        except Exception as exc:
            return _empty_figure(), [], [], f'Train/test split failed: {exc}'

    if len(df) == 0:
        return _empty_figure(), [], [], (
            f'No data in the {dataset} half of {start} -> {end}.'
        )

    strat = ScalpingStrategy()
    bt = Backtester(tp_sl_resolution=tp_sl_resolution)

    try:
        prepared = strat.prepare(df)
        trades, _ = bt.run(prepared)
    except Exception as exc:
        return _empty_figure(), [], [], f'Pipeline failed: {exc}'

    metrics = calculate_metrics(trades, bt.initial_capital)
    figure = _candlestick_figure(prepared, trades)
    cards = _metric_cards(metrics)
    rows = _trade_rows(trades)
    return figure, cards, rows, ''


def _build_layout() -> html.Div:
    controls = html.Div([
        html.Div([
            html.Label('Dataset', style={'color': '#787b86', 'fontSize': '11px'}),
            dcc.RadioItems(
                id='dataset-radio',
                options=[{'label': o, 'value': o} for o in _DATASET_OPTIONS],
                value='test',
                inline=True,
            ),
        ], style={'marginRight': '20px'}),
        html.Div([
            html.Label('Start', style={'color': '#787b86', 'fontSize': '11px'}),
            dcc.Input(id='start-date', type='text', value=_DEFAULT_START, debounce=True),
        ], style={'marginRight': '12px'}),
        html.Div([
            html.Label('End', style={'color': '#787b86', 'fontSize': '11px'}),
            dcc.Input(id='end-date', type='text', value=_DEFAULT_END, debounce=True),
        ], style={'marginRight': '12px'}),
        html.Div([
            html.Label('Timeframe', style={'color': '#787b86', 'fontSize': '11px'}),
            dcc.Dropdown(
                id='timeframe-dropdown',
                options=[{'label': o, 'value': o} for o in _TIMEFRAME_OPTIONS],
                value='15min',
                clearable=False,
                style={'width': '120px'},
            ),
        ], style={'marginRight': '12px'}),
        html.Div([
            html.Label('TP/SL Resolution', style={'color': '#787b86', 'fontSize': '11px'}),
            dcc.Dropdown(
                id='tp-sl-resolution-dropdown',
                options=[{'label': o, 'value': o} for o in _RESOLUTION_OPTIONS],
                value='conservative',
                clearable=False,
                style={'width': '180px'},
            ),
        ], style={'marginRight': '12px'}),
        html.Button('Apply', id='apply-btn', style={
            'background': '#2962ff', 'color': 'white', 'border': 'none',
            'padding': '8px 16px', 'borderRadius': '4px', 'cursor': 'pointer',
            'fontWeight': '600', 'alignSelf': 'flex-end',
        }),
    ], style={
        'display': 'flex', 'alignItems': 'flex-end', 'gap': '8px',
        'padding': '12px', 'background': '#1e222d', 'borderRadius': '6px',
        'marginBottom': '12px',
    })

    error_panel = html.Div(
        id='error-panel',
        children='',
        style={'color': '#ff5252', 'padding': '8px', 'minHeight': '20px'},
    )

    chart = dcc.Graph(id='candlestick-chart', figure=_empty_figure())

    metric_cards_container = html.Div(
        id='metric-cards',
        children=[],
        style={'display': 'flex', 'flexWrap': 'wrap', 'margin': '12px 0'},
    )

    trade_list_container = html.Div(
        id='trade-list',
        children=[],
        style={
            'background': '#1e222d', 'borderRadius': '6px',
            'maxHeight': '300px', 'overflowY': 'auto', 'padding': '12px',
        },
    )

    return html.Div([
        html.H2('NQ Trading Dashboard',
                style={'color': '#d1d4dc', 'padding': '8px 0'}),
        controls,
        error_panel,
        chart,
        metric_cards_container,
        html.H3('Trades', style={'color': '#d1d4dc', 'marginTop': '12px'}),
        trade_list_container,
    ], style={
        'background': '#131722', 'color': '#d1d4dc',
        'padding': '20px', 'minHeight': '100vh',
        'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    })


def build_app(data_path: str = '1min.csv') -> Dash:
    """Factory: build and return a Dash app instance.

    ``data_path`` is captured by the callback closure so the Apply
    button knows which CSV to load. The path need not exist when
    building the layout - the callback surfaces an error at click time.
    """
    app = Dash(__name__)
    app.layout = _build_layout()

    @app.callback(
        Output('candlestick-chart', 'figure'),
        Output('metric-cards', 'children'),
        Output('trade-list', 'children'),
        Output('error-panel', 'children'),
        Input('apply-btn', 'n_clicks'),
        Input('dataset-radio', 'value'),
        Input('start-date', 'value'),
        Input('end-date', 'value'),
        Input('timeframe-dropdown', 'value'),
        Input('tp-sl-resolution-dropdown', 'value'),
        prevent_initial_call=True,
    )
    def _apply_callback(n_clicks, dataset, start, end, timeframe, tp_sl_res):
        return on_apply(
            n_clicks=n_clicks,
            dataset=dataset,
            start=start,
            end=end,
            timeframe=timeframe,
            tp_sl_resolution=tp_sl_res,
            data_path=data_path,
        )

    return app


# Module-level app so `python3 -m src.dashboard.dash_app` still works.
app = build_app()


def run_server(host: str = '0.0.0.0', port: int = 8050, debug: bool = True) -> None:
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server()
