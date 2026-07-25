"""dsp-school (Tier-2) indicator classes. CLASSES/SCHEMA merged into library.REGISTRY/SCHEMA."""
from __future__ import annotations

from .calc import dsp
from .stances import StanceIndicator, _sign_stance


class SuperSmootherTrend(StanceIndicator):
    """Ehlers SuperSmoother trend: sign(close − SuperSmoother(close, n))."""
    key = "super_smoother"
    def stance(self, ctx):
        return _sign_stance(ctx.close - dsp.super_smoother(ctx.close, int(self.config.params.get("n", 20))))
    def warmup_bars(self): return int(self.config.params.get("n", 20))


CLASSES = (SuperSmootherTrend,)
SCHEMA = {
    "super_smoother": {"label": "Ehlers SuperSmoother trend", "mode": "confirm",
                       "params": [{"name": "n", "default": 20, "min": 4, "max": 200, "step": 1}]},
}
