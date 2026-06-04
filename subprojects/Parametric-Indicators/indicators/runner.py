"""Wire the indicator confirmation layer into the box strategy's per-bar entry gate.

The engine (engine.SimpleStrategy) enters at decision bar `idx` using the signal of the JUST-CLOSED
bar `idx-1`. So an indicator's confirm/veto for that entry must be read from bar `idx-1` (causal).
`composite_gate` builds the per-bar indicator allow-mask (aligned to the signal bar) and ANDs it with
the existing volatility gate.

Parity: with no ENABLED indicator the allow-mask is all-True ⇒ the composite gate == the vol gate
exactly, so the engine reproduces today's behaviour (regression-locked in tests/test_integration.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .base import MarketContext
from .confirm import build_gate


def market_context(df: pd.DataFrame) -> MarketContext:
    """Build a MarketContext from a decision-timeframe OHLCV frame (session = calendar day)."""
    sess = pd.to_datetime(df["Date"]).dt.normalize().astype("int64").to_numpy()
    return MarketContext(
        open=df["Open"].to_numpy(float), high=df["High"].to_numpy(float),
        low=df["Low"].to_numpy(float), close=df["Close"].to_numpy(float),
        volume=df["Volume"].to_numpy(float) if "Volume" in df.columns else np.zeros(len(df)),
        session_id=sess,
    )


def box_direction_int(df: pd.DataFrame, box: pd.DataFrame) -> np.ndarray:
    """Per-decision-bar box signal as int8 (+1 long / -1 short / 0 hold)."""
    from optimize import signals as _sig
    from optimize.fast_engine import signals_to_int
    return signals_to_int(_sig.decision_signals(df, box))


def composite_gate(vol_gate, df, box, indicators, k):
    """vol_gate: per-bar bool (engine idx). indicators: list of Indicator instances (enabled+disabled).
    Returns (gate, votes, active): gate = vol_gate ∧ (indicator allow, aligned to the signal bar)."""
    vg = np.asarray(vol_gate, dtype=bool)
    n = len(vg)
    ctx = market_context(df)
    bdir = box_direction_int(df, box)
    allow, votes, active = build_gate(ctx, bdir, indicators, k, base_gate=None)
    # Entry at idx uses the just-closed bar idx-1, so align the allow-mask forward by one bar.
    # idx 0 can never enter (engine warm-up) ⇒ leave True so all-off ⇒ gate == vol_gate exactly.
    aligned = np.ones(n, dtype=bool)
    aligned[1:] = allow[:-1]
    return vg & aligned, votes, active
