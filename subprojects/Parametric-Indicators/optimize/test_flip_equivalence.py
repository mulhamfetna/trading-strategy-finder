"""Invariant lock for the NEW flip semantics (spec 2026-06-22): flip = reverse entry direction ONLY,
then the normal exit logic (hard-SL > hard-TP > soft-SL) applies to the ENTERED direction.

Proves:
  (A) fast_backtest(flip=True, signal=S) == fast_backtest(flip=False, signal=¬S)  trade-for-trade.
  (B) an engine flip=True run yields normal-mode exit reasons: NO 'TAKE_PROFIT_SOFT', and soft
      stop-losses are live again (>=1 'STOP_LOSS_SOFT').
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PARENT = Path(__file__).resolve().parents[1]
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

from optimize import data, signals  # noqa: E402
from optimize.fast_engine import fast_backtest, signals_to_int  # noqa: E402
from engine import SimpleStrategy, SimpleStrategyParams  # noqa: E402

_TF = "4h"
CASES = [(30, 40, 60, 60), (30, 40, 60, 0), (100, 160, 200, 50), (60, 120, 150, 70)]


@pytest.fixture(scope="module")
def inputs():
    df, df1, box, vf, n = data.load_inputs(_TF)
    sig = signals_to_int(signals.decision_signals(df, box))
    return df, df1, box, vf, n, sig


def _key(t):
    return (pd.Timestamp(t["entry_time"]), t["direction"], t["exit_reason"],
            pd.Timestamp(t["exit_time"]), round(float(t["pnl_points"]), 6))


@pytest.mark.parametrize("ss,sh,tp,gp", CASES)
def test_flip_equals_reversed_signal(inputs, ss, sh, tp, gp):
    df, df1, box, vf, n, sig = inputs
    DD, DC = df["Date"].to_numpy(), df["Close"].to_numpy(float)
    MD = df1["Date"].to_numpy(); MH = df1["High"].to_numpy(float)
    ML = df1["Low"].to_numpy(float); MC = df1["Close"].to_numpy(float)
    gate = None if gp <= 0 else (vf <= float(np.percentile(vf[:n], gp)))
    flipped = fast_backtest(DD, DC, sig, gate, MD, MH, ML, MC, ss, sh, tp, True)
    reversed_ = fast_backtest(DD, DC, (-sig).astype(sig.dtype), gate, MD, MH, ML, MC, ss, sh, tp, False)
    assert len(flipped) == len(reversed_)
    assert [_key(t) for t in flipped] == [_key(t) for t in reversed_]


def test_flip_engine_uses_normal_exit_reasons(inputs):
    df, df1, box, *_ = inputs
    sp = SimpleStrategyParams(sl_soft_points=30, sl_hard_points=40, tp_soft_points=60,
                              tp_hard_points=60, data_path_4h="", data_path_1min="",
                              box_data_path="", flip_entry_direction=True)
    E0, _ = SimpleStrategy(sp).backtest(df, df1, box, entry_gate=None)
    reasons = [t.get("exit_reason") for t in E0]
    assert "TAKE_PROFIT_SOFT" not in reasons, "flip must no longer produce soft take-profits"
    assert reasons.count("STOP_LOSS_SOFT") >= 1, "soft stop-loss must be live again under flip"
