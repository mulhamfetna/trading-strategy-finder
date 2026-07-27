"""Shared stance base class, extracted from library.py so per-school lib_* modules can subclass it
without a circular import (library.py imports the lib_* modules, which import StanceIndicator here).

Imports only base + votes (both cycle-free): base defines Indicator/MarketContext; votes maps a raw
stance to (confirm_dir, veto_dir)."""
from __future__ import annotations

import numpy as np

from . import votes
from .base import Indicator, MarketContext


def _sign_stance(x: np.ndarray) -> np.ndarray:
    """sign with NaN→0, as int8 stance."""
    s = np.zeros(len(x), dtype=np.int8)
    a = np.asarray(x, dtype=float)
    s[a > 0] = 1
    s[a < 0] = -1
    return s


class StanceIndicator(Indicator):
    """Indicators whose vote is a plain bullish/bearish stance."""
    def stance(self, ctx: MarketContext) -> np.ndarray:
        raise NotImplementedError

    def directions(self, ctx: MarketContext):
        return votes.stance_directions(self.stance(ctx))
