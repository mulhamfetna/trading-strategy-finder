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
    ref_close: np.ndarray | None = None   # reference-instrument close, causally aligned to these bars
                                           # (cross-series indicators only; None ⇒ they stay neutral)

    def __len__(self) -> int:
        return len(self.close)


@dataclass
class IndicatorConfig:
    """Per-indicator controls. Defaults = disabled ⇒ parity preserved.

    NOTE: retrace + wait are GLOBAL entry-timing controls (one value each, applied to ALL
    indicators), NOT per-indicator — see runner.build_entry_resolver / timing.resolve_entry_1min.
    They are deliberately absent here."""
    enabled: bool = False
    mode: str = "both"
    params: dict = field(default_factory=dict)

    def validate(self) -> "IndicatorConfig":
        if self.mode not in _MODES:
            raise IndicatorParamError(f"mode must be one of {_MODES}, got {self.mode!r}")
        return self


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

    def warmup_bars(self) -> int:
        """How many leading bars this indicator must see before its vote is trustworthy — its own
        look-back; for COMPOSITE indicators (those built on other look-back series, e.g. Keltner =
        EMA+ATR, MACD = EMAs) the max/stack over the components they depend on. While warming the
        vote is forced NEUTRAL (see vote()) so a seeded EMA can't 'confirm' on 5 bars of data.
        0 = no warm-up. Overridden per class in library.py."""
        return 0

    def warmup_deps(self) -> str:
        """Human description of WHAT this indicator is waiting on while warming (for the log)."""
        return f"its {self.warmup_bars()}-bar look-back"

    def vote(self, ctx: MarketContext, box_dir: np.ndarray) -> np.ndarray:
        """Per-bar vote ∈ {+1 confirm, -1 veto, 0 neutral} vs the box direction + this mode.
        In 'both' mode a veto overrides a confirm on the same bar. The first `warmup_bars()` bars
        are forced NEUTRAL — the indicator (and anything it depends on) isn't warmed yet."""
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
        w = min(int(self.warmup_bars()), len(out))
        if w > 0:
            out[:w] = NEUTRAL       # still warming up (incl. dependencies) ⇒ no vote
        return out  # raw per-decision-bar vote; the GLOBAL wait is a 1-min entry delay (resolver)
