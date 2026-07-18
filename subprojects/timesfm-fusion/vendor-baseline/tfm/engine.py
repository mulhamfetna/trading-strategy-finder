"""Causal single-contract backtest engine — split into (cheap) signal build + simulation.

The EXPENSIVE part (model forecasts) lives in forecast_cache.py and is cached to disk. Here we only
turn precomputed forecast arrays into signals and walk the position loop, so a whole grid of
edge/SL/TP thresholds sweeps almost for free over one set of cached forecasts.

Flow (no look-ahead):
  1. forecast arrays (median/q_low/q_high terminal values) at each decision bar i, from close[..i].
  2. signal for entry at bar i+1 (direction + vol-adaptive SL/TP), via strategy.signal_from_arrays.
  3. position loop: enter at bar i+1 open; each later bar checks intrabar SL/TP via high/low
     (stop wins ties, conservative); force-exit at the horizon on that bar's close.
  4. P/L $ = direction * (exit - entry) * point_value  -  round-trip cost.
One position at a time (single-contract account).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import Instrument
from .strategy import Signal, StratParams


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: int
    entry: float
    exit: float
    pnl: float          # net $ after cost
    bars_held: int
    reason: str         # 'tp' | 'sl' | 'horizon'


def simulate(df: pd.DataFrame, signals: list[Signal | None], inst: Instrument,
             p: StratParams, start: int | None = None, end: int | None = None) -> list[Trade]:
    """Position loop over precomputed per-bar signals (signal[i] enters at bar i+1).

    `start`/`end` bound the ENTRY window (row indices into df), enabling clean train/test
    evaluation on one full-series signal array. Trades are force-capped to exit by `end`, so a
    train-window trade never leaks P/L from test bars (and vice-versa)."""
    o = df["open"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    lo = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)
    t = df["datetime"].to_numpy()
    n = len(df)
    lo_i = max(p.context_len - 1, start if start is not None else 0)
    hi_i = (end if end is not None else n) - 1

    trades: list[Trade] = []
    i = lo_i
    while i < hi_i:
        sig = signals[i]
        if sig is None or sig.direction == 0:
            i += 1
            continue

        entry_bar = i + 1
        entry = o[entry_bar]
        d = sig.direction
        sl = entry - d * sig.sl_dist
        tp = entry + d * sig.tp_dist
        max_exit = min(entry_bar + p.horizon, hi_i, n - 1)

        exit_bar, exit_px, reason = max_exit, c[max_exit], "horizon"
        for j in range(entry_bar, max_exit + 1):
            hit_sl = (lo[j] <= sl) if d > 0 else (h[j] >= sl)
            hit_tp = (h[j] >= tp) if d > 0 else (lo[j] <= tp)
            if hit_sl:  # conservative: stop wins ties within a bar
                exit_bar, exit_px, reason = j, sl, "sl"
                break
            if hit_tp:
                exit_bar, exit_px, reason = j, tp, "tp"
                break

        gross = d * (exit_px - entry) * inst.point_value
        pnl = gross - inst.cost_dollars
        trades.append(Trade(
            entry_time=pd.Timestamp(t[entry_bar]), exit_time=pd.Timestamp(t[exit_bar]),
            direction=d, entry=entry, exit=exit_px, pnl=pnl,
            bars_held=exit_bar - entry_bar, reason=reason,
        ))
        i = exit_bar
    return trades


def run_backtest(df: pd.DataFrame, forecaster, inst: Instrument, p: StratParams) -> list[Trade]:
    """Convenience one-shot: forecast (cached) -> signals -> simulate. Used by simple runs/tests."""
    from .forecast_cache import forecast_arrays
    from .strategy import signals_from_arrays
    med, qlo, qhi = forecast_arrays(df, forecaster, p.context_len, p.horizon)
    signals = signals_from_arrays(df, med, qlo, qhi, inst, p)
    return simulate(df, signals, inst, p)
