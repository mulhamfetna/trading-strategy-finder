"""Branch-coverage tests for Stage 2 — hand-built signal streams, no real data."""
from __future__ import annotations

import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.abspath(__file__))
_STAGE2 = os.path.abspath(os.path.join(_HERE, '..'))
sys.path.insert(0, os.path.dirname(_STAGE2))  # so `stage2` is importable

from stage1_0_reverse_signals.generate_stage2 import generate  # noqa: E402


_STAGE1_COLS = [
    'datetime', 'open', 'high', 'low', 'close', 'volume',
    'signal', 'box_id', 'box_upper', 'box_lower',
]


def _row(dt, o, h, l, c, signal, box='B_2025-01-01', bu=100.0, bl=90.0):
    return {
        'datetime': dt, 'open': o, 'high': h, 'low': l, 'close': c, 'volume': 0,
        'signal': signal, 'box_id': box, 'box_upper': bu, 'box_lower': bl,
    }


def _stage1(rows):
    return pd.DataFrame(rows, columns=_STAGE1_COLS)


# ──────────────────────────────────────────────────────────────────
# Tests 1-12 per Round-3 FINAL §4
# ──────────────────────────────────────────────────────────────────

def test_empty_input_yields_empty_output():
    df = generate(_stage1([]))
    assert len(df) == 0
    assert list(df.columns)[0] == 'first_datetime'


