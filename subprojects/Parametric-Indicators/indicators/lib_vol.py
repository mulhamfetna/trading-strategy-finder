"""vol-school indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py.

Volatility indicators as VETOes (the box strategy is vol-seeking → veto LOW-vol / chop):
  * _MagVeto  — magnitude vs its own EMA: veto BOTH where value/ref < threshold.
  * _BandVeto — veto BOTH when price breaks outside the band (overextension).
  * bounded   — choppiness / mass-index / squeeze veto BOTH on their natural threshold.
Plus donchian (stance) and rvi_dorsey (zone)."""
from __future__ import annotations

import numpy as np

from . import votes
from .base import Indicator
from .calc import osc, vol as V
from .stances import StanceIndicator, _sign_stance


class _MagVeto(Indicator):
    """Veto BOTH sides where value / EMA(value, m) < threshold (low-activity chop)."""
    def _value(self, ctx):
        raise NotImplementedError

    def directions(self, ctx):
        p = self.config.params
        val = self._value(ctx)
        ref = osc.nan_ema(val, int(p.get("m", 50)))
        return votes.magnitude_veto(val, ref, float(p.get("threshold", 0.8)))

    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 20)) + int(p.get("m", 50))


class _BandVeto(Indicator):
    """Veto BOTH sides when price closes outside [lower, upper]."""
    def _bands(self, ctx):
        raise NotImplementedError

    def directions(self, ctx):
        u, lo = self._bands(ctx)
        c = ctx.close
        veto = np.isfinite(u) & np.isfinite(lo) & ((c > u) | (c < lo))
        return votes.both_veto(veto)


# ---- magnitude-veto vols ----
class ATRNorm(_MagVeto):
    key = "atr_norm"
    def _value(self, ctx): return V.atr_norm(ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 14)))


class StdDev(_MagVeto):
    key = "stddev"
    def _value(self, ctx): return V.stddev(ctx.close, int(self.config.params.get("n", 20)))


class HistVol(_MagVeto):
    key = "hist_vol"
    def _value(self, ctx): return V.hist_vol(ctx.close, int(self.config.params.get("n", 20)))


class Parkinson(_MagVeto):
    key = "parkinson"
    def _value(self, ctx): return V.parkinson(ctx.high, ctx.low, int(self.config.params.get("n", 20)))


class GarmanKlass(_MagVeto):
    key = "garman_klass"
    def _value(self, ctx): return V.garman_klass(ctx.open, ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 20)))


class RogersSatchell(_MagVeto):
    key = "rogers_satchell"
    def _value(self, ctx): return V.rogers_satchell(ctx.open, ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 20)))


class YangZhang(_MagVeto):
    key = "yang_zhang"
    def _value(self, ctx): return V.yang_zhang(ctx.open, ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 20)))


class Ulcer(_MagVeto):
    key = "ulcer"
    def _value(self, ctx): return V.ulcer(ctx.close, int(self.config.params.get("n", 14)))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 14)) + int(p.get("m", 50))


class VolRatio(_MagVeto):
    key = "vol_ratio"
    def _value(self, ctx):
        p = self.config.params
        return V.vol_ratio(ctx.high, ctx.low, ctx.close, int(p.get("n_fast", 5)), int(p.get("n_slow", 20)))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n_slow", 20)) + int(p.get("m", 50))


# ---- band-veto vols ----
class STARC(_BandVeto):
    key = "starc"
    def _bands(self, ctx):
        p = self.config.params
        return V.starc(ctx.high, ctx.low, ctx.close, int(p.get("n", 15)), float(p.get("m", 2.0)))
    def warmup_bars(self): return int(self.config.params.get("n", 15))


class AccelBands(_BandVeto):
    key = "accel_bands"
    def _bands(self, ctx):
        p = self.config.params
        return V.accel_bands(ctx.high, ctx.low, ctx.close, int(p.get("n", 20)), float(p.get("f", 4.0)))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class ProjBands(_BandVeto):
    key = "proj_bands"
    def _bands(self, ctx):
        return V.proj_bands(ctx.high, ctx.low, int(self.config.params.get("n", 14)))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


# ---- bounded / 0-centred vetoes ----
class ChaikinVol(Indicator):
    key = "chaikin_vol"
    def directions(self, ctx):
        p = self.config.params
        cv = V.chaikin_vol(ctx.high, ctx.low, int(p.get("n", 10)), int(p.get("roc_n", 10)))
        return votes.both_veto(np.isfinite(cv) & (cv < float(p.get("threshold", -10.0))))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 10)) + int(p.get("roc_n", 10))


class MassIndex(Indicator):
    key = "mass_index"
    def directions(self, ctx):
        p = self.config.params
        mi = V.mass_index(ctx.high, ctx.low, int(p.get("n", 25)))
        return votes.both_veto(np.isfinite(mi) & (mi > float(p.get("threshold", 27.0))))
    def warmup_bars(self): return int(self.config.params.get("n", 25)) + 18


