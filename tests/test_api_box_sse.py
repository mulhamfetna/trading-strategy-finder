"""POST /api/backtest/box SSE streaming endpoint tests.

Under the no-fallback rule every field of BoxBacktestRequest is required;
tests build the request body from `box_params_dict()` so they always
ship a complete payload.
"""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from src.api.app import app
from tests._fixtures import box_params_dict


client = TestClient(app)


def _write_synth_4h_csv(path, n_rows=100):
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


def _write_box_csv(path: str, kind: str) -> None:
    prefix = 'W' if kind == 'week' else 'M'
    cols = [f'{prefix}{suffix}' for suffix in
            ['THU', 'THD', 'TH1', 'TH2', 'RHU', 'RHD',
             'IHU', 'IHD', 'ILU', 'ILD', 'RLU', 'RLD',
             'TLU', 'TLD', 'TL1', 'TL2']]
    row = {c: None for c in cols}
    row[f'{prefix}RHU'] = 20120.0
    row[f'{prefix}RHD'] = 20100.0
    pd.DataFrame({'Date': ['2025-01-01'], **{c: [v] for c, v in row.items()}}).to_csv(path, index=False)


def _parse_sse_events(text: str):
    events = []
    current_event = None
    current_data = []
    for line in text.splitlines():
        if line.startswith('event:'):
            current_event = line[len('event:'):].strip()
        elif line.startswith('data:'):
            current_data.append(line[len('data:'):].strip())
        elif line == '':
            if current_event and current_data:
                events.append((current_event, json.loads('\n'.join(current_data))))
            current_event = None
            current_data = []
    if current_event and current_data:
        events.append((current_event, json.loads('\n'.join(current_data))))
    return events


def _body(*, data_path: str, week: str, month: str, **param_overrides):
    """Build a complete /api/backtest/box request body."""
    return {
        'params': box_params_dict(**param_overrides),
        'data_path': data_path,
        'week_data_path': week,
        'month_data_path': month,
        'start': None,
        'end': None,
    }


def test_box_backtest_streams_progress_and_complete_events(tmp_path):
    csv = tmp_path / 'synth_4h.csv'
    _write_synth_4h_csv(csv, n_rows=120)
    week_csv = tmp_path / 'week.csv'
    month_csv = tmp_path / 'month.csv'
    _write_box_csv(str(week_csv), 'week')
    _write_box_csv(str(month_csv), 'month')

    resp = client.post(
        '/api/backtest/box',
        json=_body(data_path=str(csv), week=str(week_csv), month=str(month_csv)),
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers['content-type'].startswith('text/event-stream')

    events = _parse_sse_events(resp.text)
    progress = [e for e in events if e[0] == 'progress']
    complete = [e for e in events if e[0] == 'complete']
    assert len(progress) >= 1
    assert len(complete) == 1

    last_progress = progress[-1][1]
    assert last_progress['percent'] > 80.0
    for required in ('percent', 'current_idx', 'total', 'phase',
                     'trades_so_far', 'pnl_so_far', 'win_rate_so_far',
                     'current_position'):
        assert required in last_progress

    payload = complete[0][1]
    for required in ('metrics', 'trades', 'candles', 'elapsed_ms', 'boxes'):
        assert required in payload


def test_box_backtest_accepts_custom_params(tmp_path):
    csv = tmp_path / 'synth_4h.csv'
    _write_synth_4h_csv(csv, n_rows=80)
    week_csv = tmp_path / 'week.csv'
    month_csv = tmp_path / 'month.csv'
    _write_box_csv(str(week_csv), 'week')
    _write_box_csv(str(month_csv), 'month')

    resp = client.post(
        '/api/backtest/box',
        json=_body(
            data_path=str(csv),
            week=str(week_csv),
            month=str(month_csv),
            tp_target_points=50.0,
            sl_soft_points=25.0,
            sl_hard_points=50.0,
            reentry_enabled=False,
        ),
    )
    assert resp.status_code == 200, resp.text


def test_box_backtest_missing_data_path_returns_error_event(tmp_path):
    week_csv = tmp_path / 'week.csv'
    month_csv = tmp_path / 'month.csv'
    _write_box_csv(str(week_csv), 'week')
    _write_box_csv(str(month_csv), 'month')

    resp = client.post(
        '/api/backtest/box',
        json=_body(
            data_path='/tmp/opencode/does-not-exist.csv',
            week=str(week_csv),
            month=str(month_csv),
        ),
    )
    assert resp.status_code == 200

    events = _parse_sse_events(resp.text)
    errors = [e for e in events if e[0] == 'error']
    assert len(errors) == 1
    err = errors[0][1]
    # No-fallback rule: error payload now has structured code/message/system_status.
    assert err['code'] == 'missing-data-file'
    assert err['system_status']['role'] == '4h-candles'


def test_box_backtest_missing_box_file_returns_error_event(tmp_path):
    csv = tmp_path / 'synth_4h.csv'
    _write_synth_4h_csv(csv, n_rows=80)

    resp = client.post(
        '/api/backtest/box',
        json=_body(
            data_path=str(csv),
            week='/tmp/opencode/no-week.csv',
            month='/tmp/opencode/no-month.csv',
        ),
    )
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    errors = [e for e in events if e[0] == 'error']
    assert len(errors) == 1
    err = errors[0][1]
    assert err['code'] == 'missing-data-file'
    assert err['system_status']['role'] == 'box-data'


def test_request_validation_error_returns_structured_422(tmp_path):
    """A request missing fields hits Pydantic; the handler wraps with system_status."""
    resp = client.post(
        '/api/backtest/box',
        json={'params': {}},  # missing data_path, week_data_path, month_data_path, start, end
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body['code'] == 'request-validation-error'
    assert 'errors' in body['system_status']
    assert len(body['system_status']['errors']) > 0
