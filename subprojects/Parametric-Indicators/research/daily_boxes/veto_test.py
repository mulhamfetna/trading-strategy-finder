"""Option C — the VETO thesis, which DAILY-BOX-01 explicitly did not test.

DAILY-BOX-01 measured whether *breaking through* a daily zone predicts continuation (it does not). The veto
thesis is a different claim: that entering *toward* an unbroken daily zone is bad, because price stalls or
reverses at it. A veto would REMOVE those entries.

Operationalization: a trade is "walled" when a daily zone sits between its entry price and its take-profit
target -- i.e. price must punch through a daily zone to reach the target. If the thesis holds, walled trades
should earn materially LESS than clear ones, and by more than the same test run on randomly-placed zones.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from optimize.signals import _box_dates_vec
from research.daily_boxes.study_signals import LevelPairs


def wall_ahead_mask(trades: Sequence[dict], box: pd.DataFrame, pairs: LevelPairs,
                    tp_points: float) -> np.ndarray:
    """True where a daily zone lies between the trade's entry and its take-profit target.

    LONG  (target = entry + tp): a zone counts if its LOWER edge is in (entry, entry+tp].
    SHORT (target = entry - tp): a zone counts if its UPPER edge is in [entry-tp, entry).
    The near edge is the one that matters -- it is what price meets first.
    A pair with either column NaN is not a zone and never walls anything.
    """
    if tp_points <= 0:
        raise ValueError(f"tp_points must be positive, got {tp_points}")
    n = len(trades)
    out = np.zeros(n, dtype=bool)
    if n == 0:
        return out

    ets = pd.DatetimeIndex([pd.Timestamp(t["entry_time"]) for t in trades])
    sub = box.reindex(_box_dates_vec(ets))
    ep = np.array([float(t["entry_price"]) for t in trades], dtype=float)
    is_long = np.array([str(t["direction"]) == "long" for t in trades], dtype=bool)

    for upper_col, lower_col, _label in pairs:
        if upper_col not in sub.columns or lower_col not in sub.columns:
            continue
        up = sub[upper_col].to_numpy(dtype=float)
        lo = sub[lower_col].to_numpy(dtype=float)
        valid = ~np.isnan(up) & ~np.isnan(lo)
        long_hit = valid & is_long & (lo > ep) & (lo <= ep + tp_points)
        short_hit = valid & ~is_long & (up < ep) & (up >= ep - tp_points)
        out |= (long_hit | short_hit)
    return out


def veto_split(trades: Sequence[dict], box: pd.DataFrame, pairs: LevelPairs,
               tp_points: float, point_value: float) -> dict:
    """Split the book into walled vs clear trades and report what a veto would do.

    `pnl_removed_dollars` is the direct answer to "what would this veto buy us?" -- it is the P&L of the
    trades the veto would delete. A NEGATIVE value means the veto removes losses (good); a positive value
    means it removes profit (bad).
    """
    mask = wall_ahead_mask(trades, box, pairs, tp_points)
    pnl = np.array([float(t["pnl_points"]) for t in trades], dtype=float)
    walled, clear = pnl[mask], pnl[~mask]
    return {
        "n_trades": int(len(trades)),
        "n_walled": int(mask.sum()),
        "n_clear": int((~mask).sum()),
        "walled_points": walled,
        "clear_points": clear,
        "mean_walled_points": float(walled.mean()) if len(walled) else float("nan"),
        "mean_clear_points": float(clear.mean()) if len(clear) else float("nan"),
        "mean_walled_dollars": float(walled.mean()) * point_value if len(walled) else float("nan"),
        "mean_clear_dollars": float(clear.mean()) * point_value if len(clear) else float("nan"),
        "pnl_removed_dollars": float(walled.sum()) * point_value if len(walled) else 0.0,
        "total_pnl_dollars": float(pnl.sum()) * point_value if len(pnl) else 0.0,
        "mask": mask,
    }
