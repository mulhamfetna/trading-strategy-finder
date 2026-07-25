"""Pure per-indicator direction-mapping helpers (value series → confirm_dir / veto_dir).

Separated from the OOP wrappers (indicators/library.py) so the vote semantics are unit-testable in
isolation. Each returns (confirm_dir, veto_dir) int arrays ∈ {+1 long, -1 short, 0 none}.
See docs/INDICATORS.md for the per-indicator rules.
"""
from __future__ import annotations

import numpy as np

from .base import BOTH


def stance_directions(stance: np.ndarray):
    """A simple bullish/bearish stance ∈ {+1,-1,0} → confirm that side, veto the other.
    cdir = stance; vdir = -stance."""
    s = np.asarray(stance, dtype=np.int8)
    return s.copy(), (-s).astype(np.int8)


def band_directions(v: np.ndarray, lower: float, upper: float, mid: float = 50.0):
    """Mean-reversion zone logic around a midpoint. overbought ≥upper → (short, veto-long);
    oversold ≤lower → (long, veto-short); mid<v<upper bullish → (long, veto-short);
    lower<v<mid bearish → (short, veto-long); NaN or v==mid → neutral. Generalizes RSI's
    hardcoded 50 midpoint so Williams %R (mid −50), CMO (mid 0), etc. reuse it."""
    x = np.asarray(v, dtype=float)
    cdir = np.zeros(len(x), dtype=np.int8)
    vdir = np.zeros(len(x), dtype=np.int8)
    valid = ~np.isnan(x)
    overbought = valid & (x >= upper)
    oversold = valid & (x <= lower)
    bullish = valid & ~overbought & ~oversold & (x > mid)
    bearish = valid & ~overbought & ~oversold & (x < mid)
    long_zone = oversold | bullish          # supports long / vetoes short
    short_zone = overbought | bearish       # supports short / vetoes long
    cdir[long_zone] = +1; vdir[long_zone] = -1
    cdir[short_zone] = -1; vdir[short_zone] = +1
    return cdir, vdir


def rsi_directions(rsi_vals: np.ndarray, lower: float = 30.0, upper: float = 70.0):
    """RSI zones (docs §7) — thin delegate to band_directions with the classic mid=50."""
    return band_directions(rsi_vals, lower, upper, 50.0)


def magnitude_veto(value: np.ndarray, ref: np.ndarray, threshold: float):
    """Unbounded magnitude → BOTH-side veto where value/ref < threshold (low-activity chop veto,
    the box strategy being vol-seeking). cdir is always 0; NaN/inf ratios never veto."""
    a = np.asarray(value, dtype=float)
    b = np.asarray(ref, dtype=float)
    cdir = np.zeros(len(a), dtype=np.int8)
    vdir = np.zeros(len(a), dtype=np.int8)
    with np.errstate(invalid="ignore", divide="ignore"):
        ratio = a / b
    veto = np.isfinite(ratio) & (ratio < float(threshold))
    vdir[veto] = BOTH
    return cdir, vdir


def both_veto(mask: np.ndarray):
    """Boolean condition → BOTH-side veto where True (e.g. high choppiness / squeeze-on).
    cdir always 0."""
    m = np.asarray(mask, dtype=bool)
    cdir = np.zeros(len(m), dtype=np.int8)
    vdir = np.zeros(len(m), dtype=np.int8)
    vdir[m] = BOTH
    return cdir, vdir
