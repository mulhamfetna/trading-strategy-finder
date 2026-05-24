"""Regression lock for docs/SYSTEM_BLUEPRINT.md Part C — dual-timeframe.

Runs the master strategy on the real NQ_4h.csv + NQ_full_data.csv + NQ_1m.csv
datasets and asserts that the trades match the EXACT field values documented
in the system blueprint. Any deviation = drift between code and blueprint.

When the blueprint or the dataset is intentionally updated, the regenerated
numbers should be copy-pasted into both this test AND the SYSTEM_BLUEPRINT.md
Part C tables.

Skipped when any of the three data files aren't present (they're gitignored).
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.loader import load_data
from src.data.splitter import filter_by_date_range
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy, BoxStrategyParams
from tests._fixtures import box_params_dict

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_CANDLES_CSV  = os.path.join(_REPO_ROOT, 'NQ_4h.csv')
_CANDLES_1MIN = os.path.join(_REPO_ROOT, 'NQ_1m.csv')
_BOX_CSV      = os.path.join(_REPO_ROOT, 'NQ_full_data.csv')


pytestmark = pytest.mark.skipif(
    not (os.path.exists(_CANDLES_CSV) and os.path.exists(_BOX_CSV) and os.path.exists(_CANDLES_1MIN)),
    reason='NQ_4h.csv / NQ_full_data.csv / NQ_1m.csv not all present (gitignored); skip blueprint lock.',
)


@pytest.fixture(scope='module')
def january_trades():
    """The 7 trades the dual-timeframe engine produces on 2025-01-01..2025-01-31
    with the blueprint A.3 parameters."""
    params = box_params_dict()
    # Blueprint A.3: validator-compliant pair (sl_hard > sl_soft).
    params['sl_soft_points']   = 10.0
    params['sl_hard_points']   = 15.0
    params['tp_target_points'] = 150.25
    params['box_data_path']    = _BOX_CSV

    df = load_data(_CANDLES_CSV)
    df = filter_by_date_range(df, start='2025-01-01', end='2025-01-31').reset_index(drop=True)

    df_1min = load_data(_CANDLES_1MIN)
    df_1min = filter_by_date_range(df_1min, start='2025-01-01', end='2025-01-31').reset_index(drop=True)

    lookup = BoxLookup(unified_path=_BOX_CSV, tick_threshold=0.75)
    strat = BoxStrategy(params=BoxStrategyParams(**params), box_lookup=lookup)
    trades, _ = strat.backtest(df, df_1min=df_1min)
    return trades, df


def _find_trade(trades, df, entry_idx):
    matches = [t for t in trades if t['entry_idx'] == entry_idx]
    assert len(matches) == 1, f'Expected exactly one trade with entry_idx={entry_idx}; got {len(matches)}'
    return matches[0]


def test_blueprint_example_1_standard_long_soft_sl(january_trades):
    """SYSTEM_BLUEPRINT.md Part C, Example 1 — SOFT SL (dual-timeframe).

    In 4h-only mode this trade exited HARD (close 21493 ≤ sl_hard_line 21494.25).
    On the 1-min frame, a 2-min close at 21497.25 fires SOFT SL FIRST — the
    1-min closes between entry (10:00) and 15:47 never break the hard line.
    """
    trades, df = january_trades
    t = _find_trade(trades, df, entry_idx=10)
    assert t['exit_idx']           == 11
    assert t['direction']          == 'long'
    assert t['entry_signal_price'] == 21509.25
    assert t['avg_entry_price']    == 21509.25
    assert t['exit_close']         == 21497.25
    assert t['exit_price']         == 21497.25       # SOFT fills at the 2-min close
    assert t['exit_time']          == '2025-01-03T15:47:00'
    assert t['contracts']          == 1
    assert t['profit_points']      == pytest.approx(-12.00)
    assert t['profit_dollars']     == pytest.approx(-24.00)
    assert t['exit_reason']        == 'STOP LOSS (SOFT)'
    assert t['legs']               == [{'contracts': 1, 'price': 21509.25, 'candle_idx': 10}]
    assert t['box_signal']['weekly_level'] == 'W-RL'
    assert t['box_signal']['signal']       == 'long'


def test_blueprint_example_2_short_hard_sl(january_trades):
    """SYSTEM_BLUEPRINT.md Part C, Example 2 — HARD SL (dual-timeframe).

    4h-only would have shown leg-2 fill on bar 63 and a TRAIL exit on bar 66
    (+25 dollars). On 1-min, a close at 14:04 hits sl_hard_line=21305.50
    FIRST — position closes with a single leg before the leg-2 trigger
    (21390.50) is ever reached on this bar.
    """
    trades, df = january_trades
    t = _find_trade(trades, df, entry_idx=62)
    assert t['exit_idx']           == 63
    assert t['direction']          == 'short'
    assert t['entry_signal_price'] == 21290.50
    assert t['avg_entry_price']    == 21290.50       # single leg only
    assert t['exit_close']         == 21309.50       # 1-min bar's actual close
    assert t['exit_price']         == 21305.50       # HARD fills at the line
    assert t['exit_time']          == '2025-01-16T14:04:00'
    assert t['contracts']          == 1
    assert t['profit_points']      == pytest.approx(-15.00)
    assert t['profit_dollars']     == pytest.approx(-30.00)
    assert t['exit_reason']        == 'STOP LOSS (HARD)'
    assert t['legs']               == [{'contracts': 1, 'price': 21290.50, 'candle_idx': 62}]
    assert t['box_signal']['weekly_level'] == 'W-RH'
    assert t['box_signal']['signal']       == 'short'


def test_blueprint_example_3_big_candle_long_trail(january_trades):
    """SYSTEM_BLUEPRINT.md Part C, Example 3 — TRAIL (dual-timeframe).

    4h-only showed a TAKE PROFIT (high reached the +150 line within bar 102).
    On 1-min, the price stalls and a 2-min close pulls back through the
    watch line at 06:25 — TRAIL fires after only 25 minutes of holding,
    cutting the gain from $1202 to $232.
    """
    trades, df = january_trades
    t = _find_trade(trades, df, entry_idx=101)
    assert t['exit_idx']           == 102
    assert t['direction']          == 'long'
    assert t['entry_signal_price'] == 20886.75
    assert t['avg_entry_price']    == 20886.75
    assert t['exit_close']         == 20915.75
    assert t['exit_price']         == 20915.75       # TRAIL fills at the 2-min close
    assert t['exit_time']          == '2025-01-27T06:25:00'
    assert t['contracts']          == 4              # big-candle full size
    assert t['profit_points']      == pytest.approx(29.00)
    assert t['profit_dollars']     == pytest.approx(232.00)
    assert t['exit_reason']        == 'TAKE PROFIT (TRAIL)'
    assert t['legs']               == [{'contracts': 4, 'price': 20886.75, 'candle_idx': 101}]


def test_blueprint_example_4_standard_short_trail_gain(january_trades):
    """SYSTEM_BLUEPRINT.md Part C, Example 4 — TRAIL with profit (dual-timeframe).

    Replacement for the previous Example 4 (LONG at idx 109 → TP on bar 113).
    On 1-min that trade actually closes SOFT SL at 14:05 (loss). For a clean
    winning-TRAIL example, use trade #7: SHORT entry at idx 115 → TRAIL at
    14:13 with +46.75 pts.
    """
    trades, df = january_trades
    t = _find_trade(trades, df, entry_idx=115)
    assert t['exit_idx']           == 116
    assert t['direction']          == 'short'
    assert t['entry_signal_price'] == 21467.25
    assert t['avg_entry_price']    == 21467.25
    assert t['exit_close']         == 21420.50
    assert t['exit_price']         == 21420.50
    assert t['exit_time']          == '2025-01-29T14:13:00'
    assert t['contracts']          == 1
    assert t['profit_points']      == pytest.approx(46.75)
    assert t['profit_dollars']     == pytest.approx(93.50)
    assert t['exit_reason']        == 'TAKE PROFIT (TRAIL)'


def test_blueprint_total_trades_count(january_trades):
    """The full set: exactly 7 trades for 2025-01-01..2025-01-31 with the
    blueprint A.3 params. If this drifts, either the strategy logic changed
    or the dataset did."""
    trades, _ = january_trades
    assert len(trades) == 7
