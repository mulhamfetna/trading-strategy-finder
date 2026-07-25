"""bw-school indicator classes (Bill Williams + Elliott Wave Oscillator).
CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py."""
from __future__ import annotations

import numpy as np

from .calc import bw as BW, osc
from .stances import StanceIndicator, _sign_stance


class Alligator(StanceIndicator):
    """+1 when lips>teeth>jaw (bullish alignment), -1 when lips<teeth<jaw."""
    key = "alligator"
    def stance(self, ctx):
        jaw, teeth, lips = BW.alligator(ctx.high, ctx.low)
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[(lips > teeth) & (teeth > jaw)] = 1
        st[(lips < teeth) & (teeth < jaw)] = -1
        return st
    def warmup_bars(self): return 21


class Fractals(StanceIndicator):
    """Breakout of the last confirmed Williams fractal: +1 above up-fractal, -1 below down-fractal."""
    key = "fractals"
    def stance(self, ctx):
        up, dn = BW.fractal_levels(ctx.high, ctx.low)
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[np.isfinite(up) & (ctx.close > up)] = 1
        st[np.isfinite(dn) & (ctx.close < dn)] = -1
        return st
    def warmup_bars(self): return 5


class AwesomeOsc(StanceIndicator):
    key = "awesome_osc"
    def stance(self, ctx): return _sign_stance(BW.awesome((ctx.high + ctx.low) / 2.0))
    def warmup_bars(self): return 34


class AccelOsc(StanceIndicator):
    key = "accel_osc"
    def stance(self, ctx): return _sign_stance(BW.accel((ctx.high + ctx.low) / 2.0))
    def warmup_bars(self): return 39


class Gator(StanceIndicator):
    """Alligator direction, gated to only vote while BOTH gator gaps are expanding (trending)."""
    key = "gator"
    def stance(self, ctx):
        jaw, teeth, lips = BW.alligator(ctx.high, ctx.low)
        upper = np.abs(jaw - teeth)
        lower = np.abs(teeth - lips)
        expanding = (upper > osc._shift(upper, 1)) & (lower > osc._shift(lower, 1))
        st = np.zeros(len(ctx.close), dtype=np.int8)
        direction = np.sign(lips - jaw)
        st[expanding & (direction > 0)] = 1
        st[expanding & (direction < 0)] = -1
        return st
    def warmup_bars(self): return 21


class ElliottWaveOsc(StanceIndicator):
    key = "elliott_wave_osc"
    def stance(self, ctx): return _sign_stance(BW.ewo(ctx.close))
    def warmup_bars(self): return 34


CLASSES = (Alligator, Fractals, AwesomeOsc, AccelOsc, Gator, ElliottWaveOsc)
SCHEMA = {
    "alligator": {"label": "Alligator", "mode": "confirm", "params": []},
    "fractals": {"label": "Williams Fractals", "mode": "confirm", "params": []},
    "awesome_osc": {"label": "Awesome Oscillator", "mode": "confirm", "params": []},
    "accel_osc": {"label": "Accelerator Oscillator", "mode": "confirm", "params": []},
    "gator": {"label": "Gator Oscillator", "mode": "confirm", "params": []},
    "elliott_wave_osc": {"label": "Elliott Wave Oscillator", "mode": "confirm", "params": []},
}
