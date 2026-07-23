"""M1 (supply) and M2 (gate survival) for the daily-box study."""
from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
import pandas as pd

from research.daily_boxes.study_signals import LevelPairs, study_signals


def supply_stats(df_dec: pd.DataFrame, box: pd.DataFrame,
                 base_pairs: LevelPairs, daily_pairs: LevelPairs) -> dict:
    """How much NEW signal supply do the daily zones add on top of the base (weekly+monthly) set?

    'New' means a daily signal on a bar where the base set produced 'hold' — a daily signal that merely
    duplicates an existing weekly/monthly one adds no tradeable supply and is deliberately not counted.
    """
    base = study_signals(df_dec, box, base_pairs)
    daily = study_signals(df_dec, box, daily_pairs)
    combined = study_signals(df_dec, box, list(base_pairs) + list(daily_pairs))

    base_fires = base != "hold"
    daily_fires = daily != "hold"
    new_mask = daily_fires & ~base_fires

    day = pd.DatetimeIndex(df_dec["Date"]).normalize()
    per_day = pd.DataFrame({"day": day, "base": base_fires, "daily": daily_fires})
    grouped = per_day.groupby("day").any()

    return {
        "base_signals": int(base_fires.sum()),
        "daily_signals": int(daily_fires.sum()),
        "combined_signals": int((combined != "hold").sum()),
        "new_signals": int(new_mask.sum()),
        "new_mask": new_mask,
        "days_total": int(len(grouped)),
        "days_with_base_signal": int(grouped["base"].sum()),
        "days_scarce": int((~grouped["base"]).sum()),
        "days_rescued_by_daily": int((~grouped["base"] & grouped["daily"]).sum()),
    }


# Verdict bands, fixed in the design spec BEFORE any number was seen (spec section 6).
_LARGE_THRESHOLD = 0.20        # >= 20% uplift -> go B
_NEGLIGIBLE_THRESHOLD = 0.05   # <  5% uplift -> negligible


def gate_survival(new_mask: np.ndarray, gate: np.ndarray, baseline_entries: int) -> dict:
    """Of the NEW daily signals, how many land on bars the champion's live gate would have passed?

    `gate` is the engine's effective per-bar gate (vol_gate & ~veto & confirm). This is an UPPER BOUND on new
    takeable entries: it ignores position-carry, cooldown and the breaker, any of which can still block a bar
    the gate allowed.
    """
    if baseline_entries <= 0:
        raise ValueError(f"baseline_entries must be positive, got {baseline_entries}")
    new_mask = np.asarray(new_mask, dtype=bool)
    gate = np.asarray(gate, dtype=bool)
    if new_mask.shape != gate.shape:
        raise ValueError(f"shape mismatch: new_mask {new_mask.shape} vs gate {gate.shape}")

    surviving = int((new_mask & gate).sum())
    uplift = surviving / float(baseline_entries)
    if uplift >= _LARGE_THRESHOLD:
        band = "large"
    elif uplift < _NEGLIGIBLE_THRESHOLD:
        band = "negligible"
    else:
        band = "gray"
    return {
        "new_signals": int(new_mask.sum()),
        "gate_surviving": surviving,
        "uplift": uplift,
        "verdict_band": band,
    }
