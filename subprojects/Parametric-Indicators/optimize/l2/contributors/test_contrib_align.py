import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
from optimize.l2.contributors import align, loader

BAR = pd.Timedelta(hours=4)


def _dts(*iso):
    return np.array(list(iso), dtype="datetime64[ns]")


def test_identity_grid_maps_each_nq_bar_to_coincident_es_bar():
    grid = _dts("2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00")
    j = align.align_decbars(grid, grid, BAR)
    assert list(j) == [0, 1, 2]                        # exact grid ⇒ identity (Spec §3.2/§4.1)


def test_last_closed_when_contributor_is_sparser():
    nq = _dts("2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00", "2025-01-02T06:00")
    es = _dts("2025-01-01T18:00", "2025-01-02T06:00")   # ES missing the two middle bars
    j = align.align_decbars(nq, es, BAR)
    # bar0 -> es0; bars1,2 -> still es0 (last-closed ≤ their start); bar3 -> es1
    assert list(j) == [0, 0, 0, 1]


def test_minus_one_before_first_contributor_bar():
    nq = _dts("2025-01-01T10:00", "2025-01-01T18:00")
    es = _dts("2025-01-01T18:00")
    j = align.align_decbars(nq, es, BAR)
    assert list(j) == [-1, 0]                           # no ES bar available for the 10:00 NQ bar yet


def test_lookahead_guard_shifting_es_future_does_not_change_earlier_alignment():
    """Shift a LATER ES bar further into the future; every NQ bar at/before the unshifted bars keeps its
    alignment index. If alignment leaked the future, an earlier index would change. (Spec §8.2/§8.3.3.)"""
    nq = _dts("2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00", "2025-01-02T06:00")
    es = _dts("2025-01-01T18:00", "2025-01-01T22:00", "2025-01-02T02:00", "2025-01-02T06:00")
    j_before = align.align_decbars(nq, es, BAR)
    es_shift = es.copy()
    es_shift[3] = np.datetime64("2025-06-01T06:00")    # push the last ES bar months into the future
    j_after = align.align_decbars(nq, es_shift, BAR)
    # the first 3 NQ bars are unaffected; only bar3 (which used es3) loses it -> last-closed es2
    assert list(j_before[:3]) == list(j_after[:3])
    assert j_after[3] == 2                              # bar3 falls back to es2, never sees the future bar


def test_lookahead_guard_on_real_es_grid():
    """Real ES/NQ 4h grids are identical (measured 2119/2119). Shifting the entire tail of ES into the
    future must not change alignment for any NQ bar before the shift point."""
    es = loader.load_contributor_inputs("ES", "4h")
    nq_dates = es.df_dec["Date"].to_numpy()            # ES==NQ grid; reuse ES dates as the NQ grid
    es_dates = es.df_dec["Date"].to_numpy()
    j0 = align.align_decbars(nq_dates, es_dates, BAR)
    cut = len(es_dates) - 100
    es_shift = es_dates.copy()
    es_shift[cut:] = es_shift[cut:] + np.timedelta64(365, "D")
    j1 = align.align_decbars(nq_dates, es_shift, BAR)
    assert np.array_equal(j0[:cut], j1[:cut])          # earlier bars untouched by future shift


def test_gather_to_nq_uses_fill_for_missing():
    es_series = np.array([10, 20, 30], dtype=np.int8)
    j = np.array([-1, 0, 0, 2], dtype=np.int64)
    out = align.gather_to_nq(es_series, j, fill=0)
    assert list(out) == [0, 10, 10, 30]
