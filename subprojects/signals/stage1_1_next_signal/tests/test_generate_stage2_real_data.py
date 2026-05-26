"""Regression locks for Stage 1.1 against the full real-data preset.

Pins counts and first/last next-signal-window values computed from
`subprojects/signals/signals_full.csv`. Any drift means either the rule
changed or the Stage 1 dataset changed — both require deliberate
regeneration. Do NOT loosen these locks to make the suite green.

Skipped automatically if signals_full.csv isn't present (fresh clones).
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_STAGE2 = os.path.abspath(os.path.join(_HERE, '..'))
sys.path.insert(0, os.path.dirname(_STAGE2))

from stage1_1_next_signal.generate_stage2 import generate  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
_SIGNALS_FULL = os.path.join(_REPO_ROOT, 'subprojects', 'signals', 'signals_full.csv')

pytestmark = pytest.mark.skipif(
    not os.path.exists(_SIGNALS_FULL),
    reason='signals_full.csv not present (gitignored).',
)


@pytest.fixture(scope='module')
def next_signals() -> pd.DataFrame:
    signals_df = pd.read_csv(_SIGNALS_FULL)
    return generate(signals_df)


def test_total_window_count_locked(next_signals):
    assert len(next_signals) == 828


def test_pair_class_split_locked(next_signals):
    counts = next_signals.groupby(['first_signal', 'last_signal']).size().to_dict()
    assert counts == {
        ('long', 'long'):   258,
        ('long', 'short'):  186,
        ('short', 'long'):  186,
        ('short', 'short'): 198,
    }


def test_anchor_direction_split_matches_stage1_0(next_signals):
    """Sanity check: the long/short anchor split must equal the stage1.0-
    reverse-signals split (186/186) on the cross-direction subset. Strict-
    superset invariant — stage1.1 includes every stage1.0 window plus the
    same-direction extras."""
    counts = next_signals['first_signal'].value_counts().to_dict()
    assert counts == {'long': 258 + 186, 'short': 198 + 186}


def test_first_window_locked(next_signals):
    r = next_signals.iloc[0]
    assert r['first_datetime']  == '2025-01-01T18:00:00'
    assert r['first_signal']    == 'long'
    assert r['first_box_id']    == 'M-IH_2025-01-02'
    assert r['first_box_type']  == 'M-IH'
    assert r['first_close']     == 21322.25
    assert r['last_datetime']   == '2025-01-01T22:00:00'
    assert r['last_signal']     == 'long'
    assert r['last_close']      == 21389.5
    assert r['window_high']     == 21396.75
    assert r['window_low']      == 21121.75
    assert r['tp']              == 74.5
    assert r['sl']              == 200.5
    assert int(r['holds_between']) == 0


def test_last_window_locked(next_signals):
    r = next_signals.iloc[-1]
    assert r['first_datetime']  == '2026-05-19T10:00:00'
    assert r['first_signal']    == 'long'
    assert r['first_close']     == 29068.75
    assert r['last_datetime']   == '2026-05-19T18:00:00'
    assert r['last_signal']     == 'long'
    assert r['last_close']      == 28950.0
    assert r['window_high']     == 29126.5
    assert r['window_low']      == 28663.0
    assert r['tp']              == 57.75
    assert r['sl']              == 405.75
    assert int(r['holds_between']) == 1


def test_window_extremes_locked(next_signals):
    assert float(next_signals['window_high'].max()) == 29782.0
    assert float(next_signals['window_low'].min())  == 16460.0


def test_tp_sl_maxima_locked(next_signals):
    assert float(next_signals['tp'].max()) == 1735.5
    assert float(next_signals['sl'].max()) == 1672.25


def test_per_direction_tp_sl_maxima_locked(next_signals):
    long_df  = next_signals[next_signals['first_signal'] == 'long']
    short_df = next_signals[next_signals['first_signal'] == 'short']
    assert float(long_df['tp'].max())  == 1452.75
    assert float(long_df['sl'].max())  == 1672.25
    assert float(short_df['tp'].max()) == 1735.5
    assert float(short_df['sl'].max()) == 1031.25


def test_holds_between_locked(next_signals):
    assert int(next_signals['holds_between'].max()) == 23


def test_output_schema_locked(next_signals):
    assert list(next_signals.columns) == [
        'first_datetime', 'first_open', 'first_high', 'first_low', 'first_close',
        'first_signal', 'first_box_id', 'first_box_type',
        'last_datetime', 'last_open', 'last_high', 'last_low', 'last_close',
        'last_signal', 'last_box_id', 'last_box_type',
        'window_high', 'window_low',
        'tp', 'sl',
        'holds_between',
    ]


def test_box_id_columns_always_populated(next_signals):
    assert (next_signals['first_box_id'].astype(str).str.len()    > 0).all()
    assert (next_signals['last_box_id'].astype(str).str.len()     > 0).all()
    assert (next_signals['first_box_type'].astype(str).str.len()  > 0).all()
    assert (next_signals['last_box_type'].astype(str).str.len()   > 0).all()


def test_box_type_matches_first_4_chars_per_component(next_signals):
    for _, r in next_signals.iterrows():
        for parent, derived in (
            ('first_box_id', 'first_box_type'),
            ('last_box_id',  'last_box_type'),
        ):
            expected = ';'.join(p[:4] for p in str(r[parent]).split(';'))
            assert r[derived] == expected, f"row mismatch on {parent}: {r[parent]} -> {r[derived]} (expected {expected})"


def test_multi_box_id_row_counts_locked(next_signals):
    multi_first = next_signals['first_box_id'].astype(str).str.contains(';').sum()
    multi_last  = next_signals['last_box_id'].astype(str).str.contains(';').sum()
    assert int(multi_first) == 190
    assert int(multi_last)  == 191


def test_all_tp_sl_non_negative(next_signals):
    assert (next_signals['tp'] >= 0).all()
    assert (next_signals['sl'] >= 0).all()


def test_direction_aware_tp_sl_formula(next_signals):
    for _, r in next_signals.iterrows():
        if r['first_close'] > r['first_open']:
            assert r['tp'] == r['window_high'] - r['first_close']
            assert r['sl'] == r['first_close'] - r['window_low']
        else:
            assert r['first_close'] < r['first_open']
            assert r['tp'] == r['first_close'] - r['window_low']
            assert r['sl'] == r['window_high'] - r['first_close']


def test_first_last_signals_in_long_or_short(next_signals):
    """Stage 1.1: endpoints are each long or short — but NOT required to be
    opposite (unlike stage1.0)."""
    assert set(next_signals['first_signal'].unique()) <= {'long', 'short'}
    assert set(next_signals['last_signal'].unique())  <= {'long', 'short'}


def test_all_adjacent_windows_share_endpoint(next_signals):
    """Stage 1.1: every adjacent pair shares — no discard branches."""
    df = next_signals
    shared = sum(
        df['last_datetime'].iloc[i] == df['first_datetime'].iloc[i + 1]
        for i in range(len(df) - 1)
    )
    assert shared == len(df) - 1
