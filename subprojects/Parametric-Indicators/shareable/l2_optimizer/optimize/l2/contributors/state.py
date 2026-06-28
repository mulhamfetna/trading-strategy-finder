"""Contributor net state {+1 long / -1 short / 0 hold} per decision bar — BOTH definitions (Spec §4.2).

(a) touch_state     — read the DELIVERED Stage-1 touch signal (ES_SIGNALS_DELIVERY/2_holds_dropped) and
                      collapse the per-(candle × box) rows to one net state per bar (long wins ties).
                      Verified equal to optimize.signals.decision_signals(es) byte-for-byte.
(b) traversal_state — recompute via box_lookup.BoxLookup (L1-parity traversal: below→inside→above = long,
                      above→inside→below = short). Stateful ⇒ feed bars in chronological order.

The two can diverge materially; letting the optimizer pick is intentional (Spec §12)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[3]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

from box_lookup import BoxLookup                                  # noqa: E402

_SIG2INT = {"long": 1, "short": -1, "hold": 0}


def touch_state(df_dec: pd.DataFrame, delivery: pd.DataFrame) -> np.ndarray:
    """Net per-decision-bar touch state from the delivered Stage-1 signal. The delivery (2_holds_dropped)
    carries only long/short rows; a bar is long if ANY of its delivered rows is long, short if any is
    short, LONG WINS TIES (mirrors decision_signals + L1's collapse-to-one-entry-per-candle). Bars with no
    delivered row are hold (0)."""
    dates = pd.DatetimeIndex(df_dec["Date"])
    longs = pd.DatetimeIndex(delivery.loc[delivery["signal"] == "long", "datetime"].unique())
    shorts = pd.DatetimeIndex(delivery.loc[delivery["signal"] == "short", "datetime"].unique())
    out = np.zeros(len(dates), dtype=np.int8)
    out[dates.isin(shorts)] = -1
    out[dates.isin(longs)] = 1            # long assigned last ⇒ long wins ties
    return out


def traversal_state(df_dec: pd.DataFrame, box_csv: str, tick_threshold: float) -> np.ndarray:
    """Net per-decision-bar traversal state via BoxLookup (L1 parity). Stateful: ONE BoxLookup, reset,
    fed bars in chronological order. get_signal returns long/short/hold/None; None (no active box row) ⇒
    hold (0)."""
    bl = BoxLookup(unified_path=box_csv, tick_threshold=tick_threshold)
    bl.reset_state()
    dates = df_dec["Date"].to_numpy()
    closes = df_dec["Close"].to_numpy(float)
    out = np.zeros(len(df_dec), dtype=np.int8)
    for i in range(len(df_dec)):
        sig = bl.get_signal(float(closes[i]), pd.Timestamp(dates[i]))
        out[i] = _SIG2INT.get(sig, 0)
    return out
