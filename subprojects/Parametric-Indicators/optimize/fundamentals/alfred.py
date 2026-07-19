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
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

_OBS = "https://api.stlouisfed.org/fred/series/observations"

# Transient HTTP codes. These are the network having a bad day, NOT an answer about the data.
# A release dropped because of one of these is a SILENT SAMPLE LOSS — so we retry instead.
_TRANSIENT = {429, 500, 502, 503, 504}

RETRIES = 4
BACKOFF = 1.5          # seconds; doubles each attempt


class SeriesNotInAlfred(Exception):
    """The series genuinely does not exist in ALFRED at that date. EXPECTED, PERMANENT, NOT AN ERROR.

    ALFRED only archives a series from its first vintage onward. PPIFIS (PPI Final Demand) has no
    vintage before 2014-02-19, so all 43 PPI releases in our 2010-2026 calendar that predate it return
    HTTP 400 "The series does not exist in ALFRED but may exist in FRED."

    This is a FACT ABOUT THE DATA, not a failure. It must be counted and reported separately from a
    network blip — otherwise 43 expected drops and 1 real, recoverable loss look identical in the log,
    which is exactly what happened on 2026-07-14 and cost a healthy run its life.
    """



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


def vintage(series_id: str, as_of: str, retries: int = RETRIES) -> pd.Series:
    """The series EXACTLY as it stood on `as_of` (YYYY-MM-DD). Index = reference period, values = the
    numbers published at that time. Nothing released after `as_of` is included, and every value is the
    one then in force — not a later revision.

    Raises SeriesNotInAlfred if the series predates ALFRED's archive (expected — see the class docstring).
    Retries transient network failures with exponential backoff, because a release lost to a 502 is a
    silent hole in the sample. Re-raises anything still failing after `retries` attempts: a caller that
    swallows it would be re-introducing exactly the bug this function exists to prevent.
    """
    url = (f"{_OBS}?series_id={series_id}&api_key={_key()}&file_type=json"
           f"&realtime_start={as_of}&realtime_end={as_of}")

    last: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                obs = json.loads(r.read().decode())["observations"]
            break
        except urllib.error.HTTPError as e:
            # HTTP 400 from ALFRED means "this series has no vintage that far back". Permanent.
            # Retrying it 4 times just wastes 4 round-trips to be told the same thing.
            if e.code == 400:
                raise SeriesNotInAlfred(f"{series_id} has no ALFRED vintage at {as_of}") from e
            if e.code not in _TRANSIENT or attempt == retries - 1:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == retries - 1:
                raise
            last = e
        time.sleep(BACKOFF * (2 ** attempt))
    else:                                                    # pragma: no cover - loop always breaks/raises
        raise last if last else RuntimeError("unreachable")

    s = pd.Series(
        {pd.Timestamp(o["date"]): (float(o["value"]) if o["value"] not in (".", "") else float("nan"))
         for o in obs}
    ).sort_index().dropna()
    return s