class Choppiness(Indicator):
    key = "choppiness"
    def directions(self, ctx):
        p = self.config.params
        ch = V.choppiness(ctx.high, ctx.low, ctx.close, int(p.get("n", 14)))
        return votes.both_veto(np.isfinite(ch) & (ch >= float(p.get("threshold", 61.8))))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class TTMSqueeze(Indicator):
    key = "ttm_squeeze"
    def directions(self, ctx):
        sq = V.ttm_squeeze(ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 20)))
        return votes.both_veto(sq > 0.5)
    def warmup_bars(self): return int(self.config.params.get("n", 20))


# ---- stance / zone ----
class Donchian(StanceIndicator):
    key = "donchian"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 20))
        m = (V._roll_max(ctx.high, n) + V._roll_min(ctx.low, n)) / 2.0
        return _sign_stance(ctx.close - m)
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class RVIDorsey(Indicator):
    key = "rvi_dorsey"
    def directions(self, ctx):
        p = self.config.params
        v = V.rvi_dorsey(ctx.close, int(p.get("n", 14)))
        return votes.band_directions(v, float(p.get("lower", 30)), float(p.get("upper", 70)), 50.0)
    def warmup_bars(self): return int(self.config.params.get("n", 14)) + 10


CLASSES = (
    ATRNorm, StdDev, HistVol, Parkinson, GarmanKlass, RogersSatchell, YangZhang, Ulcer, VolRatio,
    STARC, AccelBands, ProjBands, ChaikinVol, MassIndex, Choppiness, TTMSqueeze, Donchian, RVIDorsey,
)

_MV = lambda ndef=20: [{"name": "n", "default": ndef, "min": 2, "max": 200, "step": 1},  # noqa: E731
                       {"name": "m", "default": 50, "min": 2, "max": 200, "step": 1},
                       {"name": "threshold", "default": 0.8, "min": 0.2, "max": 1.5, "step": 0.05}]
SCHEMA = {
    "atr_norm": {"label": "Normalized ATR (veto)", "mode": "veto", "params": _MV(14)},
    "stddev": {"label": "Std Dev (veto)", "mode": "veto", "params": _MV(20)},
    "hist_vol": {"label": "Historical Vol (veto)", "mode": "veto", "params": _MV(20)},
    "parkinson": {"label": "Parkinson Vol (veto)", "mode": "veto", "params": _MV(20)},
    "garman_klass": {"label": "Garman-Klass Vol (veto)", "mode": "veto", "params": _MV(20)},
    "rogers_satchell": {"label": "Rogers-Satchell Vol (veto)", "mode": "veto", "params": _MV(20)},
    "yang_zhang": {"label": "Yang-Zhang Vol (veto)", "mode": "veto", "params": _MV(20)},
    "ulcer": {"label": "Ulcer Index (veto)", "mode": "veto", "params": _MV(14)},
    "vol_ratio": {"label": "Volatility Ratio (veto)", "mode": "veto",
                  "params": [{"name": "n_fast", "default": 5, "min": 2, "max": 100, "step": 1},
                             {"name": "n_slow", "default": 20, "min": 2, "max": 200, "step": 1},
                             {"name": "m", "default": 50, "min": 2, "max": 200, "step": 1},
                             {"name": "threshold", "default": 0.8, "min": 0.2, "max": 1.5, "step": 0.05}]},
    "starc": {"label": "STARC Bands (veto)", "mode": "veto",
              "params": [{"name": "n", "default": 15, "min": 2, "max": 200, "step": 1},
                         {"name": "m", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1}]},
    "accel_bands": {"label": "Acceleration Bands (veto)", "mode": "veto",
                    "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1},
                               {"name": "f", "default": 4.0, "min": 1.0, "max": 10.0, "step": 0.5}]},
    "proj_bands": {"label": "Projection Bands (veto)", "mode": "veto",
                   "params": [{"name": "n", "default": 14, "min": 2, "max": 200, "step": 1}]},
    "chaikin_vol": {"label": "Chaikin Volatility (veto)", "mode": "veto",
                    "params": [{"name": "n", "default": 10, "min": 2, "max": 100, "step": 1},
                               {"name": "roc_n", "default": 10, "min": 1, "max": 100, "step": 1},
                               {"name": "threshold", "default": -10.0, "min": -50.0, "max": 0.0, "step": 1.0}]},
    "mass_index": {"label": "Mass Index (veto)", "mode": "veto",
                   "params": [{"name": "n", "default": 25, "min": 2, "max": 100, "step": 1},
                              {"name": "threshold", "default": 27.0, "min": 20.0, "max": 35.0, "step": 0.5}]},
    "choppiness": {"label": "Choppiness Index (veto)", "mode": "veto",
                   "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1},
                              {"name": "threshold", "default": 61.8, "min": 30.0, "max": 80.0, "step": 0.1}]},
    "ttm_squeeze": {"label": "TTM Squeeze (veto)", "mode": "veto",
                    "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1}]},
    "donchian": {"label": "Donchian midline trend", "mode": "confirm",
                 "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1}]},
    "rvi_dorsey": {"label": "Relative Volatility Index", "mode": "both",
                   "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1},
                              {"name": "lower", "default": 30, "min": 1, "max": 49, "step": 1},
                              {"name": "upper", "default": 70, "min": 51, "max": 99, "step": 1}]},
}
