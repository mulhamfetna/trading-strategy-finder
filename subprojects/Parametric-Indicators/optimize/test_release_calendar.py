"""Task 1 — the release calendar loads, validates, and covers the backtest window."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from optimize.fundamentals import release_calendar as rc


def test_calendar_loads_with_expected_schema():
    cal = rc.load_calendar()
    assert list(cal.columns) == ["Date", "event", "agency"]
    assert pd.api.types.is_datetime64_any_dtype(cal["Date"])
    assert cal["Date"].dt.tz is None, "must be tz-naive US-Eastern wall-clock"


def test_calendar_is_sorted_and_deduplicated():
    cal = rc.load_calendar()
    assert cal["Date"].is_monotonic_increasing
    assert not cal["Date"].duplicated().any()


def test_calendar_covers_the_backtest_window():
    cal = rc.load_calendar()
    assert cal["Date"].min() < pd.Timestamp("2025-02-15")
    assert cal["Date"].max() > pd.Timestamp("2026-04-15")


def test_release_times_are_only_the_three_known_clock_times():
    cal = rc.load_calendar()
    hhmm = set(cal["Date"].dt.strftime("%H:%M"))
    assert hhmm <= rc.VALID_TIMES, f"unexpected release times: {hhmm - rc.VALID_TIMES}"


def test_event_count_is_plausible():
    # ~9 recurring releases over ~17 months. Far fewer means a fetch silently failed;
    # far more means two-star events leaked in.
    cal = rc.load_calendar()
    assert 100 <= len(cal) <= 260, f"got {len(cal)} events"


def test_payrolls_is_present_and_at_0830():
    cal = rc.load_calendar()
    nfp = cal[cal["event"] == "nonfarm_payrolls"]
    assert len(nfp) >= 12, "expected at least 12 payrolls releases in the window"
    assert set(nfp["Date"].dt.strftime("%H:%M")) == {"08:30"}


def test_rejects_a_calendar_with_a_bad_time(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Date,event,agency\n2025-03-07 07:15:00,nonfarm_payrolls,BLS\n")
    with pytest.raises(ValueError, match="unexpected release time"):
        rc.load_calendar(str(bad))
