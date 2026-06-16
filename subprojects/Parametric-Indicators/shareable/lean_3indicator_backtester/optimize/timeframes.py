"""Decision-timeframe registry for WS-H (H.3 foundation, used by H.1's core).

ONLY the entry/decision candle varies across timeframes; exits always resolve on 1-minute
(see TASK.md §2). Each timeframe is described by:
  - name:        the label used everywhere (matches the data filenames NQ_<name>.csv)
  - minutes:     bar duration in minutes (drives the 1m sub-bar window bound + the vol window)
  - bar_td:      the same duration as a pandas Timedelta (the `+4h`-style slice bound, generalised)

The raw all-history CSVs live under Full_Canldes_Data/ (one file per timeframe). The 4h winner,
however, is reproduced from the per-year split files in DATA_ROOT (data/<year>_data/), so the
parity test (H.1) uses those; the optimiser proper (H.7) reads whichever source we point it at.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Timeframe:
    name: str
    minutes: int

    @property
    def bar_td(self) -> pd.Timedelta:
        return pd.Timedelta(minutes=self.minutes)


# The 7 available decision timeframes, finest → coarsest.
TIMEFRAMES = {
    "1m":  Timeframe("1m", 1),
    "2m":  Timeframe("2m", 2),
    "5m":  Timeframe("5m", 5),
    "15m": Timeframe("15m", 15),
    "1h":  Timeframe("1h", 60),
    "2h":  Timeframe("2h", 120),
    "4h":  Timeframe("4h", 240),
}

# Raw all-history source (Google-drive dump). Per-timeframe NQ_<name>.csv.
RAW_DIR = "Full_Canldes_Data/drive-download-20260602T124702Z-3-001"


def get(name: str) -> Timeframe:
    if name not in TIMEFRAMES:
        raise KeyError(f"unknown timeframe {name!r}; known: {list(TIMEFRAMES)}")
    return TIMEFRAMES[name]
