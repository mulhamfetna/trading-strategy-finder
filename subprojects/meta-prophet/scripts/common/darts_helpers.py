"""Shared Darts helpers — keep model-driver scripts DRY.

Darts' TimeSeries class requires uniform frequency for most DL models (same root-cause class
as NeuralProphet's uniform-grid issue — see notes/09_neuralprophet_root_cause_report.md).
Workaround: use an integer (RangeIndex) instead of datetime. The model sees a 1-bar = 1-unit
sequence and never has to reason about calendar gaps.

Accelerator is selectable via the MP_ACCELERATOR env var (default "cpu" preserves the
original local behaviour). On the ROCm server set MP_ACCELERATOR=gpu to train on the
RX 6700 XT (also export HSA_OVERRIDE_GFX_VERSION=10.3.0 for the gfx1031 override).
"""
from __future__ import annotations

import os
from typing import Sequence

import numpy as np
import pandas as pd

# Accelerator selectable via MP_ACCELERATOR (default "cpu" preserves local behaviour).
_ACCEL = os.environ.get("MP_ACCELERATOR", "cpu").lower()

# Only hide CUDA when we explicitly want CPU; otherwise leave the caller's
# CUDA_VISIBLE_DEVICES intact so the GPU stays reachable.
if _ACCEL == "cpu":
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

from darts import TimeSeries  # noqa: E402


PL_TRAINER_KWARGS = {
    "enable_progress_bar":   False,
    "enable_model_summary":  False,
    "logger":                False,
    "accelerator":           _ACCEL,
}
if _ACCEL == "gpu":
    PL_TRAINER_KWARGS["devices"] = 1


def to_target_series(df: pd.DataFrame) -> TimeSeries:
    """log_return → integer-indexed Darts TimeSeries. Drops the first NaN."""
    s = df.dropna(subset=["log_return"]).copy().reset_index(drop=True)
    values = s["log_return"].astype(float).to_numpy().reshape(-1, 1)
    return TimeSeries.from_values(values, columns=["log_return"])


def to_covariate_series(df: pd.DataFrame, cols: Sequence[str]) -> TimeSeries:
    """Bar-open-known regressors → integer-indexed Darts TimeSeries (for past_covariates)."""
    s = df.dropna(subset=["log_return", *cols]).copy().reset_index(drop=True)
    values = s[list(cols)].astype(float).to_numpy()
    return TimeSeries.from_values(values, columns=list(cols))
