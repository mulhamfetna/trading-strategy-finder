"""trend-school indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py."""
from __future__ import annotations

import numpy as np

from . import classic, votes
from .base import BOTH, LONG, SHORT, Indicator
from .calc import osc, trend as T
from .stances import StanceIndicator, _sign_stance


# ---------- simple signed-line stances ----------
class PPO(StanceIndicator):
    key = "ppo"
    def stance(self, ctx):
        p = self.config.params
        line = T.ppo(ctx.close, int(p.get("fast", 12)), int(p.get("slow", 26)))
        return _sign_stance(line - osc.nan_ema(line, int(p.get("signal", 9))))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("slow", 26)) + int(p.get("signal", 9))


class APO(StanceIndicator):
    key = "apo"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(T.apo(ctx.close, int(p.get("fast", 12)), int(p.get("slow", 26))))
    def warmup_bars(self): return int(self.config.params.get("slow", 26))


class DICross(StanceIndicator):
    key = "di_cross"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 14))
        pdi, mdi = T.plus_minus_di(ctx.high, ctx.low, ctx.close, n)
        return _sign_stance(pdi - mdi)
    def warmup_bars(self): return 2 * int(self.config.params.get("n", 14))


class Aroon(StanceIndicator):
    """Aroon strong-trend stance: +1 when up≥70 & dn≤30, -1 when dn≥70 & up≤30."""
    key = "aroon"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 25))
        up, dn = T.aroon(ctx.high, ctx.low, n)
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[(up >= 70) & (dn <= 30)] = 1
        st[(dn >= 70) & (up <= 30)] = -1
        return st
    def warmup_bars(self): return int(self.config.params.get("n", 25))


class AroonOsc(StanceIndicator):
    key = "aroon_osc"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 25))
        up, dn = T.aroon(ctx.high, ctx.low, n)
        return _sign_stance(up - dn)
    def warmup_bars(self): return int(self.config.params.get("n", 25))


class ParabolicSAR(StanceIndicator):
    key = "psar"
    def stance(self, ctx):
        p = self.config.params
        sar = T.psar(ctx.high, ctx.low, float(p.get("step", 0.02)), float(p.get("max", 0.2)))
        return _sign_stance(ctx.close - sar)
    def warmup_bars(self): return 2


class Vortex(StanceIndicator):
    key = "vortex"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 14))
        vp, vm = T.vortex(ctx.high, ctx.low, ctx.close, n)
        with np.errstate(invalid="ignore"):        # NaN/inf on warm-up/zero-range bars → neutral vote (no noisy RuntimeWarning)
            return _sign_stance(vp - vm)
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class Supertrend(StanceIndicator):
    key = "supertrend"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(T.supertrend(ctx.high, ctx.low, ctx.close,
                                         int(p.get("n", 10)), float(p.get("m", 3.0))))
    def warmup_bars(self): return int(self.config.params.get("n", 10))


class TRIX(StanceIndicator):
    key = "trix"
    def stance(self, ctx):
        p = self.config.params
        line = T.trix(ctx.close, int(p.get("n", 15)))
        return _sign_stance(line - osc.nan_ema(line, int(p.get("signal", 9))))
    def warmup_bars(self):
        p = self.config.params
        return 3 * int(p.get("n", 15)) + int(p.get("signal", 9))


class KST(StanceIndicator):
    key = "kst"
    def stance(self, ctx):
        line = T.kst(ctx.close)
        return _sign_stance(line - osc.nan_sma(line, int(self.config.params.get("signal", 9))))
    def warmup_bars(self): return 45


class Coppock(StanceIndicator):
    key = "coppock"
    def stance(self, ctx): return _sign_stance(T.coppock(ctx.close))
    def warmup_bars(self): return 24


