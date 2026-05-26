"""Synthetic-input regression tests for Stage 1 signal extractor.

Each test crafts a tiny candles + boxes CSV, runs generate(), and asserts
the row-by-row output matches the locked spec (Round 5 FINAL).
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

_HERE = os.path.dirname(__file__)
_SUBPROJECT_ROOT = os.path.abspath(os.path.join(_HERE, '..'))
sys.path.insert(0, _SUBPROJECT_ROOT)

from generate_stage1 import generate


def _write_candles(tmp_path, rows):
    """rows: list of (datetime_str, o, h, l, c, v)."""
    df = pd.DataFrame(rows, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
    path = tmp_path / 'candles.csv'
    df.to_csv(path, index=False)
    return str(path)


def _write_boxes(tmp_path, rows):
    """rows: list of dicts with at least 'Date' + level-pair columns.

    Always emits the full 52-column header to match NQ_full_data.csv
    schema. Missing cells stay NaN — they're treated as 'level inactive'.
    """
    cols = [
        'Date', 'Scraped_At', 'dOpen', 'wOpen', 'mOpen',
        'DIHD','DIHU','DILD','DILU','DRHD','DRHU','DRLD','DRLU',
        'MIHD','MIHU','MILD','MILU','MRHD','MRHU','MRLD','MRLU',
        'MTH1','MTH2','MTHD','MTHU',
        'WIHD','WIHU','WILD','WILU','WRHD','WRHU','WRLD','WRLU',
        'WTL1','WTL2','WTLD','WTLU','WTH1','WTH2','WTHD','WTHU',
        'DTL1','DTL2','DTLD','DTLU','MTL1','MTL2','MTLD','MTLU',
        'DTH1','DTH2','DTHD','DTHU',
    ]
    df = pd.DataFrame(rows, columns=cols)
    path = tmp_path / 'boxes.csv'
    df.to_csv(path, index=False)
    return str(path)


def test_candle_with_no_box_date_row_emits_single_hold(tmp_path):
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 100.0, 110.0, 90.0, 105.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2099-01-01'}])
    df = generate(candles, boxes)
    assert len(df) == 1
    assert df.iloc[0]['signal'] == 'hold'
    assert pd.isna(df.iloc[0]['box_id'])
    assert pd.isna(df.iloc[0]['box_upper'])
    assert pd.isna(df.iloc[0]['box_lower'])


def test_candle_with_all_nan_level_pairs_emits_single_hold(tmp_path):
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 100.0, 110.0, 90.0, 105.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05'}])
    df = generate(candles, boxes)
    assert len(df) == 1
    assert df.iloc[0]['signal'] == 'hold'
    assert pd.isna(df.iloc[0]['box_id'])


def test_candle_entirely_above_box_is_hold(tmp_path):
    # Candle [200, 210], box [100, 110] (via WRHU/WRHD → label 'W-RH').
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 205.0, 210.0, 200.0, 207.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0}])
    df = generate(candles, boxes)
    assert len(df) == 1
    assert df.iloc[0]['signal'] == 'hold'
    assert df.iloc[0]['box_id'] == 'W-RH_2025-01-05'


def test_candle_entirely_below_box_is_hold(tmp_path):
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 50.0, 60.0, 40.0, 55.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0}])
    df = generate(candles, boxes)
    assert df.iloc[0]['signal'] == 'hold'


def test_green_candle_touched_close_above_upper_is_long(tmp_path):
    # Box [100, 110]. Candle green: open=95, high=120, low=95, close=115.
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 95.0, 120.0, 95.0, 115.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0}])
    df = generate(candles, boxes)
    assert df.iloc[0]['signal'] == 'long'
    assert df.iloc[0]['box_upper'] == 110.0
    assert df.iloc[0]['box_lower'] == 100.0


def test_red_candle_touched_close_below_lower_is_short(tmp_path):
    # Box [100, 110]. Candle red: open=115, high=115, low=90, close=95.
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 115.0, 115.0, 90.0, 95.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0}])
    df = generate(candles, boxes)
    assert df.iloc[0]['signal'] == 'short'


def test_touched_but_close_inside_box_is_hold(tmp_path):
    # Box [100, 110]. Candle: open=95, high=108, low=95, close=105 (green, close inside).
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 95.0, 108.0, 95.0, 105.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0}])
    df = generate(candles, boxes)
    assert df.iloc[0]['signal'] == 'hold'


def test_doji_touched_close_above_is_hold(tmp_path):
    # Doji: open == close == 115, both above upper. Touched (low=95).
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 115.0, 120.0, 95.0, 115.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0}])
    df = generate(candles, boxes)
    assert df.iloc[0]['signal'] == 'hold'


def test_close_exactly_on_upper_is_hold_strict(tmp_path):
    # Green candle, close == upper exactly → must be hold (strict close rule).
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 95.0, 115.0, 95.0, 110.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0}])
    df = generate(candles, boxes)
    assert df.iloc[0]['signal'] == 'hold'


def test_touch_inclusive_at_lower_edge(tmp_path):
    # Green candle. high == box_lower exactly (touch inclusive). close > upper.
    # high=100 (== box_lower), close=115, low=100, open=100 → green (close>open).
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 100.0, 120.0, 100.0, 115.0, 1000)])
    boxes = _write_boxes(tmp_path, [{'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0}])
    df = generate(candles, boxes)
    assert df.iloc[0]['signal'] == 'long'


def test_two_active_level_pairs_emit_two_rows(tmp_path):
    # Two boxes on the same date: W-RH = [100, 110], M-RH = [120, 130].
    # Candle: green, open=95, high=125, low=95, close=115.
    #   vs W-RH [100,110]: touched, color green, close=115 > 110 → long
    #   vs M-RH [120,130]: touched (high=125 in box), but close=115 < 120 → not long;
    #                       also low=95 < 120, so touch overlaps. close inside or below.
    #                       close (115) is below lower (120) → red would be short, but candle is GREEN → hold.
    candles = _write_candles(tmp_path, [('2025-01-05 12:00:00', 95.0, 125.0, 95.0, 115.0, 1000)])
    boxes = _write_boxes(tmp_path, [{
        'Date': '2025-01-05',
        'WRHU': 110.0, 'WRHD': 100.0,
        'MRHU': 130.0, 'MRHD': 120.0,
    }])
    df = generate(candles, boxes)
    assert len(df) == 2
    signals_by_box = {row['box_id']: row['signal'] for _, row in df.iterrows()}
    assert signals_by_box['W-RH_2025-01-05'] == 'long'
    assert signals_by_box['M-RH_2025-01-05'] == 'hold'


def test_session_mapping_hour_ge_18_uses_next_day(tmp_path):
    # Candle at 18:00 on 2025-01-04 should map to box_date 2025-01-05.
    candles = _write_candles(tmp_path, [('2025-01-04 18:00:00', 95.0, 120.0, 95.0, 115.0, 1000)])
    boxes = _write_boxes(tmp_path, [
        {'Date': '2025-01-04'},  # no level pairs
        {'Date': '2025-01-05', 'WRHU': 110.0, 'WRHD': 100.0},
    ])
    df = generate(candles, boxes)
    assert len(df) == 1
    assert df.iloc[0]['signal'] == 'long'
    assert df.iloc[0]['box_id'] == 'W-RH_2025-01-05'
