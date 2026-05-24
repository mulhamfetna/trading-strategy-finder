"""End-to-end SSE tests for /api/optimize/box and friends."""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from src.api.app import app
from tests._fixtures import box_params_dict


client = TestClient(app)


def _write_synth_4h_csv(path, n_rows=240):
    timestamps = pd.date_range(start='2025-01-01 00:00:00', periods=n_rows, freq='4h')
    closes = [20000.0 + 250.0 * (i % 4 - 1.5) for i in range(n_rows)]
    df = pd.DataFrame({
        'datetime': timestamps.strftime('%Y-%m-%d %H:%M:%S'),
        'open':   [20000.0] * n_rows,
        'high':   [c + 50 for c in closes],
        'low':    [c - 50 for c in closes],
        'close':  closes,
        'volume': [1000] * n_rows,
    })
    df.to_csv(path, index=False)


def _write_unified_box_csv(path):
    """Write a unified box CSV (single file containing all W* and M* levels)."""
    suffixes = ['THU', 'THD', 'TH1', 'TH2', 'RHU', 'RHD',
                'IHU', 'IHD', 'ILU', 'ILD', 'RLU', 'RLD',
                'TLU', 'TLD', 'TL1', 'TL2']
    cols = [f'W{s}' for s in suffixes] + [f'M{s}' for s in suffixes]
    row = {c: None for c in cols}
    # Active weekly RH box only — keeps the synthetic fixture's signal source
    # narrow and deterministic.
    row['WRHU'] = 20100.0
    row['WRHD'] = 19900.0
    pd.DataFrame({'Date': ['2025-01-01'], **{c: [v] for c, v in row.items()}}).to_csv(path, index=False)


def _parse_sse_events(text):
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


def _mini_body(tmp_path):
    csv = tmp_path / 'synth_4h.csv'
    box_csv = tmp_path / 'unified_box.csv'
    _write_synth_4h_csv(csv)
    _write_unified_box_csv(box_csv)
    return {
        'baseline_params': box_params_dict(),
        'search_space': {
            'sl_soft_points': [100.0, 250.0],
            'sl_hard_delta':  [50.0, 200.0],
            'tp_target_points': [75.0, 200.0],
        },
        'budget': {'population_size': 4, 'generations': 2},
        'folds':  {'count': 2, 'min_trades_per_fold': 1},
        'data_path': str(csv),
        'box_data_path': str(box_csv),
        'max_duration_s': 120,
    }


def test_optimize_box_streams_study_started_progress_trial_complete(tmp_path, monkeypatch):
    monkeypatch.setenv('OPTUNA_DB_PATH', str(tmp_path / 'studies.db'))
    resp = client.post('/api/optimize/box', json=_mini_body(tmp_path))
    assert resp.status_code == 200
    assert resp.headers['content-type'].startswith('text/event-stream')

    events = _parse_sse_events(resp.text)
    types = [e[0] for e in events]
    assert 'study_started' in types
    assert any(t == 'trial' for t in types)
    assert any(t == 'progress' for t in types)
    assert 'complete' in types

    complete = next(e[1] for e in events if e[0] == 'complete')
    for key in ('study_id', 'pareto_front', 'top_5_by_pf', 'top_5_by_min_dd',
                'total_trials', 'pruned_count', 'elapsed_ms'):
        assert key in complete


def test_optimize_box_missing_data_path_returns_error_event(tmp_path, monkeypatch):
    monkeypatch.setenv('OPTUNA_DB_PATH', str(tmp_path / 'studies.db'))
    body = _mini_body(tmp_path)
    body['data_path'] = '/tmp/opencode/does-not-exist.csv'
    resp = client.post('/api/optimize/box', json=body)
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    errors = [e for e in events if e[0] == 'error']
    assert len(errors) >= 1
    assert errors[0][1]['code'] == 'missing-data-file'
