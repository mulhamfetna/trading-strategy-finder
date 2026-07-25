"""quant-school indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py."""
from __future__ import annotations

import numpy as np

from . import votes
from .base import Indicator
from .calc import osc, quant as Q
from .stances import StanceIndicator, _sign_stance


class ZScore(Indicator):
    key = "zscore"
    def directions(self, ctx):
        p = self.config.params
        v = Q.zscore(ctx.close, int(p.get("n", 20)))
        return votes.band_directions(v, float(p.get("lower", -2)), float(p.get("upper", 2)), 0.0)
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class DeMarker(Indicator):
    key = "demarker"
    def directions(self, ctx):
        p = self.config.params
        v = Q.demarker(ctx.high, ctx.low, int(p.get("n", 14)))
        return votes.band_directions(v, float(p.get("lower", 0.3)), float(p.get("upper", 0.7)), 0.5)
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class TDREI(Indicator):
    key = "td_rei"
    def directions(self, ctx):
        p = self.config.params
        v = Q.td_rei(ctx.high, ctx.low, 5)
        return votes.band_directions(v, float(p.get("lower", -40)), float(p.get("upper", 40)), 0.0)
    def warmup_bars(self): return 7


class HurstExp(Indicator):
    """Veto BOTH sides when Hurst < threshold (anti-persistent / mean-reverting chop)."""
    key = "hurst_exp"
    def directions(self, ctx):
        p = self.config.params
        v = Q.hurst_exp(ctx.close, int(p.get("n", 100)))
        return votes.both_veto(np.isfinite(v) & (v < float(p.get("threshold", 0.5))))
    def warmup_bars(self): return int(self.config.params.get("n", 100))


class DFA(Indicator):
    """Veto BOTH sides when DFA alpha < threshold (mean-reverting)."""
    key = "dfa"
    def directions(self, ctx):
        p = self.config.params
        v = Q.dfa(ctx.close, int(p.get("n", 100)))
        return votes.both_veto(np.isfinite(v) & (v < float(p.get("threshold", 0.5))))
    def warmup_bars(self): return int(self.config.params.get("n", 100))


class Autocorr(Indicator):
    """Veto BOTH sides when |lag-1 autocorr| < threshold (no linear structure)."""
    key = "autocorr"
    def directions(self, ctx):
        p = self.config.params
        v = Q.autocorr(ctx.close, int(p.get("n", 50)))
        return votes.both_veto(np.isfinite(v) & (np.abs(v) < float(p.get("threshold", 0.1))))
    def warmup_bars(self): return int(self.config.params.get("n", 50))


class LinRegR2(Indicator):
    """Veto BOTH sides when regression R² < threshold (no trend to ride)."""
    key = "linreg_r2"
    def directions(self, ctx):
        p = self.config.params
        v = Q.linreg_r2(ctx.close, int(p.get("n", 20)))
        return votes.both_veto(np.isfinite(v) & (v < float(p.get("threshold", 0.2))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class EfficiencyRatio(StanceIndicator):
    """Kaufman efficiency ratio as a directional filter: vote the net direction only when ER>threshold."""
    key = "efficiency_ratio"
    def stance(self, ctx):
        p = self.config.params
        n = int(p.get("n", 10))
        thr = float(p.get("threshold", 0.3))
        er = Q.efficiency_ratio(ctx.close, n)
        direction = np.sign(ctx.close - osc._shift(ctx.close, n))
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[np.isfinite(er) & (er > thr) & (direction > 0)] = 1
        st[np.isfinite(er) & (er > thr) & (direction < 0)] = -1
        return st
    def warmup_bars(self): return int(self.config.params.get("n", 10))


CLASSES = (ZScore, DeMarker, TDREI, HurstExp, DFA, Autocorr, LinRegR2, EfficiencyRatio)
SCHEMA = {
    "zscore": {"label": "Z-Score", "mode": "both",
               "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1},
                          {"name": "lower", "default": -2, "min": -5, "max": -1, "step": 1},
                          {"name": "upper", "default": 2, "min": 1, "max": 5, "step": 1}]},
    "demarker": {"label": "DeMarker", "mode": "both",
                 "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1},
                            {"name": "lower", "default": 0.3, "min": 0.05, "max": 0.49, "step": 0.01},
                            {"name": "upper", "default": 0.7, "min": 0.51, "max": 0.95, "step": 0.01}]},
    "td_rei": {"label": "TD Range Expansion Index", "mode": "both",
               "params": [{"name": "lower", "default": -40, "min": -99, "max": -1, "step": 1},
                          {"name": "upper", "default": 40, "min": 1, "max": 99, "step": 1}]},
    "hurst_exp": {"label": "Hurst Exponent (veto)", "mode": "veto",
                  "params": [{"name": "n", "default": 100, "min": 20, "max": 400, "step": 1},
                             {"name": "threshold", "default": 0.5, "min": 0.3, "max": 0.7, "step": 0.01}]},
    "dfa": {"label": "DFA exponent (veto)", "mode": "veto",
            "params": [{"name": "n", "default": 100, "min": 20, "max": 400, "step": 1},
                       {"name": "threshold", "default": 0.5, "min": 0.3, "max": 0.7, "step": 0.01}]},
    "autocorr": {"label": "Autocorrelation (veto)", "mode": "veto",
                 "params": [{"name": "n", "default": 50, "min": 5, "max": 200, "step": 1},
                            {"name": "threshold", "default": 0.1, "min": 0.0, "max": 0.5, "step": 0.01}]},
    "linreg_r2": {"label": "Linear-Reg R² (veto)", "mode": "veto",
                  "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1},
                             {"name": "threshold", "default": 0.2, "min": 0.0, "max": 0.9, "step": 0.01}]},
    "efficiency_ratio": {"label": "Kaufman Efficiency Ratio", "mode": "confirm",
                         "params": [{"name": "n", "default": 10, "min": 2, "max": 100, "step": 1},
                                    {"name": "threshold", "default": 0.3, "min": 0.0, "max": 1.0, "step": 0.05}]},
}
