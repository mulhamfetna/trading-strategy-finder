"""Regression locks for Stage 2 against the full real-data preset.

Pins counts and first/last reverse-window values computed from
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

from stage1_0_reverse_signals.generate_stage2 import generate  # noqa: E402

_REPO_ROOT = os.path.abspath(os.path.join(_HERE, '..', '..', '..', '..'))
_SIGNALS_FULL = os.path.join(_REPO_ROOT, 'subprojects', 'signals', 'signals_full.csv')

pytestmark = pytest.mark.skipif(
    not os.path.exists(_SIGNALS_FULL),
    reason='signals_full.csv not present (gitignored).',
)


@pytest.fixture(scope='module')
def reverse_signals() -> pd.DataFrame:
    signals_df = pd.read_csv(_SIGNALS_FULL)
    return generate(signals_df)


def test_total_window_count_locked(reverse_signals):
    assert len(reverse_signals) == 372


def test_direction_split_locked(reverse_signals):
    counts = reverse_signals['first_signal'].value_counts().to_dict()
    assert counts == {'long': 186, 'short': 186}


def test_first_window_locked(reverse_signals):
    r = reverse_signals.iloc[0]
    assert r['first_datetime']  == '2025-01-01T22:00:00'
    assert r['first_signal']    == 'long'
    assert r['first_box_id']    == 'M-IH_2025-01-02'
    assert r['first_box_type']  == 'M-IH'
    assert r['first_close']     == 21389.5
    assert r['last_datetime']   == '2025-01-02T10:00:00'
    assert r['last_signal']     == 'short'
    assert r['last_box_id']     == 'M-IH_2025-01-02;W-RL_2025-01-02'
    assert r['last_box_type']   == 'M-IH;W-RL'
    assert r['last_close']      == 21047.5
    assert r['window_high']     == 21490.5
    assert r['window_low']      == 20983.75
    assert r['tp']              == 101.0
    assert r['sl']              == 405.75
    assert int(r['holds_between']) == 2


def test_last_window_locked(reverse_signals):
    # Last row has a red (short) anchor — tp = first_close − window_low,
    # sl = window_high − first_close.
    r = reverse_signals.iloc[-1]
    assert r['first_datetime']  == '2026-05-15T14:00:00'
    assert r['first_signal']    == 'short'
    assert r['first_box_id']    == 'M-TH_2026-05-15'
    assert r['first_box_type']  == 'M-TH'
    assert r['first_open']      == 29449.0
    assert r['first_close']     == 29173.0
    assert r['last_datetime']   == '2026-05-18T14:00:00'
    assert r['last_signal']     == 'long'
    assert r['last_box_id']     == 'M-RH_2026-05-18;W-IL_2026-05-18'
    assert r['last_box_type']   == 'M-RH;W-IL'
    assert r['last_close']      == 29076.0
    assert r['window_high']     == 29486.75
    assert r['window_low']      == 28814.75
    assert r['tp']              == 358.25   # 29173.0 − 28814.75
    assert r['sl']              == 313.75   # 29486.75 − 29173.0
    assert int(r['holds_between']) == 5


def test_window_extremes_locked(reverse_signals):
    assert float(reverse_signals['window_high'].max()) == 29782.0
    assert float(reverse_signals['window_low'].min())  == 16480.0


def test_tp_sl_maxima_locked(reverse_signals):
    # Under direction-aware tp/sl: the biggest single tp now comes from a
    # short anchor whose window low fell far below the anchor close;
    # the biggest single sl comes from a long anchor whose window low
    # fell far below the anchor close.
    assert float(reverse_signals['tp'].max()) == 628.0
    assert float(reverse_signals['sl'].max()) == 1038.75


def test_per_direction_tp_sl_maxima_locked(reverse_signals):
    long_df  = reverse_signals[reverse_signals['first_signal'] == 'long']
    short_df = reverse_signals[reverse_signals['first_signal'] == 'short']
    assert float(long_df['tp'].max())  == 441.0
    assert float(long_df['sl'].max())  == 1038.75
    assert float(short_df['tp'].max()) == 628.0
    assert float(short_df['sl'].max()) == 1031.25


def test_holds_between_locked(reverse_signals):
    assert int(reverse_signals['holds_between'].max()) == 22


def test_output_schema_locked(reverse_signals):
    assert list(reverse_signals.columns) == [
        'first_datetime', 'first_open', 'first_high', 'first_low', 'first_close',
        'first_signal', 'first_box_id', 'first_box_type',
        'last_datetime', 'last_open', 'last_high', 'last_low', 'last_close',
        'last_signal', 'last_box_id', 'last_box_type',
        'window_high', 'window_low',
        'tp', 'sl',
        'holds_between',
    ]


def test_box_id_columns_always_populated(reverse_signals):
    # Every emitted window has long-or-short endpoints (never hold),
    # so first_box_id / last_box_id (and the derived _type cols) are non-empty.
    assert (reverse_signals['first_box_id'].astype(str).str.len()    > 0).all()
    assert (reverse_signals['last_box_id'].astype(str).str.len()     > 0).all()
    assert (reverse_signals['first_box_type'].astype(str).str.len()  > 0).all()
    assert (reverse_signals['last_box_type'].astype(str).str.len()   > 0).all()


def test_box_type_matches_first_4_chars_per_component(reverse_signals):
    """For every row, *_box_type is exactly first-4-chars of each ';'-component
    of the parent *_box_id, in the same order."""
    for _, r in reverse_signals.iterrows():
        for parent, derived in (
            ('first_box_id', 'first_box_type'),
            ('last_box_id',  'last_box_type'),
        ):
            expected = ';'.join(p[:4] for p in str(r[parent]).split(';'))
            assert r[derived] == expected, f"row mismatch on {parent}: {r[parent]} -> {r[derived]} (expected {expected})"


def test_multi_box_id_row_counts_locked(reverse_signals):
    # Rough volume check that the semicolon-joined format is producing the
    # expected number of multi-box endpoints (regression guard against an
    # accidental switch back to single-box semantics).
    multi_first = reverse_signals['first_box_id'].astype(str).str.contains(';').sum()
    multi_last  = reverse_signals['last_box_id'].astype(str).str.contains(';').sum()
    assert int(multi_first) == 80
    assert int(multi_last)  == 95


def test_all_tp_sl_non_negative(reverse_signals):
    # Both formulas produce non-negative values by construction:
    #   green anchor: window_high >= first_close ≥ first_open > window_low
    #   red   anchor: window_high > first_open ≥ first_close >= window_low
    assert (reverse_signals['tp'] >= 0).all()
    assert (reverse_signals['sl'] >= 0).all()


def test_direction_aware_tp_sl_formula(reverse_signals):
    """tp/sl on every row matches the color-keyed formula exactly."""
    for _, r in reverse_signals.iterrows():
        if r['first_close'] > r['first_open']:
            # green anchor
            assert r['tp'] == r['window_high'] - r['first_close']
            assert r['sl'] == r['first_close'] - r['window_low']
        else:
            # red anchor (Stage 1 guarantees no doji anchor)
            assert r['first_close'] < r['first_open']
            assert r['tp'] == r['first_close'] - r['window_low']
            assert r['sl'] == r['window_high'] - r['first_close']


def test_first_last_signals_always_opposite(reverse_signals):
    pairs = list(zip(reverse_signals['first_signal'], reverse_signals['last_signal']))
    assert all((a, b) in {('long', 'short'), ('short', 'long')} for a, b in pairs)


def test_adjacent_windows_share_endpoint(reverse_signals):
    # The reverse candle of window N must equal the anchor of window N+1.
    # (Some pairs may NOT share endpoints when there was a same-state discard
    # between them, but the typical case shares.)
    df = reverse_signals
    shared = sum(
        df['last_datetime'].iloc[i] == df['first_datetime'].iloc[i + 1]
        for i in range(len(df) - 1)
    )
    # At least one share must exist; we don't lock the exact count.
    assert shared > 0
