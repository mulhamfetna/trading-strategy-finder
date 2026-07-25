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
from .stances import StanceIndicator, _sign_stance


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

    def warmup_bars(self):
        p = self.config.params
        return max(int(p.get("fast", 20)), int(p.get("slow", 50)))

    def warmup_deps(self):
        p = self.config.params
        return f"EMA({int(p.get('fast', 20))}) & EMA({int(p.get('slow', 50))})"


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

    def warmup_bars(self):
        p = self.config.params
        return max(int(p.get("fast", 50)), int(p.get("slow", 200)))

    def warmup_deps(self):
        p = self.config.params
        return f"SMA({int(p.get('fast', 50))}) & SMA({int(p.get('slow', 200))})"


class MACD(StanceIndicator):
    key = "macd"
    def stance(self, ctx):
        p = self.config.params
        _, _, hist = classic.macd(ctx.close, int(p.get("fast", 12)),
                                  int(p.get("slow", 26)), int(p.get("signal", 9)))
        return _sign_stance(hist)

    def warmup_bars(self):
        p = self.config.params           # slow EMA forms the line, then the signal EMA stacks on it
        return int(p.get("slow", 26)) + int(p.get("signal", 9))

    def warmup_deps(self):
        p = self.config.params
        return (f"EMA({int(p.get('fast', 12))})/EMA({int(p.get('slow', 26))}) line "
                f"+ signal EMA({int(p.get('signal', 9))})")


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

    def warmup_bars(self):
        return int(self.config.params.get("n", 20))

    def warmup_deps(self):
        n = int(self.config.params.get("n", 20))
        return f"EMA({n}) mid + ATR({n}) band"


class OBVTrend(StanceIndicator):
    key = "obv"
    def stance(self, ctx):
        p = self.config.params
        o = classic.obv(ctx.close, ctx.volume)
        ref = classic.sma(o, int(p.get("slope", 20)))
        return _sign_stance(o - ref)

    def warmup_bars(self):
        return int(self.config.params.get("slope", 20))

    def warmup_deps(self):
        return f"OBV vs SMA({int(self.config.params.get('slope', 20))})"


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

    def warmup_bars(self):
        return int(self.config.params.get("n", 20))


class RSIZone(Indicator):
    key = "rsi"
    def directions(self, ctx):
        p = self.config.params
        r = classic.rsi(ctx.close, int(p.get("n", 14)))
        return votes.rsi_directions(r, float(p.get("lower", 30)), float(p.get("upper", 70)))

    def warmup_bars(self):
        return int(self.config.params.get("n", 14))


class StochasticZone(Indicator):
    key = "stochastic"
    def directions(self, ctx):
        p = self.config.params
        k, _ = classic.stochastic(ctx.high, ctx.low, ctx.close,
                                  int(p.get("n", 14)), int(p.get("d", 3)))
        return votes.rsi_directions(k, float(p.get("lower", 20)), float(p.get("upper", 80)))

    def warmup_bars(self):                # %K needs n, %D = SMA(%K, d) stacks ⇒ n + d - 1
        p = self.config.params
        return int(p.get("n", 14)) + int(p.get("d", 3)) - 1

    def warmup_deps(self):
        p = self.config.params
        return f"%K({int(p.get('n', 14))}) + %D SMA({int(p.get('d', 3))})"


class MFIZone(Indicator):
    key = "mfi"
    def directions(self, ctx):
        p = self.config.params
        m = classic.mfi(ctx.high, ctx.low, ctx.close, ctx.volume, int(p.get("n", 14)))
        return votes.rsi_directions(m, float(p.get("lower", 20)), float(p.get("upper", 80)))

    def warmup_bars(self):
        return int(self.config.params.get("n", 14))


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

    def warmup_bars(self):
        return int(self.config.params.get("n", 20))


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

    def warmup_bars(self):                # ATR/DX over n, then ADX = Wilder-smoothed DX over n ⇒ ~2n
        return 2 * int(self.config.params.get("n", 14)) - 1

    def warmup_deps(self):
        n = int(self.config.params.get("n", 14))
        return f"ATR({n}) + DX, then ADX smoothed over {n}"


class StructureTrend(StanceIndicator):
    key = "structure_trend"
    def stance(self, ctx):
        return smc.structure_trend(ctx.close, int(self.config.params.get("swing_l", 2)))

    def warmup_bars(self):                # a swing pivot is only confirmed swing_l bars after it
        return int(self.config.params.get("swing_l", 2))

    def warmup_deps(self):
        return f"confirmed swings (l={int(self.config.params.get('swing_l', 2))})"


