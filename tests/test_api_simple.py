"""Smoke tests for POST /api/backtest/simple (dual-SL/TP model)."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_4H  = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_4h.csv')
_1M  = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_1m.csv')
_BOX = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_full_data.csv')


pytestmark = pytest.mark.skipif(
    not (os.path.exists(_4H) and os.path.exists(_1M) and os.path.exists(_BOX)),
    reason='Real-data CSVs not present.',
)


def _payload(**overrides):
    base = {
        'sl_soft_points':  100,
        'sl_hard_points':  200,
        'tp_points':       150,
        'data_path':       _4H,
        'data_path_1min':  _1M,
        'box_data_path':   _BOX,
        'direction_scope': 'both',
        'start':           None,
        'end':             None,
    }
    base.update(overrides)
    return base


def test_endpoint_returns_summary_and_trades():
    r = client.post('/api/backtest/simple', json=_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {'summary', 'trades'}
    s = body['summary']
    assert s['n_trades']      == 590
    assert s['n_take_profit'] == 94
    assert s['n_stop_loss']   == 152 + 343
    assert s['n_open_at_eof'] == 1
    assert len(body['trades']) == 590
    assert isinstance(body['trades'][0]['entry_time'], str)


def test_endpoint_400_on_missing_4h_path():
    r = client.post('/api/backtest/simple', json=_payload(data_path='/nonexistent.csv'))
    assert r.status_code == 400


def test_endpoint_long_only_filters_signal():
    r = client.post('/api/backtest/simple', json=_payload(direction_scope='long_only'))
    assert r.status_code == 200
    trades = r.json()['trades']
    assert all(t['direction'] == 'long' for t in trades)
    assert 0 < len(trades) < 590


def test_endpoint_422_on_negative_sl():
    r = client.post('/api/backtest/simple', json=_payload(sl_soft_points=-1))
    assert r.status_code == 422


def test_endpoint_422_on_hard_below_soft():
    r = client.post('/api/backtest/simple',
                    json=_payload(sl_soft_points=200, sl_hard_points=100))
    assert r.status_code == 422
