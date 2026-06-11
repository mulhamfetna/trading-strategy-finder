"""Param-independent per-decision-bar Stage-1 signal precompute.

The entry DIRECTION (long/short/hold) depends only on the decision-bar OHLC vs the box levels — NOT
on SL/TP/gate/breaker. So it can be computed ONCE per timeframe and reused across all optimiser
trials (the H.7 speedup in TASK.md §9-f) and to find actionable entries for the SL/TP-bound study
(H.5). This mirrors engine._stage1_candle_signal + the box-date mapping exactly.

`signal[i]` is the Stage-1 signal of decision bar i (the bar that, once CLOSED, makes bar i+1
signal-eligible — the engine reads signal from the just-closed bar). 'long' | 'short' | 'hold'.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from engine import _stage1_candle_signal  # noqa: E402
from box_lookup import BoxLookup          # noqa: E402


def decision_signals(df_dec: pd.DataFrame, box: pd.DataFrame) -> np.ndarray:
    """Return an array of {'long','short','hold'} (dtype=object) aligned 1:1 with df_dec rows."""
    out = np.empty(len(df_dec), dtype=object)
    dates = df_dec["Date"].to_numpy()
    # cache box rows by box-date to avoid repeated .loc on duplicate dates
    cache: dict = {}
    for i in range(len(df_dec)):
        bd = BoxLookup._candle_to_box_date(pd.Timestamp(dates[i]))
        if bd not in cache:
            try:
                cache[bd] = box.loc[bd]
            except KeyError:
                cache[bd] = None
        out[i] = _stage1_candle_signal(df_dec.iloc[i], cache[bd])
    return out
