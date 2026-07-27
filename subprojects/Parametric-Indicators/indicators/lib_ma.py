"""ma-school indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py.

Two stance shapes, mirroring the built-ins:
  * CROSS (like EMATrend/SMATrend): +1 when close>fast>slow, -1 when close<fast<slow — for the simple
    linear MAs (wma, rma, dema, tema, tma, hma, zlema, sine_wma, vwma, lsma).
  * SINGLE-LINE (like KeltnerTrend/VWAPTrend): +1 when close>MA, -1 when close<MA — for the adaptive
    MAs whose "period" is one of several shape params (kama, vidya, alma, t3, mcginley, evwma).
Plus three specials: gmma (ribbon alignment), ma_envelope (trend + overextension veto), ma_displaced.
"""
from __future__ import annotations

import numpy as np

from . import classic
from .base import BOTH, Indicator
from .calc import ma
from .stances import StanceIndicator, _sign_stance


def _cross_stance(close: np.ndarray, f: np.ndarray, s: np.ndarray) -> np.ndarray:
    st = np.zeros(len(close), dtype=np.int8)
    st[(close > f) & (f > s)] = 1
    st[(close < f) & (f < s)] = -1
    return st


class _CrossMA(StanceIndicator):
    """Base for fast/slow-cross MAs. Subclass sets `key` and `_line(x, n)`; params are fast/slow."""
    _warm_mult = 1

    def _line(self, x, n):  # noqa: D401
        raise NotImplementedError

    def stance(self, ctx):
        p = self.config.params
        f = self._line(ctx.close, int(p.get("fast", 20)))
        s = self._line(ctx.close, int(p.get("slow", 50)))
        return _cross_stance(ctx.close, f, s)

    def warmup_bars(self):
        p = self.config.params
        return self._warm_mult * max(int(p.get("fast", 20)), int(p.get("slow", 50)))


class WMATrend(_CrossMA):
    key = "wma"
    def _line(self, x, n): return ma.wma(x, n)


class RMATrend(_CrossMA):
    key = "rma"
    def _line(self, x, n): return classic.rma(x, n)


class DEMATrend(_CrossMA):
    key = "dema"
    _warm_mult = 2
    def _line(self, x, n): return ma.dema(x, n)


class TEMATrend(_CrossMA):
    key = "tema"
    _warm_mult = 3
    def _line(self, x, n): return ma.tema(x, n)


class TMATrend(_CrossMA):
    key = "tma"
    def _line(self, x, n): return ma.tma(x, n)


class HMATrend(_CrossMA):
    key = "hma"
    def _line(self, x, n): return ma.hma(x, n)


class ZLEMATrend(_CrossMA):
    key = "zlema"
    def _line(self, x, n): return ma.zlema(x, n)


class SineWMATrend(_CrossMA):
    key = "sine_wma"
    def _line(self, x, n): return ma.sine_wma(x, n)


class LSMATrend(_CrossMA):
    key = "lsma"
    def _line(self, x, n): return ma.lsma(x, n)


class VWMATrend(StanceIndicator):
    key = "vwma"
    def stance(self, ctx):
        p = self.config.params
        f = ma.vwma(ctx.close, ctx.volume, int(p.get("fast", 20)))
        s = ma.vwma(ctx.close, ctx.volume, int(p.get("slow", 50)))
        return _cross_stance(ctx.close, f, s)
    def warmup_bars(self):
        p = self.config.params
        return max(int(p.get("fast", 20)), int(p.get("slow", 50)))


# --- single-line adaptive MAs: stance = sign(close - line) ---
class KAMATrend(StanceIndicator):
    key = "kama"
    def stance(self, ctx):
        p = self.config.params
        line = ma.kama(ctx.close, int(p.get("n", 10)), int(p.get("fast", 2)), int(p.get("slow", 30)))
        return _sign_stance(ctx.close - line)
    def warmup_bars(self): return int(self.config.params.get("n", 10))


class VIDYATrend(StanceIndicator):
    key = "vidya"
    def stance(self, ctx):
        line = ma.vidya(ctx.close, int(self.config.params.get("n", 14)))
        return _sign_stance(ctx.close - line)
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class ALMATrend(StanceIndicator):
    key = "alma"
    def stance(self, ctx):
        p = self.config.params
        line = ma.alma(ctx.close, int(p.get("n", 9)), float(p.get("offset", 0.85)), float(p.get("sigma", 6.0)))
        return _sign_stance(ctx.close - line)
    def warmup_bars(self): return int(self.config.params.get("n", 9))


class T3Trend(StanceIndicator):
    key = "t3"
    def stance(self, ctx):
        p = self.config.params
        line = ma.t3(ctx.close, int(p.get("n", 10)), float(p.get("v", 0.7)))
        return _sign_stance(ctx.close - line)
    def warmup_bars(self): return 3 * int(self.config.params.get("n", 10))


class McGinleyTrend(StanceIndicator):
    key = "mcginley"
    def stance(self, ctx):
        line = ma.mcginley(ctx.close, int(self.config.params.get("n", 14)))
        return _sign_stance(ctx.close - line)
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class EVWMATrend(StanceIndicator):
    key = "evwma"
    def stance(self, ctx):
        line = ma.evwma(ctx.close, ctx.volume, int(self.config.params.get("n", 20)))
        return _sign_stance(ctx.close - line)
    def warmup_bars(self): return int(self.config.params.get("n", 20))


