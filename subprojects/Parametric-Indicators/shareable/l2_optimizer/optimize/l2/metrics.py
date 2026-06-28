"""L2 metrics — standalone fitness on the L2 book, plus the combined-book drawdown guardrail
(report-only: the merged L1+L2 equity curve must not worsen L1's standalone drawdown)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _equity_dd(pnls) -> tuple[float, float]:
    """(total P/L, max drawdown) for a P/L sequence — same global-HWM underwater math as core."""
    if not pnls:
        return 0.0, 0.0
    eq = np.cumsum(np.asarray(pnls, dtype=float))
    dd = float((np.maximum.accumulate(eq) - eq).max())
    return float(eq[-1]), dd


def score(l2) -> dict:
    """Standalone L2 metrics from its ledger."""
    pnls = [float(t["pnl"]) for t in l2.ledger]
    total, dd = _equity_dd(pnls)
    arr = np.asarray(pnls, dtype=float)
    wins = arr[arr > 0]
    losses = arr[arr < 0]
    return dict(
        pnl=total,
        max_dd=dd,
        n=len(pnls),
        win=round(100 * (arr > 0).mean(), 1) if len(arr) else 0.0,
        pf=(round(float(wins.sum() / abs(losses.sum())), 2)
            if len(losses) and losses.sum() != 0 else None),
        payoff=(round(float(wins.mean() / abs(losses.mean())), 2)
                if len(wins) and len(losses) else None),   # avg win / |avg loss| (reward-to-risk)
        n_l1_entry_exits=int(getattr(l2, "n_l1_entry_exits", 0)),
    )


def combined(l1, l2) -> dict:
    """Merge both ledgers in realized-exit-time order and compute the combined-book P/L + drawdown.
    Guardrail: combined max_dd must not exceed L1's standalone max_dd (dd_not_worse)."""
    merged = [(pd.Timestamp(t["exit_time"]), float(t["pnl"])) for t in l1.ledger] \
        + [(pd.Timestamp(t["exit_time"]), float(t["pnl"])) for t in l2.ledger]
    merged.sort(key=lambda x: x[0])
    c_total, c_dd = _equity_dd([p for _, p in merged])
    _l1_total, l1_dd = _equity_dd([float(t["pnl"]) for t in l1.ledger])
    return dict(pnl=c_total, max_dd=c_dd, l1_only_dd=l1_dd, dd_not_worse=(c_dd <= l1_dd))
