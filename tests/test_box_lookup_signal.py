"""Tests for BoxLookup traversal-state-machine signal logic.

v3.1+ rule (2026-05-23): A signal fires only when the close TRANSITIONS
from one side of a box to the opposite side. Same-side repeats, inside-box
bars, and first observations return 'hold'. See MASTER_STRATEGY_GUIDE.md §2.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategy.box_lookup import BoxLookup


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _weekly_csv(path, dates=None, **levels) -> None:
    """Build a weekly box CSV. Pass `dates=` to override the single 2025-01-01 row.
    Each level kwarg can be a scalar (applies to all rows) or a list (one per row)."""
    if dates is None:
        dates = ['2025-01-01']
    n = len(dates)
    row_data = {}
    for c in _W_COLS:
        val = levels.get(c)
        if isinstance(val, list):
            assert len(val) == n
            row_data[c] = val
        else:
            row_data[c] = [val] * n
    pd.DataFrame({'Date': dates, **row_data}).to_csv(path, index=False)


def _monthly_csv(path, dates=None, **levels) -> None:
    if dates is None:
        dates = ['2025-01-01']
    n = len(dates)
    row_data = {}
    for c in _M_COLS:
        val = levels.get(c)
        if isinstance(val, list):
            assert len(val) == n
            row_data[c] = val
        else:
            row_data[c] = [val] * n
    pd.DataFrame({'Date': dates, **row_data}).to_csv(path, index=False)


def _lookup(tmp_path) -> BoxLookup:
    return BoxLookup(
        week_path=str(tmp_path / 'w.csv'),
        month_path=str(tmp_path / 'm.csv'),
        tick_threshold=0.75,
        weekly_window_days=7,
        monthly_window_days=30,
    )


# ----------------------------------------------------------------------
# Core traversal cases
# ----------------------------------------------------------------------

def test_first_observation_never_fires(tmp_path):
    """First time a (row, level) is observed, signal must be 'hold' regardless of side."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')  # no monthly levels — abstains
    lookup = _lookup(tmp_path)

    # close=200 (well above the box) on the very first bar.
    detail = lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03'))
    assert detail['weekly_signal'] == 'hold'
    assert detail['weekly_side'] == 'above'
    assert detail['signal'] == 'hold'


def test_traversal_below_to_above_fires_long(tmp_path):
    """A close BELOW the box, then INSIDE, then ABOVE → 'long' on the exit bar.
    The intervening inside observation is required ('entered the box')."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    # Bar 1: below box (state becomes 'below').
    d1 = lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))
    assert d1['weekly_signal'] == 'hold'
    assert d1['weekly_side'] == 'below'

    # Bar 2: inside the box ('entered').
    d2 = lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))
    assert d2['weekly_signal'] == 'hold'
    assert d2['weekly_side'] == 'inside'

    # Bar 3: above box → transition below→above (inside_seen=True) → 'long'.
    d3 = lookup.get_signal_detail(close=110.0, ts=pd.Timestamp('2025-01-03 08:00'))
    assert d3['weekly_signal'] == 'long'
    assert d3['weekly_side'] == 'above'
    assert d3['signal'] == 'long'


def test_traversal_above_to_below_fires_short(tmp_path):
    """A close ABOVE → INSIDE → BELOW → 'short' on the exit bar."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03'))             # state='above'
    lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))        # inside, inside_seen=True
    d3 = lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03 08:00'))
    assert d3['weekly_signal'] == 'short'
    assert d3['signal'] == 'short'


def test_gap_skip_does_not_fire(tmp_path):
    """A close that goes straight from one side to the opposite WITHOUT an
    intervening 'inside' observation must NOT fire — the price never entered
    the box, so no traversal occurred. State still advances silently."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    # Bar 1: below box → state='below', inside_seen=False
    lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))
    # Bar 2: gap straight to above (no inside observation) → 'hold' (gap-skip)
    d2 = lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03 04:00'))
    assert d2['weekly_signal'] == 'hold'
    assert d2['weekly_side'] == 'above'
    assert d2['signal'] == 'hold'

    # Bar 3: now drop into the box.
    d3 = lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 08:00'))
    assert d3['weekly_signal'] == 'hold'
    assert d3['weekly_side'] == 'inside'

    # Bar 4: drop below → state was 'above' (from gap-skip), inside_seen=True
    # (set on bar 3) → transition fires SHORT.
    d4 = lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03 12:00'))
    assert d4['weekly_signal'] == 'short'


def test_same_side_repeat_is_hold(tmp_path):
    """Consecutive bars on the same side after the first observation → 'hold'."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03'))  # state='above'
    for offset in range(1, 5):
        d = lookup.get_signal_detail(
            close=200.0 + offset,
            ts=pd.Timestamp('2025-01-03') + pd.Timedelta(hours=4 * offset),
        )
        assert d['weekly_signal'] == 'hold', f"offset={offset}: expected hold, got {d['weekly_signal']}"


