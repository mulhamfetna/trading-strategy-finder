"""M3 — do daily zones mark anything real?

Operationalized to match what the strategy actually trades: after a signal fires at a zone, does price CONTINUE
in the signal's direction? Measured against two dumb controls, with a block-bootstrap CI (returns are
autocorrelated, so an i.i.d. bootstrap would understate the interval) and an explicit power floor for nulls.
"""
from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
import pandas as pd

from research.daily_boxes.study_signals import LevelPairs


def directional_forward_returns(df_dec: pd.DataFrame, sig: np.ndarray, horizon: int) -> np.ndarray:
    """Points gained IN THE SIGNAL'S DIRECTION `horizon` bars after each signal.

    long  -> (close[i+h] - close[i])
    short -> (close[i] - close[i+h])
    hold / no future bar -> NaN (excluded from every statistic)
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    C = df_dec["Close"].to_numpy(dtype=float)
    n = len(C)
    fwd = np.full(n, np.nan)
    if n > horizon:
        fwd[: n - horizon] = C[horizon:] - C[: n - horizon]
    direction = np.where(sig == "long", 1.0, np.where(sig == "short", -1.0, np.nan))
    return fwd * direction


def control_location(box: pd.DataFrame, pairs: LevelPairs, rng: np.random.Generator,
                     frac: float) -> pd.DataFrame:
    """CONTROL 1 — keep each zone's WIDTH, move its LOCATION by a random offset.

    Offset is drawn per (row, pair) as Uniform(-frac, +frac) * |zone midpoint|, so it scales with price. Kills
    the "any line looks meaningful" explanation while holding zone geometry fixed.
    """
    out = box.copy()
    for upper, lower, _label in pairs:
        if upper not in out.columns or lower not in out.columns:
            continue
        up = out[upper].to_numpy(dtype=float)
        lo = out[lower].to_numpy(dtype=float)
        mid = (up + lo) / 2.0
        offset = rng.uniform(-frac, frac, size=len(out)) * np.abs(mid)
        out[upper] = up + offset
        out[lower] = lo + offset
    return out


def control_date(box: pd.DataFrame, pairs: LevelPairs, rng: np.random.Generator) -> pd.DataFrame:
    """CONTROL 2 — give each day ANOTHER day's zones.

    Zone geometry and the overall level distribution are preserved exactly; only the date-specific information
    is destroyed. Rows are permuted as whole units so a day's zones stay internally consistent.
    """
    out = box.copy()
    cols = [c for u, l, _ in pairs for c in (u, l) if c in out.columns]
    if not cols:
        return out
    perm = rng.permutation(len(out))
    out[cols] = out[cols].to_numpy()[perm]
    return out


def block_bootstrap_ci(x: np.ndarray, block: int, n_boot: int, alpha: float,
                       rng: np.random.Generator) -> Tuple[float, float]:
    """Two-sided (1-alpha) CI for the MEAN of `x` via a moving-block bootstrap.

    Blocks preserve short-range autocorrelation; an i.i.d. bootstrap would produce a falsely narrow interval on
    financial returns.
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return (float("nan"), float("nan"))
    if block < 1:
        raise ValueError(f"block must be >= 1, got {block}")
    block = min(block, len(x))
    n_blocks = int(np.ceil(len(x) / block))
    max_start = len(x) - block + 1

    means = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        starts = rng.integers(0, max_start, size=n_blocks)
        sample = np.concatenate([x[s:s + block] for s in starts])[: len(x)]
        means[b] = sample.mean()
    lo = float(np.quantile(means, alpha / 2.0))
    hi = float(np.quantile(means, 1.0 - alpha / 2.0))
    return (lo, hi)


def block_bootstrap_diff_ci(x: np.ndarray, y: np.ndarray, block: int, n_boot: int, alpha: float,
                            rng: np.random.Generator) -> Tuple[float, float, float]:
    """CI for the DIFFERENCE of means (mean(x) - mean(y)), two independent block bootstraps.

    This is the number that actually decides 'are the real zones better than the control?'. Comparing two
    overlapping one-sample CIs by eye is NOT a test of their difference — two intervals can overlap while the
    difference is significant, and vice versa. The arms are unpaired (different bars fire under real vs
    control zones), so each is resampled independently.

    Returns (point_estimate, lo, hi).
    """
    x = np.asarray(x, dtype=float); x = x[~np.isnan(x)]
    y = np.asarray(y, dtype=float); y = y[~np.isnan(y)]
    if len(x) == 0 or len(y) == 0:
        return (float("nan"), float("nan"), float("nan"))

    def _draw(v: np.ndarray) -> float:
        b = min(block, len(v))
        n_blocks = int(np.ceil(len(v) / b))
        starts = rng.integers(0, len(v) - b + 1, size=n_blocks)
        return float(np.concatenate([v[s:s + b] for s in starts])[: len(v)].mean())

    diffs = np.array([_draw(x) - _draw(y) for _ in range(n_boot)], dtype=float)
    return (float(x.mean() - y.mean()),
            float(np.quantile(diffs, alpha / 2.0)),
            float(np.quantile(diffs, 1.0 - alpha / 2.0)))


def min_detectable_effect(x: np.ndarray, power: float = 0.80, alpha: float = 0.05) -> float:
    """Smallest mean effect a two-sided one-sample t-test could detect at `power`, given this sample's spread.

    Reported alongside every NULL result: a null that could not have detected a tradeable effect anyway is not
    evidence of absence. Uses the normal approximation (z=1.96 at alpha=.05, z=0.84 at power=.80), which is
    accurate at the sample sizes here (n in the hundreds to thousands).
    """
    from scipy.stats import norm

    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2:
        return float("nan")
    z_alpha = norm.ppf(1.0 - alpha / 2.0)
    z_power = norm.ppf(power)
    return float((z_alpha + z_power) * x.std(ddof=1) / np.sqrt(n))
