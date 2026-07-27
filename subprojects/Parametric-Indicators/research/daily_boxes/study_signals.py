"""The champion Stage-1 box rule, with the level set as a REQUIRED argument.

This is a faithful reimplementation of `optimize.signals.decision_signals`, which hardcodes
`engine._LEVEL_PAIRS` (= weekly + monthly). The only difference is that the level list is passed in, so the
study can ask "what if the daily zones were included?" WITHOUT editing any production module.

Fidelity is not assumed — tests/test_daily_boxes_signals.py asserts this function equals decision_signals
element-for-element when handed _LEVEL_PAIRS.

The rule (verbatim from decision_signals' docstring):
  - color: green = close>open, red = close<open; a doji (close==open) => hold.
  - a pair contributes only if BOTH columns are present and non-NaN ('valid') AND the bar's [low,high]
    overlaps [lower,upper] ('touched').
  - long iff green & touched & close>upper; short iff red & touched & close<lower (any pair).
  - long WINS ties; missing box row / NaN levels => that pair invalid => hold.
"""
from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
import pandas as pd

from optimize.signals import _box_dates_vec

LevelPairs = Sequence[Tuple[str, str, str]]


def study_signals(df_dec: pd.DataFrame, box: pd.DataFrame, pairs: LevelPairs) -> np.ndarray:
    """Stage-1 signals over an EXPLICIT level-pair list.

    `pairs` is required on purpose: there is no default level set, so a caller can never silently measure a
    different zone universe than it intended.
    """
    if pairs is None:
        raise ValueError("pairs must be an explicit list of (upper, lower, label) triples")

    n = len(df_dec)
    out = np.empty(n, dtype=object)
    if n == 0:
        return out

    O = df_dec["Open"].to_numpy(dtype=float)
    H = df_dec["High"].to_numpy(dtype=float)
    L = df_dec["Low"].to_numpy(dtype=float)
    C = df_dec["Close"].to_numpy(dtype=float)

    sub = box.reindex(_box_dates_vec(pd.DatetimeIndex(df_dec["Date"])))

    green = C > O
    red = C < O
    has_long = np.zeros(n, dtype=bool)
    has_short = np.zeros(n, dtype=bool)

    for upper_col, lower_col, _label in pairs:
        if upper_col not in sub.columns or lower_col not in sub.columns:
            continue
        up = sub[upper_col].to_numpy(dtype=float)
        lo = sub[lower_col].to_numpy(dtype=float)
        valid = ~np.isnan(up) & ~np.isnan(lo)
        touched = valid & (L <= up) & (H >= lo)
        has_long |= green & touched & (C > up)
        has_short |= red & touched & (C < lo)

    out[:] = "hold"
    out[has_short] = "short"
    out[has_long] = "long"        # long assigned last => long wins ties (matches the production rule)
    return out
