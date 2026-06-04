"""WS-I indicator framework — config, market context, and the Indicator base class.

OOP-first (per the architecture directive): each indicator is its own class producing, per bar, a
`confirm_dir` and a `veto_dir` ∈ {+1 long, -1 short, 0 none}. The base `vote()` maps those against
the box's per-bar direction and the indicator's `mode` into a vote ∈ {+1 confirm, -1 veto, 0
neutral}. The confirmation aggregator (indicators/confirm.py) combines active votes with the K rule.

No silent fallback: bad config raises IndicatorParamError (surfaced to the UI).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

CONFIRM, VETO, NEUTRAL = 1, -1, 0
LONG, SHORT, HOLD = 1, -1, 0
BOTH = 2  # direction-agnostic sentinel for cdir/vdir (e.g. ADX "no trend" vetoes either side)
_MODES = ("confirm", "veto", "both")
_RETRACE_UNITS = ("atr_mult", "points")


class IndicatorParamError(ValueError):
    """Invalid indicator parameter. Surfaced to the UI; never silently clamped/defaulted."""


@dataclass
class MarketContext:
    """Decision-timeframe OHLCV arrays (+ optional session ids for VWAP). Shared across indicators."""
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray
    session_id: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.close)


@dataclass
class IndicatorConfig:
    """Per-indicator controls. Defaults = disabled & immediate ⇒ parity preserved."""
    enabled: bool = False
    mode: str = "both"
    retrace_amount: float = 0.0
    retrace_unit: str = "atr_mult"
    wait_bars: int = 0
    params: dict = field(default_factory=dict)

    def validate(self) -> "IndicatorConfig":
        if self.mode not in _MODES:
            raise IndicatorParamError(f"mode must be one of {_MODES}, got {self.mode!r}")
        if self.retrace_unit not in _RETRACE_UNITS:
            raise IndicatorParamError(f"retrace_unit must be one of {_RETRACE_UNITS}, got {self.retrace_unit!r}")
        if self.retrace_amount < 0:
            raise IndicatorParamError(f"retrace_amount must be ≥ 0, got {self.retrace_amount}")
        if self.wait_bars < 0 or int(self.wait_bars) != self.wait_bars:
            raise IndicatorParamError(f"wait_bars must be a non-negative integer, got {self.wait_bars!r}")
        return self


def apply_wait(vote: np.ndarray, wait_bars: int) -> np.ndarray:
    """Debounce CONFIRM votes: a confirm only counts after the indicator has confirmed for
    wait_bars+1 consecutive bars (a run reset by any non-confirm bar). VETO is immediate (safety
    first) and untouched. wait_bars=0 ⇒ identity (parity)."""
    if wait_bars <= 0:
        return vote
    out = vote.copy()
    run = 0
    for t in range(len(out)):
        if vote[t] == CONFIRM:
            run += 1
            if run <= wait_bars:
                out[t] = NEUTRAL
        else:
            run = 0
    return out


class Indicator(ABC):
    """Base indicator. Subclasses implement `directions(ctx)`."""
    key: str = ""

    def __init__(self, config: IndicatorConfig | None = None) -> None:
        self.config = (config or IndicatorConfig()).validate()

    @abstractmethod
    def directions(self, ctx: MarketContext):
        """Return (confirm_dir, veto_dir): int arrays per bar in {+1,-1,0}."""

    def series(self, ctx: MarketContext) -> dict:
        """Raw indicator value(s) per bar, for logging/plotting. Override as useful."""
        return {}

    def vote(self, ctx: MarketContext, box_dir: np.ndarray) -> np.ndarray:
        """Per-bar vote ∈ {+1 confirm, -1 veto, 0 neutral} vs the box direction + this mode.
        In 'both' mode a veto overrides a confirm on the same bar."""
        cdir, vdir = self.directions(ctx)
        bd = np.asarray(box_dir)
        has_signal = bd != HOLD
        would_confirm = ((cdir == bd) | (cdir == BOTH)) & has_signal
        would_veto = ((vdir == bd) | (vdir == BOTH)) & has_signal
        out = np.zeros(len(bd), dtype=np.int8)
        if self.config.mode in ("confirm", "both"):
            out[would_confirm] = CONFIRM
        if self.config.mode in ("veto", "both"):
            out[would_veto] = VETO  # veto applied last ⇒ overrides confirm in 'both'
        return apply_wait(out, self.config.wait_bars)
