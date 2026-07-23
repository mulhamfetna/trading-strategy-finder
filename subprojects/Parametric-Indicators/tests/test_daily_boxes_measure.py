"""Supply accounting must be exact on a frame whose answer is known by construction."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.daily_boxes.measure import supply_stats           # noqa: E402

# One bar per day, 3 days. Bars are green (close>open) and close above the WEEKLY upper on day 1 only,
# and above the DAILY upper on days 1 and 2. Day 3 touches nothing.
_PAIRS_W = [("WU", "WL", "W")]
_PAIRS_D = [("DU", "DL", "D")]


def _frame():
    df_dec = pd.DataFrame({
        "Date":  pd.to_datetime(["2025-01-02 08:00", "2025-01-03 08:00", "2025-01-06 08:00"]),
        "Open":  [100.0, 100.0, 100.0],
        "High":  [130.0, 130.0, 130.0],
        "Low":    [90.0,  90.0,  90.0],
        "Close": [125.0, 115.0, 101.0],
    })
    box = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
        "WU":   [120.0, 120.0, 500.0],     # day1 close 125 > 120 -> weekly fires; day2 115 < 120 -> no
        "WL":   [110.0, 110.0, 490.0],
        "DU":   [110.0, 110.0, 500.0],     # day1 AND day2 close above 110 -> daily fires both
        "DL":   [105.0, 105.0, 490.0],
    })
    return df_dec, box.set_index("Date", drop=False)


def test_supply_counts_are_exact():
    df_dec, box = _frame()
    s = supply_stats(df_dec, box, _PAIRS_W, _PAIRS_D)
    assert s["base_signals"] == 1          # only day 1
    assert s["daily_signals"] == 2         # days 1 and 2
    assert s["new_signals"] == 1           # day 2 only (day 1 already covered by weekly)
    assert s["combined_signals"] == 2
    assert list(s["new_mask"]) == [False, True, False]


def test_scarcity_rescue_is_counted():
    df_dec, box = _frame()
    s = supply_stats(df_dec, box, _PAIRS_W, _PAIRS_D)
    assert s["days_total"] == 3
    assert s["days_with_base_signal"] == 1
    assert s["days_scarce"] == 2                 # days 2 and 3 have no weekly signal
    assert s["days_rescued_by_daily"] == 1       # daily creates one on day 2 only


def test_new_signals_never_exceed_daily_signals():
    df_dec, box = _frame()
    s = supply_stats(df_dec, box, _PAIRS_W, _PAIRS_D)
    assert s["new_signals"] <= s["daily_signals"]