def test_only_holds_yields_empty_output():
    rows = [
        _row('2025-01-01T00:00:00', 100, 105, 95, 100, 'hold'),
        _row('2025-01-01T04:00:00', 100, 105, 95, 100, 'hold'),
        _row('2025-01-01T08:00:00', 100, 105, 95, 100, 'hold'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 0


def test_single_long_never_reversed_yields_empty():
    rows = [
        _row('2025-01-01T00:00:00', 100, 105, 95, 102, 'long'),
        _row('2025-01-01T04:00:00', 102, 107, 97, 103, 'hold'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 0


def test_immediate_long_to_short_zero_holds_between():
    # green anchor (open=100, close=108) → tp = high − close, sl = close − low
    rows = [
        _row('2025-01-01T00:00:00', 100, 110, 95, 108, 'long'),
        _row('2025-01-01T04:00:00', 108, 112, 80, 85,  'short'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 1
    r = df.iloc[0]
    assert r['first_signal'] == 'long'
    assert r['last_signal'] == 'short'
    assert r['holds_between'] == 0
    assert r['window_high'] == 112.0
    assert r['window_low'] == 80.0
    assert r['tp'] == 112 - 108   # window_high − first_close
    assert r['sl'] == 108 - 80    # first_close − window_low


def test_long_two_holds_short_holds_between_is_two():
    rows = [
        _row('2025-01-01T00:00:00', 100, 110, 95, 108, 'long'),
        _row('2025-01-01T04:00:00', 108, 115, 100, 110, 'hold'),
        _row('2025-01-01T08:00:00', 110, 120, 105, 115, 'hold'),
        _row('2025-01-01T12:00:00', 115, 116, 70, 75, 'short'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 1
    r = df.iloc[0]
    assert r['holds_between'] == 2
    assert r['window_high'] == 120.0
    assert r['window_low'] == 70.0


def test_long_repeat_discards_first_anchor():
    rows = [
        _row('2025-01-01T00:00:00', 100, 110, 95, 108, 'long'),
        _row('2025-01-01T04:00:00', 108, 115, 100, 113, 'long'),  # discard anchor 0
        _row('2025-01-01T08:00:00', 113, 116, 100, 105, 'hold'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 0  # second long is still open at EOF -> dropped


def test_long_hold_long_hold_short_anchor_is_second_long():
    rows = [
        _row('2025-01-01T00:00:00', 100, 110, 95, 108, 'long'),
        _row('2025-01-01T04:00:00', 108, 109, 100, 105, 'hold'),
        _row('2025-01-01T08:00:00', 105, 115, 100, 112, 'long'),   # new anchor
        _row('2025-01-01T12:00:00', 112, 118, 100, 110, 'hold'),
        _row('2025-01-01T16:00:00', 110, 113, 70, 80,  'short'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 1
    r = df.iloc[0]
    assert r['first_datetime'] == '2025-01-01T08:00:00'
    assert r['holds_between'] == 1
    # window covers candles 2,3,4 -> high = max(115,118,113)=118; low=min(100,100,70)=70
    assert r['window_high'] == 118.0
    assert r['window_low'] == 70.0


def test_long_short_long_emits_two_windows_with_shared_short():
    rows = [
        _row('2025-01-01T00:00:00', 100, 110, 95, 108, 'long'),
        _row('2025-01-01T04:00:00', 108, 112, 70, 75,  'short'),
        _row('2025-01-01T08:00:00', 75,  120, 72, 115, 'long'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 2
    r0, r1 = df.iloc[0], df.iloc[1]
    assert r0['first_signal'] == 'long'   and r0['last_signal'] == 'short'
    assert r1['first_signal'] == 'short'  and r1['last_signal'] == 'long'
    # The shared candle: r0.last_datetime == r1.first_datetime
    assert r0['last_datetime'] == r1['first_datetime'] == '2025-01-01T04:00:00'


def test_green_anchor_tp_is_window_high_minus_close():
    # green anchor (open=95, close=100) → tp = window_high − first_close
    rows = [
        _row('2025-01-01T00:00:00',  95, 110, 90, 100, 'long'),
        _row('2025-01-01T04:00:00', 100, 200, 95, 105, 'hold'),   # high spike to 200
        _row('2025-01-01T08:00:00', 105, 106, 70,  75, 'short'),
    ]
    df = generate(_stage1(rows))
    r = df.iloc[0]
    assert r['window_high'] == 200.0
    assert r['tp'] == 200 - 100   # window_high − first_close
    assert r['tp'] >= 0


def test_green_anchor_sl_is_close_minus_window_low():
    # green anchor (open=95, close=100) → sl = first_close − window_low
    rows = [
        _row('2025-01-01T00:00:00',  95, 110, 90, 100, 'long'),
        _row('2025-01-01T04:00:00', 100, 105, 50,  90, 'hold'),   # low dive to 50
        _row('2025-01-01T08:00:00',  90, 100, 70,  75, 'short'),
    ]
    df = generate(_stage1(rows))
    r = df.iloc[0]
    assert r['window_low'] == 50.0
    assert r['sl'] == 100 - 50    # first_close − window_low
    assert r['sl'] >= 0


def test_red_anchor_tp_is_close_minus_window_low():
    # red anchor (open=105, close=100) → tp = first_close − window_low
    rows = [
        _row('2025-01-01T00:00:00', 105, 110, 95, 100, 'short'),
        _row('2025-01-01T04:00:00', 100, 105, 50,  90, 'hold'),   # low dive to 50
        _row('2025-01-01T08:00:00',  90, 130, 85, 120, 'long'),
    ]
    df = generate(_stage1(rows))
    r = df.iloc[0]
    assert r['first_signal'] == 'short'
    assert r['window_low'] == 50.0
    assert r['tp'] == 100 - 50    # first_close − window_low
    assert r['tp'] >= 0


def test_red_anchor_sl_is_window_high_minus_close():
    # red anchor (open=105, close=100) → sl = window_high − first_close
    rows = [
        _row('2025-01-01T00:00:00', 105, 110, 95, 100, 'short'),
        _row('2025-01-01T04:00:00', 100, 200, 95, 110, 'hold'),   # high spike to 200
        _row('2025-01-01T08:00:00', 110, 130, 85, 125, 'long'),
    ]
    df = generate(_stage1(rows))
    r = df.iloc[0]
    assert r['first_signal'] == 'short'
    assert r['window_high'] == 200.0
    assert r['sl'] == 200 - 100   # window_high − first_close
    assert r['sl'] >= 0


def test_nan_box_hold_rows_participate_in_window_extremes():
    # A hold candle whose only Stage 1 row has NaN box columns still counts
    # as a hold candle in the candle-level stream and contributes its high/low.
    rows = [
        _row('2025-01-01T00:00:00', 100, 110, 95, 108, 'long'),
        {
            'datetime': '2025-01-01T04:00:00', 'open': 108, 'high': 130,
            'low': 60, 'close': 100, 'volume': 0,
            'signal': 'hold', 'box_id': None, 'box_upper': None, 'box_lower': None,
        },
        _row('2025-01-01T08:00:00', 100, 105, 70, 75, 'short'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 1
    r = df.iloc[0]
    assert r['holds_between'] == 1
    assert r['window_high'] == 130.0
    assert r['window_low'] == 60.0


def test_multi_row_anchor_candle_collapses_to_single_anchor():
    # A single 4h candle with two Stage 1 rows (e.g. long on W-RH AND long on
    # M-IH). The collapse must treat it as one candle whose state is 'long',
    # not as two candles. The anchor's first_box_id must be the
    # semicolon-joined sorted list of both matching box_ids.
    rows = [
        # candle 0 has two long rows on different box_ids (deliberately
        # inserted out of alphabetical order to verify sorting)
        {'datetime': '2025-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 95,
         'close': 108, 'volume': 0, 'signal': 'long', 'box_id': 'B_2025-01-01',
         'box_upper': 106, 'box_lower': 99},
        {'datetime': '2025-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 95,
         'close': 108, 'volume': 0, 'signal': 'long', 'box_id': 'A_2025-01-01',
         'box_upper': 105, 'box_lower': 98},
        _row('2025-01-01T04:00:00', 108, 112, 70, 75, 'short', box='Z_2025-01-01'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 1
    r = df.iloc[0]
    assert r['first_datetime'] == '2025-01-01T00:00:00'
    assert r['first_signal'] == 'long'
    assert r['first_box_id'] == 'A_2025-01-01;B_2025-01-01'   # sorted + joined
    assert r['last_box_id'] == 'Z_2025-01-01'                  # single box
    assert r['holds_between'] == 0


def test_box_id_excludes_hold_rows_on_same_candle():
    # A candle has both a long row and a hold row (different level pairs).
    # first_box_id must contain ONLY the long row's box_id, not the hold one.
    rows = [
        {'datetime': '2025-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 95,
         'close': 108, 'volume': 0, 'signal': 'long', 'box_id': 'LONG_BOX',
         'box_upper': 105, 'box_lower': 98},
        {'datetime': '2025-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 95,
         'close': 108, 'volume': 0, 'signal': 'hold', 'box_id': 'HOLD_BOX',
         'box_upper': 200, 'box_lower': 150},
        _row('2025-01-01T04:00:00', 108, 112, 70, 75, 'short', box='SHORT_BOX'),
    ]
    df = generate(_stage1(rows))
    r = df.iloc[0]
    assert r['first_box_id'] == 'LONG_BOX'
    assert r['last_box_id']  == 'SHORT_BOX'


def test_leading_holds_are_skipped():
    rows = [
        _row('2025-01-01T00:00:00', 100, 105, 95, 100, 'hold'),
        _row('2025-01-01T04:00:00', 100, 105, 95, 100, 'hold'),
        _row('2025-01-01T08:00:00', 100, 110, 95, 108, 'long'),
        _row('2025-01-01T12:00:00', 108, 112, 70, 75,  'short'),
    ]
    df = generate(_stage1(rows))
    assert len(df) == 1
    assert df.iloc[0]['first_datetime'] == '2025-01-01T08:00:00'


def test_output_schema_locked():
    rows = [
        _row('2025-01-01T00:00:00', 100, 110, 95, 108, 'long'),
        _row('2025-01-01T04:00:00', 108, 112, 70, 75,  'short'),
    ]
    df = generate(_stage1(rows))
    assert list(df.columns) == [
        'first_datetime', 'first_open', 'first_high', 'first_low', 'first_close',
        'first_signal', 'first_box_id', 'first_box_type',
        'last_datetime', 'last_open', 'last_high', 'last_low', 'last_close',
        'last_signal', 'last_box_id', 'last_box_type',
        'window_high', 'window_low',
        'tp', 'sl',
        'holds_between',
    ]


def test_box_type_strips_date_for_single_box():
    rows = [
        _row('2025-01-01T00:00:00', 100, 110, 95, 108, 'long',  box='M-IH_2025-01-01'),
        _row('2025-01-01T04:00:00', 108, 112, 70,  75, 'short', box='W-RL_2025-01-01'),
    ]
    df = generate(_stage1(rows))
    r = df.iloc[0]
    assert r['first_box_id']   == 'M-IH_2025-01-01'
    assert r['first_box_type'] == 'M-IH'
    assert r['last_box_id']    == 'W-RL_2025-01-01'
    assert r['last_box_type']  == 'W-RL'


def test_box_type_preserves_order_and_count_in_multi_box():
    rows = [
        # Two long box_ids on the anchor candle; one short on the reverse.
        {'datetime': '2025-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 95,
         'close': 108, 'volume': 0, 'signal': 'long', 'box_id': 'M-IH_2025-01-01',
         'box_upper': 105, 'box_lower': 98},
        {'datetime': '2025-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 95,
         'close': 108, 'volume': 0, 'signal': 'long', 'box_id': 'W-RL_2025-01-01',
         'box_upper': 106, 'box_lower': 99},
        _row('2025-01-01T04:00:00', 108, 112, 70, 75, 'short', box='W-IL_2025-01-01'),
    ]
    df = generate(_stage1(rows))
    r = df.iloc[0]
    assert r['first_box_id']   == 'M-IH_2025-01-01;W-RL_2025-01-01'
    assert r['first_box_type'] == 'M-IH;W-RL'         # same order, semicolon-joined
    assert r['last_box_id']    == 'W-IL_2025-01-01'
    assert r['last_box_type']  == 'W-IL'


def test_box_type_collapses_sub_labels_to_first_4_chars():
    # Per the spec: literal first-4-chars rule. `M-TH_sub_2025-01-01` becomes
    # `M-TH`, the same prefix as `M-TH_2025-01-01`. If both fire on the same
    # candle, the resulting box_type has a duplicate — no dedup.
    rows = [
        {'datetime': '2025-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 95,
         'close': 108, 'volume': 0, 'signal': 'long', 'box_id': 'M-TH_2025-01-01',
         'box_upper': 105, 'box_lower': 98},
        {'datetime': '2025-01-01T00:00:00', 'open': 100, 'high': 110, 'low': 95,
         'close': 108, 'volume': 0, 'signal': 'long', 'box_id': 'M-TH_sub_2025-01-01',
         'box_upper': 106, 'box_lower': 99},
        _row('2025-01-01T04:00:00', 108, 112, 70, 75, 'short'),
    ]
    df = generate(_stage1(rows))
    r = df.iloc[0]
    # box_id stays distinct; box_type collapses both into 'M-TH'.
    assert r['first_box_id']   == 'M-TH_2025-01-01;M-TH_sub_2025-01-01'
    assert r['first_box_type'] == 'M-TH;M-TH'
