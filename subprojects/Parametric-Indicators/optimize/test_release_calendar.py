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
    # ~9 recurring high-impact releases per month. Far fewer means a fetch silently failed;
    # far more means two-star events leaked in.
    #
    # Scaled to the calendar's OWN span rather than a hardcoded count: this guard was written for a
    # 17-MONTH calendar (bound 100..260) and went stale the moment the fundamental-analysis workstream
    # extended it to 17 YEARS (1,208 events, 2010->2026). Deriving the band from the span keeps the
    # original intent — catch a silent fetch hole or a two-star leak — without breaking on every
    # legitimate extension.
    cal = rc.load_calendar()
    span_months = (cal["Date"].max() - cal["Date"].min()).days / 30.44
    per_month = len(cal) / span_months
    assert 3.0 <= per_month <= 15.0, (
        f"got {len(cal)} events over {span_months:.1f} months = {per_month:.2f}/month "
        f"(expected ~9/month; too few => a fetch silently failed, too many => two-star events leaked in)"
    )


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