class DPO(StanceIndicator):
    key = "dpo"
    def stance(self, ctx): return _sign_stance(T.dpo(ctx.close, int(self.config.params.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class LinRegSlope(StanceIndicator):
    key = "linreg_slope"
    def stance(self, ctx): return _sign_stance(T.linreg_slope(ctx.close, int(self.config.params.get("n", 14))))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class QQE(StanceIndicator):
    key = "qqe"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(T.qqe(ctx.close, int(p.get("n", 14)), int(p.get("sf", 5)), float(p.get("f", 4.236))))
    def warmup_bars(self): return 2 * int(self.config.params.get("n", 14))


class ASI(StanceIndicator):
    key = "asi"
    def stance(self, ctx):
        a = T.asi(ctx.open, ctx.high, ctx.low, ctx.close, float(self.config.params.get("limit", 3.0)))
        return _sign_stance(a - osc._shift(a, 1))
    def warmup_bars(self): return 1


class EXPMA(StanceIndicator):
    key = "expma"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(classic.ema(ctx.close, int(p.get("fast", 12))) - classic.ema(ctx.close, int(p.get("slow", 50))))
    def warmup_bars(self): return int(self.config.params.get("slow", 50))


class DMA(StanceIndicator):
    key = "dma"
    def stance(self, ctx):
        p = self.config.params
        ddd, ama = T.dma(ctx.close, int(p.get("fast", 10)), int(p.get("slow", 50)), int(p.get("m", 10)))
        return _sign_stance(ddd - ama)
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("slow", 50)) + int(p.get("m", 10))


class BBI(StanceIndicator):
    key = "bbi"
    def stance(self, ctx): return _sign_stance(ctx.close - T.bbi(ctx.close))
    def warmup_bars(self): return 24


class ElderRay(StanceIndicator):
    """+1 when bull power >0 and rising; -1 when bear power <0 and falling."""
    key = "elder_ray"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 13))
        bull, bear = T.elder_ray(ctx.high, ctx.low, ctx.close, n)
        pb, pbe = osc._shift(bull, 1), osc._shift(bear, 1)
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[(bull > 0) & (bull > pb)] = 1
        st[(bear < 0) & (bear < pbe)] = -1
        return st
    def warmup_bars(self): return int(self.config.params.get("n", 13))


class ElderImpulse(StanceIndicator):
    """+1 when EMA rising AND MACD-hist rising; -1 when both falling."""
    key = "elder_impulse"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 13))
        e = classic.ema(ctx.close, n)
        _, _, hist = classic.macd(ctx.close, 12, 26, 9)
        e_up = e > osc._shift(e, 1)
        h_up = hist > osc._shift(hist, 1)
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[e_up & h_up] = 1
        st[(~e_up) & (~h_up)] = -1
        return st
    def warmup_bars(self): return 35


# ---------- veto indicators (custom directions) ----------
class TrendIntensity(Indicator):
    """TII zone around 50 (mean-reversion within the trend)."""
    key = "trend_intensity"
    def directions(self, ctx):
        p = self.config.params
        v = T.trend_intensity(ctx.close, int(p.get("n", 60)))
        return votes.band_directions(v, float(p.get("lower", 40)), float(p.get("upper", 60)), 50.0)
    def warmup_bars(self): return int(self.config.params.get("n", 60))


class LinRegChannel(Indicator):
    """Veto BOTH sides when price is beyond ±k·resid-std of the regression line (overextended)."""
    key = "linreg_channel"
    def directions(self, ctx):
        p = self.config.params
        dev, std = T.linreg_dev(ctx.close, int(p.get("n", 100)))
        k = float(p.get("k", 2.0))
        return votes.both_veto(np.isfinite(dev) & np.isfinite(std) & (np.abs(dev) > k * std))
    def warmup_bars(self): return int(self.config.params.get("n", 100))


class Chandelier(Indicator):
    """Veto longs when close < long chandelier stop; veto shorts when close > short stop."""
    key = "chandelier"
    def directions(self, ctx):
        p = self.config.params
        ls, ss = T.chandelier(ctx.high, ctx.low, ctx.close, int(p.get("n", 22)), float(p.get("m", 3.0)))
        c = ctx.close
        vdir = np.zeros(len(c), dtype=np.int8)
        vdir[np.isfinite(ls) & (c < ls)] = LONG
        vdir[np.isfinite(ss) & (c > ss)] = SHORT
        return np.zeros(len(c), dtype=np.int8), vdir
    def warmup_bars(self): return int(self.config.params.get("n", 22))


class ChandeKroll(Indicator):
    key = "chande_kroll"
    def directions(self, ctx):
        p = self.config.params
        cl, cs = T.chande_kroll(ctx.high, ctx.low, ctx.close,
                                int(p.get("n", 10)), float(p.get("m", 1.0)), int(p.get("p", 9)))
        c = ctx.close
        vdir = np.zeros(len(c), dtype=np.int8)
        vdir[np.isfinite(cl) & (c < cl)] = LONG
        vdir[np.isfinite(cs) & (c > cs)] = SHORT
        return np.zeros(len(c), dtype=np.int8), vdir
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 10)) + int(p.get("p", 9))


CLASSES = (
    PPO, APO, DICross, Aroon, AroonOsc, ParabolicSAR, Vortex, Supertrend, TRIX, KST, Coppock, DPO,
    TrendIntensity, LinRegSlope, LinRegChannel, Chandelier, ChandeKroll, QQE, ElderRay, ElderImpulse,
    ASI, EXPMA, DMA, BBI,
)

_FS = [{"name": "fast", "default": 12, "min": 2, "max": 200, "step": 1},
       {"name": "slow", "default": 26, "min": 2, "max": 400, "step": 1}]
