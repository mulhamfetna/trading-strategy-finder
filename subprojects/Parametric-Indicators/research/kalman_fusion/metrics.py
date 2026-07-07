"""Pure Pareto metrics for the study rig — no engine imports, trivially testable."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np


@dataclass
class Metrics:
    n_entries: int
    n_eligible: int
    entry_rate: float
    payoff: float        # avg win / avg loss
    total_pnl: float
    win_rate: float
    pf: float            # gross win / gross loss
    expectancy: float    # mean per-trade P/L
    max_dd: float


def payoff_ratio(pnls) -> float:
    a = np.asarray(pnls, dtype=float)
    wins = a[a > 0]; losses = a[a < 0]
    avg_w = wins.mean() if wins.size else 0.0
    avg_l = -losses.mean() if losses.size else 0.0
    if avg_l > 0:
        return float(avg_w / avg_l)
    return math.inf if avg_w > 0 else 0.0


def max_drawdown(pnls_in_exit_order) -> float:
    a = np.asarray(pnls_in_exit_order, dtype=float)
    if a.size == 0:
        return 0.0
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(eq)
    return float((peak - eq).max())


def summarize(pnls, n_eligible: int, pnls_exit_order=None) -> Metrics:
    a = np.asarray(pnls, dtype=float)
    n = int(a.size)
    wins = a[a > 0]; losses = a[a < 0]
    gross_w = float(wins.sum()); gross_l = float(-losses.sum())
    pf = (gross_w / gross_l) if gross_l > 0 else (math.inf if gross_w > 0 else 0.0)
    dd = max_drawdown(pnls_exit_order if pnls_exit_order is not None else pnls)
    return Metrics(
        n_entries=n,
        n_eligible=int(n_eligible),
        entry_rate=(n / n_eligible) if n_eligible else 0.0,
        payoff=payoff_ratio(a),
        total_pnl=float(a.sum()),
        win_rate=(float((a > 0).sum()) / n) if n else 0.0,
        pf=pf,
        expectancy=(float(a.mean()) if n else 0.0),
        max_dd=dd,
    )
