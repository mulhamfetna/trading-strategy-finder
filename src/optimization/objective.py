"""Objective function for the NSGA-II optimiser.

`evaluate()` runs one trial across all walk-forward folds, aggregates the
metrics, and returns `(median_PF, max_MaxDD)` for Optuna to minimise/maximise.

Edge-case routing (locked by Q3.1 / Q3.2 + v3.1 update notes):

  PF=None                    → optuna.TrialPruned
  PF=0.0                     → return (0.0, max_dd) — NSGA-II dominates normally
  total_trades < min_floor   → optuna.TrialPruned
  malformed-box-geometry     → optuna.TrialPruned
  missing-candle-columns     → re-raise (study-fatal)
  missing-data-file          → re-raise (study-fatal)
  missing-parameter          → re-raise (study-fatal)
  any other ConfigurationError → optuna.TrialPruned
"""
from __future__ import annotations

import statistics
from dataclasses import asdict
from typing import List, Optional, Tuple

import optuna
import pandas as pd

from src.exceptions import ConfigurationError
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy, BoxStrategyParams


_STUDY_FATAL_CODES = frozenset({
    'missing-candle-columns',
    'missing-data-file',
    'missing-parameter',
})


def _build_strategy(
    baseline: BoxStrategyParams,
    suggested: dict,
    lookup: BoxLookup,
) -> BoxStrategy:
    """Splice the searched params into the baseline; return a BoxStrategy."""
    params_dict = {**asdict(baseline), **suggested}
    return BoxStrategy(params=BoxStrategyParams(**params_dict), box_lookup=lookup)


def _compute_pf_and_dd(trades: List[dict]) -> Tuple[Optional[float], float]:
    """Compute (profit_factor, max_drawdown) for a single fold.

    profit_factor is None when there are zero losing trades. max_drawdown
    is always a non-positive float (worst peak-to-trough cumulative dollar PnL).
    """
    if not trades:
        return None, 0.0

    gross_profit = sum(t['profit_dollars'] for t in trades if t['profit_dollars'] > 0)
    gross_loss = sum(-t['profit_dollars'] for t in trades if t['profit_dollars'] < 0)
    pf: Optional[float] = (gross_profit / gross_loss) if gross_loss > 0 else None

    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        cum += t['profit_dollars']
        peak = max(peak, cum)
        max_dd = min(max_dd, cum - peak)
    return pf, max_dd


def evaluate(
    suggested_params: dict,
    baseline_params: BoxStrategyParams,
    folds: List[pd.DataFrame],
    min_trades_per_fold: int,
    box_lookup: BoxLookup,
) -> Tuple[float, float]:
    """Per-trial evaluation across `folds`. Returns (median_pf, max_dd).

    Raises:
        optuna.TrialPruned: when this candidate should be removed from the front.
        ConfigurationError: when a study-fatal error occurs (re-raises).
    """
    fold_pfs: List[float] = []
    fold_dds: List[float] = []

    for fold_idx, df_fold in enumerate(folds):
        try:
            strat = _build_strategy(baseline_params, suggested_params, box_lookup)
            trades, _state = strat.backtest(df_fold)
        except ConfigurationError as exc:
            if exc.code in _STUDY_FATAL_CODES:
                raise
            raise optuna.TrialPruned(f'fold {fold_idx} prune: {exc.code}')

        if len(trades) < min_trades_per_fold:
            raise optuna.TrialPruned(
                f'fold {fold_idx} prune: {len(trades)} trades < min={min_trades_per_fold}'
            )

        pf, dd = _compute_pf_and_dd(trades)
        if pf is None:
            raise optuna.TrialPruned(
                f'fold {fold_idx} prune: profit_factor undefined (no losses)'
            )

        fold_pfs.append(pf)
        fold_dds.append(dd)

    return statistics.median(fold_pfs), min(fold_dds)
