"""osc-school indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py.

Two shapes: zone oscillators (_Zone → votes.band_directions with a per-indicator midpoint) and
signed-momentum stances (StanceIndicator → sign of the line, or of line-minus-signal)."""
from __future__ import annotations

import numpy as np

from . import votes
from .base import Indicator
from .calc import osc
from .stances import StanceIndicator, _sign_stance


class _Zone(Indicator):
    """Mean-reversion zone oscillator. Subclass sets key, _MID/_LO/_HI defaults, `_value(ctx)`,
    warmup_bars. Params lower/upper are tunable; midpoint is fixed per indicator."""
    _MID = 50.0
    _LO = 30.0
    _HI = 70.0

    def _value(self, ctx):
        raise NotImplementedError

    def directions(self, ctx):
        p = self.config.params
        lo = float(p.get("lower", self._LO))
        hi = float(p.get("upper", self._HI))
        return votes.band_directions(self._value(ctx), lo, hi, self._MID)


# ---------- zone oscillators ----------
class RSICutler(_Zone):
    key = "rsi_cutler"
    def _value(self, ctx): return osc.rsi_cutler(ctx.close, int(self.config.params.get("n", 14)))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class RSIConnors(_Zone):
    key = "rsi_connors"
    _LO, _HI = 20.0, 80.0
    def _value(self, ctx): return osc.connors_rsi(ctx.close)
    def warmup_bars(self): return 100


class StochRSI(_Zone):
    key = "stoch_rsi"
    _LO, _HI = 20.0, 80.0
    def _value(self, ctx):
        p = self.config.params
        return osc.stoch_rsi(ctx.close, int(p.get("n", 14)), int(p.get("k", 14)), int(p.get("d", 3)))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 14)) + int(p.get("k", 14))


class KDJ(_Zone):
    key = "kdj"
    _LO, _HI = 20.0, 80.0
    def _value(self, ctx): return osc.kdj_k(ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 9)))
    def warmup_bars(self): return int(self.config.params.get("n", 9))


class WilliamsR(_Zone):
    key = "williams_r"
    _MID, _LO, _HI = -50.0, -80.0, -20.0
    def _value(self, ctx): return osc.williams_r(ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 14)))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class CMO(_Zone):
    key = "cmo"
    _MID, _LO, _HI = 0.0, -50.0, 50.0
    def _value(self, ctx): return osc.cmo(ctx.close, int(self.config.params.get("n", 14)))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class UltimateOsc(_Zone):
    key = "ultimate_osc"
    def _value(self, ctx): return osc.ultimate_osc(ctx.high, ctx.low, ctx.close)
    def warmup_bars(self): return 28


class SMI(_Zone):
    key = "smi"
    _MID, _LO, _HI = 0.0, -40.0, 40.0
    def _value(self, ctx):
        p = self.config.params
        return osc.smi(ctx.high, ctx.low, ctx.close, int(p.get("n", 14)), int(p.get("smooth", 3)))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 14)) + 2 * int(p.get("smooth", 3))


class RMI(_Zone):
    key = "rmi"
    def _value(self, ctx):
        p = self.config.params
        return osc.rmi(ctx.close, int(p.get("n", 14)), int(p.get("m", 5)))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n", 14)) + int(p.get("m", 5))


class DynamicDMI(_Zone):
    key = "cmo_chande_dmi"
    def _value(self, ctx): return osc.dynamic_dmi(ctx.close, int(self.config.params.get("n", 14)))
    def warmup_bars(self): return 2 * int(self.config.params.get("n", 14))


class WaveTrend(_Zone):
    key = "wavetrend"
    _MID, _LO, _HI = 0.0, -60.0, 60.0
    def _value(self, ctx):
        p = self.config.params
        return osc.wavetrend(ctx.high, ctx.low, ctx.close, int(p.get("n1", 10)), int(p.get("n2", 21)))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("n1", 10)) + int(p.get("n2", 21))


class PGO(_Zone):
    key = "pgo"
    _MID, _LO, _HI = 0.0, -3.0, 3.0
    def _value(self, ctx): return osc.pgo(ctx.high, ctx.low, ctx.close, int(self.config.params.get("n", 14)))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class PSY(_Zone):
    key = "psy"
    _LO, _HI = 25.0, 75.0
    def _value(self, ctx): return osc.psy(ctx.close, int(self.config.params.get("n", 12)))
    def warmup_bars(self): return int(self.config.params.get("n", 12))


