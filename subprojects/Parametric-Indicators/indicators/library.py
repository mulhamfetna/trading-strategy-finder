"""Group A indicator classes (OOP wrappers over indicators/classic.py + votes.py) and the registry.

Each class turns its raw series into per-bar (confirm_dir, veto_dir). Most are stance-based
(bullish/bearish → confirm that side, veto the other); RSI/Stoch/MFI use mean-reversion zone logic;
CCI is a breakout stance; Bollinger is a veto-on-stretch; ADX is a no-trend veto. All causal.

REGISTRY maps a string key → class. build(key, config) constructs one. Defaults live on each class.
"""
from __future__ import annotations

import numpy as np

from . import classic, smc, votes
from .base import BOTH, Indicator, MarketContext


def _sign_stance(x: np.ndarray) -> np.ndarray:
    """sign with NaN→0, as int8 stance."""
    s = np.zeros(len(x), dtype=np.int8)
    a = np.asarray(x, dtype=float)
    s[a > 0] = 1
    s[a < 0] = -1
    return s


class StanceIndicator(Indicator):
    """Indicators whose vote is a plain bullish/bearish stance."""
    def stance(self, ctx: MarketContext) -> np.ndarray:
        raise NotImplementedError

    def directions(self, ctx: MarketContext):
        return votes.stance_directions(self.stance(ctx))


class EMATrend(StanceIndicator):
    key = "ema_trend"
    def stance(self, ctx):
        p = self.config.params
        f = classic.ema(ctx.close, int(p.get("fast", 20)))
        s = classic.ema(ctx.close, int(p.get("slow", 50)))
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[(ctx.close > f) & (f > s)] = 1
        st[(ctx.close < f) & (f < s)] = -1
        return st


class SMATrend(StanceIndicator):
    key = "sma_trend"
    def stance(self, ctx):
        p = self.config.params
        f = classic.sma(ctx.close, int(p.get("fast", 50)))
        s = classic.sma(ctx.close, int(p.get("slow", 200)))
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[(ctx.close > f) & (f > s)] = 1
        st[(ctx.close < f) & (f < s)] = -1
        return st


class MACD(StanceIndicator):
    key = "macd"
    def stance(self, ctx):
        p = self.config.params
        _, _, hist = classic.macd(ctx.close, int(p.get("fast", 12)),
                                  int(p.get("slow", 26)), int(p.get("signal", 9)))
        return _sign_stance(hist)


class VWAPTrend(StanceIndicator):
    key = "vwap"
    def stance(self, ctx):
        sess = ctx.session_id if ctx.session_id is not None else np.zeros(len(ctx.close), dtype=int)
        v = classic.vwap(ctx.high, ctx.low, ctx.close, ctx.volume, sess)
        return _sign_stance(ctx.close - v)


class KeltnerTrend(StanceIndicator):
    key = "keltner"
    def stance(self, ctx):
        p = self.config.params
        mid, _, _ = classic.keltner(ctx.high, ctx.low, ctx.close,
                                    int(p.get("n", 20)), float(p.get("m", 2.0)))
        return _sign_stance(ctx.close - mid)


class OBVTrend(StanceIndicator):
    key = "obv"
    def stance(self, ctx):
        p = self.config.params
        o = classic.obv(ctx.close, ctx.volume)
        ref = classic.sma(o, int(p.get("slope", 20)))
        return _sign_stance(o - ref)


class CCIBreakout(StanceIndicator):
    key = "cci"
    def stance(self, ctx):
        p = self.config.params
        thr = float(p.get("threshold", 100.0))
        c = classic.cci(ctx.high, ctx.low, ctx.close, int(p.get("n", 20)))
        st = np.zeros(len(c), dtype=np.int8)
        st[c >= thr] = 1
        st[c <= -thr] = -1
        return st


class RSIZone(Indicator):
    key = "rsi"
    def directions(self, ctx):
        p = self.config.params
        r = classic.rsi(ctx.close, int(p.get("n", 14)))
        return votes.rsi_directions(r, float(p.get("lower", 30)), float(p.get("upper", 70)))


