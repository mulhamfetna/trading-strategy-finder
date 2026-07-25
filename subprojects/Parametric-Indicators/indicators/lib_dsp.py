"""dsp-school (Tier-2) indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA."""
from __future__ import annotations

import numpy as np

from .calc import dsp
from .stances import StanceIndicator, _sign_stance


class SuperSmootherTrend(StanceIndicator):
    """Ehlers SuperSmoother trend: sign(close − SuperSmoother(close, n))."""
    key = "super_smoother"
    def stance(self, ctx):
        return _sign_stance(ctx.close - dsp.super_smoother(ctx.close, int(self.config.params.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class RoofingOsc(StanceIndicator):
    """Ehlers Roofing Filter cycle: +1 above zero, −1 below (band-limited oscillator)."""
    key = "roofing"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(dsp.roofing(ctx.close, int(p.get("hp_period", 48)), int(p.get("lp_period", 10))))
    def warmup_bars(self): return int(self.config.params.get("hp_period", 48))


class BandpassOsc(StanceIndicator):
    """Ehlers Band-Pass cycle: +1 above zero, −1 below."""
    key = "bandpass"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(dsp.bandpass(ctx.close, int(p.get("period", 20)), float(p.get("bandwidth", 0.3))))
    def warmup_bars(self): return 2 * int(self.config.params.get("period", 20))


class FRAMATrend(StanceIndicator):
    """Fractal Adaptive MA trend: sign(close − FRAMA(n))."""
    key = "frama"
    def stance(self, ctx):
        return _sign_stance(ctx.close - dsp.frama(ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 16))))
    def warmup_bars(self): return int(self.config.params.get("n", 16)) + 1


class MAMAFAMATrend(StanceIndicator):
    """MESA Adaptive MA cross: +1 when MAMA>FAMA (uptrend), −1 when MAMA<FAMA."""
    key = "mama_fama"
    def stance(self, ctx):
        p = self.config.params
        mama, fama = dsp.mama_fama(ctx.close, float(p.get("fast", 0.5)), float(p.get("slow", 0.05)))
        return _sign_stance(mama - fama)
    def warmup_bars(self): return 20


CLASSES = (SuperSmootherTrend, RoofingOsc, BandpassOsc, FRAMATrend, MAMAFAMATrend)
SCHEMA = {
    "super_smoother": {"label": "Ehlers SuperSmoother trend", "mode": "confirm",
                       "params": [{"name": "n", "default": 20, "min": 4, "max": 200, "step": 1}]},
    "roofing": {"label": "Ehlers Roofing Filter", "mode": "confirm",
                "params": [{"name": "hp_period", "default": 48, "min": 10, "max": 200, "step": 1},
                           {"name": "lp_period", "default": 10, "min": 4, "max": 100, "step": 1}]},
    "bandpass": {"label": "Ehlers Band-Pass", "mode": "confirm",
                 "params": [{"name": "period", "default": 20, "min": 4, "max": 200, "step": 1},
                            {"name": "bandwidth", "default": 0.3, "min": 0.1, "max": 0.9, "step": 0.05}]},
    "frama": {"label": "Fractal Adaptive MA trend", "mode": "confirm",
              "params": [{"name": "n", "default": 16, "min": 4, "max": 200, "step": 2}]},
    "mama_fama": {"label": "MESA Adaptive MA (MAMA/FAMA)", "mode": "confirm",
                  "params": [{"name": "fast", "default": 0.5, "min": 0.1, "max": 1.0, "step": 0.05},
                             {"name": "slow", "default": 0.05, "min": 0.01, "max": 0.5, "step": 0.01}]},
}
