"""Bar-open-known regressors. Computed strictly from bars with close_time <= bar_open_time."""
from __future__ import annotations

import pandas as pd

_TOD_LABELS = ("asia", "eu", "rth_open", "lunch", "rth_close")
_DOW_LABELS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _time_of_day_bucket(hour: int) -> str:
    """Coarse 4h NQ session bucket — five disjoint buckets covering 24h."""
    if 18 <= hour < 22:  return "asia"
    if hour >= 22 or hour < 2:  return "eu"
    if 2 <= hour < 6:    return "eu"
    if 6 <= hour < 10:   return "rth_open"
    if 10 <= hour < 14:  return "lunch"
    return "rth_close"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add regressor columns. df MUST already have a `log_return` column."""
    if "log_return" not in df.columns:
        raise ValueError("build_features requires a `log_return` column (call add_log_return first)")
    out = df.copy()

    out["prior_log_return"] = out["log_return"].shift(1)
    prior_range = (out["high"] - out["low"]) / out["close"]
    out["prior_range"] = prior_range.shift(1)
    out["rolling_20bar_vol"] = out["log_return"].shift(1).rolling(window=20, min_periods=20).std()

    hours = out["datetime"].dt.hour
    tod = hours.apply(_time_of_day_bucket)
    for label in _TOD_LABELS:
        out[f"tod_{label}"] = (tod == label).astype(int)

    dow_num = out["datetime"].dt.dayofweek
    for i, label in enumerate(_DOW_LABELS):
        out[f"dow_{label}"] = (dow_num == i).astype(int)

    return out


REGRESSOR_COLUMNS: tuple[str, ...] = (
    "prior_log_return",
    "prior_range",
    "rolling_20bar_vol",
    *(f"tod_{l}" for l in _TOD_LABELS),
    *(f"dow_{l}" for l in _DOW_LABELS),
)


def usable_regressors(df: pd.DataFrame, candidates: tuple[str, ...] = REGRESSOR_COLUMNS) -> list[str]:
    """Drop regressors with <2 unique values in df (e.g., dow_sat is always 0 for CME futures
    because the market is closed Saturday). NeuralProphet rejects singular columns."""
    return [c for c in candidates if df[c].nunique(dropna=True) >= 2]
