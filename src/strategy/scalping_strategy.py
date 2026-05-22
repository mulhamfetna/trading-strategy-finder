"""Scalping strategy configuration + preparation pipeline (iter 7, item 6b).

OOP wrapper around the existing FP indicator/signal/ML pipeline. Stores
the strategy configuration (RSI period, EMA periods, volume threshold,
ML toggle) and exposes a single ``prepare(df)`` entry that runs the
full pipeline.

The actual transforms (RSI/EMA/volume spike calculation, signal rule
evaluation, ML feature engineering) stay FP - they're called from
prepare() but their implementations live in src/indicators/ and
src/signals/ where they're shared with the other strategies.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

from src.indicators.scalping import (
    calculate_rsi,
    calculate_ema,
    calculate_volume_spike,
)
from src.signals.base_signals import generate_scalping_signals
from src.signals.ml_filter import train_ml_filter, apply_ml_filter, add_ml_features


class ScalpingStrategy:
    """Scalping strategy configuration + preparation pipeline.

    Defaults match the v1.0.0 frozen parameters
    (``best_config.txt`` historical: rsi_period=5, ema=5/15,
    vol_threshold=2.0).

    Usage::

        strat = ScalpingStrategy()
        train = strat.prepare(train_df)
        ml = strat.train_ml(train)
        test = strat.prepare(test_df)
        test = strat.apply_ml(test, ml)
    """

    def __init__(
        self,
        rsi_period: int = 5,
        ema_fast: int = 5,
        ema_slow: int = 15,
        vol_threshold: float = 2.0,
        use_ml: bool = True,
    ):
        self.rsi_period = rsi_period
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.vol_threshold = vol_threshold
        self.use_ml = use_ml

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run the indicator + signal + ML-features pipeline on a copy of
        the input DataFrame. The input is not mutated.

        Returns a DataFrame with:
          - ``rsi_<period>`` (e.g. ``rsi_5``)
          - ``ema_<fast>``, ``ema_<slow>`` (e.g. ``ema_5``, ``ema_15``)
          - ``volume_spike`` (bool)
          - ``signal`` (-1/0/1) - the rule-based signal
          - ML feature columns (when ``use_ml=True``)
        """
        out = df.copy()
        out = calculate_rsi(out, period=self.rsi_period)
        out = calculate_ema(out, periods=[self.ema_fast, self.ema_slow])
        out = calculate_volume_spike(out, threshold=self.vol_threshold)
        out = generate_scalping_signals(out, rsi_period=self.rsi_period)
        if self.use_ml:
            out = add_ml_features(out)
        return out

    def train_ml(self, prepared_df: pd.DataFrame):
        """Train the Random Forest filter on a prepared training DataFrame.

        ``prepared_df`` must already have the ML feature columns (i.e.
        ``prepare()`` was called with ``use_ml=True``). Returns whatever
        ``train_ml_filter`` returns (the model + feature spec dict).
        """
        if not self.use_ml:
            raise RuntimeError(
                "train_ml called on a strategy configured with use_ml=False"
            )
        return train_ml_filter(prepared_df)

    def apply_ml(self, prepared_df: pd.DataFrame, ml_data) -> pd.DataFrame:
        """Apply a trained ML filter to a prepared DataFrame. Returns a
        new DataFrame with the ML-filtered signal column."""
        if not self.use_ml:
            raise RuntimeError(
                "apply_ml called on a strategy configured with use_ml=False"
            )
        return apply_ml_filter(prepared_df, ml_data)
