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
    """No-fallback rule: missing file → ConfigurationError → 422 with
    structured code/system_status."""
    resp = client.get('/api/candles', params={
        'start': '2025-09-01',
        'end': '2025-09-30',
        'data_path': '/tmp/opencode/does-not-exist.csv',
    })

    assert resp.status_code == 422
    body = resp.json()
    assert body['code'] == 'missing-data-file'
    assert body['system_status']['role'] == 'candles'


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


# ---- /api/upload-data-file ---- (BUG-022 regression locks)

def test_upload_rejects_non_csv_extension():
    resp = client.post(
        '/api/upload-data-file',
        files={'file': ('something.exe', b'header,value\n1,2\n', 'application/octet-stream')},
    )
    assert resp.status_code == 400
    assert 'csv' in resp.json()['detail'].lower()


def test_upload_strips_path_traversal_via_basename(tmp_path):
    # filename with traversal segments should be reduced to basename;
    # destination must stay inside the repo root, no .., no nested dirs.
    resp = client.post(
        '/api/upload-data-file',
        files={'file': ('../../etc/passwd.csv', b'a,b\n1,2\n', 'text/csv')},
    )
    # Either accepted as basename "passwd.csv" or rejected outright — never written outside the repo.
    if resp.status_code == 200:
        # Cleanup the test artifact written at repo root.
        body = resp.json()
        assert '/' not in body['path']
        repo_root = os.path.dirname(os.path.dirname(__file__))
        written = os.path.join(repo_root, body['path'])
        if os.path.exists(written):
            os.remove(written)
    else:
        assert resp.status_code in (400, 413)


def test_upload_caps_oversize_files(monkeypatch):
    # Patch the size cap to a tiny value and verify the server rejects.
    # The src/api/__init__.py re-exports `app` over the submodule name,
    # so we fetch the real module via sys.modules.
    import sys
    app_module = sys.modules['src.api.app']

    monkeypatch.setattr(app_module, 'MAX_UPLOAD_BYTES', 16)
    payload = b'a,b\n' + b'1,2\n' * 100  # >16 bytes

    resp = client.post(
        '/api/upload-data-file',
        files={'file': ('big.csv', payload, 'text/csv')},
    )
    assert resp.status_code == 413
    # Confirm the file was cleaned up.
    repo_root = os.path.dirname(os.path.dirname(__file__))
    assert not os.path.exists(os.path.join(repo_root, 'big.csv'))


