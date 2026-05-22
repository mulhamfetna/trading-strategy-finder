"""Phase C2: POST /api/backtest/scaling SSE streaming endpoint tests.

The endpoint runs the ScalingStrategy and streams Server-Sent Events:
  event: progress      { percent, current_idx, total, phase, trades_so_far, ... }
  event: progress      ...
  event: complete      { metrics, trades, candles, elapsed_ms }
  event: error         { detail }     # only on failure
"""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from src.api.app import app


client = TestClient(app)


def _write_synth_4h_csv(path, n_rows=100):
    """Synthetic 4h OHLCV CSV in the NQ_4h.csv format ('datetime' col)."""
    timestamps = pd.date_range(start='2025-01-01 00:00:00', periods=n_rows, freq='4h')
    df = pd.DataFrame({
        'datetime': timestamps.strftime('%Y-%m-%d %H:%M:%S'),
        'open':   [20000.0 + i * 5 for i in range(n_rows)],
        'high':   [20020.0 + i * 5 for i in range(n_rows)],
        'low':    [19980.0 + i * 5 for i in range(n_rows)],
        'close':  [20010.0 + i * 5 for i in range(n_rows)],
        'volume': [1000 + i for i in range(n_rows)],
    })
    df.to_csv(path, index=False)


def _parse_sse_events(text: str):
    """Parse a raw SSE text stream into a list of (event_type, data_dict)."""
    events = []
    current_event = None
    current_data = []
    for line in text.splitlines():
        if line.startswith('event:'):
            current_event = line[len('event:'):].strip()
        elif line.startswith('data:'):
            current_data.append(line[len('data:'):].strip())
        elif line == '':
            # blank line = event boundary
            if current_event and current_data:
                events.append((current_event, json.loads('\n'.join(current_data))))
            current_event = None
            current_data = []
    if current_event and current_data:
        events.append((current_event, json.loads('\n'.join(current_data))))
    return events


def test_scaling_backtest_streams_progress_and_complete_events(tmp_path):
    csv = tmp_path / 'synth_4h.csv'
    _write_synth_4h_csv(csv, n_rows=120)

    resp = client.post(
        '/api/backtest/scaling',
        json={'params': {}, 'data_path': str(csv)},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers['content-type'].startswith('text/event-stream')

    events = _parse_sse_events(resp.text)

    # At least 1 progress event and exactly 1 complete event
    progress = [e for e in events if e[0] == 'progress']
    complete = [e for e in events if e[0] == 'complete']
    assert len(progress) >= 1, f"expected progress events, got {[e[0] for e in events]}"
    assert len(complete) == 1, f"expected exactly 1 complete event, got {len(complete)}"

    # Last progress event should be at or near 100%
    last_progress = progress[-1][1]
    assert last_progress['percent'] > 80.0
    # Required fields on progress events
    for required in ('percent', 'current_idx', 'total', 'phase',
                     'trades_so_far', 'pnl_so_far', 'win_rate_so_far',
                     'current_position', 'current_legs_filled'):
        assert required in last_progress

    # Complete event carries metrics + trades + candles
    payload = complete[0][1]
    for required in ('metrics', 'trades', 'candles', 'elapsed_ms'):
        assert required in payload
    assert isinstance(payload['trades'], list)
    assert isinstance(payload['candles'], list)
    assert payload['elapsed_ms'] >= 0


def test_scaling_backtest_accepts_custom_params(tmp_path):
    """Tunable thresholds must reach the strategy."""
    csv = tmp_path / 'synth_4h.csv'
    _write_synth_4h_csv(csv, n_rows=80)

    resp = client.post(
        '/api/backtest/scaling',
        json={
            'params': {
                'total_contracts': 2,
                'leg1_contracts': 2,
                'leg2_contracts': 0,
                'leg3_contracts': 0,
                'tp_target_points': 50.0,
                'sl_soft_points': 25.0,
                'sl_hard_points': 50.0,
                'reentry_enabled': False,
            },
            'data_path': str(csv),
        },
    )
    assert resp.status_code == 200, resp.text


def test_scaling_backtest_missing_data_path_returns_error_event(tmp_path):
    """A missing CSV must surface as an SSE error event, not a 500."""
    resp = client.post(
        '/api/backtest/scaling',
        json={'params': {}, 'data_path': '/tmp/opencode/does-not-exist.csv'},
    )
    assert resp.status_code == 200  # SSE stream still opens

    events = _parse_sse_events(resp.text)
    errors = [e for e in events if e[0] == 'error']
    assert len(errors) == 1
    assert 'detail' in errors[0][1]
