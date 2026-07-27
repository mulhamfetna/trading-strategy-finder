"""Option C — the VETO thesis: is a trade worse when a daily zone sits between entry and target?

These tests pin the geometry on hand-built trades whose answer is known by construction.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.daily_boxes.veto_test import veto_split, wall_ahead_mask   # noqa: E402

_PAIRS = [("DU", "DL", "D")]


def _box():
    # one box row for 2025-01-02, a daily zone spanning 120..130
    return pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-02"]),
        "DU": [130.0],
        "DL": [120.0],
    }).set_index("Date", drop=False)


def _trade(direction, entry_price, pnl):
    return {"entry_time": pd.Timestamp("2025-01-02 08:00"), "entry_price": entry_price,
            "direction": direction, "pnl_points": pnl}


def test_long_with_zone_between_entry_and_target_is_walled():
    # entry 100, tp 50 -> target 150. Zone lower edge 120 is inside (100, 150] -> WALL
    m = wall_ahead_mask([_trade("long", 100.0, 0.0)], _box(), _PAIRS, tp_points=50.0)
    assert list(m) == [True]


def test_long_with_zone_beyond_target_is_clear():
    # entry 100, tp 10 -> target 110. Zone lower edge 120 is beyond -> no wall
    m = wall_ahead_mask([_trade("long", 100.0, 0.0)], _box(), _PAIRS, tp_points=10.0)
    assert list(m) == [False]


def test_long_with_zone_behind_entry_is_clear():
    # entry 200 is ABOVE the zone entirely -> nothing ahead
    m = wall_ahead_mask([_trade("long", 200.0, 0.0)], _box(), _PAIRS, tp_points=50.0)
    assert list(m) == [False]


def test_short_direction_is_mirrored():
    # short from 150, tp 50 -> target 100. Zone upper edge 130 is inside [100, 150) -> WALL
    m = wall_ahead_mask([_trade("short", 150.0, 0.0)], _box(), _PAIRS, tp_points=50.0)
    assert list(m) == [True]
    # short from 110 -> target 60; zone upper 130 is ABOVE entry, not ahead -> clear
    m2 = wall_ahead_mask([_trade("short", 110.0, 0.0)], _box(), _PAIRS, tp_points=50.0)
    assert list(m2) == [False]


def test_nan_zone_never_counts_as_a_wall():
    box = pd.DataFrame({"Date": pd.to_datetime(["2025-01-02"]),
                        "DU": [np.nan], "DL": [np.nan]}).set_index("Date", drop=False)
    m = wall_ahead_mask([_trade("long", 100.0, 0.0)], box, _PAIRS, tp_points=50.0)
    assert list(m) == [False]


def test_zero_or_negative_tp_is_an_error():
    with pytest.raises(ValueError):
        wall_ahead_mask([_trade("long", 100.0, 0.0)], _box(), _PAIRS, tp_points=0.0)


def test_veto_split_reports_both_groups_and_the_removed_pnl():
    trades = [_trade("long", 100.0, +10.0),    # walled  (zone 120 within target 150)
              _trade("long", 100.0, -20.0),    # walled
              _trade("long", 200.0, +5.0)]     # clear
    r = veto_split(trades, _box(), _PAIRS, tp_points=50.0, point_value=20.0)
    assert r["n_walled"] == 2
    assert r["n_clear"] == 1
    assert r["mean_walled_points"] == pytest.approx(-5.0)
    assert r["mean_clear_points"] == pytest.approx(5.0)
    # vetoing the walled trades removes their summed P&L
    assert r["pnl_removed_dollars"] == pytest.approx((10.0 - 20.0) * 20.0)


def test_veto_split_handles_an_all_clear_book_without_crashing():
    trades = [_trade("long", 200.0, +5.0)]
    r = veto_split(trades, _box(), _PAIRS, tp_points=50.0, point_value=20.0)
    assert r["n_walled"] == 0
    assert np.isnan(r["mean_walled_points"])
