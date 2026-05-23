"""Tests for the 1-1-2 scaling strategy state machine (phase C1).

The strategy is documented in Currunt_Strategy_Algo_for_Trading.md.
These tests exercise the deterministic edge cases on tiny synthetic
candle sequences so the simulator's behavior is locked down before
we wire it to real 4h data.

Conventions used in test cases:
  - All prices in absolute points (NQ-style: 21000-23000 range, but
    we use round numbers like 20000 for readability).
  - Each "candle" is the row dict the simulator reads.
  - Strategy parameters get spelled out per-test so the intent is
    obvious without having to scroll to a shared fixture.
"""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategy.scaling_strategy import ScalingStrategy, ScalingParams
from tests._fixtures import scaling_params


def _candles(rows):
    """Build a DataFrame from a list of (datetime, o, h, l, c) tuples."""
    return pd.DataFrame(
        [dict(zip(['Date', 'Open', 'High', 'Low', 'Close', 'Volume'], r + (1000,))) for r in rows]
    )


# ---- defaults ----

def test_default_params_match_playbook_values():
    p = scaling_params()
    assert p.total_contracts == 4
    assert p.leg1_contracts == 1
    assert p.leg2_contracts == 1
    assert p.leg3_contracts == 2
    assert p.leg2_pullback_points == 100
    assert p.leg3_pullback_points == 150
    assert p.big_candle_threshold_points == 400
    assert p.big_candle_full_contracts == 4
    assert p.tp_target_points == 150
    assert p.tp_watch_threshold_points == 50
    assert p.sl_soft_points == 200
    assert p.sl_hard_points == 300
    assert p.reentry_enabled is True
    assert p.reentry_cooldown_candles == 1
    assert p.big_candle_reverses_dir is True


# ---- entry trigger ----

def test_long_entry_when_candle_closes_above_prior_close():
    """Default trigger: current close > prev close -> long signal,
    enter leg1 (1 contract) at the prev close as the base level."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),  # prev close = 20000
        ('2025-01-01 04:00', 20001, 20050, 19995, 20030),  # close > prev close -> long
    ])
    strat = ScalingStrategy(params=scaling_params())

    trades, _ = strat.backtest(df)

    # No closed trade yet (just opened). Strategy reports open positions
    # as part of the final state if we expose that; for this test we
    # just check that at least one leg was filled.
    state = strat.last_state
    assert state['direction'] == 'long'
    assert state['contracts_filled'] == 1
    assert state['base_level'] == 20000


def test_short_entry_when_candle_closes_below_prior_close():
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 19999, 20005, 19950, 19970),  # close < prev close -> short
    ])
    strat = ScalingStrategy(params=scaling_params())

    strat.backtest(df)

    state = strat.last_state
    assert state['direction'] == 'short'
    assert state['contracts_filled'] == 1


def test_big_candle_exception_reverses_direction_and_takes_full_size():
    """A green candle larger than the big_candle_threshold inverts to a
    short and takes all 4 contracts immediately."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 20000, 20500, 19990, 20450),  # close - open = 450 > 400 (big)
    ])
    strat = ScalingStrategy(params=scaling_params())

    strat.backtest(df)

    state = strat.last_state
    assert state['direction'] == 'short', "green big candle should flip to short"
    assert state['contracts_filled'] == 4, "should be fully loaded"


# ---- scaling-in ----