def test_inside_box_returns_hold_without_changing_state(tmp_path):
    """Inside-box bars are transient — they return 'hold' and do not reset state."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    # Establish state='above'.
    lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03'))

    # Drop into the box.
    d_inside = lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))
    assert d_inside['weekly_signal'] == 'hold'
    assert d_inside['weekly_side'] == 'inside'

    # Now go BELOW — state was preserved as 'above', so this is a real
    # above→below transition → 'short'.
    d_below = lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03 08:00'))
    assert d_below['weekly_signal'] == 'short'


def test_inside_then_same_side_exit_is_hold(tmp_path):
    """above → inside → above stays 'hold' the whole way (state never changed)."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03'))      # state='above'
    d_inside = lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))
    d_same = lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03 08:00'))
    assert d_inside['weekly_signal'] == 'hold'
    assert d_same['weekly_signal'] == 'hold'


def test_state_resets_when_active_box_row_changes(tmp_path):
    """When the week rolls over to a new row, state is keyed per-row so the
    new row starts fresh (no carry-over)."""
    # Two weekly rows: 2025-01-01 (active week 1) and 2025-01-08 (active week 2).
    _weekly_csv(
        tmp_path / 'w.csv',
        dates=['2025-01-01', '2025-01-08'],
        WRHU=[105.0, 305.0],
        WRHD=[100.0, 300.0],
    )
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    # Bar in week 1: above the week-1 box → state(week1, W-RH)='above'
    lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03'))

    # Bar in week 2: state(week2, W-RH) is None → first observation → 'hold'
    d = lookup.get_signal_detail(close=400.0, ts=pd.Timestamp('2025-01-09'))
    assert d['weekly_signal'] == 'hold'
    assert d['weekly_side'] == 'above'


# ----------------------------------------------------------------------
# Aggregation
# ----------------------------------------------------------------------

def test_no_active_row_returns_none_signal(tmp_path):
    """When neither weekly nor monthly has an active row, aggregate signal is None."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)  # row covers 2025-01-01..08
    _monthly_csv(tmp_path / 'm.csv')                          # row covers 2025-01-01..31
    lookup = _lookup(tmp_path)

    # Date AFTER both windows: no active row.
    detail = lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-03-01'))
    assert detail['signal'] is None
    assert detail['weekly_signal'] is None
    assert detail['monthly_signal'] is None


def test_aggregate_hold_when_active_row_but_no_traversal(tmp_path):
    """Active row(s) but no traversal this bar → aggregate signal is 'hold'."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    detail = lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03'))
    assert detail['weekly_signal'] == 'hold'
    assert detail['signal'] == 'hold'


def test_weekly_priority_over_monthly(tmp_path):
    """When weekly fires a directional signal it wins; monthly is ignored."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv', MRHU=205.0, MRHD=10.0)
    lookup = _lookup(tmp_path)

    # Setup: below weekly box (state='below'); monthly close=50 is 'inside'
    # (10..205) → state(M) untouched.
    lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))
    # Inside weekly box → inside_seen=True
    lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))
    # Above weekly box (transition below→above → LONG); still inside monthly.
    d = lookup.get_signal_detail(close=110.0, ts=pd.Timestamp('2025-01-03 08:00'))
    assert d['weekly_signal'] == 'long'
    assert d['signal'] == 'long'


def test_monthly_fires_when_weekly_holds(tmp_path):
    """If weekly returns 'hold' but monthly fires a directional traversal, the
    aggregate falls through to monthly."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=305.0, WRHD=10.0)   # huge weekly box (always 'inside')
    _monthly_csv(tmp_path / 'm.csv', MRHU=105.0, MRHD=100.0)
    lookup = _lookup(tmp_path)

    # Bar 1: close=50 → weekly 'inside', monthly 'below'. state(M)='below'.
    lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))
    # Bar 2: close=102 → weekly 'inside', monthly 'inside'. state(M)
    # inside_seen=True.
    lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))
    # Bar 3: close=110 → weekly 'inside' (hold), monthly 'above' (transition → LONG).
    d = lookup.get_signal_detail(close=110.0, ts=pd.Timestamp('2025-01-03 08:00'))
    assert d['weekly_signal'] == 'hold'
    assert d['monthly_signal'] == 'long'
    assert d['signal'] == 'long'


