"""Cross-series (Tier-2) indicator classes — primary vs an aligned reference instrument.
All read ctx.ref_close; when it is None (no reference wired) they emit NO votes ⇒ existing parity holds.
CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py."""
from __future__ import annotations

import numpy as np

from . import votes
from .base import Indicator
from .calc import osc, xseries as xs
from .stances import StanceIndicator, _sign_stance

_NEUTRAL2 = None  # sentinel unused; explicit zeros below for clarity


class _NeedsRef:
    """Mixin: True when a usable reference close is present."""
    @staticmethod
    def _ref(ctx):
        return ctx.ref_close if getattr(ctx, "ref_close", None) is not None else None


class RollingCorr(Indicator, _NeedsRef):
    """Veto BOTH sides when primary↔reference return correlation is low (reference decoupled ⇒ its
    signal is unreliable). |corr| below threshold ⇒ veto."""
    key = "rolling_corr"
    needs_ref = True
    def directions(self, ctx):
        r = self._ref(ctx)
        n = len(ctx.close)
        if r is None:
            return np.zeros(n, np.int8), np.zeros(n, np.int8)
        p = self.config.params
        corr = xs.rolling_corr(ctx.close, r, int(p.get("n", 50)))
        return votes.both_veto(np.isfinite(corr) & (np.abs(corr) < float(p.get("threshold", 0.3))))
    def warmup_bars(self): return int(self.config.params.get("n", 50))


class RollingBeta(StanceIndicator, _NeedsRef):
    """Beta-scaled reference lead: sign(beta · reference's recent move) — expect the primary to follow."""
    key = "rolling_beta"
    needs_ref = True
    def stance(self, ctx):
        r = self._ref(ctx)
        if r is None:
            return np.zeros(len(ctx.close), np.int8)
        p = self.config.params
        n, lag = int(p.get("n", 50)), int(p.get("lag", 5))
        beta = xs.rolling_beta(ctx.close, r, n)
        refret = r - osc._shift(r, lag)
        return _sign_stance(beta * refret)
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 50)) + int(p.get("lag", 5))


class Cointegration(Indicator, _NeedsRef):
    """Pair spread z-score (mean-reversion): z≥upper ⇒ primary rich vs reference → short; z≤lower → long."""
    key = "cointegration"
    needs_ref = True
    def directions(self, ctx):
        r = self._ref(ctx)
        n = len(ctx.close)
        if r is None:
            return np.zeros(n, np.int8), np.zeros(n, np.int8)
        p = self.config.params
        z = xs.spread_zscore(ctx.close, r, int(p.get("n", 50)))
        return votes.band_directions(z, float(p.get("lower", -2)), float(p.get("upper", 2)), 0.0)
    def warmup_bars(self): return int(self.config.params.get("n", 50))


class PCAFactor(StanceIndicator, _NeedsRef):
    """2-series PCA common-factor direction: sign of the primary's projection on PC1 of [primary,ref] returns."""
    key = "pca_factor"
    needs_ref = True
    def stance(self, ctx):
        r = self._ref(ctx)
        if r is None:
            return np.zeros(len(ctx.close), np.int8)
        return _sign_stance(xs.pca_factor(ctx.close, r, int(self.config.params.get("n", 50))))
    def warmup_bars(self): return int(self.config.params.get("n", 50))


CLASSES = (RollingCorr, RollingBeta, Cointegration, PCAFactor)
SCHEMA = {
    "rolling_corr": {"label": "Cross-corr (veto decoupled)", "mode": "veto",
                     "params": [{"name": "n", "default": 50, "min": 5, "max": 300, "step": 1},
                                {"name": "threshold", "default": 0.3, "min": 0.0, "max": 0.95, "step": 0.05}]},
    "rolling_beta": {"label": "Cross-beta lead", "mode": "confirm",
                     "params": [{"name": "n", "default": 50, "min": 5, "max": 300, "step": 1},
                                {"name": "lag", "default": 5, "min": 1, "max": 50, "step": 1}]},
    "cointegration": {"label": "Pair spread z-score", "mode": "both",
                      "params": [{"name": "n", "default": 50, "min": 10, "max": 300, "step": 1},
                                 {"name": "lower", "default": -2, "min": -5, "max": -1, "step": 1},
                                 {"name": "upper", "default": 2, "min": 1, "max": 5, "step": 1}]},
    "pca_factor": {"label": "PCA common-factor direction", "mode": "confirm",
                   "params": [{"name": "n", "default": 50, "min": 5, "max": 300, "step": 1}]},
}
