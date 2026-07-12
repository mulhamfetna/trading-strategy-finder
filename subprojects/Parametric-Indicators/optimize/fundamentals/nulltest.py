"""The honesty harness: fake release calendars.

If the veto rule "works" just as well on a FAKE calendar, it has not learned anything about news --
it has learned that flattening trades sometimes helps. That is a fact about our stop placement, not
about the world, and it would not generalise to a single future release.

The fake preserves the event COUNT and the TIME-OF-DAY distribution (08:30 / 14:00) and changes only
the DATES -- to days with no real release. Randomising the clock time too would merely rediscover
that 08:30 is a volatile minute, which we already know and which is not the claim under test.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def fake_calendar(cal: pd.DataFrame, df1: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Same size, same clock times, different (release-free) dates. Deterministic per seed."""
    rng = np.random.default_rng(seed)

    all_days = pd.Series(df1["Date"].dt.normalize().unique()).sort_values()
    real_days = set(cal["Date"].dt.normalize())
    free_days = np.array([d for d in all_days if d not in real_days], dtype="datetime64[ns]")
    if len(free_days) < len(cal):
        raise ValueError(f"only {len(free_days)} release-free days for {len(cal)} fake events")

    picks = rng.choice(free_days, size=len(cal), replace=False)
    times = cal["Date"].dt.strftime("%H:%M:%S").to_numpy()   # preserve the time-of-day mix

    rows = [
        {"Date": pd.Timestamp(f"{pd.Timestamp(d).date()} {t}"), "event": "fake", "agency": "NULL"}
        for d, t in zip(picks, times)
    ]
    return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
