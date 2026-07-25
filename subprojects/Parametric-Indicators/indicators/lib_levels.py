"""levels-school indicator classes (Ichimoku + session pivots).
CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py."""
from __future__ import annotations

import numpy as np

from .base import Indicator
from .calc import levels as LV, osc
from .stances import StanceIndicator, _sign_stance


def _sess(ctx):
    return ctx.session_id if ctx.session_id is not None else np.zeros(len(ctx.close), dtype=int)


def _breakout(close, upper, lower):
    st = np.zeros(len(close), dtype=np.int8)
    st[np.isfinite(upper) & (close > upper)] = 1
    st[np.isfinite(lower) & (close < lower)] = -1
    return st


class IchimokuTKCross(StanceIndicator):
    key = "ichimoku_tk_cross"
    def stance(self, ctx):
        p = self.config.params
        tenkan, kijun, _, _ = LV.ichimoku_lines(ctx.high, ctx.low, int(p.get("t", 9)), int(p.get("k", 26)), 52)
        return _sign_stance(tenkan - kijun)
    def warmup_bars(self): return int(self.config.params.get("k", 26))


class IchimokuCloud(StanceIndicator):
    key = "ichimoku_cloud"
    def stance(self, ctx):
        p = self.config.params
        pa, pb = LV.cloud_past(ctx.high, ctx.low, int(p.get("t", 9)), int(p.get("k", 26)), int(p.get("b", 52)))
        return _breakout(ctx.close, np.maximum(pa, pb), np.minimum(pa, pb))
    def warmup_bars(self): return int(self.config.params.get("b", 52)) + 26


class IchimokuChikou(StanceIndicator):
    key = "ichimoku_chikou"
    def stance(self, ctx):
        lag = int(self.config.params.get("lag", 26))
        return _sign_stance(ctx.close - osc._shift(ctx.close, lag))
    def warmup_bars(self): return int(self.config.params.get("lag", 26))


class _Pivot(StanceIndicator):
    def _pp(self, pO, pH, pL, pC):
        raise NotImplementedError
    def stance(self, ctx):
        pO, pH, pL, pC = LV.prior_session_ohlc(ctx.open, ctx.high, ctx.low, ctx.close, _sess(ctx))
        return _sign_stance(ctx.close - self._pp(pO, pH, pL, pC))
    def warmup_bars(self): return 1


class PivotFloor(_Pivot):
    key = "pivot_floor"
    def _pp(self, pO, pH, pL, pC): return LV.floor_pp(pH, pL, pC)


class PivotWoodie(_Pivot):
    key = "pivot_woodie"
    def _pp(self, pO, pH, pL, pC): return LV.woodie_pp(pH, pL, pC)


class PivotDemark(_Pivot):
    key = "pivot_demark"
    def _pp(self, pO, pH, pL, pC): return LV.demark_pp(pO, pH, pL, pC)


class PivotCamarilla(StanceIndicator):
    key = "pivot_camarilla"
    def stance(self, ctx):
        _, pH, pL, pC = LV.prior_session_ohlc(ctx.open, ctx.high, ctx.low, ctx.close, _sess(ctx))
        r3, s3 = LV.camarilla_bands(pH, pL, pC)
        return _breakout(ctx.close, r3, s3)
    def warmup_bars(self): return 1


class PivotFib(StanceIndicator):
    key = "pivot_fib"
    def stance(self, ctx):
        _, pH, pL, pC = LV.prior_session_ohlc(ctx.open, ctx.high, ctx.low, ctx.close, _sess(ctx))
        r1, s1 = LV.fib_levels(pH, pL, pC)
        return _breakout(ctx.close, r1, s1)
    def warmup_bars(self): return 1


class CPR(StanceIndicator):
    key = "cpr"
    def stance(self, ctx):
        _, pH, pL, pC = LV.prior_session_ohlc(ctx.open, ctx.high, ctx.low, ctx.close, _sess(ctx))
        top, bot = LV.cpr_levels(pH, pL, pC)
        return _breakout(ctx.close, top, bot)
    def warmup_bars(self): return 1


CLASSES = (IchimokuTKCross, IchimokuCloud, IchimokuChikou, PivotFloor, PivotWoodie, PivotDemark,
           PivotCamarilla, PivotFib, CPR)
SCHEMA = {
    "ichimoku_tk_cross": {"label": "Ichimoku Tenkan/Kijun cross", "mode": "confirm",
                          "params": [{"name": "t", "default": 9, "min": 2, "max": 100, "step": 1},
                                     {"name": "k", "default": 26, "min": 2, "max": 200, "step": 1}]},
    "ichimoku_cloud": {"label": "Ichimoku cloud", "mode": "confirm",
                       "params": [{"name": "t", "default": 9, "min": 2, "max": 100, "step": 1},
                                  {"name": "k", "default": 26, "min": 2, "max": 200, "step": 1},
                                  {"name": "b", "default": 52, "min": 2, "max": 300, "step": 1}]},
    "ichimoku_chikou": {"label": "Ichimoku Chikou", "mode": "confirm",
                        "params": [{"name": "lag", "default": 26, "min": 1, "max": 200, "step": 1}]},
    "pivot_floor": {"label": "Floor pivot", "mode": "confirm", "params": []},
    "pivot_woodie": {"label": "Woodie pivot", "mode": "confirm", "params": []},
    "pivot_camarilla": {"label": "Camarilla pivot", "mode": "confirm", "params": []},
    "pivot_fib": {"label": "Fibonacci pivot", "mode": "confirm", "params": []},
    "pivot_demark": {"label": "DeMark pivot", "mode": "confirm", "params": []},
    "cpr": {"label": "Central Pivot Range", "mode": "confirm", "params": []},
}
