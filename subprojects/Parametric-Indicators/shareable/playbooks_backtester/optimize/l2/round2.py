"""Round-2 exit-model A/B (spec §9): compare round-1 'L1-priority force-close' vs 'keep-L2-open, discard-L1'.

- l1_priority (round 1): when L1 opens during an L2 trade, L2 force-closes ('L1-entry'); L1 keeps its trade.
- keep_l2 (round 2): L2 runs to its own SL/TP; the OVERLAPPING L1 trade is dropped (the single account was
  held by L2, so L1 could not have entered). The combined book for keep_l2 therefore removes those L1 trades.

compare() returns both modes' standalone-L2 + combined-book metrics so we can judge which exit rule the
data prefers. Pure read; no engine bytes changed (golden-safe)."""
from __future__ import annotations

import types

import numpy as np

from optimize.l2 import engine, metrics


def _l2_spans(l1, res) -> list:
    """[ (entry_idx, exit_bar) ) for each L2 trade — exit_bar = first decision bar at/after exit_time."""
    dec_dates = l1.df_dec["Date"].to_numpy()
    spans = []
    for t in res.ledger:
        e = int(t["entry_idx"])
        xb = int(np.searchsorted(dec_dates, np.datetime64(t["exit_time"]), side="left"))
        spans.append((e, max(xb, e + 1)))
    return spans


def _drop_overlapped_l1(l1_ledger: list, spans: list):
    """Drop L1 trades whose entry bar falls inside any L2 span (keep_l2 world)."""
    kept, dropped = [], 0
    for t in l1_ledger:
        e = int(t["entry_idx"])
        if any(a <= e < b for a, b in spans):
            dropped += 1
        else:
            kept.append(t)
    return kept, dropped


def compare(l1, l2_params: dict) -> dict:
    """Run both exit modes; return {l1_priority:{l2,combined}, keep_l2:{l2,combined,l1_dropped}}."""
    r1 = engine.run_l2(l1, l2_params, exit_mode="l1_priority")
    out = {"l1_priority": {"l2": metrics.score(r1), "combined": metrics.combined(l1, r1)}}

    r2 = engine.run_l2(l1, l2_params, exit_mode="keep_l2")
    l1_kept, l1_dropped = _drop_overlapped_l1(l1.ledger, _l2_spans(l1, r2))
    l1k = types.SimpleNamespace(ledger=l1_kept)
    out["keep_l2"] = {"l2": metrics.score(r2), "combined": metrics.combined(l1k, r2),
                      "l1_dropped": l1_dropped}
    return out