def test_leg2_fills_at_100_point_pullback():
    """After leg 1 long entry at 20000, price moves down 100 points
    (against us). Next candle's low <= 19900 triggers leg 2 (1 more
    contract). Now 2 contracts filled."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 20001, 20050, 19995, 20030),  # leg 1 long, base 20000
        ('2025-01-01 08:00', 20030, 20030, 19899, 19920),  # low touches 19899 < 19900 -> leg 2 fires
    ])
    strat = ScalingStrategy(params=scaling_params())

    strat.backtest(df)

    state = strat.last_state
    assert state['contracts_filled'] == 2
    assert state['legs'][1]['contracts'] == 1
    assert state['legs'][1]['price'] == pytest_approx(19900)


def test_leg3_fills_at_150_point_pullback():
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 20001, 20050, 19995, 20030),       # leg 1 long, base 20000
        ('2025-01-01 08:00', 20030, 20030, 19899, 19920),       # leg 2 fires at 19900
        ('2025-01-01 12:00', 19920, 19925, 19849, 19870),       # low 19849 <= 19850 -> leg 3 (2 contracts)
    ])
    strat = ScalingStrategy(params=scaling_params())

    strat.backtest(df)

    state = strat.last_state
    assert state['contracts_filled'] == 4
    assert state['legs'][2]['contracts'] == 2
    assert state['legs'][2]['price'] == pytest_approx(19850)


# ---- take profit ----

def test_tp_exit_when_high_reaches_target_after_full_load():
    """Once fully loaded long at average ~ (20000+19900+19850+19850)/4 = 19900,
    high reaching avg + 150 = 20050 triggers TP exit."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 20001, 20050, 19995, 20030),
        ('2025-01-01 08:00', 20030, 20030, 19899, 19920),
        ('2025-01-01 12:00', 19920, 19925, 19849, 19870),       # fully loaded after this candle
        ('2025-01-01 16:00', 19870, 20055, 19860, 20050),       # high 20055 >= 19900 + 150 = 20050
    ])
    strat = ScalingStrategy(params=scaling_params())

    trades, _ = strat.backtest(df)

    assert len(trades) >= 1
    assert trades[0]['exit_reason'] == 'TAKE PROFIT'
    assert trades[0]['profit_points'] > 0


# ---- stop loss ----

def test_sl_soft_exit_when_close_below_soft_line():
    """Long entry at 20000, SL soft at 20000 - 200 = 19800. A candle
    that CLOSES below 19800 (not just wicks) exits the position."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 20001, 20050, 19995, 20030),     # leg 1 long, base 20000
        ('2025-01-01 08:00', 20030, 20035, 19795, 19799),     # closes BELOW 19800 -> soft SL exit
    ])
    strat = ScalingStrategy(params=scaling_params())

    trades, _ = strat.backtest(df)

    assert len(trades) == 1
    assert 'STOP LOSS' in trades[0]['exit_reason']
    assert trades[0]['profit_points'] < 0


def test_sl_soft_does_not_exit_on_wick_only():
    """A wick past 19800 that closes back above does NOT exit (the
    playbook says SL1 requires a candle close)."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 20001, 20050, 19995, 20030),
        ('2025-01-01 08:00', 20030, 20035, 19790, 19850),     # wicks to 19790 but closes at 19850 (above SL)
    ])
    strat = ScalingStrategy(params=scaling_params())

    trades, _ = strat.backtest(df)

    assert len(trades) == 0, "wick-only should not trigger SL"


# ---- progress callback ----

def test_progress_callback_invoked_for_every_candle():
    """Backtest invokes the optional progress callback per candle so the
    API can stream progress events."""
    df = _candles([
        ('2025-01-01 00:00', 20000, 20010, 19990, 20000),
        ('2025-01-01 04:00', 20001, 20050, 19995, 20030),
        ('2025-01-01 08:00', 20030, 20035, 19999, 20015),
    ])

    progress_events = []

    def on_progress(event):
        progress_events.append(event)

    strat = ScalingStrategy(params=scaling_params())
    strat.backtest(df, on_progress=on_progress)

    assert len(progress_events) == len(df)
    # Each event must carry the canonical progress shape
    for i, event in enumerate(progress_events):
        assert event['current_idx'] == i
        assert event['total'] == len(df)
        assert 0 <= event['percent'] <= 100
        assert 'trades_so_far' in event
        assert 'pnl_so_far' in event


# ---- helpers ----

def pytest_approx(value, rel=1e-6):
    """Tiny shim so we don't have to import pytest just for approx."""
    import pytest
    return pytest.approx(value, rel=rel)
