"""Stage 1 · S1.3 — rolling-window indexer for the SL/TP sub-optimizer.

Given the per-decision-bar month labels ('YYYY-MM', sorted), produce **trailing N-month windows stepped by
1 month** as contiguous df-index ranges. Default N=3 (the chosen chunking): each window covers
[anchor-2 … anchor] and is tagged by its last (anchor) month — so each window yields one Stage-2 data
point at monthly resolution while spanning 3 months for trade-count stability.
"""
from __future__ import annotations

import numpy as np


def month_bounds(months: np.ndarray):
    """Ordered-unique months + inclusive (lo, hi) df-index range per month. `months` must be sorted
    (contiguous per month — true for a Date-sorted decision frame)."""
    uniq = list(dict.fromkeys(months.tolist()))     # insertion order = chronological
    bounds = {}
    for m in uniq:
        idx = np.nonzero(months == m)[0]
        bounds[m] = (int(idx[0]), int(idx[-1]))
    return uniq, bounds


def rolling_windows(months: np.ndarray, size: int = 3, step: int = 1) -> list[dict]:
    """Trailing `size`-month windows stepped by `step`. Each dict:
      {anchor, start_month, end_month, months, idx_lo, idx_hi (inclusive), n_bars}."""
    uniq, bounds = month_bounds(months)
    out = []
    for k in range(size - 1, len(uniq), step):
        wm = uniq[k - size + 1:k + 1]
        lo = bounds[wm[0]][0]
        hi = bounds[wm[-1]][1]
        out.append({"anchor": uniq[k], "start_month": wm[0], "end_month": wm[-1],
                    "months": list(wm), "idx_lo": lo, "idx_hi": hi, "n_bars": hi - lo + 1})
    return out
