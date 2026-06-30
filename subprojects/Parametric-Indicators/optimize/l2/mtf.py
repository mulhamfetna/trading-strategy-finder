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

from optimize.l2 import engine as _engine


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


def run_dual_tf(primary: LayerView, secondary: LayerView, pv: float) -> DualResult:
    """Fuse primary + secondary on the master grid (finer tf) under primary priority (spec §3):
    primary trades kept verbatim (owner 'L1'); a secondary trade is admitted only if the primary is flat at
    its entry bar, and is force-closed at the first primary entry strictly inside it (reason 'L1-entry');
    P/L recomputed honestly as pnl_points*pv. Single shared position: never two owners open at once."""
    master, _ = master_grid(primary, secondary)
    prim_state = _state_on_master(primary, master)
    prim_trades = _remap_to_master(primary, master)
    for t in prim_trades:
        t["owner"] = "L1"
    # secondary candidates: drop any whose entry bar has the primary in-position
    sec_cand = [t for t in _remap_to_master(secondary, master)
                if not prim_state[int(t["entry_idx"])]]
    # force-close each at the first primary entry strictly inside the trade (reuse the oracle helper)
    prim_entries = [int(t["entry_idx"]) for t in prim_trades]
    sec_fc = _engine.force_close_on_l1_entry(sec_cand, prim_entries, master.dates, master.close, pv)
    for t in sec_fc:
        t["owner"] = "L2"
        t["pnl"] = float(t["pnl_points"]) * pv          # honest recompute after any truncation
    ledger = sorted(prim_trades + sec_fc, key=lambda t: int(t["entry_idx"]))
    sec_view = LayerView(dates=master.dates, close=master.close, ledger=sec_fc,
                         state=np.zeros(len(master.dates), bool), bar_td=master.bar_td)
    sec_state = _state_on_master(sec_view, master)
    return DualResult(master_dates=master.dates, master_close=master.close, ledger=ledger,
                      prim_state=prim_state, sec_state=sec_state)
