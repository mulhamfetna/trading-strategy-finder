"""Forecaster interface + a causal Mock (placeholder) + the real TimesFM wrapper.

The rest of the stack talks ONLY to the `Forecaster` protocol, so we can develop and validate
the whole pipeline against `MockForecaster` (no heavy download, fully causal, no look-ahead) and
then swap in `TimesFMForecaster` by changing one line.

A forecast is a *distribution over the future path*: a median path plus low/high quantiles. The
strategy layer turns that distribution into (direction, edge, risk sizing).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ForecastResult:
    """Per-context forecast over `horizon` steps ahead.

    median : (H,) point forecast (the model's central path)
    q_low  : (H,) low quantile path  (e.g. 10th pct)
    q_high : (H,) high quantile path (e.g. 90th pct)
    All in the SAME units as the input context (we feed close prices).
    """
    median: np.ndarray
    q_low: np.ndarray
    q_high: np.ndarray
    q_low_level: float = 0.1
    q_high_level: float = 0.9


class Forecaster:
    """Interface. Implementations must be strictly causal: they see only `context`."""

    name = "abstract"

    def forecast_batch(self, contexts: list[np.ndarray], horizon: int) -> list[ForecastResult]:
        raise NotImplementedError

    def forecast(self, context: np.ndarray, horizon: int) -> ForecastResult:
        return self.forecast_batch([context], horizon)[0]


class MockForecaster(Forecaster):
    """PLACEHOLDER forecaster — NOT predictive, exists only to exercise the pipeline causally.

    Median path = last close continued with a small damped fraction of the recent drift
    (a weak-momentum random walk). Quantiles = last close +/- rolling realized-vol scaled by
    sqrt(step). It never sees the future. Real TimesFM replaces this entirely; any 'edge' here is
    an artifact of the drift term and should be treated as the null, not a result.
    """

    name = "mock"

    def __init__(self, drift_lookback: int = 24, drift_gain: float = 0.15, vol_lookback: int = 96):
        self.drift_lookback = drift_lookback
        self.drift_gain = drift_gain
        self.vol_lookback = vol_lookback

    def forecast_batch(self, contexts: list[np.ndarray], horizon: int) -> list[ForecastResult]:
        out = []
        z10, z90 = 1.2816, 1.2816  # ~10th/90th pct of a standard normal (symmetric)
        for ctx in contexts:
            ctx = np.asarray(ctx, dtype=float)
            last = ctx[-1]
            # recent per-step drift (points/bar), damped
            lb = min(self.drift_lookback, len(ctx) - 1)
            drift = (ctx[-1] - ctx[-1 - lb]) / lb if lb > 0 else 0.0
            drift *= self.drift_gain
            # per-step realized vol (points) from recent diffs
            vlb = min(self.vol_lookback, len(ctx) - 1)
            diffs = np.diff(ctx[-vlb - 1:]) if vlb > 0 else np.array([0.0])
            sigma1 = float(np.std(diffs)) if diffs.size else 0.0
            steps = np.arange(1, horizon + 1, dtype=float)
            median = last + drift * steps
            band = sigma1 * np.sqrt(steps)
            out.append(ForecastResult(
                median=median,
                q_low=median - z10 * band,
                q_high=median + z90 * band,
            ))
        return out


class TimesFMForecaster(Forecaster):
    """Real Google TimesFM (zero-shot). Lazy-loaded so the harness imports without the package.

    Install:  pip install timesfm[torch]
    Weights are pulled from HuggingFace on first use (google/timesfm-2.5-200m-pytorch).
    """

    name = "timesfm-2.5-200m"

    def __init__(self, horizon_cap: int = 64, context_cap: int = 512,
                 per_core_batch_size: int = 32, normalize: bool = True):
        self.horizon_cap = horizon_cap
        self.context_cap = context_cap
        self.per_core_batch_size = per_core_batch_size
        self.normalize = normalize
        self._model = None

    def _ensure(self):
        if self._model is not None:
            return
        import torch  # noqa: F401
        import timesfm
        from timesfm import ForecastConfig
        torch.set_float32_matmul_precision("high")
        m = timesfm.TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
        # TimesFM 2.5 must be compiled before forecasting. Fix max context/horizon and normalize
        # inputs (essential for price series that live at ~5k..25k levels).
        m.compile(ForecastConfig(
            max_context=self.context_cap,
            max_horizon=self.horizon_cap,
            normalize_inputs=self.normalize,
            fix_quantile_crossing=True,
            per_core_batch_size=self.per_core_batch_size,
        ))
        self._model = m

    def forecast_batch(self, contexts: list[np.ndarray], horizon: int) -> list[ForecastResult]:
        self._ensure()
        h = min(horizon, self.horizon_cap)
        inputs = [np.asarray(c, dtype=float)[-self.context_cap:] for c in contexts]
        n_ctx = len(inputs)
        # NOTE: TimesFM.forecast mutates the list it's given (appends padding), so pass a copy and
        # trust the returned array length. Returns (point[N,H], quantiles[N,H,Q]); Q=[mean,q10..q90].
        point, quantiles = self._model.forecast(horizon=h, inputs=list(inputs))
        point = np.asarray(point)[:n_ctx]
        quantiles = np.asarray(quantiles)[:n_ctx]
        q = quantiles.shape[-1]
        lo_idx, hi_idx = (1, 9) if q >= 10 else (0, q - 1)  # 10th and 90th deciles
        out = []
        for i in range(point.shape[0]):
            out.append(ForecastResult(
                median=point[i][:h],
                q_low=quantiles[i][:h, lo_idx],
                q_high=quantiles[i][:h, hi_idx],
            ))
        return out


def get_forecaster(name: str, **kw) -> Forecaster:
    name = name.lower()
    if name in ("mock", "placeholder"):
        return MockForecaster(**kw)
    if name in ("timesfm", "tfm", "timesfm-2.5", "real"):
        return TimesFMForecaster(**kw)
    raise ValueError(f"unknown forecaster: {name}")
