"""Regression tests for the Big-Candle vs Box conflict policy.

See MASTER_STRATEGY_GUIDE.md §5. Three policies:
  - 'big_candle_wins' (default): big-candle reverses, ignoring the box signal.
  - 'box_wins': take the box direction with full big-candle size.
  - 'skip': disagreement ⇒ no trade.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy, BoxStrategyParams
from tests._fixtures import box_strategy_params


@pytest.fixture
def df_4h_big_green_above_edge():
    """A 4-bar 4h frame engineered to trigger the §5 Big-Candle vs Box conflict
    under the v3.1 traversal rule (with C3 fix: requires intervening 'inside').

    Bar 0 (setup): closes BELOW the weekly RH box. state(W-RH)='below'.
    Bar 1 (entered): closes INSIDE the weekly RH box. inside_seen=True.
    Bar 2 (big green): open=20000, close=20500 → candle_size=500 > 400.
        Close 20500 is above the weekly RHU edge (20100) → side='above'.
        Transition below→inside→above (inside_seen=True) ⇒ box says LONG.
        Big-candle direction reverses the green ⇒ SHORT. CONFLICT (§5).
    Bar 3 (filler): calm bar so the strategy has room after bar-2 open.
    """
    return pd.DataFrame({
        'Date':   pd.to_datetime([
            '2025-01-03 00:00:00',
            '2025-01-03 04:00:00',
            '2025-01-03 08:00:00',
            '2025-01-03 12:00:00',
        ]),
        'Open':   [19500.0, 20060.0, 20000.0, 20500.0],
        'High':   [19510.0, 20080.0, 20520.0, 20510.0],
        'Low':    [19480.0, 20050.0, 19990.0, 20480.0],
        'Close':  [19490.0, 20075.0, 20500.0, 20500.0],
        'Volume': [1000, 1000, 1000, 800],
    })


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _unified_csv(path, dates=None, **levels):
    """Build a unified box CSV (all W* and M* columns)."""
    if dates is None:
        dates = ['2025-01-03']
    n = len(dates)
    row_data = {}
    for c in _W_COLS + _M_COLS:
        val = levels.get(c)
        row_data[c] = ([val] * n) if not isinstance(val, list) else val
    pd.DataFrame({'Date': dates, **row_data}).to_csv(path, index=False)


@pytest.fixture
def box_lookup_with_upper_at_20100(tmp_path):
    """A BoxLookup whose only active level is a weekly RH box at 20100/20050.
    Any close > 20100.75 fires LONG; close < 20049.25 fires SHORT.

    All test candles are on 2025-01-03 with hour < 18, so box_date=2025-01-03.
    """
    _unified_csv(tmp_path / 'u.csv', WRHU=20100.0, WRHD=20050.0)
    return BoxLookup(unified_path=str(tmp_path / 'u.csv'), tick_threshold=0.75)


def test_big_candle_wins_reverses_against_box(df_4h_big_green_above_edge, box_lookup_with_upper_at_20100):
    params = box_strategy_params(big_candle_resolution='big_candle_wins')
    strat = BoxStrategy(params=params, box_lookup=box_lookup_with_upper_at_20100)
    _trades, state = strat.backtest(df_4h_big_green_above_edge)
    # Position opens on bar 2 (the big-green conflict bar); bars 0-1 set
    # traversal state ('below' then 'inside').
    assert state['direction'] == 'short', f"expected short, got {state['direction']}"
    assert state['opened_at_idx'] == 2


def test_box_wins_takes_box_direction(df_4h_big_green_above_edge, box_lookup_with_upper_at_20100):
    params = box_strategy_params(big_candle_resolution='box_wins')
    strat = BoxStrategy(params=params, box_lookup=box_lookup_with_upper_at_20100)
    _trades, state = strat.backtest(df_4h_big_green_above_edge)
    assert state['direction'] == 'long', f"expected long, got {state['direction']}"
    # Full-size big-candle leg (default = 4 contracts).
    assert state['contracts_filled'] == params.big_candle_full_contracts


def test_skip_produces_no_trade_on_conflict(box_lookup_with_upper_at_20100):
    """A 3-bar fixture: bar 0 'below' setup; bar 1 'inside' (entered the box);
    bar 2 is the big-green traversal-completion bar. With 'skip' the conflict
    bar must not open a position."""
    df = pd.DataFrame({
        'Date':   pd.to_datetime([
            '2025-01-03 00:00:00',
            '2025-01-03 04:00:00',
            '2025-01-03 08:00:00',
        ]),
        'Open':   [19500.0, 20060.0, 20000.0],
        'High':   [19510.0, 20080.0, 20520.0],
        'Low':    [19480.0, 20050.0, 19990.0],
        'Close':  [19490.0, 20075.0, 20500.0],
        'Volume': [1000, 1000, 1000],
    })
    params = box_strategy_params(big_candle_resolution='skip')
    strat = BoxStrategy(params=params, box_lookup=box_lookup_with_upper_at_20100)
    _trades, state = strat.backtest(df)
    # With 'skip' the conflict bar must not open a position.
    assert state['direction'] == 'flat', f"expected flat, got {state['direction']}"


def test_no_conflict_when_box_signal_agrees(tmp_path):
    """A big green bar that closes BELOW the weekly RL box (after a setup bar
    above the RL box) traverses above→below ⇒ SHORT. Big-candle reversal
    (green→short) also says SHORT. No conflict — all three policies trade short."""
    unified_csv = tmp_path / 'u.csv'
    _unified_csv(unified_csv, WRLU=19500.0, WRLD=19450.0)

    # 3-bar fixture: bar 0 above WRL box (state='above'); bar 1 inside WRL
    # box (inside_seen=True); bar 2 is a big-green that closes below WRL.
    df = pd.DataFrame({
        'Date':   pd.to_datetime([
            '2025-01-03 00:00:00',
            '2025-01-03 04:00:00',
            '2025-01-03 08:00:00',
        ]),
        'Open':   [19550.0, 19490.0, 18950.0],
        'High':   [19560.0, 19495.0, 19450.0],
        'Low':    [19540.0, 19470.0, 18940.0],
        'Close':  [19555.0, 19475.0, 19400.0],
        'Volume': [1000, 1000, 1000],
    })

    for policy in ('big_candle_wins', 'box_wins', 'skip'):
        # Fresh BoxLookup so state doesn't leak between policies.
        lookup = BoxLookup(unified_path=str(unified_csv), tick_threshold=0.75)
        strat = BoxStrategy(
            params=box_strategy_params(big_candle_resolution=policy),
            box_lookup=lookup,
        )
        _trades, state = strat.backtest(df)
        assert state['direction'] == 'short', f"policy={policy}: expected short, got {state['direction']}"
