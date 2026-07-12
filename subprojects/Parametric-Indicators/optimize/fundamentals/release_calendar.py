"""Load + validate the committed three-star US release calendar. Pure; no network.

Timestamps are tz-naive US-Eastern wall-clock, matching the bar frames. Verified empirically: mean
1-minute volume peaks at 09:30 and 15:59-16:00 (the US cash open/close) and the session opens at
18:00 (the CME Globex reopen). US economic releases are announced in Eastern time, so a release
timestamp compares directly against df['Date'] with no conversion and no DST handling.

The calendar is produced by fetch_calendar.py and COMMITTED as us_high_impact.csv, so every backtest
is reproducible from the repo without a network call or an API key.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CALENDAR_CSV = Path(__file__).parent / "us_high_impact.csv"

# Every release we can authoritatively source lands on one of exactly two Eastern clock times:
#   08:30 - BLS (payrolls, CPI, PPI), BEA (GDP, PCE), Census (retail sales)
#   14:00 - Federal Reserve (FOMC statement)
#
# 10:00 (ISM manufacturing / services) is a KNOWN GAP: FRED does not carry ISM (it is proprietary),
# and we refuse to rule-derive its dates. See the note in fetch_calendar.py. If ISM is ever sourced
# properly, add "10:00" here.
VALID_TIMES = {"08:30", "14:00"}


def load_calendar(path: str | None = None) -> pd.DataFrame:
    """Return the release calendar as ['Date', 'event', 'agency'], sorted, deduplicated.

    Raises ValueError if any timestamp falls outside the three known release times. That is almost
    always a timezone bug, and it must fail loudly rather than silently mis-window every backtest.
    """
    p = Path(path) if path else CALENDAR_CSV
    if not p.exists():
        raise FileNotFoundError(
            f"release calendar not found: {p}\n"
            "Build it with: FRED_API_KEY=... python3 optimize/fundamentals/fetch_calendar.py"
        )
    df = pd.read_csv(p, parse_dates=["Date"])
    df = df[["Date", "event", "agency"]].sort_values("Date").reset_index(drop=True)
    df = df.drop_duplicates(subset=["Date"], keep="first").reset_index(drop=True)

    bad = set(df["Date"].dt.strftime("%H:%M")) - VALID_TIMES
    if bad:
        raise ValueError(
            f"unexpected release time(s) {sorted(bad)} — expected {sorted(VALID_TIMES)}. "
            "This is almost certainly a timezone bug in the calendar build."
        )
    return df
