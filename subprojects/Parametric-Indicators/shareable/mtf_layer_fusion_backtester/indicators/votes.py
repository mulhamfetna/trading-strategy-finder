"""Pure per-indicator direction-mapping helpers (value series → confirm_dir / veto_dir).

Separated from the OOP wrappers (indicators/library.py) so the vote semantics are unit-testable in
isolation. Each returns (confirm_dir, veto_dir) int arrays ∈ {+1 long, -1 short, 0 none}.
See docs/INDICATORS.md for the per-indicator rules.
"""
from __future__ import annotations

import numpy as np


def stance_directions(stance: np.ndarray):
    """A simple bullish/bearish stance ∈ {+1,-1,0} → confirm that side, veto the other.
    cdir = stance; vdir = -stance."""
    s = np.asarray(stance, dtype=np.int8)
    return s.copy(), (-s).astype(np.int8)


def rsi_directions(rsi_vals: np.ndarray, lower: float = 30.0, upper: float = 70.0):
    """RSI zones (docs §7): overbought ≥upper → (short, veto-long); oversold ≤lower →
    (long, veto-short); 50<r<upper bullish → (long, veto-short); lower<r<50 bearish →
    (short, veto-long); NaN or r==50 → neutral."""
    r = np.asarray(rsi_vals, dtype=float)
    cdir = np.zeros(len(r), dtype=np.int8)
    vdir = np.zeros(len(r), dtype=np.int8)
    valid = ~np.isnan(r)
    overbought = valid & (r >= upper)
    oversold = valid & (r <= lower)
    bullish = valid & ~overbought & ~oversold & (r > 50)
    bearish = valid & ~overbought & ~oversold & (r < 50)
    long_zone = oversold | bullish          # supports long / vetoes short
    short_zone = overbought | bearish       # supports short / vetoes long
    cdir[long_zone] = +1; vdir[long_zone] = -1
    cdir[short_zone] = -1; vdir[short_zone] = +1
    return cdir, vdir
