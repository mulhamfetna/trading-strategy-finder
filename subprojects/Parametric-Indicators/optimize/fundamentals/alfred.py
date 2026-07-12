"""ALFRED point-in-time vintages — the FIRST PRINT of a statistic, as it stood on release morning.

WHY THIS EXISTS. FRED shows you the number as it is TODAY. ALFRED ("ArchivaL FRED") archives every
prior version. The difference is not cosmetic: 2025 payrolls were revised DOWN by 801k-1,032k jobs
between the first print and today. Backtesting a surprise model against today's value would trade on
a number nobody had that morning — roughly a million jobs of hindsight per event.

This module returns, for a given release date, the series EXACTLY as a trader saw it that morning:
every observation that existed then, at the value it then had, and nothing after.

Free. Official (St. Louis Fed). No vendor. Needs only FRED_API_KEY.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

import pandas as pd

_OBS = "https://api.stlouisfed.org/fred/series/observations"


def _key() -> str:
    k = os.environ.get("FRED_API_KEY")
    if not k:
        p = Path.home() / ".config" / "fred" / "api_key"
        if p.exists():
            k = p.read_text().strip()
    if not k:
        raise SystemExit("FRED_API_KEY not set (or ~/.config/fred/api_key missing).\n"
                         "Free key: https://fred.stlouisfed.org/docs/api/api_key.html")
    return k


def vintage(series_id: str, as_of: str) -> pd.Series:
    """The series EXACTLY as it stood on `as_of` (YYYY-MM-DD). Index = reference period, values = the
    numbers published at that time. Nothing released after `as_of` is included, and every value is the
    one then in force — not a later revision.
    """
    url = (f"{_OBS}?series_id={series_id}&api_key={_key()}&file_type=json"
           f"&realtime_start={as_of}&realtime_end={as_of}")
    with urllib.request.urlopen(url, timeout=30) as r:
        obs = json.loads(r.read().decode())["observations"]
    s = pd.Series(
        {pd.Timestamp(o["date"]): (float(o["value"]) if o["value"] not in (".", "") else float("nan"))
         for o in obs}
    ).sort_index().dropna()
    return s
