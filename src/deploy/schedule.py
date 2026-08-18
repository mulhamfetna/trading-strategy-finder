"""WS-DEPLOY D1 (#128) — the release schedule: generation and loading.

The executor is SCHEDULE-DRIVEN: it needs nothing but the known release timestamps. This module
turns the TradingView calendar into a small committed `release_schedule.csv` and loads it back
with validation.

⚠️ REPLAY-PARITY CONSTRAINT (the reason the generation pipeline looks pedantic): the M3 study
selected events as  load_tv_events() -> [5-series verified+FOMC set, actual & forecast present,
per-instrument floor, sort by time, DEDUPE same-minute keep-first] -> filter to the 3 target
series. The dedupe happens BEFORE the target filter, so a CPI print sharing a minute with a
Retail Sales print may be dropped entirely. To reproduce M3's event set EXACTLY, the generator
replicates that order of operations — including the pre-filter dedupe — and records for each row
whether it is `confirmed` (actual existed at generation time; used by replay) or `scheduled`
(future; used by paper mode).

Regeneration (documented update path for future dates):
    python3 -m src.deploy.schedule --tv-csv <path to tv_us_calendar_raw.csv> \
        --out src/deploy/data/release_schedule.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

VERIFIED_SET = ["Non Farm Payrolls", "Inflation Rate MoM", "Retail Sales MoM",
                "Durable Goods Orders MoM", "Fed Interest Rate Decision"]
TARGET_SERIES = ["Inflation Rate MoM", "Non Farm Payrolls", "Fed Interest Rate Decision"]
FLOOR_YEAR = 2016

HERE = Path(__file__).resolve().parent
DEFAULT_SCHEDULE = HERE / "data" / "release_schedule.csv"


def generate(tv_csv: Path, out: Path) -> pd.DataFrame:
    d = pd.read_csv(tv_csv, low_memory=False)
    d["utc"] = pd.to_datetime(d["date"], format="mixed", utc=True)
    d["et"] = d["utc"].dt.tz_convert("America/New_York").dt.tz_localize(None)

    # ⚠️ The confirmed set replicates M3's load_tv_events() VERBATIM — including pandas'
    # DEFAULT (non-stable) sort before the same-minute dedupe. The first version used a stable
    # sort and lost 2 CPI events on shared 8:30 minutes to a different tie-break (2017-02-15,
    # 2017-06-14): the committed evidence was produced by the default sort's order, so parity
    # means replicating it call-for-call, not "equivalently".
    conf = d[d.title.isin(VERIFIED_SET) & d.actual.notna() & d.forecast.notna()]
    conf = conf[conf.et.dt.year >= FLOOR_YEAR].sort_values("et").reset_index(drop=True)
    conf = conf.drop_duplicates(subset="et", keep="first").reset_index(drop=True)
    conf = conf[conf.title.isin(TARGET_SERIES)][["title", "et"]].copy()
    conf["status"] = "confirmed"

    # scheduled rows: future events with no actual yet (paper mode only)
    fut = d[d.title.isin(TARGET_SERIES) & d.actual.isna()]
    fut = fut[fut.et.dt.year >= FLOOR_YEAR][["title", "et"]].copy()
    fut["status"] = "scheduled"

    sched = pd.concat([conf, fut]).sort_values("et").reset_index(drop=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    sched.to_csv(out, index=False)
    print(f"wrote {out}: {len(conf)} confirmed + {len(fut)} scheduled rows "
          f"({sched.et.min()} .. {sched.et.max()})")
    return sched


def load(path: Path = DEFAULT_SCHEDULE) -> pd.DataFrame:
    s = pd.read_csv(path, parse_dates=["et"])
    missing = {"title", "et", "status"} - set(s.columns)
    if missing:
        raise ValueError(f"schedule {path} missing columns {missing}")
    bad = set(s.title.unique()) - set(TARGET_SERIES)
    if bad:
        raise ValueError(f"schedule contains non-target series {bad}")
    if s.et.duplicated().any():
        raise ValueError("schedule contains duplicate timestamps — regenerate")
    return s.sort_values("et").reset_index(drop=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tv-csv", required=True)
    ap.add_argument("--out", default=str(DEFAULT_SCHEDULE))
    a = ap.parse_args()
    generate(Path(a.tv_csv), Path(a.out))