class StochasticZone(Indicator):
    key = "stochastic"
    def directions(self, ctx):
        p = self.config.params
        k, _ = classic.stochastic(ctx.high, ctx.low, ctx.close,
                                  int(p.get("n", 14)), int(p.get("d", 3)))
        return votes.rsi_directions(k, float(p.get("lower", 20)), float(p.get("upper", 80)))


class MFIZone(Indicator):
    key = "mfi"
    def directions(self, ctx):
        p = self.config.params
        m = classic.mfi(ctx.high, ctx.low, ctx.close, ctx.volume, int(p.get("n", 14)))
        return votes.rsi_directions(m, float(p.get("lower", 20)), float(p.get("upper", 80)))


class BollingerVeto(Indicator):
    key = "bollinger"
    def directions(self, ctx):
        p = self.config.params
        _, up, lo = classic.bollinger(ctx.close, int(p.get("n", 20)), float(p.get("k", 2.0)))
        n = len(ctx.close)
        cdir = np.zeros(n, dtype=np.int8)
        vdir = np.zeros(n, dtype=np.int8)
        vdir[ctx.close >= up] = +1   # stretched at upper → veto a long
        vdir[ctx.close <= lo] = -1   # stretched at lower → veto a short
        return cdir, vdir


class ADXVeto(Indicator):
    key = "adx"
    def directions(self, ctx):
        p = self.config.params
        thr = float(p.get("threshold", 25.0))
        adxv, pdi, mdi = classic.adx(ctx.high, ctx.low, ctx.close, int(p.get("n", 14)))
        n = len(ctx.close)
        cdir = np.zeros(n, dtype=np.int8)
        vdir = np.zeros(n, dtype=np.int8)
        trending = ~np.isnan(adxv) & (adxv >= thr)
        no_trend = ~np.isnan(adxv) & (adxv < thr)
        vdir[no_trend] = BOTH                       # no trend → veto either side
        cdir[trending & (pdi > mdi)] = +1           # trend up → confirm long
        cdir[trending & (mdi > pdi)] = -1           # trend down → confirm short
        return cdir, vdir


class StructureTrend(StanceIndicator):
    key = "structure_trend"
    def stance(self, ctx):
        return smc.structure_trend(ctx.close, int(self.config.params.get("swing_l", 2)))


class OrderBlock(StanceIndicator):
    key = "order_block"
    def stance(self, ctx):
        return smc.order_blocks(ctx.open, ctx.high, ctx.low, ctx.close,
                                int(self.config.params.get("swing_l", 2)))


class FVGConfirm(StanceIndicator):
    key = "fvg"
    def stance(self, ctx):
        return smc.fvg_active_direction(ctx.high, ctx.low, int(self.config.params.get("lookback", 3)))


REGISTRY = {c.key: c for c in (
    EMATrend, SMATrend, MACD, VWAPTrend, KeltnerTrend, OBVTrend, CCIBreakout,
    RSIZone, StochasticZone, MFIZone, BollingerVeto, ADXVeto,
    StructureTrend, OrderBlock, FVGConfirm,
)}


def build(key: str, config=None) -> Indicator:
    if key not in REGISTRY:
        raise KeyError(f"unknown indicator key {key!r}; known: {sorted(REGISTRY)}")
    return REGISTRY[key](config)


def from_specs(specs):
    """Build a list of Indicator instances from dashboard/API specs (strict, no silent fallback).
    Each spec: {key, enabled?, mode?, retrace_amount?, retrace_unit?, wait_bars?, params?{}}.
    Raises IndicatorParamError on an unknown key or invalid config."""
    from .base import IndicatorConfig, IndicatorParamError
    out = []
    for s in (specs or []):
        key = s.get("key")
        if key not in REGISTRY:
            raise IndicatorParamError(f"unknown indicator key {key!r}; known: {sorted(REGISTRY)}")
        cfg = IndicatorConfig(
            enabled=bool(s.get("enabled", False)),
            mode=s.get("mode", "both"),
            retrace_amount=float(s.get("retrace_amount", 0.0)),
            retrace_unit=s.get("retrace_unit", "atr_mult"),
            wait_bars=int(s.get("wait_bars", 0)),
            params=dict(s.get("params", {})),
        )
        out.append(REGISTRY[key](cfg))  # constructor validates the config
    return out
