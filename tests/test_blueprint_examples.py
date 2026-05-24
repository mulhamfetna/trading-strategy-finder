"""Regression lock for docs/SYSTEM_BLUEPRINT.md Part C.

This test runs the master strategy on the real NQ_4h.csv + NQ_full_data.csv
datasets and asserts that the trades match the EXACT field values documented
in the system blueprint. Any deviation = drift between code and blueprint.

When the blueprint or the dataset is intentionally updated, the regenerated
numbers should be copy-pasted into both this test AND the SYSTEM_BLUEPRINT.md
Part C tables.

Skipped when the data files aren't present (they're gitignored).
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.data.loader import load_data
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy, BoxStrategyParams
from tests._fixtures import box_params_dict

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
_CANDLES_CSV = os.path.join(_REPO_ROOT, 'NQ_4h.csv')
_BOX_CSV     = os.path.join(_REPO_ROOT, 'NQ_full_data.csv')


pytestmark = pytest.mark.skipif(
    not (os.path.exists(_CANDLES_CSV) and os.path.exists(_BOX_CSV)),
    reason='NQ_4h.csv / NQ_full_data.csv not present (gitignored); skip blueprint lock.',
)


@pytest.fixture(scope='module')
def january_trades():
    """The 7 trades the engine produces on 2025-01-01..2025-01-31 with the
    blueprint A.3 parameters."""
    params = box_params_dict()
    params['sl_hard_points']   = 15.0     # blueprint A.3
    params['sl_soft_points']   = 200.0
    params['tp_target_points'] = 150.25
    params['box_data_path']    = _BOX_CSV

    df = load_data(_CANDLES_CSV)
    df = df[(df['Date'] >= '2025-01-01') & (df['Date'] <= '2025-01-31')].reset_index(drop=True)
    lookup = BoxLookup(unified_path=_BOX_CSV, tick_threshold=0.75)
    strat = BoxStrategy(params=BoxStrategyParams(**params), box_lookup=lookup)
    trades, _ = strat.backtest(df)
    return trades, df


def _find_trade(trades, df, entry_idx):
    matches = [t for t in trades if t['entry_idx'] == entry_idx]
    assert len(matches) == 1, f'Expected exactly one trade with entry_idx={entry_idx}; got {len(matches)}'
    return matches[0]


def test_blueprint_example_1_standard_long_sl_hard(january_trades):
    """SYSTEM_BLUEPRINT.md Part C, Example 1."""
    trades, df = january_trades
    t = _find_trade(trades, df, entry_idx=10)
    assert t['exit_idx']           == 11
    assert t['direction']          == 'long'
    assert t['entry_signal_price'] == 21509.25
    assert t['exit_close']         == 21493.00
    assert t['avg_entry_price']    == 21509.25
    assert t['exit_price']         == 21494.25
    assert t['contracts']          == 1
    assert t['profit_points']      == -15.00
    assert t['profit_dollars']     == -30.00
    assert t['exit_reason']        == 'STOP LOSS (HARD)'
    assert t['legs']               == [{'contracts': 1, 'price': 21509.25, 'candle_idx': 10}]
    assert t['box_signal']['weekly_level'] == 'W-RL'
    assert t['box_signal']['signal']       == 'long'


def test_blueprint_example_2_multi_leg_short_trail(january_trades):
    """SYSTEM_BLUEPRINT.md Part C, Example 2."""
    trades, df = january_trades
    t = _find_trade(trades, df, entry_idx=62)
    assert t['exit_idx']           == 66
    assert t['direction']          == 'short'
    assert t['entry_signal_price'] == 21290.50
    assert t['exit_close']         == 21334.25
    assert t['avg_entry_price']    == 21340.50
    assert t['exit_price']         == 21334.25      # TRAIL stores bar close
    assert t['contracts']          == 2
    assert t['profit_points']      == pytest.approx(6.25)
    assert t['profit_dollars']     == pytest.approx(25.00)
    assert t['exit_reason']        == 'TAKE PROFIT (TRAIL)'
    assert t['legs'] == [
        {'contracts': 1, 'price': 21290.50, 'candle_idx': 62},
        {'contracts': 1, 'price': 21390.50, 'candle_idx': 63},
    ]
    assert t['box_signal']['weekly_level'] == 'W-RH'
    assert t['box_signal']['signal']       == 'short'


def test_blueprint_example_3_big_candle_long_tp(january_trades):
    """SYSTEM_BLUEPRINT.md Part C, Example 3."""
    trades, df = january_trades
    t = _find_trade(trades, df, entry_idx=101)
    assert t['exit_idx']           == 102
    assert t['direction']          == 'long'
    assert t['entry_signal_price'] == 20886.75
    assert t['exit_close']         == 21334.25      # bar 102 close
    assert t['avg_entry_price']    == 20886.75
    assert t['exit_price']         == 21037.00      # TP line (synthetic)
    assert t['contracts']          == 4             # big-candle full size
    assert t['profit_points']      == pytest.approx(150.25)
    assert t['profit_dollars']     == pytest.approx(1202.00)
    assert t['exit_reason']        == 'TAKE PROFIT'
    assert t['legs'] == [{'contracts': 4, 'price': 20886.75, 'candle_idx': 101}]


def test_blueprint_example_4_standard_long_tp_cross_day(january_trades):
    """SYSTEM_BLUEPRINT.md Part C, Example 4."""
    trades, df = january_trades
    t = _find_trade(trades, df, entry_idx=109)
    assert t['exit_idx']           == 113
    assert t['direction']          == 'long'
    assert t['entry_signal_price'] == 21540.25
    assert t['exit_close']         == 21665.00      # bar 113 close, NOT the TP line
    assert t['avg_entry_price']    == 21540.25
    assert t['exit_price']         == 21690.50      # TP line (synthetic)
    assert t['contracts']          == 1
    assert t['profit_points']      == pytest.approx(150.25)
    assert t['profit_dollars']     == pytest.approx(300.50)
    assert t['exit_reason']        == 'TAKE PROFIT'


def test_blueprint_total_trades_count(january_trades):
    """The full set: exactly 7 trades for 2025-01-01..2025-01-31 with the
    blueprint A.3 params. If this drifts, either the strategy logic changed
    or the dataset did."""
    trades, _ = january_trades
    assert len(trades) == 7
