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
