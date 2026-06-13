"""Stage 1 · S1.3 — tests for the rolling-window indexer."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from optimize.sub.windows import rolling_windows, month_bounds


def _months(spec):
    """spec = [('2024-01', 3), ('2024-02', 2), ...] → flat sorted month-label array."""
    out = []
    for m, n in spec:
        out += [m] * n
    return np.array(out, dtype=object)


def test_three_month_trailing_windows():
    months = _months([("2024-01", 3), ("2024-02", 2), ("2024-03", 4), ("2024-04", 1), ("2024-05", 2)])
    w = rolling_windows(months, size=3, step=1)
    # 5 months, size 3 → anchors 2024-03, 2024-04, 2024-05 → 3 windows
    assert [x["anchor"] for x in w] == ["2024-03", "2024-04", "2024-05"]
    first = w[0]
    assert first["start_month"] == "2024-01" and first["end_month"] == "2024-03"
    assert first["idx_lo"] == 0 and first["idx_hi"] == 3 + 2 + 4 - 1   # bars of Jan+Feb+Mar, inclusive
    assert first["n_bars"] == 9
    # the second window drops Jan, adds Apr
    assert w[1]["months"] == ["2024-02", "2024-03", "2024-04"]
    assert w[1]["idx_lo"] == 3                                          # first Feb bar
    assert w[1]["idx_hi"] == 3 + 2 + 4 + 1 - 1                          # last Apr bar


def test_index_ranges_are_contiguous_and_cover():
    months = _months([("a", 2), ("b", 2), ("c", 2), ("d", 2)])  # labels just need ordering
    w = rolling_windows(months, size=2, step=1)
    assert [x["anchor"] for x in w] == ["b", "c", "d"]
    for x in w:
        assert x["n_bars"] == x["idx_hi"] - x["idx_lo"] + 1


def test_month_bounds_basic():
    months = _months([("m1", 3), ("m2", 1)])
    uniq, b = month_bounds(months)
    assert uniq == ["m1", "m2"] and b["m1"] == (0, 2) and b["m2"] == (3, 3)