SCHEMA = {
    "ppo": {"label": "PPO", "mode": "confirm", "params": _FS + [{"name": "signal", "default": 9, "min": 1, "max": 100, "step": 1}]},
    "apo": {"label": "APO", "mode": "confirm", "params": _FS},
    "di_cross": {"label": "DMI (+DI/−DI cross)", "mode": "confirm",
                 "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1}]},
    "aroon": {"label": "Aroon (strong trend)", "mode": "confirm",
              "params": [{"name": "n", "default": 25, "min": 2, "max": 200, "step": 1}]},
    "aroon_osc": {"label": "Aroon Oscillator", "mode": "confirm",
                  "params": [{"name": "n", "default": 25, "min": 2, "max": 200, "step": 1}]},
    "psar": {"label": "Parabolic SAR", "mode": "confirm",
             "params": [{"name": "step", "default": 0.02, "min": 0.01, "max": 0.2, "step": 0.01},
                        {"name": "max", "default": 0.2, "min": 0.05, "max": 0.5, "step": 0.01}]},
    "vortex": {"label": "Vortex", "mode": "confirm",
               "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1}]},
    "supertrend": {"label": "Supertrend", "mode": "confirm",
                   "params": [{"name": "n", "default": 10, "min": 2, "max": 100, "step": 1},
                              {"name": "m", "default": 3.0, "min": 1.0, "max": 8.0, "step": 0.5}]},
    "trix": {"label": "TRIX", "mode": "confirm",
             "params": [{"name": "n", "default": 15, "min": 2, "max": 100, "step": 1},
                        {"name": "signal", "default": 9, "min": 1, "max": 100, "step": 1}]},
    "kst": {"label": "Know Sure Thing", "mode": "confirm",
            "params": [{"name": "signal", "default": 9, "min": 1, "max": 100, "step": 1}]},
    "coppock": {"label": "Coppock Curve", "mode": "confirm", "params": []},
    "dpo": {"label": "Detrended Price Osc", "mode": "confirm",
            "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1}]},
    "trend_intensity": {"label": "Trend Intensity Index", "mode": "both",
                        "params": [{"name": "n", "default": 60, "min": 2, "max": 200, "step": 1},
                                   {"name": "lower", "default": 40, "min": 1, "max": 49, "step": 1},
                                   {"name": "upper", "default": 60, "min": 51, "max": 99, "step": 1}]},
    "linreg_slope": {"label": "Linear-Reg Slope", "mode": "confirm",
                     "params": [{"name": "n", "default": 14, "min": 2, "max": 200, "step": 1}]},
    "linreg_channel": {"label": "Linear-Reg Channel (veto)", "mode": "veto",
                       "params": [{"name": "n", "default": 100, "min": 10, "max": 400, "step": 1},
                                  {"name": "k", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1}]},
    "chandelier": {"label": "Chandelier Exit (veto)", "mode": "veto",
                   "params": [{"name": "n", "default": 22, "min": 2, "max": 100, "step": 1},
                              {"name": "m", "default": 3.0, "min": 1.0, "max": 8.0, "step": 0.5}]},
    "chande_kroll": {"label": "Chande-Kroll Stop (veto)", "mode": "veto",
                     "params": [{"name": "n", "default": 10, "min": 2, "max": 100, "step": 1},
                                {"name": "m", "default": 1.0, "min": 0.5, "max": 5.0, "step": 0.5},
                                {"name": "p", "default": 9, "min": 2, "max": 100, "step": 1}]},
    "qqe": {"label": "QQE", "mode": "confirm",
            "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1},
                       {"name": "sf", "default": 5, "min": 1, "max": 50, "step": 1},
                       {"name": "f", "default": 4.236, "min": 1.0, "max": 8.0, "step": 0.001}]},
    "elder_ray": {"label": "Elder Ray", "mode": "confirm",
                  "params": [{"name": "n", "default": 13, "min": 2, "max": 100, "step": 1}]},
    "elder_impulse": {"label": "Elder Impulse", "mode": "confirm",
                      "params": [{"name": "n", "default": 13, "min": 2, "max": 100, "step": 1}]},
    "asi": {"label": "Accumulation Swing Index", "mode": "confirm",
            "params": [{"name": "limit", "default": 3.0, "min": 0.5, "max": 10.0, "step": 0.5}]},
    "expma": {"label": "EXPMA cross", "mode": "confirm",
              "params": [{"name": "fast", "default": 12, "min": 2, "max": 200, "step": 1},
                         {"name": "slow", "default": 50, "min": 2, "max": 400, "step": 1}]},
    "dma": {"label": "DMA", "mode": "confirm",
            "params": [{"name": "fast", "default": 10, "min": 2, "max": 200, "step": 1},
                       {"name": "slow", "default": 50, "min": 2, "max": 400, "step": 1},
                       {"name": "m", "default": 10, "min": 1, "max": 100, "step": 1}]},
    "bbi": {"label": "BBI", "mode": "confirm", "params": []},
}