# --- specials ---
class GMMATrend(StanceIndicator):
    """Guppy ribbon: +1 when every short EMA is above every long EMA, -1 when every short is below."""
    key = "gmma"
    _SHORT = (3, 5, 8, 10, 12, 15)
    _LONG = (30, 35, 40, 45, 50, 60)
    def stance(self, ctx):
        shorts = np.vstack([classic.ema(ctx.close, p) for p in self._SHORT])
        longs = np.vstack([classic.ema(ctx.close, p) for p in self._LONG])
        min_short, max_short = shorts.min(0), shorts.max(0)
        min_long, max_long = longs.min(0), longs.max(0)
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[min_short > max_long] = 1
        st[max_short < min_long] = -1
        return st
    def warmup_bars(self): return max(self._LONG)


class MAEnvelope(Indicator):
    """SMA-envelope: confirm the trend (close vs SMA); veto BOTH sides when price is overextended
    beyond ±pct% of the SMA (mean-reversion risk)."""
    key = "ma_envelope"
    def directions(self, ctx):
        p = self.config.params
        n = int(p.get("n", 20))
        pct = float(p.get("pct", 2.5))
        mid = classic.sma(ctx.close, n)
        cdir = _sign_stance(ctx.close - mid)
        with np.errstate(invalid="ignore", divide="ignore"):
            dev = np.abs(ctx.close / mid - 1.0) * 100.0
        vdir = np.zeros(len(ctx.close), dtype=np.int8)
        vdir[np.isfinite(dev) & (dev > pct)] = BOTH
        return cdir, vdir
    def warmup_bars(self): return int(self.config.params.get("n", 20))


class MADisplaced(StanceIndicator):
    """Displaced SMA: stance = sign(close − SMA(n) shifted d bars into the past)."""
    key = "ma_displaced"
    def stance(self, ctx):
        p = self.config.params
        n = int(p.get("n", 20))
        d = int(p.get("d", 5))
        line = classic.sma(ctx.close, n)
        disp = np.full(len(line), np.nan)
        if d < len(line):
            disp[d:] = line[:-d] if d > 0 else line
        return _sign_stance(ctx.close - disp)
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 20)) + int(p.get("d", 5))


CLASSES = (
    WMATrend, RMATrend, DEMATrend, TEMATrend, TMATrend, HMATrend, ZLEMATrend, SineWMATrend,
    LSMATrend, VWMATrend, KAMATrend, VIDYATrend, ALMATrend, T3Trend, McGinleyTrend, EVWMATrend,
    GMMATrend, MAEnvelope, MADisplaced,
)

_FS = [{"name": "fast", "default": 20, "min": 2, "max": 400, "step": 1},
       {"name": "slow", "default": 50, "min": 2, "max": 400, "step": 1}]
SCHEMA = {
    "wma":   {"label": "WMA trend", "mode": "confirm", "params": _FS},
    "rma":   {"label": "RMA / Wilder trend", "mode": "confirm", "params": _FS},
    "dema":  {"label": "DEMA trend", "mode": "confirm", "params": _FS},
    "tema":  {"label": "TEMA trend", "mode": "confirm", "params": _FS},
    "tma":   {"label": "Triangular MA trend", "mode": "confirm", "params": _FS},
    "hma":   {"label": "Hull MA trend", "mode": "confirm", "params": _FS},
    "zlema": {"label": "Zero-lag EMA trend", "mode": "confirm", "params": _FS},
    "sine_wma": {"label": "Sine-weighted MA trend", "mode": "confirm", "params": _FS},
    "lsma":  {"label": "Least-squares MA trend", "mode": "confirm", "params": _FS},
    "vwma":  {"label": "Volume-weighted MA trend", "mode": "confirm", "params": _FS},
    "kama":  {"label": "KAMA trend", "mode": "confirm",
              "params": [{"name": "n", "default": 10, "min": 2, "max": 100, "step": 1},
                         {"name": "fast", "default": 2, "min": 2, "max": 30, "step": 1},
                         {"name": "slow", "default": 30, "min": 2, "max": 200, "step": 1}]},
    "vidya": {"label": "VIDYA trend", "mode": "confirm",
              "params": [{"name": "n", "default": 14, "min": 2, "max": 200, "step": 1}]},
    "alma":  {"label": "ALMA trend", "mode": "confirm",
              "params": [{"name": "n", "default": 9, "min": 2, "max": 200, "step": 1},
                         {"name": "offset", "default": 0.85, "min": 0.0, "max": 1.0, "step": 0.05},
                         {"name": "sigma", "default": 6.0, "min": 1.0, "max": 12.0, "step": 0.5}]},
    "t3":    {"label": "T3 trend", "mode": "confirm",
              "params": [{"name": "n", "default": 10, "min": 2, "max": 100, "step": 1},
                         {"name": "v", "default": 0.7, "min": 0.0, "max": 1.0, "step": 0.05}]},
    "mcginley": {"label": "McGinley Dynamic trend", "mode": "confirm",
                 "params": [{"name": "n", "default": 14, "min": 2, "max": 200, "step": 1}]},
    "evwma": {"label": "Elastic VWMA trend", "mode": "confirm",
              "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1}]},
    "gmma":  {"label": "Guppy MMA ribbon", "mode": "confirm", "params": []},
    "ma_envelope": {"label": "MA envelope (trend + overextension veto)", "mode": "both",
                    "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1},
                               {"name": "pct", "default": 2.5, "min": 0.1, "max": 10.0, "step": 0.1}]},
    "ma_displaced": {"label": "Displaced MA trend", "mode": "confirm",
                     "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1},
                                {"name": "d", "default": 5, "min": 1, "max": 50, "step": 1}]},
}
