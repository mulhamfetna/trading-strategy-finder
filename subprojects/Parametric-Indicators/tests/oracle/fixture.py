"""Deterministic OHLCV fixture shared by every indicator reference test.

Fixed seed → identical arrays every run (no wall-clock / no global RNG state). High/low are widened
to enclose open & close so every bar is valid. Returns plain numpy arrays (the MarketContext shape)."""
from __future__ import annotations

import numpy as np


def ohlcv(n: int = 300) -> dict:
    rng = np.random.default_rng(20260725)             # fixed seed → deterministic
    ret = rng.normal(0.0, 0.01, n)
    close = 100.0 * np.exp(np.cumsum(ret))
    spread = np.abs(rng.normal(0.0, 0.4, n)) + 0.1
    high = close + spread
    low = close - spread
    openp = np.concatenate([[close[0]], close[:-1]])   # today's open = yesterday's close
    high = np.maximum.reduce([high, openp, close])     # enclose O & C
    low = np.minimum.reduce([low, openp, close])
    volume = rng.integers(500, 5000, n).astype(float)
    return {"open": openp, "high": high, "low": low, "close": close, "volume": volume}
