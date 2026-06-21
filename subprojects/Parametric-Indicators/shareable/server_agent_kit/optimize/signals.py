"""Param-independent per-decision-bar Stage-1 signal precompute.

The entry DIRECTION (long/short/hold) depends only on the decision-bar OHLC vs the box levels — NOT
on SL/TP/gate/breaker. So it can be computed ONCE per timeframe and reused across all optimiser
trials (the H.7 speedup in TASK.md §9-f) and to find actionable entries for the SL/TP-bound study
(H.5). This mirrors engine._stage1_candle_signal + the box-date mapping exactly.

`signal[i]` is the Stage-1 signal of decision bar i (the bar that, once CLOSED, makes bar i+1
signal-eligible — the engine reads signal from the just-closed bar). 'long' | 'short' | 'hold'.

PERFORMANCE (Axis B · Step B1, task #210): `decision_signals` is the VECTORIZED (numpy) implementation.
`decision_signals_ref` is the original per-bar pandas loop, kept verbatim as the FROZEN reference that
`tests/test_axisB_signal_equiv.py` asserts the vectorized version reproduces element-for-element. The
two must agree bit-for-bit; the reference is the spec (it calls engine._stage1_candle_signal directly).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from engine import _stage1_candle_signal, _LEVEL_PAIRS  # noqa: E402
from box_lookup import BoxLookup                         # noqa: E402


def decision_signals_ref(df_dec: pd.DataFrame, box: pd.DataFrame) -> np.ndarray:
    """FROZEN reference — the original per-bar loop. Returns {'long','short','hold'} (dtype=object)
    aligned 1:1 with df_dec rows. Mirrors engine._stage1_candle_signal + the box-date mapping exactly.
    Kept as the immutable spec for the Step-B1 equivalence test; DO NOT optimize this function."""
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


def _box_dates_vec(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Vectorized equivalent of BoxLookup._candle_to_box_date over a whole DatetimeIndex.
    Rule (verbatim): strip tz; candles with hour >= 18 belong to the NEXT session day's box; normalize
    to midnight. tz-naive in → tz-naive out (the box index is always tz-naive)."""
    if dates.tz is not None:
        dates = dates.tz_localize(None)
    same_day = dates.normalize()
    next_day = (dates + pd.Timedelta(days=1)).normalize()
    rolled = np.where(dates.hour >= 18, next_day.values, same_day.values)
    return pd.DatetimeIndex(rolled)


def decision_signals(df_dec: pd.DataFrame, box: pd.DataFrame) -> np.ndarray:
    """VECTORIZED Stage-1 signal (Axis B · Step B1). Returns {'long','short','hold'} (dtype=object,
    Python str) aligned 1:1 with df_dec rows. Bit-identical to `decision_signals_ref` (which is the
    spec) — see tests/test_axisB_signal_equiv.py.

    Method: gather each bar's box row in one `reindex` (NaN where the date is absent), then compute the
    long/short/hold collapse with pure numpy array ops — no per-bar pandas access. Tie-break and edge
    conventions match the scalar rule exactly:
      • color: green = close>open, red = close<open; a doji (close==open) ⇒ hold.
      • a level pair contributes only if BOTH columns are present and non-NaN ('valid') AND the bar's
        [low,high] overlaps [lower,upper] ('touched').
      • long iff green & touched & close>upper; short iff red & touched & close<lower (any pair).
      • long WINS ties (assigned last); missing box row / NaN levels ⇒ that pair invalid ⇒ hold.
    """
    n = len(df_dec)
    out = np.empty(n, dtype=object)
    if n == 0:
        return out

    O = df_dec["Open"].to_numpy(dtype=float)
    H = df_dec["High"].to_numpy(dtype=float)
    L = df_dec["Low"].to_numpy(dtype=float)
    C = df_dec["Close"].to_numpy(dtype=float)

    # one vectorized gather: each bar's box row aligned by its (rolled) box-date; absent date ⇒ NaN row.
    box_dates = _box_dates_vec(pd.DatetimeIndex(df_dec["Date"]))
    sub = box.reindex(box_dates)

    green = C > O
    red = C < O
    has_long = np.zeros(n, dtype=bool)
    has_short = np.zeros(n, dtype=bool)

    for upper_col, lower_col, _label in _LEVEL_PAIRS:
        # a column absent from the box ⇒ this pair never contributes (matches the scalar's `continue`).
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
    out[has_long] = "long"   # long assigned last ⇒ long wins ties (matches the scalar rule)
    return out
