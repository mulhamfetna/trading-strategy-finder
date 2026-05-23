"""Tests for src/data/loader.py and the 4h CSV column normalization.

Phase C1: loader needs to handle NQ_4h.csv which uses a single
'datetime' column (lowercase) instead of the 'Date'+'Time' pair.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.loader import load_data


def test_load_data_normalizes_lowercase_datetime_column(tmp_path):
    """A CSV with lowercase 'datetime' (like NQ_4h.csv) loads cleanly
    and yields a canonical 'Date' column the downstream pipeline
    expects."""
    csv = tmp_path / 'four_hour.csv'
    csv.write_text(
        'datetime,open,high,low,close,volume\n'
        '2025-01-01 18:00:00,21269.0,21333.0,21121.75,21322.25,32778\n'
        '2025-01-01 22:00:00,21321.75,21396.75,21287.0,21389.5,20661\n',
        encoding='utf-8',
    )

    df = load_data(str(csv))

    # OHLCV title-cased
    for col in ('Open', 'High', 'Low', 'Close', 'Volume'):
        assert col in df.columns, f"missing {col}"
    # datetime normalized to Date (and parseable as timestamps)
    assert 'Date' in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df['Date']) or pd.to_datetime(df['Date']).notna().all()
    assert len(df) == 2


def test_load_real_nq_4h_csv():
    """Smoke test the real NQ_4h.csv that ships with the repo."""
    repo_root = Path(__file__).resolve().parents[1]
    csv = repo_root / 'NQ_4h.csv'
    if not csv.exists():
        # File is gitignored; explicit skip so CI shows it as SKIP, not PASS.
        pytest.skip(f"NQ_4h.csv missing at {csv}; gitignored data file.")

    df = load_data(str(csv))

    assert {'Open', 'High', 'Low', 'Close', 'Volume', 'Date'}.issubset(df.columns)
    assert len(df) > 100  # has many bars
    # The 4h timeframe means consecutive timestamps should be 4 hours apart.
    deltas = pd.to_datetime(df['Date']).diff().dropna().dt.total_seconds() / 3600
    # Most bars should be ~4h apart (some weekend gaps allowed).
    four_hour_share = (deltas.between(3.9, 4.1)).mean()
    assert four_hour_share > 0.8, f"expected mostly 4h gaps, got {four_hour_share:.2%}"
