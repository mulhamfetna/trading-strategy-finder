"""Causal alignment of a contributor's decision bars onto NQ's decision grid (Spec §4.1).

The single Part-A alignment chokepoint. For each NQ decision bar we take the contributor's LAST-CLOSED
decision bar — causal, no look-ahead by construction. A contributor bar 'closes' at start+bar_td and is
available to NQ bar i (which closes at nq_start_i + bar_td) iff es_start_j + bar_td ≤ nq_start_i + bar_td,
i.e. es_start_j ≤ nq_start_i (the bar_td offsets cancel ONLY when both grids share the same bar width).
For the ES exact grid (identical bar_td) this is the coincident bar (identity). ETFs with a DIFFERENT
bar width cannot rely on this cancellation — they must gate on a real close-vs-close comparison
(contributor-close ≤ NQ-close) in Part B before reuse; the searchsorted `start ≤ start` rule used here
is causal ONLY for equal-width grids (e.g. ES, same bar_td as NQ)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def align_decbars(nq_dec_dates, es_dec_dates, bar_td: pd.Timedelta) -> np.ndarray:
    """Index, per NQ decision bar, of the contributor's last-closed decision bar (start ≤ NQ start);
    -1 where no contributor bar exists yet. `bar_td` is accepted for interface symmetry with
    runner._decbar_1min_index and to document the close-offset cancellation; it must be > 0."""
    assert bar_td > pd.Timedelta(0), "bar_td must be positive"
    nq = np.asarray(nq_dec_dates, dtype="datetime64[ns]")
    es = np.asarray(es_dec_dates, dtype="datetime64[ns]")
    # last contributor bar whose START ≤ this NQ bar's START — searchsorted only ever looks backward,
    # so future contributor bars cannot influence an earlier NQ bar's index (look-ahead safe).
    j = np.searchsorted(es, nq, side="right") - 1
    return j.astype(np.int64)


def gather_to_nq(es_series: np.ndarray, j_es: np.ndarray, fill=0) -> np.ndarray:
    """Map a per-contributor-bar series onto NQ decision bars via the alignment index j_es.
    j_es < 0 (no contributor bar yet) ⇒ `fill`."""
    es_series = np.asarray(es_series)
    out = np.full(len(j_es), fill, dtype=es_series.dtype)
    ok = np.asarray(j_es) >= 0
    out[ok] = es_series[np.asarray(j_es)[ok]]
    return out
