"""dsp-school (Tier-2) indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA."""
from __future__ import annotations

import numpy as np

from . import votes
from .base import Indicator
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


class LaguerreRSI(Indicator):
    key = "laguerre_rsi"
    def directions(self, ctx):
        p = self.config.params
        v = dsp.laguerre_rsi(ctx.close, float(p.get("gamma", 0.5)))
        return votes.band_directions(v, float(p.get("lower", 0.2)), float(p.get("upper", 0.8)), 0.5)
    def warmup_bars(self): return 10


class SchaffTC(Indicator):
    key = "schaff_trend_cycle"
    def directions(self, ctx):
        p = self.config.params
        v = dsp.schaff_trend_cycle(ctx.close, int(p.get("fast", 23)), int(p.get("slow", 50)), int(p.get("cycle", 10)))
        return votes.band_directions(v, float(p.get("lower", 25)), float(p.get("upper", 75)), 50.0)
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("slow", 50)) + 2 * int(p.get("cycle", 10))


class CyberCycle(StanceIndicator):
    key = "cyber_cycle"
    def stance(self, ctx): return _sign_stance(dsp.cyber_cycle(ctx.close, float(self.config.params.get("alpha", 0.07))))
    def warmup_bars(self): return 7


class CenterOfGravity(StanceIndicator):
    key = "center_of_gravity"
    def stance(self, ctx): return _sign_stance(dsp.center_of_gravity(ctx.close, int(self.config.params.get("n", 10))))
    def warmup_bars(self): return int(self.config.params.get("n", 10))


class Sinewave(StanceIndicator):
    """Ehlers Sine Wave: +1 when sine > leadsine (cycle up-phase), −1 otherwise."""
    key = "sinewave"
    def stance(self, ctx):
        sine, lead = dsp.hilbert_sinewave(ctx.close)
        return _sign_stance(sine - lead)
    def warmup_bars(self): return 20


class HilbertCycle(Indicator):
    """Veto BOTH sides when the measured dominant cycle period is very short (fast/unstable chop)."""
    key = "hilbert_cycle"
    def directions(self, ctx):
        per, _ = dsp.dominant_cycle(ctx.close)
        thr = float(self.config.params.get("threshold", 10.0))
        return votes.both_veto((per > 0) & (per < thr))
    def warmup_bars(self): return 20


CLASSES = (SuperSmootherTrend, RoofingOsc, BandpassOsc, FRAMATrend, MAMAFAMATrend,
           LaguerreRSI, SchaffTC, CyberCycle, CenterOfGravity, Sinewave, HilbertCycle)
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
    "laguerre_rsi": {"label": "Laguerre RSI", "mode": "both",
                     "params": [{"name": "gamma", "default": 0.5, "min": 0.1, "max": 0.9, "step": 0.05},
                                {"name": "lower", "default": 0.2, "min": 0.05, "max": 0.45, "step": 0.05},
                                {"name": "upper", "default": 0.8, "min": 0.55, "max": 0.95, "step": 0.05}]},
    "schaff_trend_cycle": {"label": "Schaff Trend Cycle", "mode": "both",
                           "params": [{"name": "fast", "default": 23, "min": 2, "max": 100, "step": 1},
                                      {"name": "slow", "default": 50, "min": 2, "max": 200, "step": 1},
                                      {"name": "cycle", "default": 10, "min": 2, "max": 50, "step": 1},
                                      {"name": "lower", "default": 25, "min": 1, "max": 49, "step": 1},
                                      {"name": "upper", "default": 75, "min": 51, "max": 99, "step": 1}]},
    "cyber_cycle": {"label": "Ehlers Cyber Cycle", "mode": "confirm",
                    "params": [{"name": "alpha", "default": 0.07, "min": 0.01, "max": 0.5, "step": 0.01}]},
    "center_of_gravity": {"label": "Ehlers Center of Gravity", "mode": "confirm",
                          "params": [{"name": "n", "default": 10, "min": 2, "max": 100, "step": 1}]},
    "sinewave": {"label": "Ehlers Sine Wave", "mode": "confirm", "params": []},
    "hilbert_cycle": {"label": "Hilbert dominant-cycle (veto)", "mode": "veto",
                      "params": [{"name": "threshold", "default": 10.0, "min": 6.0, "max": 30.0, "step": 1.0}]},
}