class OrderBlock(StanceIndicator):
    key = "order_block"
    _supports_signal_at = True          # task #210 Step E: can compute its signal only at sampled bars

    def stance(self, ctx, signal_at=None):
        return smc.order_blocks(ctx.open, ctx.high, ctx.low, ctx.close,
                                int(self.config.params.get("swing_l", 2)), signal_at=signal_at)

    def directions(self, ctx, signal_at=None):
        # override StanceIndicator.directions so the (optional) sampled-overlap index set reaches
        # order_blocks; default None ⇒ full computation (decision-TF path + parity unchanged).
        return votes.stance_directions(self.stance(ctx, signal_at=signal_at))

    def warmup_bars(self):
        return int(self.config.params.get("swing_l", 2))

    def warmup_deps(self):
        return f"confirmed swings (l={int(self.config.params.get('swing_l', 2))})"


class FVGConfirm(StanceIndicator):
    key = "fvg"
    def stance(self, ctx):
        return smc.fvg_active_direction(ctx.high, ctx.low, int(self.config.params.get("lookback", 3)))

    def warmup_bars(self):
        return int(self.config.params.get("lookback", 3))


class IFVGConfirm(StanceIndicator):
    """Inverse FVG (Q6): an FVG that price closed through inverts to an opposing S/R zone; +1 within a live
    bullish IFVG, -1 within a bearish one. Stateful zone detector ⇒ supports the sampled-bar (signal_at) path."""
    key = "ifvg"
    _supports_signal_at = True

    def stance(self, ctx, signal_at=None):
        return smc.ifvg(ctx.high, ctx.low, ctx.close, signal_at=signal_at)

    def directions(self, ctx, signal_at=None):
        return votes.stance_directions(self.stance(ctx, signal_at=signal_at))

    def warmup_bars(self):
        return 3                              # FVG needs 3 candles before it can form/invert


class BreakerBlock(StanceIndicator):
    """Breaker block (Q6): an order block price closed beyond flips role/direction into an entry zone; +1 within
    a live bullish breaker, -1 within a bearish one. Stateful ⇒ supports the sampled-bar (signal_at) path."""
    key = "breaker"
    _supports_signal_at = True

    def stance(self, ctx, signal_at=None):
        return smc.breaker_blocks(ctx.open, ctx.high, ctx.low, ctx.close,
                                  int(self.config.params.get("swing_l", 2)), signal_at=signal_at)

    def directions(self, ctx, signal_at=None):
        return votes.stance_directions(self.stance(ctx, signal_at=signal_at))

    def warmup_bars(self):
        return int(self.config.params.get("swing_l", 2))

    def warmup_deps(self):
        return f"confirmed swings (l={int(self.config.params.get('swing_l', 2))})"


class CISDConfirm(StanceIndicator):
    """CISD (Q6): standard Change-In-State-of-Delivery — +1 on a close back through the prior bearish leg's open
    (bullish shift), -1 on a close through the prior bullish leg's open (bearish shift)."""
    key = "cisd"
    def stance(self, ctx):
        return smc.cisd(ctx.open, ctx.close)

    def warmup_bars(self):
        return 1


from . import lib_ma, lib_trend, lib_osc, lib_vol, lib_volume, lib_levels, lib_bw, lib_quant  # noqa: E402
from . import lib_dsp  # noqa: E402  (Tier-2)

_SCHOOLS = (lib_ma, lib_trend, lib_osc, lib_vol, lib_volume, lib_levels, lib_bw, lib_quant, lib_dsp)
_BUILTINS = (
    EMATrend, SMATrend, MACD, VWAPTrend, KeltnerTrend, OBVTrend, CCIBreakout,
    RSIZone, StochasticZone, MFIZone, BollingerVeto, ADXVeto,
    StructureTrend, OrderBlock, FVGConfirm, IFVGConfirm, BreakerBlock, CISDConfirm,
)
REGISTRY = {c.key: c for c in (*_BUILTINS, *(c for m in _SCHOOLS for c in m.CLASSES))}


def build(key: str, config=None) -> Indicator:
    if key not in REGISTRY:
        raise KeyError(f"unknown indicator key {key!r}; known: {sorted(REGISTRY)}")
    return REGISTRY[key](config)


