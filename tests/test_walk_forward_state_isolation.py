"""Locks the determinism claim that a single BoxLookup, when used across
multiple BoxStrategy.backtest() calls, yields identical per-fold trade lists
as a fresh BoxLookup instance would."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.optimization.walk_forward import split_folds
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy
from tests._fixtures import box_strategy_params


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _unified_csv(path, dates=None, **levels):
    """Build a unified box CSV (all W* + M* columns in a single file)."""
    if dates is None:
        dates = ['2025-01-01']
    n = len(dates)
    row_data = {}
    for c in _W_COLS + _M_COLS:
        val = levels.get(c)
        row_data[c] = ([val] * n) if not isinstance(val, list) else val
    pd.DataFrame({'Date': dates, **row_data}).to_csv(path, index=False)


def _synth_4h(n_bars: int) -> pd.DataFrame:
    timestamps = pd.date_range(start='2025-01-01', periods=n_bars, freq='4h')
    base = 20000.0
    # Sawtooth pattern so the close crosses through the box repeatedly.
    closes = [base + 200 * (i % 4 - 1.5) for i in range(n_bars)]
    return pd.DataFrame({
        'Date':  timestamps,
        'Open':  [base] * n_bars,
        'High':  [c + 10 for c in closes],
        'Low':   [c - 10 for c in closes],
        'Close': closes,
        'Volume': [1000] * n_bars,
    })


def test_back_to_back_backtests_on_shared_lookup_match_fresh_instances(tmp_path):
    unified_csv = tmp_path / 'u.csv'
    _unified_csv(unified_csv, WRHU=20100.0, WRHD=20000.0)

    df = _synth_4h(120)
    folds = split_folds(df, fold_count=3)

    shared_lookup = BoxLookup(unified_path=str(unified_csv), tick_threshold=0.75)
    params = box_strategy_params()

    shared_results = []
    for f in folds:
        strat = BoxStrategy(params=params, box_lookup=shared_lookup)
        trades, _state = strat.backtest(f)
        shared_results.append(len(trades))

    fresh_results = []
    for f in folds:
        fresh_lookup = BoxLookup(unified_path=str(unified_csv), tick_threshold=0.75)
        strat = BoxStrategy(params=params, box_lookup=fresh_lookup)
        trades, _state = strat.backtest(f)
        fresh_results.append(len(trades))

    assert shared_results == fresh_results, (
        f'shared-lookup trades={shared_results} != fresh-lookup trades={fresh_results}; '
        f'reset_state() is not isolating folds.'
    )
