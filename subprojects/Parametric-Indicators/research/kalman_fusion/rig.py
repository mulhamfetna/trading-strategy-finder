"""The shared evaluation rig. Given an admit-mask (+ optional direction override), run the ONE
parity-locked engine (fast_backtest) and return Metrics. Every mechanism plugs in here so results
are apples-to-apples and P/L is engine-computed, never re-derived."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401  (path insert)
from optimize import counterfactual_pause as cp
from optimize.fast_engine import fast_backtest
from research.kalman_fusion.metrics import Metrics, summarize


def evaluate(C, admit, direction=None, n_eligible=None) -> Metrics:
    dd, cl, si, md, mh, ml, mc, sls, slh, tp, flip = cp._bt_args(C)
    si = np.asarray(si).copy()
    if direction is not None:
        d = np.asarray(direction)
        si = np.where(d != 0, d, si)               # override where the policy specifies a direction
    admit = np.asarray(admit, dtype=bool)
    trades = fast_backtest(dd, cl, si, admit, md, mh, ml, mc, sls, slh, tp, flip)
    pnls = [t["pnl_points"] * C["pv"] for t in trades]     # exit order (engine emits closed trades in order)
    if n_eligible is None:
        n_eligible = int(admit.sum())
    return summarize(pnls, n_eligible=n_eligible, pnls_exit_order=pnls)