# Per-indicator UI schema (the dashboard hardcodes NOTHING — it renders from this).
# Each: label, default mode, and tunable params [{name, default, min, max, step}].
SCHEMA = {
    "ema_trend":  {"label": "EMA trend", "mode": "confirm",
                   "params": [{"name": "fast", "default": 20, "min": 2, "max": 400, "step": 1},
                              {"name": "slow", "default": 50, "min": 2, "max": 400, "step": 1}]},
    "sma_trend":  {"label": "SMA trend", "mode": "confirm",
                   "params": [{"name": "fast", "default": 50, "min": 2, "max": 400, "step": 1},
                              {"name": "slow", "default": 200, "min": 2, "max": 400, "step": 1}]},
    "macd":       {"label": "MACD", "mode": "confirm",
                   "params": [{"name": "fast", "default": 12, "min": 2, "max": 100, "step": 1},
                              {"name": "slow", "default": 26, "min": 2, "max": 200, "step": 1},
                              {"name": "signal", "default": 9, "min": 1, "max": 100, "step": 1}]},
    "vwap":       {"label": "VWAP", "mode": "confirm", "params": []},
    "keltner":    {"label": "Keltner", "mode": "confirm",
                   "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1},
                              {"name": "m", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1}]},
    "obv":        {"label": "OBV", "mode": "confirm",
                   "params": [{"name": "slope", "default": 20, "min": 2, "max": 200, "step": 1}]},
    "cci":        {"label": "CCI breakout", "mode": "both",
                   "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1},
                              {"name": "threshold", "default": 100, "min": 20, "max": 300, "step": 5}]},
    "rsi":        {"label": "RSI", "mode": "both",
                   "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1},
                              {"name": "lower", "default": 30, "min": 1, "max": 49, "step": 1},
                              {"name": "upper", "default": 70, "min": 51, "max": 99, "step": 1}]},
    "stochastic": {"label": "Stochastic", "mode": "both",
                   "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1},
                              {"name": "d", "default": 3, "min": 1, "max": 50, "step": 1},
                              {"name": "lower", "default": 20, "min": 1, "max": 49, "step": 1},
                              {"name": "upper", "default": 80, "min": 51, "max": 99, "step": 1}]},
    "mfi":        {"label": "MFI", "mode": "both",
                   "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1},
                              {"name": "lower", "default": 20, "min": 1, "max": 49, "step": 1},
                              {"name": "upper", "default": 80, "min": 51, "max": 99, "step": 1}]},
    "bollinger":  {"label": "Bollinger (veto)", "mode": "veto",
                   "params": [{"name": "n", "default": 20, "min": 2, "max": 200, "step": 1},
                              {"name": "k", "default": 2.0, "min": 0.5, "max": 5.0, "step": 0.1}]},
    "adx":        {"label": "ADX (veto)", "mode": "veto",
                   "params": [{"name": "n", "default": 14, "min": 2, "max": 100, "step": 1},
                              {"name": "threshold", "default": 25, "min": 5, "max": 60, "step": 1}]},
    "structure_trend": {"label": "Structure trend (SMC)", "mode": "both",
                        "params": [{"name": "swing_l", "default": 2, "min": 1, "max": 20, "step": 1}]},
    "order_block": {"label": "Order block → breaker (SMC)", "mode": "both",
                    "params": [{"name": "swing_l", "default": 2, "min": 1, "max": 20, "step": 1}]},
    "fvg":        {"label": "Fair value gap (SMC)", "mode": "both",
                   "params": [{"name": "lookback", "default": 3, "min": 1, "max": 50, "step": 1}]},
    "ifvg":       {"label": "Inverse FVG (SMC)", "mode": "both", "params": []},
    "breaker":    {"label": "Breaker block (SMC)", "mode": "both",
                   "params": [{"name": "swing_l", "default": 2, "min": 1, "max": 20, "step": 1}]},
    "cisd":       {"label": "CISD — delivery shift (SMC)", "mode": "both", "params": []},
}
for _m in _SCHOOLS:                       # merge per-school schemas (keys must be unique)
    for _k, _v in _m.SCHEMA.items():
        if _k in SCHEMA:
            raise KeyError(f"duplicate indicator key {_k!r}")
        SCHEMA[_k] = _v
MODES = ("confirm", "veto", "both")
RETRACE_UNITS = ("atr_mult", "points")


def schema():
    """UI schema for every registered indicator (key + label + default mode + tunable params).
    Plus the shared enums. The frontend builds the whole indicator panel from this — no hardcoding."""
    inds = [dict(key=k, **SCHEMA[k]) for k in REGISTRY]
    return {"indicators": inds, "modes": list(MODES), "retrace_units": list(RETRACE_UNITS),
            "retrace_default": {"amount": 0.0, "unit": "atr_mult"}, "wait_default": 0, "k_default": 1,
            "gen_params": [{"name": "swing_l", "default": 2, "min": 1, "max": 20, "step": 1},
                           {"name": "golf_n", "default": 3, "min": 1, "max": 50, "step": 1}]}


def from_specs(specs):
    """Build a list of Indicator instances from dashboard/API specs (strict, no silent fallback).
    Each spec: {key, enabled?, mode?, params?{}}. retrace + wait are GLOBAL (not per-indicator) and
    are NOT read here — see strategy.build_payload → runner.build_layer.
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
            params=dict(s.get("params", {})),
        )
        out.append(REGISTRY[key](cfg))  # constructor validates the config
    return out