# ---------- signed-momentum stances ----------
class Momentum(StanceIndicator):
    key = "momentum"
    def stance(self, ctx): return _sign_stance(osc.momentum(ctx.close, int(self.config.params.get("n", 10))))
    def warmup_bars(self): return int(self.config.params.get("n", 10))


class ROC(StanceIndicator):
    key = "roc"
    def stance(self, ctx): return _sign_stance(osc.roc(ctx.close, int(self.config.params.get("n", 9))))
    def warmup_bars(self): return int(self.config.params.get("n", 9))


class Disparity(StanceIndicator):
    key = "disparity"
    def stance(self, ctx): return _sign_stance(osc.disparity(ctx.close, int(self.config.params.get("n", 14))))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class BIAS(StanceIndicator):
    key = "bias"
    def stance(self, ctx): return _sign_stance(osc.bias(ctx.close, int(self.config.params.get("n", 6))))
    def warmup_bars(self): return int(self.config.params.get("n", 6))


class BalanceOfPower(StanceIndicator):
    key = "balance_of_power"
    def stance(self, ctx):
        return _sign_stance(osc.balance_of_power(ctx.open, ctx.high, ctx.low, ctx.close,
                                                 int(self.config.params.get("n", 14))))
    def warmup_bars(self): return int(self.config.params.get("n", 14))


class TSI(StanceIndicator):
    key = "tsi"
    def stance(self, ctx):
        p = self.config.params
        t = osc.tsi(ctx.close, int(p.get("r", 25)), int(p.get("s", 13)))
        sig = osc.nan_ema(t, int(p.get("signal", 13)))
        return _sign_stance(t - sig)
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("r", 25)) + int(p.get("s", 13))


class RVGI(StanceIndicator):
    key = "rvgi"
    def stance(self, ctx):
        n = int(self.config.params.get("n", 14))
        rvi = osc.rvgi(ctx.open, ctx.high, ctx.low, ctx.close, n)
        return _sign_stance(rvi - osc.rvgi_signal(rvi))
    def warmup_bars(self): return int(self.config.params.get("n", 14)) + 4


class Fisher(StanceIndicator):
    key = "fisher"
    def stance(self, ctx):
        f = osc.fisher(ctx.high, ctx.low, int(self.config.params.get("n", 9)))
        return _sign_stance(f - osc._shift(f, 1))
    def warmup_bars(self): return int(self.config.params.get("n", 9))


class DerivativeOsc(StanceIndicator):
    key = "derivative_osc"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(osc.derivative_osc(ctx.close, int(p.get("rsi_n", 14)), int(p.get("s1", 5)),
                                               int(p.get("s2", 3)), int(p.get("signal", 9))))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("rsi_n", 14)) + int(p.get("s1", 5)) + int(p.get("s2", 3)) + int(p.get("signal", 9))


class ErgodicOsc(StanceIndicator):
    key = "ergodic_osc"
    def stance(self, ctx):
        p = self.config.params
        return _sign_stance(osc.ergodic(ctx.close, int(p.get("r", 32)), int(p.get("s", 5)), int(p.get("signal", 5))))
    def warmup_bars(self):
        p = self.config.params
        return int(p.get("r", 32)) + int(p.get("s", 5))


_N = lambda default, lo=2, hi=200: [{"name": "n", "default": default, "min": lo, "max": hi, "step": 1}]  # noqa: E731
_ZONE = lambda lo, hi, lomin=1, lomax=49, himin=51, himax=99: [  # noqa: E731
    {"name": "lower", "default": lo, "min": lomin, "max": lomax, "step": 1},
    {"name": "upper", "default": hi, "min": himin, "max": himax, "step": 1}]

