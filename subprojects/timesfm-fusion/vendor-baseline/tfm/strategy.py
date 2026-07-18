"""Turn a probabilistic forecast into a trade decision + volatility-adaptive risk.

STANDALONE mode: TimesFM decides the direction itself. But we never trade a raw point forecast —
we require the expected move to (a) exceed the forecast's own uncertainty by a margin (edge_k) and
(b) clear an absolute cost/noise floor. SL/TP are sized off the forecast distribution, so risk
adapts to the current price regime and the chosen timeframe automatically.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .forecaster import ForecastResult

# q_high - q_low spans the 10th..90th deciles ~= 2.5631 standard deviations.
_DECILE_SPAN_SIGMAS = 2.0 * 1.28155


@dataclass
class StratParams:
    context_len: int = 512      # bars of history fed to the forecaster (matches TimesFM max_context)
    horizon: int = 24           # bars ahead to forecast / max hold
    direction_mode: str = "momentum"  # 'momentum' (median vs close) | 'skew' (quantile asymmetry)
    edge_k: float = 0.35        # require |signal| > edge_k * sigma_horizon
    min_edge_ticks: float = 8.0 # AND require |signal| > this many ticks (cost/noise floor)
    sl_mult: float = 1.30       # stop distance = sl_mult * sigma_horizon
    tp_mult: float = 1.80       # target distance = tp_mult * sigma_horizon
    gate_spread_pct: float = 100.0  # skip bars whose forecast uncertainty is above this pct (100=off)


@dataclass
class Signal:
    direction: int      # +1 long, -1 short, 0 flat
    sl_dist: float      # points
    tp_dist: float      # points
    exp_move: float     # points (median target - last close)
    sigma_h: float      # points (1-sigma at horizon end)


def _sigma_from_forecast(fc: ForecastResult) -> float:
    """1-sigma (points) of the terminal forecast, from the 10-90 decile band."""
    band = float(fc.q_high[-1] - fc.q_low[-1])
    return max(band / _DECILE_SPAN_SIGMAS, 1e-9)


def signal_from_forecast(fc: ForecastResult, last_close: float, tick: float,
                         p: StratParams, sigma_gate: float | None = None) -> Signal:
    """Map a forecast to a Signal. `sigma_gate` (if given) is the vol threshold in points; a
    terminal sigma above it means the regime is too uncertain -> stand aside."""
    sigma_h = _sigma_from_forecast(fc)
    exp_move = float(fc.median[-1] - last_close)

    if sigma_gate is not None and sigma_h > sigma_gate:
        return Signal(0, 0.0, 0.0, exp_move, sigma_h)

    edge_ok = abs(exp_move) > p.edge_k * sigma_h
    floor_ok = abs(exp_move) > p.min_edge_ticks * tick
    if not (edge_ok and floor_ok):
        return Signal(0, 0.0, 0.0, exp_move, sigma_h)

    direction = 1 if exp_move > 0 else -1
    return Signal(direction, p.sl_mult * sigma_h, p.tp_mult * sigma_h, exp_move, sigma_h)


def signals_from_arrays(df: pd.DataFrame, med: np.ndarray, qlo: np.ndarray, qhi: np.ndarray,
                        inst, p: StratParams) -> list[Signal | None]:
    """Build per-bar signals from cached terminal-forecast arrays (cheap, no model calls).

    signal[i] enters at bar i+1. NaN forecast -> None. Applies the optional forward-vol gate:
    bars whose terminal sigma is above the `gate_spread_pct` percentile (over eligible bars) are
    skipped — a regime filter that stands aside when the model itself is most uncertain.
    """
    n = len(df)
    close = df["close"].to_numpy(dtype=float)
    sigma = (qhi - qlo) / _DECILE_SPAN_SIGMAS
    # the directional 'signal' magnitude compared against edge_k*sigma and the tick floor:
    #   momentum: how far the median forecast drifts from the current price
    #   skew    : quantile asymmetry (upside tail minus downside tail) -> distributional lean
    if p.direction_mode == "skew":
        signal = (qhi - med) - (med - qlo)   # >0 => upside-skewed => long
    else:
        signal = med - close                 # momentum / drift
    exp_move = signal

    eligible = ~np.isnan(med)
    sigma_gate = None
    if p.gate_spread_pct < 100.0 and eligible.any():
        sigma_gate = float(np.percentile(sigma[eligible], p.gate_spread_pct))

    tick = inst.tick
    out: list[Signal | None] = [None] * n
    for i in range(n):
        if not eligible[i]:
            continue
        s_h = max(sigma[i], 1e-9)
        em = exp_move[i]
        if sigma_gate is not None and s_h > sigma_gate:
            out[i] = Signal(0, 0.0, 0.0, em, s_h)
            continue
        if abs(em) > p.edge_k * s_h and abs(em) > p.min_edge_ticks * tick:
            d = 1 if em > 0 else -1
            out[i] = Signal(d, p.sl_mult * s_h, p.tp_mult * s_h, em, s_h)
        else:
            out[i] = Signal(0, 0.0, 0.0, em, s_h)
    return out
