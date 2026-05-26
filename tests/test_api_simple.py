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
        'sl_soft_points':       100,
        'sl_hard_points':       200,
        'tp_soft_points':       100,
        'tp_hard_points':       150,
        'data_path':            _4H,
        'data_path_1min':       _1M,
        'box_data_path':        _BOX,
        'direction_scope':      'both',
        'flip_entry_direction': False,
        'start':                None,
        'end':                  None,
    }
    base.update(overrides)
    return base


def test_endpoint_returns_summary_and_trades():
    r = client.post('/api/backtest/simple', json=_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {'summary', 'metrics', 'trades', 'candles', 'elapsed_ms'}
    s = body['summary']
    assert s['n_trades']      == 594
    assert s['n_take_profit'] == 271
    assert s['n_stop_loss']   == 8 + 315
    assert s['n_open_at_eof'] == 0
    assert len(body['trades']) == 594
    assert isinstance(body['trades'][0]['entry_time'], str)
    # Dashboard-compat fields on each trade.
    t0 = body['trades'][0]
    for key in ('entry_idx', 'exit_idx', 'direction', 'entry_signal_price',
                'exit_close', 'avg_entry_price', 'exit_price', 'contracts',
                'profit_points', 'profit_dollars', 'exit_reason', 'legs',
                'sl_soft_line', 'sl_hard_line', 'tp_soft_line', 'tp_hard_line',
                'flip'):
        assert key in t0, f'missing {key} in trade payload'
    # Metrics block matches the canonical Metrics interface (same one the
    # box endpoint produces) so the MetricsCards UI renders all panels
    # without nulls. Closed trades = 589; the 1 OPEN trade is excluded.
    m = body['metrics']
    # No-look-ahead engine: 0 OPEN trades; all 594 closed.
    assert m['total_trades'] == 594
    for key in ('total_profit', 'win_rate', 'profit_factor', 'avg_profit',
                'avg_loss', 'gross_profit', 'gross_loss', 'expected_value',
                'max_drawdown', 'sharpe_ratio', 'wins', 'losses'):
        assert key in m, f'metrics missing canonical field {key}'
    # win_rate must be a PERCENT (0-100), not a fraction (0-1).
    assert m['win_rate'] > 1.0, 'win_rate should be a percentage (0-100), got fraction'
    # Candles array present for chart overlay — canonical t/o/h/l/c/v keys
    # so frontend `toUTCTimestamp(c.t)` works without translation.
    assert len(body['candles']) > 0
    assert set(body['candles'][0]) == {'t','o','h','l','c','v'}


def test_endpoint_400_on_missing_4h_path():
    r = client.post('/api/backtest/simple', json=_payload(data_path='/nonexistent.csv'))
    assert r.status_code == 400


def test_endpoint_long_only_filters_signal():
    r = client.post('/api/backtest/simple', json=_payload(direction_scope='long_only'))
    assert r.status_code == 200
    trades = r.json()['trades']
    assert all(t['direction'] == 'long' for t in trades)
    assert 0 < len(trades) < 594


def test_endpoint_422_on_negative_sl():
    r = client.post('/api/backtest/simple', json=_payload(sl_soft_points=-1))
    assert r.status_code == 422


def test_endpoint_422_on_hard_below_soft():
    r = client.post('/api/backtest/simple',
                    json=_payload(sl_soft_points=200, sl_hard_points=100))
    assert r.status_code == 422


def test_endpoint_422_on_tp_hard_below_soft():
    r = client.post('/api/backtest/simple',
                    json=_payload(tp_soft_points=200, tp_hard_points=100))
    assert r.status_code == 422


def test_endpoint_flip_on_flips_directions():
    """Flip ON: the same data should produce reversed directions vs flip OFF."""
    off = client.post('/api/backtest/simple', json=_payload(flip_entry_direction=False)).json()
    on  = client.post('/api/backtest/simple', json=_payload(flip_entry_direction=True)).json()
    # Same number of signal-firing bars in both runs, so totals are close but
    # not identical (different exit paths). However, the first trade's signal
    # comes from bar 0 — the only thing that matters is direction.
    assert off['trades'][0]['direction'] != on['trades'][0]['direction']
    # Flip-on summary carries the new TAKE_PROFIT_SOFT count.
    assert 'n_take_profit_soft' in on['summary']
    assert on['summary']['n_trades'] == 539
    assert on['summary']['n_take_profit_hard'] == 32
    assert on['summary']['n_take_profit_soft'] == 304
    assert on['summary']['n_stop_loss_hard']   == 203
    # Flipped first trade exposes the new line fields.
    t0 = on['trades'][0]
    assert t0['flip'] is True
    for k in ('sl_soft_line', 'sl_hard_line', 'tp_soft_line', 'tp_hard_line'):
        assert k in t0
