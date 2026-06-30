"""Multi-timeframe layer fusion.

Spec: docs/superpowers/specs/2026-06-30-multi-timeframe-layer-fusion-design.md

The secondary layer, in the new `independent` L2 mode, is a full L1 run on its OWN timeframe. This module
merges two layers' trade ledgers on a master grid (the finer timeframe) under primary priority: the primary's
trades are kept verbatim; a secondary trade is admitted only while the primary is flat and is force-closed the
instant a primary trade opens inside it. Pure over its inputs — no data loading, no I/O — so it is trivially
unit-testable. Today's residual-manager L2 path (engine.run_l2) is untouched.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class LayerView:
    dates: np.ndarray   # df_dec["Date"].to_numpy() — decision-bar timestamps (datetime64), ascending
    close: np.ndarray   # df_dec["Close"].to_numpy(float)
    ledger: list        # taken trade dicts (entry_idx, entry_price, exit_time, exit_price, direction,
                        #   exit_reason, pnl_points, pnl)
    state: np.ndarray   # bool per decision bar, True = in-position
    bar_td: object      # pandas Timedelta — bar duration


@dataclass
class DualResult:
    master_dates: np.ndarray
    master_close: np.ndarray
    ledger: list                  # combined trades, each = trade dict + "owner" in {"L1","L2"}, by entry_idx
    prim_state: np.ndarray        # primary in-position on the master grid (bool)
    sec_state: np.ndarray         # admitted-secondary in-position on the master grid (bool)


def master_grid(primary: LayerView, secondary: LayerView):
    """(finer, coarser) by bar_td; primary wins ties (its grid is the master when equal)."""
    return (primary, secondary) if primary.bar_td <= secondary.bar_td else (secondary, primary)


def _remap_to_master(layer: LayerView, master: LayerView) -> list:
    """Copies of `layer.ledger` with `entry_idx` re-pointed to the master bar whose timestamp matches the
    trade's entry timestamp (`layer.dates[entry_idx]`). All other fields carried unchanged."""
    out = []
    for t in layer.ledger:
        ts = layer.dates[int(t["entry_idx"])]
        j = int(np.searchsorted(master.dates, ts, side="left"))
        j = min(j, len(master.dates) - 1)
        tt = dict(t)
        tt["entry_idx"] = j
        out.append(tt)
    return out


def _state_on_master(layer: LayerView, master: LayerView) -> np.ndarray:
    """Boolean in-position projected onto master bars by epoch time: a master bar is in-position iff its
    timestamp falls in some trade's [entry_ts, exit_time). The entry bar is always occupied."""
    st = np.zeros(len(master.dates), dtype=bool)
    for t in layer.ledger:
        e_ts = layer.dates[int(t["entry_idx"])]
        x_ts = np.datetime64(t["exit_time"])
        lo = int(np.searchsorted(master.dates, e_ts, side="left"))
        hi = int(np.searchsorted(master.dates, x_ts, side="left"))
        hi = max(hi, lo + 1)
        st[lo:hi] = True
    return st
