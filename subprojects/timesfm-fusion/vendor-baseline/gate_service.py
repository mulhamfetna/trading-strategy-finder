"""Deployable TimesFM volatility gate — the exact causal rule that lifted NQ Return/DD 9.4 -> 18.8.

Two pieces:
  1. `VolGate` — a live decision object. Feed it each trade's pre-entry TimesFM band; it answers
     ALLOW / VETO using only the volatilities it has already seen (causal, no look-ahead). Drop this
     into a live loop: call `.reading(band)` once you have the forecast for the bar before entry.
  2. `gate_reference_book()` — apply the same rule to a reference trade log offline, returning the
     kept book + stats. This is the "integration" of the gate into the existing strategy.

The live rule (verbatim): before an NQ entry, take TimesFM's forecast band (q90-q10) at the prior
bar, divide by price (stationary), and VETO the entry if that value is above the `pct`-th percentile
of its own history so far (default 85 => skip the ~15% highest-vol regimes). Warm-up: allow all
until `min_history` readings exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class VolGate:
    pct: float = 85.0
    min_history: int = 40
    _hist: list = field(default_factory=list)

    def allow(self, rel_band: float | None) -> bool:
        """Return True to take the trade, False to veto. `rel_band` = (q90-q10)/price at the prior
        bar. None (no forecast) -> allow. Decision uses only prior readings; then records this one."""
        if rel_band is None or np.isnan(rel_band):
            return True
        if len(self._hist) < self.min_history:
            self._hist.append(rel_band)
            return True
        thr = float(np.percentile(self._hist, self.pct))
        self._hist.append(rel_band)
        return rel_band <= thr


def _stats(pnls: np.ndarray) -> dict:
    n = len(pnls)
    if n == 0:
        return dict(n=0, pnl=0.0, dd=0.0, ret_dd=0.0, win=0.0)
    eq = np.cumsum(pnls)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    return dict(n=n, pnl=float(pnls.sum()), dd=dd,
                ret_dd=float(pnls.sum() / dd) if dd else float("inf"),
                win=100.0 * (pnls > 0).mean())


def gate_reference_book(entry_times, pnls, rel_bands, pct: float = 85.0):
    """Apply the causal VolGate to a reference book (already time-sorted).

    entry_times : iterable of entry timestamps (for the output log)
    pnls        : per-trade net P/L ($)
    rel_bands   : per-trade pre-entry TimesFM (q90-q10)/price (np.nan where unavailable)
    Returns (kept_mask, baseline_stats, gated_stats, rows) where rows lists every trade with its
    keep/veto decision — the deployable audit trail.
    """
    gate = VolGate(pct=pct)
    pnls = np.asarray(pnls, dtype=float)
    keep = np.ones(len(pnls), dtype=bool)
    rows = []
    for i, (t, band) in enumerate(zip(entry_times, rel_bands)):
        keep[i] = gate.allow(band)
        rows.append(dict(entry_time=t, pnl=float(pnls[i]), rel_band=band, kept=bool(keep[i])))
    return keep, _stats(pnls), _stats(pnls[keep]), rows
