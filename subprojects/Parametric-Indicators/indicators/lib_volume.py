"""volume-school indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py.

Mostly stances = sign of a money-flow line vs its own smoothing; vzo / volume_ratio_asia are zones."""
from __future__ import annotations

import numpy as np

from . import classic, votes
from .base import Indicator
from .calc import volume as VO
from .stances import StanceIndicator, _sign_stance


class AdLine(StanceIndicator):
    key = "ad_line"
    def stance(self, ctx):
        ad = VO.ad_line(ctx.high, ctx.low, ctx.close, ctx.volume)
        return _sign_stance(ad - classic.sma(ad, int(self.config.params.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class CMF(StanceIndicator):
    key = "cmf"
    def stance(self, ctx):
        return _sign_stance(VO.cmf(ctx.high, ctx.low, ctx.close, ctx.volume, int(self.config.params.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class ChaikinOsc(StanceIndicator):
    key = "chaikin_osc"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(VO.chaikin_osc(ctx.high, ctx.low, ctx.close, ctx.volume,
                                           int(p.get("fast", 3)), int(p.get("slow", 10))))
    def warmup_bars(self): return int(self.config.params.get("slow", 10))


class PVT(StanceIndicator):
    key = "pvt"
    def stance(self, ctx):
        p = VO.pvt(ctx.close, ctx.volume)
        return _sign_stance(p - classic.sma(p, int(self.config.params.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class TVI(StanceIndicator):
    key = "tvi"
    def stance(self, ctx):
        p = self.config.params
        t = VO.tvi(ctx.close, ctx.volume, float(p.get("min_tick", 0.01)))
        return _sign_stance(t - classic.sma(t, int(p.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class NVI(StanceIndicator):
    key = "nvi"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 255))
        line = VO.nvi(ctx.close, ctx.volume)
        return _sign_stance(line - classic.ema(line, n))
    def warmup_bars(self): return int(self.config.params.get("n", 255))


class PVI(StanceIndicator):
    key = "pvi"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 255))
        line = VO.pvi(ctx.close, ctx.volume)
        return _sign_stance(line - classic.ema(line, n))
    def warmup_bars(self): return int(self.config.params.get("n", 255))


class EOM(StanceIndicator):
    key = "eom"
    def stance(self, ctx):
        return _sign_stance(VO.eom(ctx.high, ctx.low, ctx.volume, int(self.config.params.get("n", 14))))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class ForceIndex(StanceIndicator):
    key = "force_index"
    def stance(self, ctx):
        return _sign_stance(VO.force_index(ctx.close, ctx.volume, int(self.config.params.get("n", 13))))
    def warmup_bars(self): return int(self.config.params.get("n", 13))


class Klinger(StanceIndicator):
    key = "klinger"
    def stance(self, ctx):
        p = self.config.params
        kvo, sig = VO.klinger(ctx.high, ctx.low, ctx.close, ctx.volume,
                              int(p.get("fast", 34)), int(p.get("slow", 55)), int(p.get("signal", 13)))
        return _sign_stance(kvo - sig)
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("slow", 55)) + int(p.get("signal", 13))


class VolOsc(StanceIndicator):
    key = "vol_osc"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(VO.vol_osc(ctx.volume, int(p.get("fast", 5)), int(p.get("slow", 20))))
    def warmup_bars(self): return int(self.config.params.get("slow", 20))


class DemandIndex(StanceIndicator):
    key = "demand_index"
    def stance(self, ctx):
        return _sign_stance(VO.demand_index(ctx.close, ctx.volume, int(self.config.params.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class TwiggsMF(StanceIndicator):
    key = "twiggs_mf"
    def stance(self, ctx):
        return _sign_stance(VO.twiggs_mf(ctx.high, ctx.low, ctx.close, ctx.volume, int(self.config.params.get("n", 21))))
    def warmup_bars(self): return int(self.config.params.get("n", 21))


class WVAD(StanceIndicator):
    key = "wvad"
    def stance(self, ctx):
        return _sign_stance(VO.wvad(ctx.open, ctx.high, ctx.low, ctx.close, ctx.volume, int(self.config.params.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class BWMFI(StanceIndicator):
    key = "bw_mfi"
    def stance(self, ctx): return _sign_stance(VO.bw_mfi(ctx.high, ctx.low, ctx.volume))
    def warmup_bars(self): return 1


class AnchoredVWAP(StanceIndicator):
    key = "anchored_vwap"
    def stance(self, ctx):
        sess = ctx.session_id if ctx.session_id is not None else np.zeros(len(ctx.close), dtype=int)
        av = VO.anchored_vwap(ctx.high, ctx.low, ctx.close, ctx.volume, sess)
        return _sign_stance(ctx.close - av)
    def warmup_bars(self): return 1


class VZO(Indicator):
    key = "vzo"
    def directions(self, ctx):
        p = self.config.params
        v = VO.vzo(ctx.close, ctx.volume, int(p.get("n", 14)))
        return votes.band_directions(v, float(p.get("lower", -40)), float(p.get("upper", 40)), 0.0)
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class VolumeRatioAsia(Indicator):
    key = "volume_ratio_asia"
    def directions(self, ctx):
        p = self.config.params
        v = VO.volume_ratio_asia(ctx.close, ctx.volume, int(p.get("n", 26)))
        return votes.band_directions(v, float(p.get("lower", 70)), float(p.get("upper", 150)), 100.0)
    def warmup_bars(self): return int(self.config.params.get("n", 26))


CLASSES = (
    AdLine, CMF, ChaikinOsc, PVT, TVI, NVI, PVI, EOM, ForceIndex, Klinger, VolOsc, DemandIndex,
    TwiggsMF, WVAD, BWMFI, AnchoredVWAP, VZO, VolumeRatioAsia,
)

_N = lambda d, lo=2, hi=200: [{"name": "n", "default": d, "min": lo, "max": hi, "step": 1}]  # noqa: E731
SCHEMA = {
    "ad_line": {"label": "Accumulation/Distribution Line", "mode": "confirm", "params": _N(20)},
    "cmf": {"label": "Chaikin Money Flow", "mode": "confirm", "params": _N(20)},
    "chaikin_osc": {"label": "Chaikin Oscillator", "mode": "confirm",
                    "params": [{"name": "fast", "default": 3, "min": 2, "max": 50, "step": 1},
                               {"name": "slow", "default": 10, "min": 2, "max": 100, "step": 1}]},
    "pvt": {"label": "Price Volume Trend", "mode": "confirm", "params": _N(20)},
    "tvi": {"label": "Trade Volume Index", "mode": "confirm",
            "params": [{"name": "min_tick", "default": 0.01, "min": 0.0, "max": 5.0, "step": 0.01}] + _N(20)},
    "nvi": {"label": "Negative Volume Index", "mode": "confirm", "params": _N(255, 2, 400)},
    "pvi": {"label": "Positive Volume Index", "mode": "confirm", "params": _N(255, 2, 400)},
    "eom": {"label": "Ease of Movement", "mode": "confirm", "params": _N(14)},
    "force_index": {"label": "Force Index", "mode": "confirm", "params": _N(13)},
    "klinger": {"label": "Klinger Volume Oscillator", "mode": "confirm",
                "params": [{"name": "fast", "default": 34, "min": 2, "max": 100, "step": 1},
                           {"name": "slow", "default": 55, "min": 2, "max": 200, "step": 1},
                           {"name": "signal", "default": 13, "min": 1, "max": 100, "step": 1}]},
    "vol_osc": {"label": "Volume Oscillator", "mode": "confirm",
                "params": [{"name": "fast", "default": 5, "min": 2, "max": 100, "step": 1},
                           {"name": "slow", "default": 20, "min": 2, "max": 200, "step": 1}]},
    "demand_index": {"label": "Demand Index", "mode": "confirm", "params": _N(20)},
    "twiggs_mf": {"label": "Twiggs Money Flow", "mode": "confirm", "params": _N(21)},
    "wvad": {"label": "Williams VAD", "mode": "confirm", "params": _N(20)},
    "bw_mfi": {"label": "BW Market Facilitation Index", "mode": "confirm", "params": []},
    "anchored_vwap": {"label": "Anchored VWAP", "mode": "confirm", "params": []},
    "vzo": {"label": "Volume Zone Oscillator", "mode": "both",
            "params": _N(14, 2, 100) + [{"name": "lower", "default": -40, "min": -99, "max": -1, "step": 1},
                                        {"name": "upper", "default": 40, "min": 1, "max": 99, "step": 1}]},
    "volume_ratio_asia": {"label": "Volume Ratio (VR)", "mode": "both",
                          "params": _N(26, 2, 200) + [{"name": "lower", "default": 70, "min": 1, "max": 99, "step": 1},
                                                      {"name": "upper", "default": 150, "min": 101, "max": 400, "step": 1}]},
}
