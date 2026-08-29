"""Unit tests for the ORB reference on synthetic sessions with hand-computed answers (#183)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from optimize.orb.orb_reference import run_cell, run_c1, sessionize


def _session(day: str, start: str, n: int, closes: list[float], width: float = 0.5) -> pd.DataFrame:
    """n one-minute bars from day+start; each bar's open = prev close, high/low = close +/- width."""
    t0 = pd.Timestamp(f"{day} {start}")
    rows = []
    prev = closes[0]
    for i, c in enumerate(closes[:n]):
        rows.append(dict(datetime=t0 + pd.Timedelta(minutes=i), open=prev, high=max(prev, c) + width,
                         low=min(prev, c) - width, close=c, volume=1))
        prev = c
    return pd.DataFrame(rows)


def test_globex_session_id_maps_evening_bars_to_next_day():
    df = _session("2026-03-02", "17:58", 5, [100, 100, 100, 100, 100])
    s = sessionize(df, "globex", "NQ")
    assert list(s["session"]) == ["2026-03-02", "2026-03-02", "2026-03-03", "2026-03-03", "2026-03-03"]
    assert list(s["msa"][2:]) == [0, 1, 2]


def test_long_breakout_r1_hits_target_gap_fill_at_open():
    # OR (5 bars) closes 100..100 -> high 100.5 low 99.5 ; bar 6 closes 101 (> ORH) -> entry at bar 7 open = 101
    # R1: stop = 99.5, R = 1.5, target = 116. Then a bar gaps to open 120 -> fill at OPEN (120), not at 116.
    closes = [100, 100, 100, 100, 100, 101, 101, 120, 120, 120]
    df = _session("2026-03-02", "09:30", len(closes), closes)
    df.loc[7, "open"] = 120; df.loc[7, "high"] = 121; df.loc[7, "low"] = 119      # the gap bar
    book = run_cell(df, "cash", "NQ", 5, "R1")
    assert len(book) == 1
    t = book.iloc[0]
    assert t.direction == "long" and t.entry_price == 101 and t.exit_reason == "TARGET" and t.exit_price == 120
    assert t.points == pytest.approx(19.0)


def test_short_breakout_r3_stop_first_when_both_touched():
    # OR high 100.5 low 99.5; bar 6 closes 99 (< ORL) -> short entry at bar 7 open = 99
    # R3: stop = 100.5, target = 99 - 0.5*1.0 = 98.5. Bar 7 spans 98..101 (both touched) -> STOP first at 100.5
    closes = [100, 100, 100, 100, 100, 99, 99, 99]
    df = _session("2026-03-02", "09:30", len(closes), closes)
    df.loc[6, "low"] = 98.8                                       # entry bar must not reach the target (98.5)
    df.loc[7, "high"] = 101; df.loc[7, "low"] = 98
    book = run_cell(df, "cash", "NQ", 5, "R3")
    t = book.iloc[0]
    assert t.direction == "short" and t.exit_reason == "STOP" and t.exit_price == 100.5
    assert t.points == pytest.approx(99 - 100.5)


def test_no_trade_when_both_sides_break_same_bar_and_void_range():
    closes = [100, 100, 100, 100, 100, 100, 100]
    df = _session("2026-03-02", "09:30", len(closes), closes)
    df.loc[5, "close"] = 100; df.loc[5, "high"] = 105; df.loc[5, "low"] = 95      # touches both, closes inside -> no breakout
    assert run_cell(df, "cash", "NQ", 5, "R1").empty
    df2 = _session("2026-03-02", "09:30", 7, closes).drop(index=2)                 # missing OR bar -> void
    assert run_cell(df2, "cash", "NQ", 5, "R1").empty


def test_eod_flat_and_point_value():
    closes = [100, 100, 100, 100, 100, 101, 102, 103]
    df = _session("2026-03-02", "09:30", len(closes), closes)
    book = run_cell(df, "cash", "ES", 5, "R2")        # R2 needs ATR14 -> none on a single session -> no trade
    assert book.empty
    book = run_cell(df, "cash", "ES", 5, "R1", point_value=50.0)
    t = book.iloc[0]
    assert t.exit_reason == "EOD" and t.exit_price == 103 and t.pnl == pytest.approx((103 - 101) * 50)


def test_c1_threshold_uses_only_prior_sessions():
    days = pd.bdate_range("2026-01-05", periods=70)
    frames = []
    rng = np.random.default_rng(0)
    for d in days:
        c0 = 100.0
        closes = list(c0 + np.cumsum(rng.normal(0, 0.05, 30)))
        frames.append(_session(d.strftime("%Y-%m-%d"), "09:30", 30, closes, width=0.01))
    df = pd.concat(frames, ignore_index=True)
    book = run_c1(df, "NQ")
    # first 60 sessions cannot trade (no rho); any trade must be in the last 10 days
    assert book.empty or pd.to_datetime(book["session"]).min() > days[59]
