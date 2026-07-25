"""tier2-misc (approximate/stateful) indicator classes. Merged into library.REGISTRY/SCHEMA."""
from __future__ import annotations

import numpy as np

from . import votes
from .base import Indicator
from .calc import osc, tier2 as T2
from .stances import StanceIndicator, _sign_stance


class JMATrend(StanceIndicator):
    """Jurik MA (approx) trend: sign(close − JMA)."""
    key = "jma"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(ctx.close - T2.jma(ctx.close, int(p.get("length", 14)),
                                               float(p.get("phase", 0)), int(p.get("power", 2))))
    def warmup_bars(self): return int(self.config.params.get("length", 14))


class GarchEWMA(Indicator):
    """EWMA (RiskMetrics) volatility as a vol-seeking veto (block low-vol chop)."""
    key = "garch_ewma"
    def directions(self, ctx):
        p = self.config.params
        val = T2.ewma_vol(ctx.close, float(p.get("lam", 0.94)))
        ref = osc.nan_ema(val, int(p.get("m", 50)))
        return votes.magnitude_veto(val, ref, float(p.get("threshold", 0.8)))
    def warmup_bars(self): return int(self.config.params.get("m", 50)) + 2


class EMDMode(StanceIndicator):
    """Ehlers EMD trend/cycle mode: +1 mean>avg-peak (uptrend), −1 mean<avg-valley, else 0 (cycle)."""
    key = "emd"
    def stance(self, ctx):
        p = self.config.params
        mean, apeak, avalley = T2.ehlers_emd(ctx.high, ctx.low, int(p.get("period", 20)), float(p.get("bandwidth", 0.3)))
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[np.isfinite(mean) & (mean > apeak)] = 1
        st[np.isfinite(mean) & (mean < avalley)] = -1
        return st
    def warmup_bars(self): return 2 * int(self.config.params.get("period", 20))


class TDSequential(StanceIndicator):
    """DeMark TD Setup: +1 on a 9-bar buy setup (reversal up), −1 on a 9-bar sell setup."""
    key = "td_sequential"
    def stance(self, ctx): return _sign_stance(T2.td_sequential(ctx.close))
    def warmup_bars(self): return 9


class TDCombo(StanceIndicator):
    """DeMark TD Setup with perfection (bar 8/9 extreme)."""
    key = "td_combo"
    def stance(self, ctx): return _sign_stance(T2.td_combo(ctx.close))
    def warmup_bars(self): return 9


class KalmanTrend(StanceIndicator):
    """1-D random-walk Kalman smoother trend: sign(close − Kalman)."""
    key = "kalman"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(ctx.close - T2.kalman(ctx.close, float(p.get("q", 0.001)), float(p.get("r", 0.1))))
    def warmup_bars(self): return 5


class OUHalflife(Indicator):
    """Veto BOTH sides when the OU coefficient b ≥ 0 (no mean-reversion structure / random walk)."""
    key = "ou_halflife"
    def directions(self, ctx):
        n = int(self.config.params.get("n", 50))
        b = T2.ou_coefficient(ctx.close, n)
        return votes.both_veto(np.isfinite(b) & (b >= 0))
    def warmup_bars(self): return int(self.config.params.get("n", 50))


CLASSES = (JMATrend, GarchEWMA, EMDMode, TDSequential, TDCombo, KalmanTrend, OUHalflife)
SCHEMA = {
    "jma": {"label": "Jurik MA (approx) trend", "mode": "confirm",
            "params": [{"name": "length", "default": 14, "min": 2, "max": 200, "step": 1},
                       {"name": "phase", "default": 0, "min": -100, "max": 100, "step": 5},
                       {"name": "power", "default": 2, "min": 1, "max": 4, "step": 1}]},
    "garch_ewma": {"label": "EWMA volatility (veto)", "mode": "veto",
                   "params": [{"name": "lam", "default": 0.94, "min": 0.8, "max": 0.99, "step": 0.01},
                              {"name": "m", "default": 50, "min": 2, "max": 200, "step": 1},
                              {"name": "threshold", "default": 0.8, "min": 0.2, "max": 1.5, "step": 0.05}]},
    "emd": {"label": "Ehlers EMD (trend/cycle mode)", "mode": "confirm",
            "params": [{"name": "period", "default": 20, "min": 4, "max": 100, "step": 1},
                       {"name": "bandwidth", "default": 0.3, "min": 0.1, "max": 0.9, "step": 0.05}]},
    "td_sequential": {"label": "TD Sequential (setup)", "mode": "both", "params": []},
    "td_combo": {"label": "TD Combo (perfected setup)", "mode": "both", "params": []},
    "kalman": {"label": "Kalman trend", "mode": "confirm",
               "params": [{"name": "q", "default": 0.001, "min": 0.0001, "max": 1.0, "step": 0.0001},
                          {"name": "r", "default": 0.1, "min": 0.001, "max": 10.0, "step": 0.01}]},
    "ou_halflife": {"label": "OU half-life (veto no-reversion)", "mode": "veto",
                    "params": [{"name": "n", "default": 50, "min": 10, "max": 300, "step": 1}]},
}
