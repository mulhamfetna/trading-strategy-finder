"""Real-data regression lock for the Stage 1 signal extractor.

Runs `generate()` on the full preset (`data/full_data/NQ_4h.csv` +
`data/full_data/NQ_full_data.csv`) and asserts the locked totals and a
few specific (datetime, box_id) → signal triplets. If any of these
drift, either the rule changed or the dataset did — regenerate the
locked values from the new run.

Skipped if either data file is missing (gitignored).
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

_HERE = os.path.dirname(__file__)
_SUBPROJECT_ROOT = os.path.abspath(os.path.join(_HERE, '..'))
_REPO_ROOT = os.path.abspath(os.path.join(_SUBPROJECT_ROOT, '..', '..'))
sys.path.insert(0, _SUBPROJECT_ROOT)

from generate_stage1 import generate

_CANDLES = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_4h.csv')
_BOXES   = os.path.join(_REPO_ROOT, 'data', 'full_data', 'NQ_full_data.csv')

pytestmark = pytest.mark.skipif(
    not (os.path.exists(_CANDLES) and os.path.exists(_BOXES)),
    reason='NQ_4h.csv / NQ_full_data.csv not both present (gitignored).',
)


@pytest.fixture(scope='module')
def signals():
    return generate(_CANDLES, _BOXES)


def test_total_row_count_locked(signals):
    """20,322 = expected output across 2025-01-01..2026-05-19 with full level
    pair set (8 weekly + 8 monthly). Regenerate if data or rule changes."""
    assert len(signals) == 20322


def test_signal_distribution_locked(signals):
    counts = signals['signal'].value_counts().to_dict()
    assert counts == {'hold': 19256, 'long': 559, 'short': 507}


def test_first_long_signal_locked(signals):
    longs = signals[signals['signal'] == 'long'].reset_index(drop=True)
    first = longs.iloc[0]
    assert first['datetime']  == '2025-01-01T18:00:00'
    assert first['box_id']    == 'M-IH_2025-01-02'
    assert first['box_upper'] == pytest.approx(21292.26980175)
    assert first['box_lower'] == pytest.approx(21194.99964831)
    assert first['close']     == pytest.approx(21322.25)


def test_first_short_signal_locked(signals):
    shorts = signals[signals['signal'] == 'short'].reset_index(drop=True)
    first = shorts.iloc[0]
    assert first['datetime']  == '2025-01-02T10:00:00'
    assert first['box_id']    == 'W-RL_2025-01-02'
    assert first['box_upper'] == pytest.approx(21407.91444)
    assert first['box_lower'] == pytest.approx(21312.60315)
    assert first['close']     == pytest.approx(21047.5)


def test_output_schema_locked(signals):
    assert list(signals.columns) == [
        'datetime', 'open', 'high', 'low', 'close', 'volume',
        'signal', 'box_id', 'box_upper', 'box_lower',
    ]


def test_every_candle_emits_at_least_one_row(signals):
    """Spec: every 4h candle in the preset produces at least one row."""
    df_candles = pd.read_csv(_CANDLES)
    assert signals['datetime'].nunique() == len(df_candles)