def test_conflict_flag_false_under_normal_traversal(tmp_path):
    """Conflict requires both timeframes to fire opposite *directional* signals on
    the same bar. Under traversal semantics with single-close-per-bar this is
    geometrically constrained; this test verifies the flag stays False in a
    normal coupled-traversal scenario."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv', MRHU=105.0, MRHD=100.0)  # same geometry
    lookup = _lookup(tmp_path)

    lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))   # both 'below'
    lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))   # both inside
    d = lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03 08:00'))   # both LONG
    assert d['weekly_signal'] == 'long'
    assert d['monthly_signal'] == 'long'
    assert d['conflict'] is False
    assert d['signal'] == 'long'


# ----------------------------------------------------------------------
# Stacked levels (C4 fix)
# ----------------------------------------------------------------------

def test_multiple_levels_evolve_independently(tmp_path):
    """When the same row has multiple levels (e.g., W-RH and W-IH), the state
    for each level must evolve independently — a 'closest level' pick must not
    strand state on the other level."""
    # Two levels on the same weekly row: W-RH at 100..110, W-IH at 50..60.
    _weekly_csv(tmp_path / 'w.csv', WRHU=110.0, WRHD=100.0, WIHU=60.0, WIHD=50.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    # Bar 1: close=200 → above BOTH boxes. state(W-RH)='above', state(W-IH)='above'.
    lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-03'))
    # Bar 2: close=105 → inside W-RH (100..110), above W-IH (>60.75).
    # state(W-RH).inside_seen=True; state(W-IH) unchanged.
    lookup.get_signal_detail(close=105.0, ts=pd.Timestamp('2025-01-03 04:00'))
    # Bar 3: close=80 → above W-RH? no (80<100.75 → 'inside' W-RH? lower=100, 80<100-0.75=99.25 → 'below' W-RH).
    # Actually 80 < 99.25 → 'below' W-RH. State(W-RH)='above', inside_seen=True →
    # transition fires SHORT for W-RH.
    # W-IH: 80 > 60.75 → 'above'. State stays 'above', signal 'hold'.
    # W-RH wins (it fired). Signal='short'.
    d3 = lookup.get_signal_detail(close=80.0, ts=pd.Timestamp('2025-01-03 08:00'))
    assert d3['weekly_signal'] == 'short'
    assert d3['weekly_level'] == 'W-RH'

    # Bar 4: close=55 → inside W-IH. state(W-IH).inside_seen=True.
    #         W-RH: 55 < 99.25 → 'below', state stays 'below', signal 'hold'.
    lookup.get_signal_detail(close=55.0, ts=pd.Timestamp('2025-01-03 12:00'))
    # Bar 5: close=30 → below BOTH boxes.
    #   W-RH: state='below', inside_seen=False (was reset after the short fire);
    #         30 below, state stays 'below' → 'hold'.
    #   W-IH: state='above', inside_seen=True; 30 < 49.25 → 'below'; transition
    #         fires SHORT.
    d5 = lookup.get_signal_detail(close=30.0, ts=pd.Timestamp('2025-01-03 16:00'))
    assert d5['weekly_signal'] == 'short'
    assert d5['weekly_level'] == 'W-IH'  # the level that fired this bar


# ----------------------------------------------------------------------
# reset_state behaviour
# ----------------------------------------------------------------------

def test_reset_state_clears_history(tmp_path):
    """After reset_state(), the next bar is a fresh first observation."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))   # state='below'
    lookup.reset_state()

    # After reset: 'above' on this bar should NOT fire (first observation again).
    d = lookup.get_signal_detail(close=200.0, ts=pd.Timestamp('2025-01-04'))
    assert d['weekly_signal'] == 'hold'
    assert d['weekly_side'] == 'above'


def test_get_signal_matches_get_signal_detail(tmp_path):
    """The convenience `get_signal` and `get_signal_detail['signal']` agree."""
    _weekly_csv(tmp_path / 'w.csv', WRHU=105.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)

    # NOTE: each call mutates state, so we test the IDENTICAL sequence twice
    # with a reset between them.
    lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))
    lookup.get_signal_detail(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))
    sig_detail = lookup.get_signal_detail(close=110.0, ts=pd.Timestamp('2025-01-03 08:00'))['signal']

    lookup.reset_state()
    lookup.get_signal(close=50.0, ts=pd.Timestamp('2025-01-03'))
    lookup.get_signal(close=102.0, ts=pd.Timestamp('2025-01-03 04:00'))
    sig_simple = lookup.get_signal(close=110.0, ts=pd.Timestamp('2025-01-03 08:00'))

    assert sig_detail == sig_simple == 'long'


def test_classify_raises_on_zero_height_box(tmp_path):
    """A box with upper == lower (zero-height) is geometrically undefined and
    must raise — no silent fallback (no-fallback rule)."""
    from src.exceptions import ConfigurationError
    _weekly_csv(tmp_path / 'w.csv', WRHU=100.0, WRHD=100.0)
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)
    with pytest.raises(ConfigurationError) as exc:
        lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))
    assert exc.value.code == 'malformed-box-geometry'


def test_classify_raises_on_swapped_edges(tmp_path):
    """If a CSV has upper < lower (data prep bug), raise rather than silently
    fix — per the no-fallback rule the data must be corrected upstream."""
    from src.exceptions import ConfigurationError
    _weekly_csv(tmp_path / 'w.csv', WRHU=100.0, WRHD=110.0)  # swapped
    _monthly_csv(tmp_path / 'm.csv')
    lookup = _lookup(tmp_path)
    with pytest.raises(ConfigurationError) as exc:
        lookup.get_signal_detail(close=50.0, ts=pd.Timestamp('2025-01-03'))
    assert exc.value.code == 'malformed-box-geometry'