CLASSES = (
    RSICutler, RSIConnors, StochRSI, KDJ, WilliamsR, CMO, UltimateOsc, SMI, RMI, DynamicDMI,
    WaveTrend, PGO, PSY, Momentum, ROC, Disparity, BIAS, BalanceOfPower, TSI, RVGI, Fisher,
    DerivativeOsc, ErgodicOsc,
)
SCHEMA = {
    "rsi_cutler": {"label": "RSI (Cutler)", "mode": "both", "params": _N(14, 2, 100) + _ZONE(30, 70)},
    "rsi_connors": {"label": "Connors RSI", "mode": "both", "params": _ZONE(20, 80)},
    "stoch_rsi": {"label": "Stochastic RSI", "mode": "both",
                  "params": _N(14, 2, 100) + [{"name": "k", "default": 14, "min": 2, "max": 100, "step": 1},
                                              {"name": "d", "default": 3, "min": 1, "max": 50, "step": 1}]
                  + _ZONE(20, 80)},
    "kdj": {"label": "KDJ (%K)", "mode": "both", "params": _N(9, 2, 100) + _ZONE(20, 80)},
    "williams_r": {"label": "Williams %R", "mode": "both",
                   "params": _N(14, 2, 100) + [{"name": "lower", "default": -80, "min": -99, "max": -51, "step": 1},
                                               {"name": "upper", "default": -20, "min": -49, "max": -1, "step": 1}]},
    "cmo": {"label": "Chande Momentum Osc", "mode": "both",
            "params": _N(14, 2, 100) + [{"name": "lower", "default": -50, "min": -99, "max": -1, "step": 1},
                                        {"name": "upper", "default": 50, "min": 1, "max": 99, "step": 1}]},
    "ultimate_osc": {"label": "Ultimate Oscillator", "mode": "both", "params": _ZONE(30, 70)},
    "smi": {"label": "Stochastic Momentum Index", "mode": "both",
            "params": _N(14, 2, 100) + [{"name": "smooth", "default": 3, "min": 1, "max": 50, "step": 1},
                                        {"name": "lower", "default": -40, "min": -99, "max": -1, "step": 1},
                                        {"name": "upper", "default": 40, "min": 1, "max": 99, "step": 1}]},
    "rmi": {"label": "Relative Momentum Index", "mode": "both",
            "params": _N(14, 2, 100) + [{"name": "m", "default": 5, "min": 1, "max": 100, "step": 1}] + _ZONE(30, 70)},
    "cmo_chande_dmi": {"label": "Dynamic Momentum Index", "mode": "both",
                       "params": _N(14, 2, 100) + _ZONE(30, 70)},
    "wavetrend": {"label": "WaveTrend", "mode": "both",
                  "params": [{"name": "n1", "default": 10, "min": 2, "max": 100, "step": 1},
                             {"name": "n2", "default": 21, "min": 2, "max": 100, "step": 1},
                             {"name": "lower", "default": -60, "min": -99, "max": -1, "step": 1},
                             {"name": "upper", "default": 60, "min": 1, "max": 99, "step": 1}]},
    "pgo": {"label": "Pretty Good Oscillator", "mode": "both",
            "params": _N(14, 2, 100) + [{"name": "lower", "default": -3, "min": -20, "max": -1, "step": 1},
                                        {"name": "upper", "default": 3, "min": 1, "max": 20, "step": 1}]},
    "psy": {"label": "Psychological Line", "mode": "both", "params": _N(12, 2, 100) + _ZONE(25, 75)},
    "momentum": {"label": "Momentum", "mode": "confirm", "params": _N(10, 1, 200)},
    "roc": {"label": "Rate of Change", "mode": "confirm", "params": _N(9, 1, 200)},
    "disparity": {"label": "Disparity Index", "mode": "confirm", "params": _N(14, 2, 200)},
    "bias": {"label": "BIAS", "mode": "confirm", "params": _N(6, 2, 200)},
    "balance_of_power": {"label": "Balance of Power", "mode": "confirm", "params": _N(14, 2, 200)},
    "tsi": {"label": "True Strength Index", "mode": "confirm",
            "params": [{"name": "r", "default": 25, "min": 2, "max": 100, "step": 1},
                       {"name": "s", "default": 13, "min": 2, "max": 100, "step": 1},
                       {"name": "signal", "default": 13, "min": 1, "max": 100, "step": 1}]},
    "rvgi": {"label": "Relative Vigor Index", "mode": "confirm", "params": _N(14, 2, 200)},
    "fisher": {"label": "Fisher Transform", "mode": "confirm", "params": _N(9, 2, 100)},
    "derivative_osc": {"label": "Derivative Oscillator", "mode": "confirm",
                       "params": [{"name": "rsi_n", "default": 14, "min": 2, "max": 100, "step": 1},
                                  {"name": "s1", "default": 5, "min": 1, "max": 50, "step": 1},
                                  {"name": "s2", "default": 3, "min": 1, "max": 50, "step": 1},
                                  {"name": "signal", "default": 9, "min": 1, "max": 100, "step": 1}]},
    "ergodic_osc": {"label": "Ergodic Oscillator", "mode": "confirm",
                    "params": [{"name": "r", "default": 32, "min": 2, "max": 100, "step": 1},
                               {"name": "s", "default": 5, "min": 2, "max": 100, "step": 1},
                               {"name": "signal", "default": 5, "min": 1, "max": 100, "step": 1}]},
}
