"""Walk-forward tuning: pick params on TRAIN only, report on held-out TEST.

Efficiency: the grid is split into EXPENSIVE keys (context_len, horizon — each needs a fresh model
pass) and CHEAP keys (edge_k, min_edge_ticks, sl_mult, tp_mult, gate_spread_pct — pure thresholding
on cached forecasts). We forecast once per (context_len, horizon) and sweep all cheap combos over it,
so a big grid costs only a handful of model passes. Forecasts are disk-cached across runs.

Fitness = return/DD (the 'high profit, low drawdown' objective) subject to a min trade count and
positive P/L, so we don't crown a fragile 2-trade fluke.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, replace

import pandas as pd

from .data import Instrument
from .engine import simulate
from .forecast_cache import forecast_arrays
from .forecaster import Forecaster
from .metrics import Stats, compute_stats
from .strategy import StratParams, signals_from_arrays

EXPENSIVE_KEYS = ("context_len", "horizon")

DEFAULT_GRID = dict(
    context_len=[512],
    horizon=[12, 24, 48],
    edge_k=[0.15, 0.25, 0.4],
    min_edge_ticks=[4.0, 8.0],
    sl_mult=[1.0, 1.5],
    tp_mult=[1.5, 2.5],
    gate_spread_pct=[100.0],
)


@dataclass
class WFResult:
    best: StratParams
    train_stats: Stats
    test_stats: Stats
    leaderboard: list[tuple[StratParams, Stats]]


def _fitness(s: Stats, min_trades: int) -> float:
    if s.n < min_trades or s.pnl <= 0:
        return float("-inf")
    return s.ret_dd if s.ret_dd != float("inf") else 999.0


def walk_forward(df: pd.DataFrame, forecaster: Forecaster, inst: Instrument,
                 train_frac: float = 0.70, base: StratParams | None = None,
                 grid: dict | None = None, min_trades: int = 15, top_k: int = 8,
                 cache_prefix: str = "run", progress: bool = False) -> WFResult:
    """Forecast the FULL series once per (context_len,horizon) [disk-cached], then evaluate the
    threshold grid on the TRAIN slice and report the single best config on the held-out TEST slice.
    Train/test are index windows into the same signal array — no re-forecasting, no boundary waste.
    """
    base = base or StratParams()
    grid = grid or DEFAULT_GRID
    n = len(df)
    cut = int(round(n * train_frac))

    cheap_keys = [k for k in grid if k not in EXPENSIVE_KEYS]
    exp_keys = [k for k in EXPENSIVE_KEYS if k in grid]
    exp_combos = list(itertools.product(*(grid[k] for k in exp_keys))) or [()]
    cheap_combos = list(itertools.product(*(grid[k] for k in cheap_keys))) or [()]

    train_scored: list[tuple[StratParams, Stats, Stats]] = []  # (params, train_stats, test_stats)
    for ec in exp_combos:
        p0 = replace(base, **dict(zip(exp_keys, ec)))
        med, qlo, qhi = forecast_arrays(df, forecaster, p0.context_len, p0.horizon,
                                        cache_key=f"{cache_prefix}_full", progress=progress)
        for cc in cheap_combos:
            p = replace(p0, **dict(zip(cheap_keys, cc)))
            sigs = signals_from_arrays(df, med, qlo, qhi, inst, p)
            tr = compute_stats(simulate(df, sigs, inst, p, start=p.context_len - 1, end=cut))
            te = compute_stats(simulate(df, sigs, inst, p, start=cut, end=n))
            train_scored.append((p, tr, te))

    train_scored.sort(key=lambda x: _fitness(x[1], min_trades), reverse=True)
    leaderboard = [(p, tr) for p, tr, _ in train_scored[:top_k]]
    best_p, best_train, best_test = train_scored[0]
    return WFResult(best=best_p, train_stats=best_train, test_stats=best_test,
                    leaderboard=leaderboard)
