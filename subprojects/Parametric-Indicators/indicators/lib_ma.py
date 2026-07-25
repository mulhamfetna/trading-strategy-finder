"""ma-school indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA by library.py.

Each is a moving-average trend stance: +1 when close>fast>slow (uptrend), -1 when close<fast<slow,
else 0 — identical shape to the built-in EMATrend/SMATrend, differing only in the MA primitive."""
from __future__ import annotations

import numpy as np

from .calc import ma
from .stances import StanceIndicator


class WMATrend(StanceIndicator):
    key = "wma"

    def stance(self, ctx):
        p = self.config.params
        f = ma.wma(ctx.close, int(p.get("fast", 20)))
        s = ma.wma(ctx.close, int(p.get("slow", 50)))
        st = np.zeros(len(ctx.close), dtype=np.int8)
        st[(ctx.close > f) & (f > s)] = 1
        st[(ctx.close < f) & (f < s)] = -1
        return st

    def warmup_bars(self):
        p = self.config.params
        return max(int(p.get("fast", 20)), int(p.get("slow", 50)))

    def warmup_deps(self):
        p = self.config.params
        return f"WMA({int(p.get('fast', 20))}) & WMA({int(p.get('slow', 50))})"


CLASSES = (WMATrend,)
SCHEMA = {
    "wma": {"label": "WMA trend", "mode": "confirm",
            "params": [{"name": "fast", "default": 20, "min": 2, "max": 400, "step": 1},
                       {"name": "slow", "default": 50, "min": 2, "max": 400, "step": 1}]},
}
