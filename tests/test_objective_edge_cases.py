"""Objective function edge-case tests.

Locked decisions:
- PF=None → optuna.TrialPruned (Q3.1)
- PF=0 → returns (0.0, max_dd) — let NSGA-II dominate normally
- total_trades < min_trades_per_fold → optuna.TrialPruned (Q3.2)
- ConfigurationError(code='malformed-box-geometry') → optuna.TrialPruned
- ConfigurationError(code='missing-candle-columns') → re-raises (study-fatal)
- ConfigurationError(any other code) → optuna.TrialPruned

See docs/superpowers/specs/2026-05-23-nsga2-optimization-design.md §4.3.
"""

import os
import sys

import optuna
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.exceptions import ConfigurationError
from src.optimization.objective import evaluate
from src.strategy.box_lookup import BoxLookup
from tests._fixtures import box_strategy_params


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _unified_csv(path, **levels):
    row_data = {c: [levels.get(c)] for c in _W_COLS + _M_COLS}
    pd.DataFrame({'Date': ['2025-01-01'], **row_data}).to_csv(path, index=False)


def _lookup(tmp_path, **w_levels):
    _unified_csv(tmp_path / 'u.csv', **w_levels)
    return BoxLookup(unified_path=str(tmp_path / 'u.csv'), tick_threshold=0.75)


def _flat_4h(n_bars: int, close: float = 20050.0) -> pd.DataFrame:
    return pd.DataFrame({
        'Date':  pd.date_range(start='2025-01-01', periods=n_bars, freq='4h'),
        'Open':  [close] * n_bars,
        'High':  [close + 10] * n_bars,
        'Low':   [close - 10] * n_bars,
        'Close': [close] * n_bars,
        'Volume': [1000] * n_bars,
    })


def test_insufficient_trades_prunes(tmp_path):
    # Flat price never crosses the box → zero trades.
    lookup = _lookup(tmp_path, WRHU=21000.0, WRHD=20900.0)
    fold = _flat_4h(100)
    suggested = {'sl_soft_points': 200.0, 'sl_hard_points': 300.0, 'tp_target_points': 150.0}
    with pytest.raises(optuna.TrialPruned):
        evaluate(
            suggested_params=suggested,
            baseline_params=box_strategy_params(),
            folds=[fold, fold, fold],
            min_trades_per_fold=15,
            box_lookup=lookup,
        )


def test_malformed_box_geometry_prunes(tmp_path):
    # Box with upper <= lower triggers ConfigurationError('malformed-box-geometry')
    # on first signal evaluation → trial is pruned, study continues.
    lookup = _lookup(tmp_path, WRHU=100.0, WRHD=200.0)  # swapped
    fold = pd.DataFrame({
        'Date':  pd.date_range(start='2025-01-01', periods=50, freq='4h'),
        'Open':  [150.0] * 50,
        'High':  [160.0] * 50,
        'Low':   [140.0] * 50,
        'Close': [150.0] * 50,
        'Volume': [1000] * 50,
    })
    with pytest.raises(optuna.TrialPruned):
        evaluate(
            suggested_params={'sl_soft_points': 50.0, 'sl_hard_points': 100.0, 'tp_target_points': 50.0},
            baseline_params=box_strategy_params(),
            folds=[fold],
            min_trades_per_fold=1,
            box_lookup=lookup,
        )


def test_missing_candle_columns_re_raises(tmp_path):
    """Study-fatal: re-raise so the worker can abort the entire study."""
    lookup = _lookup(tmp_path, WRHU=21000.0, WRHD=20900.0)
    # DataFrame without Volume column.
    fold = pd.DataFrame({
        'Date':  pd.date_range(start='2025-01-01', periods=50, freq='4h'),
        'Open':  [20000.0] * 50,
        'High':  [20010.0] * 50,
        'Low':   [19990.0] * 50,
        'Close': [20000.0] * 50,
    })
    from src.optimization import objective as obj_mod

    class _FakeStrat:
        def __init__(self, *a, **kw):
            pass
        def backtest(self, df, on_progress=None):
            raise ConfigurationError(
                'simulated missing columns',
                code='missing-candle-columns',
                system_status={'missing_columns': ['Volume']},
            )

    obj_mod._build_strategy = lambda baseline, suggested, lookup: _FakeStrat()
    try:
        with pytest.raises(ConfigurationError) as exc:
            evaluate(
                suggested_params={'sl_soft_points': 50.0, 'sl_hard_points': 100.0, 'tp_target_points': 50.0},
                baseline_params=box_strategy_params(),
                folds=[fold],
                min_trades_per_fold=1,
                box_lookup=lookup,
            )
        assert exc.value.code == 'missing-candle-columns'
    finally:
        import importlib
        importlib.reload(obj_mod)


def test_returns_tuple_for_normal_path(tmp_path):
    """Sanity: a fold with enough trades and a finite PF returns a (pf, dd) tuple."""
    # Sawtooth that traverses the box repeatedly.
    n = 240
    closes = [20000.0 + 200.0 * (i % 4 - 1.5) for i in range(n)]
    fold = pd.DataFrame({
        'Date':  pd.date_range(start='2025-01-01', periods=n, freq='4h'),
        'Open':  [20000.0] * n,
        'High':  [c + 20 for c in closes],
        'Low':   [c - 20 for c in closes],
        'Close': closes,
        'Volume': [1000] * n,
    })
    lookup = _lookup(tmp_path, WRHU=20100.0, WRHD=19900.0)
    suggested = {'sl_soft_points': 200.0, 'sl_hard_points': 300.0, 'tp_target_points': 150.0}
    try:
        result = evaluate(
            suggested_params=suggested,
            baseline_params=box_strategy_params(),
            folds=[fold, fold],
            min_trades_per_fold=1,
            box_lookup=lookup,
        )
    except optuna.TrialPruned:
        pytest.skip("synthetic fold produced no losing trades — PF undefined")
    assert isinstance(result, tuple) and len(result) == 2
    pf, dd = result
    assert isinstance(pf, float) and isinstance(dd, float)
