"""Confirmation aggregator — combine active per-indicator votes into a per-bar allow/deny mask.

The K rule (frozen decision #1/#5): a box signal is allowed at bar b iff
  (no ACTIVE indicator votes VETO at b)  AND  (count of ACTIVE indicators voting CONFIRM at b ≥ K).
Inactive indicators (enabled=False) are ignored by the decision but their votes are still logged
elsewhere with active=0.
"""
from __future__ import annotations

import numpy as np

from .base import CONFIRM, VETO


def aggregate(votes: np.ndarray, active: np.ndarray, k: int) -> np.ndarray:
    """votes: (n_ind, n_bars) ∈ {+1,-1,0}; active: (n_ind,) bool; k: int.
    Returns allow: (n_bars,) bool per the K rule."""
    votes = np.asarray(votes)
    active = np.asarray(active, dtype=bool)
    if votes.ndim != 2 or votes.shape[0] == 0:
        return np.zeros(votes.shape[1] if votes.ndim == 2 else 0, dtype=bool)
    av = votes[active]                       # only active indicators count
    if av.shape[0] == 0:
        return np.zeros(votes.shape[1], dtype=bool)
    no_veto = ~(av == VETO).any(axis=0)
    enough = (av == CONFIRM).sum(axis=0) >= k
    return no_veto & enough


def build_gate(ctx, box_dir, indicators, k, base_gate=None):
    """Compose the indicator confirmation mask with an optional base gate (e.g. the vol gate).

    indicators: list of Indicator instances (enabled + disabled). Disabled ones still have their
    votes computed (for logging) but are excluded from the decision. With NO active indicator the
    indicators impose no constraint ⇒ gate == base_gate (parity).

    Returns (gate: bool array, votes: (n_ind, n_bars) int array, active: (n_ind,) bool).
    """
    box_dir = np.asarray(box_dir)
    n = len(box_dir)
    base = np.ones(n, dtype=bool) if base_gate is None else np.asarray(base_gate, dtype=bool)
    if indicators:
        votes_arr = np.stack([ind.vote(ctx, box_dir) for ind in indicators])
        active = np.array([bool(ind.config.enabled) for ind in indicators])
    else:
        votes_arr = np.zeros((0, n), dtype=np.int8)
        active = np.zeros(0, dtype=bool)
    if active.sum() == 0:
        allow = np.ones(n, dtype=bool)        # no active judges ⇒ pass-through (parity)
    else:
        allow = aggregate(votes_arr, active, k)
    return base & allow, votes_arr, active
