"""Phase A: FastAPI backend tests (TODO: live dashboard migration).

Tests the three REST endpoints that replace the Dash callback:
- GET /api/strategy/config
- GET /api/candles
- POST /api/backtest

Uses FastAPI TestClient - no live server needed. Synthetic CSV in
tmp_path keeps tests fast and reproducible.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def _write_synth_15min_csv(path, n_rows=200):
    """Synthetic OHLCV CSV (same helper as other tests)."""
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


# ---- /api/strategy/config ----

def test_strategy_config_returns_v1_defaults():
    """Strategy config endpoint returns the v1.0.0 frozen defaults and
    the enumerated control options the frontend needs."""
    resp = client.get('/api/strategy/config')

    assert resp.status_code == 200
    data = resp.json()
    # v1 frozen defaults
    assert data['rsi_period'] == 5
    assert data['ema_fast'] == 5
    assert data['ema_slow'] == 15
    assert data['vol_threshold'] == 2.0
    assert data['stop_loss'] == 0.6
    assert data['take_profit'] == 1.8
    assert data['tp_sl_resolution'] == 'conservative'
    # enumerations the frontend needs to populate controls
    assert set(data['tp_sl_resolution_options']) == {
        'conservative', 'optimistic', 'direction-proxy',
    }
    assert '15min' in data['timeframe_options']
    assert set(data['dataset_options']) == {'train', 'test'}


# ---- /api/candles ----

def test_candles_returns_ohlcv_in_range(tmp_path):
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    resp = client.get('/api/candles', params={
        'start': '2025-09-01',
        'end': '2025-09-30',
        'dataset': 'test',
        'data_path': str(csv),
    })

    assert resp.status_code == 200
    body = resp.json()
    assert 'candles' in body
    assert isinstance(body['candles'], list)
    assert body['count'] == len(body['candles'])
    if body['candles']:
        candle = body['candles'][0]
        # Shape: t, o, h, l, c, v
        for key in ('t', 'o', 'h', 'l', 'c', 'v'):
            assert key in candle


def test_candles_handles_missing_data_path():
    resp = client.get('/api/candles', params={
        'start': '2025-09-01',
        'end': '2025-09-30',
        'dataset': 'test',
        'data_path': '/tmp/opencode/does-not-exist.csv',
    })

    assert resp.status_code == 404
    assert 'detail' in resp.json()


def test_candles_handles_inverted_range(tmp_path):
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    resp = client.get('/api/candles', params={
        'start': '2025-09-30',
        'end': '2025-09-01',  # before start
        'dataset': 'test',
        'data_path': str(csv),
    })

    assert resp.status_code == 400


# ---- /api/backtest ----

def test_backtest_runs_pipeline_and_returns_metrics(tmp_path):
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    resp = client.post('/api/backtest', json={
        'start': '2025-09-01',
        'end': '2025-12-31',
        'dataset': 'test',
        'timeframe': '15min',
        'tp_sl_resolution': 'conservative',
        'stop_loss': 0.6,
        'take_profit': 1.8,
        'data_path': str(csv),
    })

    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Required output blocks
    assert 'metrics' in data
    assert 'trades' in data
    assert 'candles' in data
    # Metrics dict has the canonical keys
    for key in ('total_profit', 'win_rate', 'profit_factor', 'total_trades'):
        assert key in data['metrics'], f"missing metric: {key}"
    # Trades is a list (possibly empty for synth data)
    assert isinstance(data['trades'], list)


def test_backtest_passes_tp_sl_resolution_through(tmp_path):
    """The resolution mode must reach the engine - same regression
    guard as test_dash_resolver.test_on_apply_passes_tp_sl_resolution_through."""
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    for mode in ('conservative', 'optimistic', 'direction-proxy'):
        resp = client.post('/api/backtest', json={
            'start': '2025-09-01',
            'end': '2025-12-31',
            'dataset': 'test',
            'timeframe': '15min',
            'tp_sl_resolution': mode,
            'stop_loss': 0.6,
            'take_profit': 1.8,
            'data_path': str(csv),
        })
        assert resp.status_code == 200, f"mode={mode}: {resp.text}"


def test_backtest_rejects_unknown_tp_sl_resolution(tmp_path):
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    resp = client.post('/api/backtest', json={
        'start': '2025-09-01',
        'end': '2025-12-31',
        'dataset': 'test',
        'timeframe': '15min',
        'tp_sl_resolution': 'not-a-mode',
        'stop_loss': 0.6,
        'take_profit': 1.8,
        'data_path': str(csv),
    })

    assert resp.status_code == 422  # Pydantic validation error


def test_backtest_handles_inverted_range(tmp_path):
    csv = tmp_path / 'synth.csv'
    _write_synth_15min_csv(csv, n_rows=200)

    resp = client.post('/api/backtest', json={
        'start': '2025-09-30',
        'end': '2025-09-01',
        'dataset': 'test',
        'timeframe': '15min',
        'tp_sl_resolution': 'conservative',
        'stop_loss': 0.6,
        'take_profit': 1.8,
        'data_path': str(csv),
    })

    assert resp.status_code == 400
