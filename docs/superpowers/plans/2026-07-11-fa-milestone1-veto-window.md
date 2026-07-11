# Fundamental Analysis — Milestone 1: The Veto Window — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block new entries and force-flatten not-yet-profitable open trades during a measured
volatility window around scheduled high-impact US economic releases — and prove the effect is
distinguishable from chance.

**Architecture:** A committed CSV of release timestamps (built from FRED's release-dates API + a
hand-curated release-time map + the Fed's JSON calendar) is turned into a boolean mask over the
decision frame. That mask is AND-ed into the existing composite `entry_gate` (the one thing both
engines actually consult to block a trade), and a new `NEWS_VETO` exit candidate is threaded through
both engines exactly the way `cap_mode="eod"` already is. The feature defaults OFF and must be
byte-identical to today when off.

**Tech Stack:** Python 3, pandas, numpy, pytest. No new dependencies.

---

## Global Constraints

Copy these into every task's mental checklist. Violating any one of them breaks the build.

- **Project root for every command:** `/mnt/data/projects/trading/subprojects/Parametric-Indicators`
- **Required env for every run:**
  `export WSH_DATA_BASE=/mnt/data/projects/trading WSG_DATA_ROOT=/mnt/data/projects/trading/data`
- **Identity default is non-negotiable.** With the feature off (`news_veto=False`), every result must
  be **byte-identical** to today. The repo rule (`MASTER.md:167`) is: *every engine change must keep
  the golden 6/6 + the anchors byte-identical.* Gate: `python3 perf/check_golden.py`.
- **Two engines, one contract.** `engine.py` (exact/causal) and `optimize/fast_engine.py` (vectorized)
  must agree trade-for-trade. Gate: `python3 optimize/test_fast_parity.py`.
- **Masks are `bool[len(df_dec)]`, entry-bar aligned.** Convention (`indicators/runner.py:188`):
  `out[1:] = raw[:-1]; out[0] = <identity>`. Index `idx` describes the bar you would **enter** on;
  its signal came from bar `idx-1`. Getting this shift wrong introduces look-ahead.
- **`fast_engine` masks are NOT bounds-tolerant.** `engine.py:473` treats out-of-range as
  "not blocked"; `fast_engine.py:97` indexes raw. Arrays must be **exactly** `len(d_dates)`.
- **`fast_engine` skips bars** (`idx = max(idx+1, nxt)`, fast_engine.py:230-231) while `engine` sweeps
  every bar. Never rely on a per-bar side effect.
- **Timezone:** all bar `Date` values are **tz-naive US Eastern wall-clock**. Verified empirically:
  mean volume peaks at `09:30` and `15:59–16:00` (US cash open/close) and the session starts `18:00`
  (CME Globex reopen). US economic releases are announced in Eastern time, so **no timezone
  conversion is needed and DST is handled for free.**
- **Data span:** NQ 1-minute data runs **2025-01-01 18:00 → 2026-05-19 19:59**. Not to "today".
- **In-sample / out-of-sample split is already defined:** `config.YEARS = (2025, 2026)`;
  `load_inputs` returns `n_split` = number of decision bars in 2025. **2025 = in-sample,
  2026 = out-of-sample.** Measure on 2025. Test on 2026. Never both on the same data.
- **Point values:** `NQ = 20.0`, `CL = 1000.0` (`optimize/instruments.py:25-26`).
- **Commit after every task.** Tests colocated with source as `optimize/test_*.py`.

### The real `core.backtest_metrics` contract (verified — do not guess it)

```python
core.backtest_metrics(
    df_dec, df1, box, vf, n_split,      # positional — from data.load_inputs(tf, instrument)
    params: dict,
    bar_duration: pd.Timedelta,         # positional
    *, gate_ref_vf=None, sig_int=None, gate_used=None, contrib=None,
    pv: float = config.NQ_POINT_VALUE,  # point value — CL needs pv=1000.0
) -> dict
```

**Returned metric keys** (`optimize/core.py:364-380`) — the names matter:

`pnl` · **`pnl_2025`** · **`pnl_2026`** · `max_dd` · `n_taken` · `n_candidates` ·
`n_skipped_breaker` · `exposure` · `win` · `pf` · `payoff` · `n_locks` · **`trades`**

Two things to note, because they simplify the plan:
- It is **`pnl`**, not `total_pnl`.
- **`pnl_2025` and `pnl_2026` are already split out.** The in-sample / out-of-sample separation is
  built into the engine's own metrics — Task 6 does not need to slice anything by hand.
- **`trades` is always returned.** There is no `want_trades` flag.

Every test below uses this one helper rather than repeating the seven-argument call:

```python
def _run(tf="4h", inst="NQ", **over):
    from optimize import data, core, signals, timeframes as TF
    from optimize.fast_engine import signals_to_int
    from presets import champion_preset
    from optimize import instruments
    df_dec, df1, box, vf, n_split = data.load_inputs(tf, instrument=inst)
    p = dict(champion_preset(tf)); p.update(over)
    return core.backtest_metrics(
        df_dec, df1, box, vf, n_split, p, TF.get(tf).bar_td,
        sig_int=signals_to_int(signals.decision_signals(df_dec, box)),
        pv=instruments.point_value(inst),
    )
```

### The two lines that actually block a trade

Discovered during planning; the spec's phrasing ("add one more veto mask") was **wrong**. The
`veto_mask` parameter does **not** block — it only drives flip / carry-abort / intra-candle-rescue.
The composite `entry_gate` is the sole blocker:

| Engine | Read | **Block** |
|---|---|---|
| `engine.py` | `:473` `gated = ... bool(entry_gate[idx])` | **`:520-521` `if not gated: continue`** |
| `optimize/fast_engine.py` | — | **`:97` `if gate is not None and not gate[idx]:`** |

Callers pre-AND the veto into the gate (`indicators/runner.py:251`, `optimize/core.py:273`).
**Our mask joins the gate the same way.**

### Prerequisite: a free FRED API key

Register at <https://fred.stlouisfed.org/docs/api/api_key.html> (free, instant). Then:

```bash
export FRED_API_KEY=<your key>
```

Verified during planning: `https://api.stlouisfed.org/fred/release/dates?release_id=50&file_type=json`
exists and returns `400 Variable api_key is not set` without one. `www.bls.gov` returns **403 to all
automated fetches** (even with a browser User-Agent) — do **not** plan on scraping it. FRED is the way in.

---

## File Structure

**New package** `optimize/fundamentals/` — one responsibility per file:

| File | Responsibility |
|---|---|
| `optimize/fundamentals/__init__.py` | empty package marker |
| `optimize/fundamentals/fetch_calendar.py` | **one-time CLI.** Hits FRED + the Fed JSON calendar, joins the release-time map, writes the CSV artifact. Never imported by the engine. |
| `optimize/fundamentals/us_high_impact.csv` | **the committed artifact.** What everything else reads. Auditable, diffable, reproducible. |
| `optimize/fundamentals/release_calendar.py` | loads + validates the CSV. Pure, no network. |
| `optimize/fundamentals/window.py` | measures the volatility envelope; builds the decision-frame mask and the 1-min force-exit targets. |
| `optimize/fundamentals/nulltest.py` | generates fake calendars (the honesty harness). |
| `optimize/test_release_calendar.py` | Task 1 tests |
| `optimize/test_release_window.py` | Tasks 2–3 tests |
| `optimize/test_news_veto_parity.py` | Tasks 4–5 tests (engine ↔ fast_engine) |

**Modified:**

| File | Change |
|---|---|
| `engine.py` | `SimpleStrategyParams` += 3 params; `ExitReason` += `NEWS_VETO`; force-exit block |
| `optimize/fast_engine.py` | `fast_backtest` += 1 arg; reason code `R_NEWS_VETO`; `t_news` exit candidate |
| `optimize/core.py` | build + memoise the window arrays; AND the mask into `gate` |

---

## Task 1: The release calendar

**Files:**
- Create: `optimize/fundamentals/__init__.py`
- Create: `optimize/fundamentals/fetch_calendar.py`
- Create: `optimize/fundamentals/release_calendar.py`
- Create: `optimize/fundamentals/us_high_impact.csv` (generated, then committed)
- Test: `optimize/test_release_calendar.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `release_calendar.load_calendar(path: str | None = None) -> pd.DataFrame`
    → columns `["Date", "event", "agency"]`; `Date` is tz-naive datetime64 US-Eastern
      wall-clock; sorted ascending; no duplicate `Date`.
  - `release_calendar.CALENDAR_CSV: Path` — the default artifact path.

**Why FRED and not BLS.** BLS 403s every automated fetch. More importantly, **the 2025 and 2026
government shutdowns rescheduled releases** (BLS publishes "Revised news release dates following the
2025 and 2026 lapses in appropriations", plus a separate September-2025 CPI reschedule notice). FRED's
`release/dates` endpoint records when each statistic **actually came out**, so reschedules are handled
for free rather than special-cased. This matters: a calendar built from originally-planned dates would
veto on quiet days and trade naked through the real ones.

**Release-time map.** FRED gives the **date**; the **time** is a per-release constant in Eastern time.
These nine are the "three-star" set:

| FRED `release_id` | Event | Agency | Time (ET) |
|---|---|---|---|
| 50 | Employment Situation (Non-Farm Payrolls) | BLS | 08:30 |
| 10 | Consumer Price Index | BLS | 08:30 |
| 46 | Producer Price Index | BLS | 08:30 |
| 53 | Gross Domestic Product | BEA | 08:30 |
| 54 | Personal Income & Outlays (PCE) | BEA | 08:30 |
| 8  | Advance Retail Sales | Census | 08:30 |
| 175 | ISM Manufacturing PMI | ISM | 10:00 |
| 176 | ISM Services PMI | ISM | 10:00 |
| — | FOMC statement | Federal Reserve | 14:00 |

**Task 2 independently validates every one of these times** by checking that the measured volatility
spike actually centres on the claimed minute. If a `release_id` or a time is wrong, the envelope comes
out visibly off-centre and the test in Task 2 fails. Do not skip that validation.

- [ ] **Step 1: Write the failing test**

Create `optimize/test_release_calendar.py`:

```python
"""Task 1 — the release calendar loads, validates, and covers the backtest window."""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from optimize.fundamentals import release_calendar as rc


def test_calendar_loads_with_expected_schema():
    cal = rc.load_calendar()
    assert list(cal.columns) == ["Date", "event", "agency"]
    assert pd.api.types.is_datetime64_any_dtype(cal["Date"])
    assert cal["Date"].dt.tz is None, "must be tz-naive US-Eastern wall-clock"


def test_calendar_is_sorted_and_deduplicated():
    cal = rc.load_calendar()
    assert cal["Date"].is_monotonic_increasing
    assert not cal["Date"].duplicated().any()


def test_calendar_covers_the_backtest_window():
    cal = rc.load_calendar()
    assert cal["Date"].min() < pd.Timestamp("2025-02-15")
    assert cal["Date"].max() > pd.Timestamp("2026-04-15")


def test_release_times_are_only_the_three_known_clock_times():
    cal = rc.load_calendar()
    hhmm = set(cal["Date"].dt.strftime("%H:%M"))
    assert hhmm <= {"08:30", "10:00", "14:00"}, f"unexpected release times: {hhmm}"


def test_event_count_is_plausible():
    # ~9 recurring releases over ~17 months. Far fewer means a fetch silently failed;
    # far more means two-star events leaked in.
    cal = rc.load_calendar()
    assert 100 <= len(cal) <= 260, f"got {len(cal)} events"


def test_payrolls_is_present_and_at_0830():
    cal = rc.load_calendar()
    nfp = cal[cal["event"] == "nonfarm_payrolls"]
    assert len(nfp) >= 12, "expected at least 12 payrolls releases in the window"
    assert set(nfp["Date"].dt.strftime("%H:%M")) == {"08:30"}


def test_rejects_a_calendar_with_a_bad_time(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Date,event,agency\n2025-03-07 07:15:00,nonfarm_payrolls,BLS\n")
    with pytest.raises(ValueError, match="unexpected release time"):
        rc.load_calendar(str(bad))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
export WSH_DATA_BASE=/mnt/data/projects/trading WSG_DATA_ROOT=/mnt/data/projects/trading/data
python3 -m pytest optimize/test_release_calendar.py -q
```
Expected: **FAIL** — `ModuleNotFoundError: No module named 'optimize.fundamentals'`

- [ ] **Step 3: Create the package and the fetcher**

Create `optimize/fundamentals/__init__.py` (empty file).

Create `optimize/fundamentals/fetch_calendar.py`:

```python
"""One-time CLI: build the three-star US release calendar from free, authoritative sources.

Dates come from FRED's release/dates API — it records when each statistic ACTUALLY came out, so the
2025/2026 shutdown reschedules are captured for free (BLS's own published schedule was revised, and
www.bls.gov 403s every automated fetch anyway). Times are per-release Eastern-time constants,
independently validated by the volatility-envelope check in optimize/fundamentals/window.py.

  export FRED_API_KEY=...
  python3 optimize/fundamentals/fetch_calendar.py --start 2025-01-01 --end 2026-06-30
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

import pandas as pd

FRED = "https://api.stlouisfed.org/fred/release/dates"
FOMC_JSON = "https://www.federalreserve.gov/json/calendar.json"

# (fred_release_id, event slug, agency, Eastern release time)
RELEASES = [
    (50,  "nonfarm_payrolls", "BLS",    "08:30"),
    (10,  "cpi",              "BLS",    "08:30"),
    (46,  "ppi",              "BLS",    "08:30"),
    (53,  "gdp",              "BEA",    "08:30"),
    (54,  "pce",              "BEA",    "08:30"),
    (8,   "retail_sales",     "Census", "08:30"),
    (175, "ism_manufacturing", "ISM",   "10:00"),
    (176, "ism_services",     "ISM",    "10:00"),
]

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch_fred_dates(release_id: int, start: str, end: str, api_key: str) -> list[str]:
    url = (f"{FRED}?release_id={release_id}&file_type=json&api_key={api_key}"
           f"&realtime_start={start}&realtime_end={end}"
           f"&include_release_dates_with_no_data=false&limit=1000")
    payload = _get_json(url)
    return [d["date"] for d in payload.get("release_dates", [])]


def fetch_fomc_dates(start: str, end: str) -> list[str]:
    """FOMC statement days. The Fed's JSON calendar marks multi-day meetings; the statement lands on
    the LAST day at 14:00 ET."""
    payload = _get_json(FOMC_JSON)
    out = []
    for m in payload.get("mc", []):
        days = m.get("days") or []
        if not days:
            continue
        last = f"{m['year']}-{int(m['month']):02d}-{int(max(days)):02d}"
        if start <= last <= end:
            out.append(last)
    return sorted(set(out))


def build(start: str, end: str, api_key: str) -> pd.DataFrame:
    rows = []
    for rid, event, agency, hhmm in RELEASES:
        dates = fetch_fred_dates(rid, start, end, api_key)
        print(f"  {event:20s} release_id={rid:<4d} -> {len(dates)} dates")
        if not dates:
            raise RuntimeError(f"FRED returned 0 dates for {event} (release_id={rid}) — check the id")
        for d in dates:
            rows.append({"Date": pd.Timestamp(f"{d} {hhmm}:00"), "event": event, "agency": agency})

    fomc = fetch_fomc_dates(start, end)
    print(f"  {'fomc':20s} federalreserve.gov  -> {len(fomc)} dates")
    for d in fomc:
        rows.append({"Date": pd.Timestamp(f"{d} 14:00:00"), "event": "fomc", "agency": "Federal Reserve"})

    df = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
    # Two releases can share a minute (CPI and retail sales never do, but PPI/retail can).
    # Collapse to one row per timestamp: the window is the same either way.
    df = df.drop_duplicates(subset=["Date"], keep="first").reset_index(drop=True)
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--out", default=str(Path(__file__).parent / "us_high_impact.csv"))
    a = ap.parse_args()

    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise SystemExit("FRED_API_KEY not set. Free key: https://fred.stlouisfed.org/docs/api/api_key.html")

    print(f"Building calendar {a.start} .. {a.end}")
    df = build(a.start, a.end, key)
    df.to_csv(a.out, index=False)
    print(f"\nwrote {len(df)} events -> {a.out}")
    print(df["event"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Create the loader**

Create `optimize/fundamentals/release_calendar.py`:

```python
"""Load + validate the committed three-star US release calendar. Pure; no network.

Timestamps are tz-naive US-Eastern wall-clock, matching the bar frames (verified: mean volume peaks
at 09:30 and 15:59-16:00 = the US cash open/close, and the session opens 18:00 = CME Globex reopen).
So a release timestamp compares directly against df['Date'] with no conversion and no DST handling.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CALENDAR_CSV = Path(__file__).parent / "us_high_impact.csv"

# Every three-star US release lands on one of exactly three Eastern clock times.
VALID_TIMES = {"08:30", "10:00", "14:00"}


def load_calendar(path: str | None = None) -> pd.DataFrame:
    """Return the release calendar as ['Date', 'event', 'agency'], sorted, deduplicated.

    Raises ValueError if any timestamp falls outside the three known release times — that is
    almost always a timezone bug, and it must fail loudly rather than silently mis-window.
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
        raise ValueError(f"unexpected release time(s) {sorted(bad)} — expected {sorted(VALID_TIMES)}")
    return df
```

- [ ] **Step 5: Generate the artifact**

```bash
cd /mnt/data/projects/trading/subprojects/Parametric-Indicators
export FRED_API_KEY=<your key>
python3 optimize/fundamentals/fetch_calendar.py --start 2025-01-01 --end 2026-06-30
```
Expected: a per-event date count for all 9 releases (each ≥ 12), then
`wrote NNN events -> .../us_high_impact.csv` with NNN roughly 130–200.

**If any release prints 0 dates, the `release_id` is wrong — stop and look it up at
<https://fred.stlouisfed.org/releases>. Do not proceed with a partial calendar.**

- [ ] **Step 6: Run tests to verify they pass**

```bash
python3 -m pytest optimize/test_release_calendar.py -q
```
Expected: **7 passed**

- [ ] **Step 7: Commit**

```bash
git add optimize/fundamentals/ optimize/test_release_calendar.py
git commit -m "feat(fa): three-star US release calendar from FRED release-dates + Fed JSON

Dates from FRED's release/dates API (records when each statistic ACTUALLY came out, so the
2025/2026 shutdown reschedules are captured for free). Times are per-release Eastern constants,
validated against the volatility envelope in the next task. www.bls.gov 403s all automated
fetches, so FRED is the way in.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Measure the volatility envelope (and validate the calendar)

**Files:**
- Create: `optimize/fundamentals/window.py`
- Test: `optimize/test_release_window.py`

**Interfaces:**
- Consumes: `release_calendar.load_calendar()`; `optimize.data.load_inputs(tf, instrument)`.
- Produces:
  - `window.measure_envelope(df1: pd.DataFrame, cal: pd.DataFrame, pre: int = 60, post: int = 60) -> pd.DataFrame`
    → index `offset_min` in `[-pre, +post]`; columns `["mean_abs_ret_bp", "baseline_bp", "ratio"]`.
    `ratio` = that minute's mean absolute 1-minute return divided by the all-day baseline.
  - `window.derive_bounds(env: pd.DataFrame, threshold: float = 1.5) -> tuple[int, int]`
    → `(pre_min, post_min)`: the contiguous run of `ratio >= threshold` bracketing offset 0.

**The window is measured, not chosen.** We do not pick "15 minutes each side" because 15 is round.
We ask the data when the disturbance actually starts and ends.

**This task also validates Task 1.** If our claimed release times are right, the envelope peaks at
offset 0. If a `release_id` or a clock time is wrong, the peak lands somewhere else and
`test_envelope_peaks_at_offset_zero` fails. That test is the calendar's proof, not a formality.

**One global window, not one per event type.** Deliberate — see spec §3.3. With ~150–200 total
releases, a per-event window means ~20 events per estimate, which is not enough to measure anything.

- [ ] **Step 1: Write the failing test**

Create `optimize/test_release_window.py`:

```python
"""Tasks 2-3 — the volatility envelope, the derived bounds, and the decision-frame mask."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from optimize import data
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals import window as W


def _bundle(tf="4h", inst="NQ"):
    df_dec, df1, _box, _vf, _n = data.load_inputs(tf, instrument=inst)
    return df_dec, df1


def test_envelope_has_one_row_per_offset():
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    assert list(env.index) == list(range(-60, 61))
    assert (env["ratio"] > 0).all()


def test_envelope_peaks_at_offset_zero():
    """THE CALENDAR VALIDATION. If our release timestamps are right, the volatility spike lands ON
    the release minute. If a release_id or a clock time is wrong, it lands elsewhere and this fails."""
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    peak = int(env["ratio"].idxmax())
    assert -1 <= peak <= 1, f"volatility peaks at offset {peak}, not 0 — calendar timestamps are wrong"


def test_release_minute_is_visibly_more_volatile_than_baseline():
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    assert env.loc[0, "ratio"] > 2.0, "the release minute should be >2x a normal minute"


def test_far_from_release_returns_to_baseline():
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    assert env.loc[-60, "ratio"] < 1.6
    assert env.loc[60, "ratio"] < 1.6


def test_derive_bounds_brackets_zero_and_is_sane():
    _, df1 = _bundle()
    env = W.measure_envelope(df1, rc.load_calendar(), pre=60, post=60)
    pre, post = W.derive_bounds(env, threshold=1.5)
    assert pre >= 0 and post >= 1
    assert pre <= 60 and post <= 60


def test_mask_is_decision_length_bool_and_entry_aligned():
    df_dec, df1 = _bundle()
    cal = rc.load_calendar()
    mask = W.release_window_mask(df_dec, cal, pre_min=5, post_min=15)
    assert mask.dtype == np.bool_
    assert len(mask) == len(df_dec)
    assert mask[0] == False, "bar 0 can never be entry-blocked (identity, matches runner.py:188)"
    assert mask.any(), "with a real calendar some decision bars must be inside a window"


def test_mask_is_all_false_for_an_empty_calendar():
    df_dec, _ = _bundle()
    empty = pd.DataFrame({"Date": pd.to_datetime([]), "event": [], "agency": []})
    mask = W.release_window_mask(df_dec, empty, pre_min=5, post_min=15)
    assert not mask.any(), "identity default: no releases => no blocking"


def test_exit_targets_point_at_the_window_open():
    _, df1 = _bundle()
    cal = rc.load_calendar()
    tgt = W.news_exit_targets(df1, cal, pre_min=5)
    assert len(tgt) == len(df1)
    inside = tgt[tgt >= 0]
    assert len(inside) > 0
    # every target must be a valid 1-min index, at or before the bar it is attached to
    assert (inside < len(df1)).all()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest optimize/test_release_window.py -q
```
Expected: **FAIL** — `ImportError: cannot import name 'window'`

- [ ] **Step 3: Write the implementation**

Create `optimize/fundamentals/window.py`:

```python
"""Measure the volatility envelope around scheduled releases; build the masks the engines consume.

Two products:
  1. measure_envelope / derive_bounds  — the window is MEASURED from the data, never chosen.
  2. release_window_mask / news_exit_targets — what the engines actually eat.

Alignment contract (indicators/runner.py:188): the decision-frame mask is ENTRY-BAR aligned. mask[idx]
describes the bar you would ENTER on; its signal came from idx-1. mask[0] is always False.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def measure_envelope(df1: pd.DataFrame, cal: pd.DataFrame,
                     pre: int = 60, post: int = 60) -> pd.DataFrame:
    """Mean absolute 1-minute return at each minute-offset from a release, vs the all-day baseline.

    Returns a frame indexed by offset_min in [-pre, +post] with columns
    ['mean_abs_ret_bp', 'baseline_bp', 'ratio'].  ratio = mean_abs_ret_bp / baseline_bp.
    """
    close = df1["Close"].to_numpy(dtype=np.float64)
    ret_bp = np.zeros(len(close), dtype=np.float64)
    ret_bp[1:] = np.abs(np.diff(close) / close[:-1]) * 10_000.0   # basis points
    baseline = float(ret_bp[1:].mean())

    minute_index = pd.Index(df1["Date"])
    rows = []
    for off in range(-pre, post + 1):
        stamps = cal["Date"] + pd.Timedelta(minutes=off)
        pos = minute_index.get_indexer(stamps)          # -1 where that minute does not exist
        pos = pos[pos >= 0]
        m = float(ret_bp[pos].mean()) if len(pos) else float("nan")
        rows.append({"offset_min": off, "mean_abs_ret_bp": m,
                     "baseline_bp": baseline, "ratio": m / baseline})
    return pd.DataFrame(rows).set_index("offset_min")


def derive_bounds(env: pd.DataFrame, threshold: float = 1.5) -> tuple[int, int]:
    """The contiguous run of elevated volatility that brackets offset 0.

    pre_min  = how many minutes BEFORE the release volatility is already elevated.
    post_min = how many minutes AFTER  the release it stays elevated.
    """
    hot = env["ratio"] >= threshold
    if not bool(hot.get(0, False)):
        raise ValueError("offset 0 is not elevated — the calendar timestamps are almost certainly wrong")

    pre_min = 0
    while (-(pre_min + 1)) in hot.index and bool(hot[-(pre_min + 1)]):
        pre_min += 1
    post_min = 0
    while (post_min + 1) in hot.index and bool(hot[post_min + 1]):
        post_min += 1
    return pre_min, post_min


def _window_edges(cal: pd.DataFrame, pre_min: int, post_min: int):
    starts = (cal["Date"] - pd.Timedelta(minutes=pre_min)).to_numpy(dtype="datetime64[ns]")
    ends = (cal["Date"] + pd.Timedelta(minutes=post_min)).to_numpy(dtype="datetime64[ns]")
    return starts, ends


def release_window_mask(df_dec: pd.DataFrame, cal: pd.DataFrame,
                        pre_min: int, post_min: int) -> np.ndarray:
    """bool[len(df_dec)] — True where a NEW ENTRY must be blocked. Entry-bar aligned.

    A decision bar is 'in a release window' if its OWN timestamp falls inside one. We then shift by
    one bar (out[1:] = raw[:-1]; out[0] = False) so the flag lands on the bar you would ENTER on --
    the same convention as indicators/runner.py:188. Without the shift we would be reading a bar that
    has not closed yet: look-ahead.
    """
    n = len(df_dec)
    raw = np.zeros(n, dtype=bool)
    if len(cal) == 0:
        return raw   # identity: no releases, no blocking

    d = df_dec["Date"].to_numpy(dtype="datetime64[ns]")
    starts, ends = _window_edges(cal, pre_min, post_min)
    for s, e in zip(starts, ends):
        raw |= (d >= s) & (d <= e)

    out = np.zeros(n, dtype=bool)
    out[1:] = raw[:-1]
    out[0] = False
    return out


def news_exit_targets(df1: pd.DataFrame, cal: pd.DataFrame, pre_min: int) -> np.ndarray:
    """int64[len(df1)] — for each 1-min bar, the index of the NEXT window-open at or after it, or -1.

    The engines force-flatten AT the window open (not inside it): once the storm starts we are already
    too late. -1 means 'no release ahead of this bar' => no forced exit.

    Mirrors the shape of optimize/trading_days.py::eod_targets, which is the template this whole
    feature follows.
    """
    n = len(df1)
    tgt = np.full(n, -1, dtype=np.int64)
    if len(cal) == 0:
        return tgt   # identity

    m = pd.Index(df1["Date"])
    starts, _ = _window_edges(cal, pre_min, 0)
    # searchsorted: first 1-min bar at or after each window open
    open_idx = np.searchsorted(m.to_numpy(dtype="datetime64[ns]"), starts, side="left")
    open_idx = np.unique(open_idx[(open_idx >= 0) & (open_idx < n)])
    if len(open_idx) == 0:
        return tgt

    # for every bar, the next window-open at or after it
    pos = np.searchsorted(open_idx, np.arange(n), side="left")
    valid = pos < len(open_idx)
    tgt[valid] = open_idx[pos[valid]]
    return tgt
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest optimize/test_release_window.py -q
```
Expected: **8 passed**

**If `test_envelope_peaks_at_offset_zero` fails, STOP.** It means a release time or `release_id` in
Task 1 is wrong. Fix the calendar, do not loosen the test — that test is the only thing standing
between us and a silently mis-timestamped calendar.

- [ ] **Step 5: Record the measured window**

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from optimize import data
from optimize.fundamentals import release_calendar as rc, window as W
_, df1, *_ = data.load_inputs('4h')
env = W.measure_envelope(df1, rc.load_calendar())
print(env.loc[-10:20, ['ratio']].to_string())
print()
print('DERIVED WINDOW (pre, post) =', W.derive_bounds(env))
"
```
Write the derived `(pre, post)` into the commit message. These are the defaults for Task 4.

- [ ] **Step 6: Commit**

```bash
git add optimize/fundamentals/window.py optimize/test_release_window.py
git commit -m "feat(fa): measure the volatility envelope around releases; derive the window from data

The window is measured, not chosen. test_envelope_peaks_at_offset_zero doubles as the calendar's
proof: if a release timestamp were wrong, the spike would not land on offset 0.

Derived window: pre=<N> post=<N> minutes at ratio>=1.5.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Block entries — wire the mask into the gate (both engines)

**Files:**
- Modify: `engine.py` (params dataclass, ~`:96-100`)
- Modify: `optimize/core.py` (build + memoise the mask; AND into `gate` at `:273`)
- Test: `optimize/test_news_veto_parity.py`

**Interfaces:**
- Consumes: `window.release_window_mask(...)`.
- Produces: three new params, threaded everywhere:
  - `news_veto: bool = False` — master switch. **Off = byte-identical to today.**
  - `news_pre_min: int = 5` — replace with the value derived in Task 2.
  - `news_post_min: int = 15` — replace with the value derived in Task 2.

**The gate is the only blocker.** `engine.py:520` and `fast_engine.py:97`. We do not touch
`veto_mask` — it does not block. We AND into the composite `gate`, exactly as
`optimize/core.py:273` already does: `gate = base & ~vmask & cmask`.

- [ ] **Step 1: Write the failing test**

Create `optimize/test_news_veto_parity.py`:

```python
"""Tasks 3-5 — the news veto blocks entries, force-flattens, and keeps both engines in lockstep."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from optimize import core, data, instruments, signals
from optimize import timeframes as TF
from optimize.fast_engine import signals_to_int
from optimize.fundamentals import release_calendar as rc
from optimize.fundamentals import window as W
from presets import champion_preset


def _run(tf="4h", inst="NQ", **over):
    """The seven-argument call, once. See 'The real core.backtest_metrics contract' above."""
    df_dec, df1, box, vf, n_split = data.load_inputs(tf, instrument=inst)
    p = dict(champion_preset(tf)); p.update(over)
    return core.backtest_metrics(
        df_dec, df1, box, vf, n_split, p, TF.get(tf).bar_td,
        sig_int=signals_to_int(signals.decision_signals(df_dec, box)),
        pv=instruments.point_value(inst),
    )


def test_off_by_default_is_byte_identical():
    """The identity contract. news_veto absent == news_veto=False == today's numbers."""
    base = _run()
    off = _run(news_veto=False)
    assert base["pnl"] == off["pnl"]
    assert base["n_taken"] == off["n_taken"]
    assert base["max_dd"] == off["max_dd"]


def test_veto_on_removes_entries_and_never_adds_any():
    """A veto can only ever REMOVE trades. If it adds one, the mask is inverted or misaligned."""
    off = _run(news_veto=False)
    on = _run(news_veto=True, news_pre_min=5, news_post_min=15)
    assert on["n_taken"] <= off["n_taken"], "the veto ADDED trades — mask is inverted"
    assert on["n_taken"] < off["n_taken"], "the veto removed nothing — mask never fires"


def test_no_entry_lands_inside_a_release_window():
    """The behavioural assertion: with the veto on, ZERO entries occur inside a window."""
    df_dec, *_ = data.load_inputs("4h")
    mask = W.release_window_mask(df_dec, rc.load_calendar(), pre_min=5, post_min=15)

    res = _run(news_veto=True, news_pre_min=5, news_post_min=15)
    entry_idx = np.array([t["entry_idx"] for t in res["trades"]], dtype=int)
    assert not mask[entry_idx].any(), "an entry fired inside a release window"
```

**Plus the parity test.** `optimize/test_fast_parity.py` currently exposes only `main(tf)` — there is
**no reusable comparator**. Extract one: lift its trade-for-trade comparison body into
`assert_parity(params: dict, tf: str = "4h") -> None`, have its existing six `CASES` call it, then add
the news case here:

```python
def test_engine_and_fast_engine_agree_with_the_veto_on():
    from optimize.test_fast_parity import assert_parity
    assert_parity(dict(champion_preset("4h"),
                       news_veto=True, news_pre_min=5, news_post_min=15), tf="4h")
```

Do **not** duplicate the comparator — `test_fast_parity.py` is the canonical contract
(*"the contract that lets the optimiser use the 200× faster path safely"*), and two copies will drift.

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest optimize/test_news_veto_parity.py -q
```
Expected: **FAIL** — `news_veto` is not a known param.

> If `optimize/test_fast_parity.py` exposes no reusable `assert_parity`, add one there by extracting
> its existing comparison body into a function and having its own cases call it. Do not duplicate the
> comparator.

- [ ] **Step 3: Add the params to the engine**

In `engine.py`, in `SimpleStrategyParams` (near the existing cap params at `:96-100`):

```python
    # --- news veto (fundamental analysis, milestone 1) -------------------------------
    # Off by default: news_veto=False must be byte-identical to pre-feature behaviour.
    news_veto: bool = False
    news_pre_min: int = 5      # minutes BEFORE the release the window opens  (measured, Task 2)
    news_post_min: int = 15    # minutes AFTER  the release the window closes (measured, Task 2)
```

- [ ] **Step 4: Build + memoise the mask in `core.py`, and AND it into the gate**

In `optimize/core.py`, alongside the existing `_EOD_MEMO` (`:288-298`), add:

```python
_NEWS_MEMO: dict = {}


def _news_window_mask(params: dict, df_dec) -> "np.ndarray | None":
    """bool[len(df_dec)] where a new entry must be blocked, or None when the feature is off.

    Memoised on (id-of-frame, pre, post) exactly like _EOD_MEMO — the calendar and the frame are both
    immutable within a run, so the mask is recomputed once, not once per trial.
    """
    if not params.get("news_veto"):
        return None                      # identity: byte-identical to pre-feature
    pre = int(params.get("news_pre_min", 5))
    post = int(params.get("news_post_min", 15))
    key = (id(df_dec), len(df_dec), pre, post)
    if key not in _NEWS_MEMO:
        from optimize.fundamentals import release_calendar as _rc
        from optimize.fundamentals import window as _W
        _NEWS_MEMO[key] = _W.release_window_mask(df_dec, _rc.load_calendar(), pre, post)
    return _NEWS_MEMO[key]
```

Then, immediately after the existing composite gate is built (`optimize/core.py:273`,
`gate = base & ~vmask & cmask`), add:

```python
    news_mask = _news_window_mask(params, df_dec)
    if news_mask is not None:
        gate = gate & ~news_mask        # a release window can only ever REMOVE eligibility
```

Apply the identical AND in the contributor path (`_contributor_gate`, `core.py:138`) so both routes
to the gate agree.

- [ ] **Step 5: Run tests to verify entry-blocking passes**

```bash
python3 -m pytest optimize/test_news_veto_parity.py -q -k "byte_identical or removes_entries or lands_inside"
```
Expected: **3 passed**

- [ ] **Step 6: Prove the identity default with the golden gate**

```bash
python3 perf/check_golden.py
```
Expected: `✅ ALL GOLDEN BASELINES MATCH` — **this is the hard gate (`MASTER.md:167`).** If any
timeframe moves, the feature is leaking when it is supposed to be off.

- [ ] **Step 7: Commit**

```bash
git add engine.py optimize/core.py optimize/test_news_veto_parity.py
git commit -m "feat(fa): block entries inside the measured release window

ANDs the release-window mask into the composite entry_gate (the only thing either engine actually
consults to block a trade -- engine.py:520 / fast_engine.py:97). veto_mask is NOT the blocker.
Off by default; golden 6/6 byte-identical.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Force-flatten open trades — the profit exemption

**Files:**
- Modify: `engine.py` — `ExitReason` (`:54-63`), force-exit block (near the EOD cap, `:362-370`)
- Modify: `optimize/fast_engine.py` — reason codes (`:29-32`), `fast_backtest` signature (`:50`),
  exit candidate (near `t_eod`, `:165-177`)
- Modify: `optimize/core.py` — build + memoise `news_exit_targets`, thread to `fast_backtest`
- Test: `optimize/test_news_veto_parity.py` (extend)

**Interfaces:**
- Consumes: `window.news_exit_targets(df1, cal, pre_min)` → `int64[len(df1)]`.
- Produces: new param `news_profit_exempt_mult: float = 1.0` — an open trade survives the window if
  its unrealized profit is at least this multiple of its stop distance.

**There is no unrealized-P/L variable in this engine.** `open_trade` (`engine.py:571-589`) holds
`entry_price`, `direction`, and three **static** absolute lines (`sl_soft_line`, `sl_hard_line`,
`tp_hard_line`). Nothing mutates. So we compute profit **at a single point in time** — the 1-min bar
where the window opens — not as a running tally. That keeps it cheap in both engines and, crucially,
keeps it expressible in `fast_engine`'s vectorized `argmax`-over-candidates model.

**The exemption, in the units the engine already speaks:**

```
stop_distance = |entry_price - sl_hard_line|                  (static, set at entry)
profit_pts    = (close_at_window_open - entry_price)          for a long
              = (entry_price - close_at_window_open)          for a short
EXEMPT  iff   profit_pts >= news_profit_exempt_mult * stop_distance
```

`news_profit_exempt_mult = 1.0` means "already up by one stop's worth" — i.e. risking nothing that
was not already won. This is the **single tunable threshold** of the whole milestone.

**Tie-break contract (must be documented in BOTH files, the way `cap_mode` already is):** if a
`NEWS_VETO` exit and a price exit (`STOP_LOSS_HARD` / `TAKE_PROFIT_HARD` / `STOP_LOSS_SOFT`) land on
the same 1-minute bar, **the price exit wins** — the market got there first, within the bar. `NEWS_VETO`
is ordered **after** the price exits and **before** `TIME_CAP`/`END_OF_DAY` in `fast_engine`'s `order`
list, and `engine.py` must check it in the same relative position.

- [ ] **Step 1: Write the failing test**

Append to `optimize/test_news_veto_parity.py`:

```python
def test_force_flatten_produces_news_veto_exits():
    res = _run(news_veto=True, news_pre_min=5, news_post_min=15, news_profit_exempt_mult=1.0)
    reasons = [t["exit_reason"] for t in res["trades"]]
    assert "NEWS_VETO" in reasons, "no trade was force-flattened at a release window"


def test_the_profit_exemption_is_actually_applied():
    """Monotonic in the threshold. mult=0.0 exempts any trade in profit at all, so FEW are killed.
    mult=99.0 exempts almost nothing, so MANY are killed. If the two are equal, the exemption is
    being ignored and every windowed trade is being flattened unconditionally."""
    lenient = _run(news_veto=True, news_pre_min=5, news_post_min=15, news_profit_exempt_mult=0.0)
    strict = _run(news_veto=True, news_pre_min=5, news_post_min=15, news_profit_exempt_mult=99.0)
    n_lenient = sum(t["exit_reason"] == "NEWS_VETO" for t in lenient["trades"])
    n_strict = sum(t["exit_reason"] == "NEWS_VETO" for t in strict["trades"])
    assert n_strict > n_lenient, "the profit exemption is not being applied"


def test_parity_holds_with_force_flatten_on():
    from optimize.test_fast_parity import assert_parity
    assert_parity(dict(champion_preset("4h"),
                       news_veto=True, news_pre_min=5, news_post_min=15,
                       news_profit_exempt_mult=1.0), tf="4h")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest optimize/test_news_veto_parity.py -q -k "force_flatten or exempt"
```
Expected: **FAIL** — `"NEWS_VETO" in reasons` is False; no such exit reason exists.

- [ ] **Step 3: Add the exit reason to `engine.py`**

Extend the `ExitReason` literal (`engine.py:54-63`):

```python
ExitReason = Literal[
    "STOP_LOSS_HARD", "STOP_LOSS_SOFT", "TAKE_PROFIT_HARD", "TAKE_PROFIT_SOFT",
    "TIME_CAP", "END_OF_DAY", "FORCE_CLOSE", "NEWS_VETO", "OPEN",
]
```

Add the param to `SimpleStrategyParams`:

```python
    news_profit_exempt_mult: float = 1.0   # survive the window iff profit >= this * stop distance
```

- [ ] **Step 4: Force-exit in `engine.py`**

**Follow the existing house pattern — do NOT call `_finalise` yourself.** The EOD cap
(`engine.py:362-370`) does not finalise the trade; it merely sets `exit_reason` / `fill` /
`resets_counter`, and a **shared block at `engine.py:372-380`** does the rest:

```python
                if exit_reason is not None and fill is not None:
                    sub_ts = pd.Timestamp(md_arr[t])
                    _finalise(open_trade, sub_ts, fill, exit_reason, ep, d, pv)
                    trades.append(open_trade)
                    blocked_until = sub_ts
                    open_trade = None
                    soft_consec_count = 0
                    return
```

(`_finalise` takes **seven** args — `trade, exit_ts, fill, reason, entry_price, direction,
point_value` — which is one more reason not to hand-roll a call to it.)

So the new block sets the same three locals and lets the shared block finalise. Inside
`_walk_exit_for_4h(idx)` (`engine.py:297`), **after** the price-exit checks (`:330-349`) and
**before** the bars cap (`:355`):

```python
                # --- NEWS_VETO force-flatten ------------------------------------------------
                # Runs only when no price exit already fired on this bar ⇒ a same-bar tie resolves
                # to the price exit. Placed BEFORE the bars/EOD caps, so a same-bar tie against
                # those resolves to NEWS_VETO. fast_engine mirrors both by ordering `order`
                # (see fast_engine.py, the t_news entry).
                if exit_reason is None and news_target_arr is not None:
                    w = int(news_target_arr[t])              # next window-open at or after bar t
                    if w == t:                               # the window opens on THIS bar
                        stop_dist = abs(ep - open_trade['sl_hard_line'])
                        px = mc_arr[t]
                        profit = (px - ep) if d == 'long' else (ep - px)
                        exempt = (stop_dist > 0
                                  and profit >= self.params.news_profit_exempt_mult * stop_dist)
                        if not exempt:
                            exit_reason, fill, resets_counter = 'NEWS_VETO', px, True
```

Build `news_target_arr` once, next to the EOD targets (`engine.py:265-269`):

```python
        news_target_arr = None
        if self.params.news_veto:
            from optimize.fundamentals import release_calendar as _rc
            from optimize.fundamentals import window as _W
            news_target_arr = _W.news_exit_targets(
                pd.DataFrame({"Date": md_arr}), _rc.load_calendar(), self.params.news_pre_min)
```

> `ep` and `d` are the entry-price / direction locals the surrounding block already uses (they are
> what gets passed to `_finalise` at `:374`). Reuse them; do not re-derive from `open_trade`.

- [ ] **Step 5: Force-exit in `optimize/fast_engine.py`**

Add the reason code alongside the others (`fast_engine.py:29-32`):

```python
R_NEWS_VETO = 7
REASON_NAME[R_NEWS_VETO] = "NEWS_VETO"
```

Add to the `fast_backtest` signature (`:50`):

```python
                  news_target: np.ndarray | None = None,
                  news_profit_exempt_mult: float = 1.0,
```

Compute the candidate next to `t_eod` (`:165-172`):

```python
    # --- NEWS_VETO candidate ---------------------------------------------------------
    # Mirrors engine.py's block inside _walk_exit_for_4h (see engine.py, NEWS_VETO section).
    # Same-bar tie-break: price exits win (they are earlier in `order`); NEWS_VETO precedes the caps.
    t_news = -1
    if news_target is not None:
        w = news_target[e0]                     # e0 = global 1-min index of entry
        if w >= 0 and lo <= w < hi:
            stop_dist = abs(entry_px - sl_hard_line)
            px = m_close[w]
            profit = (px - entry_px) if is_long else (entry_px - px)
            if not (stop_dist > 0 and profit >= news_profit_exempt_mult * stop_dist):
                t_news = w
```

Insert into `order` (`:175-177`) **after** the price exits, **before** the caps:

```python
    order = [(t_slh, R_SL_HARD), (t_tph, R_TP_HARD), (t_soft, R_SL_SOFT),
             (t_news, R_NEWS_VETO),                       # <-- new
             (t_bars, R_TIME_CAP), (t_eod, R_EOD)]
```

- [ ] **Step 6: Thread it through `optimize/core.py`**

Alongside `_NEWS_MEMO`, add:

```python
_NEWS_TGT_MEMO: dict = {}


def _news_exit_targets(params: dict, d1) -> "np.ndarray | None":
    """int64[len(d1)] force-exit targets, or None when off. Memoised like _EOD_MEMO.

    NOTE the same sharp edge as eod_targets (core.py:285-287): this MUST be built on the SLICED d1,
    not the full df1, or the indices point at the wrong bars.
    """
    if not params.get("news_veto"):
        return None
    pre = int(params.get("news_pre_min", 5))
    key = (id(d1), len(d1), pre)
    if key not in _NEWS_TGT_MEMO:
        from optimize.fundamentals import release_calendar as _rc
        from optimize.fundamentals import window as _W
        _NEWS_TGT_MEMO[key] = _W.news_exit_targets(d1, _rc.load_calendar(), pre)
    return _NEWS_TGT_MEMO[key]
```

Pass it at the `fast_backtest(...)` call (`core.py:300-301`):

```python
        news_target=_news_exit_targets(params, d1),
        news_profit_exempt_mult=float(params.get("news_profit_exempt_mult", 1.0)),
```

- [ ] **Step 7: Run the full test file**

```bash
python3 -m pytest optimize/test_news_veto_parity.py -q
```
Expected: **7 passed** (including both parity tests)

- [ ] **Step 8: Run BOTH hard gates**

```bash
python3 optimize/test_fast_parity.py     # engine <-> fast_engine, trade-for-trade
python3 perf/check_golden.py             # identity default, 6/6 byte-identical
```
Expected: parity OK, and `✅ ALL GOLDEN BASELINES MATCH`.

- [ ] **Step 9: Commit**

```bash
git add engine.py optimize/fast_engine.py optimize/core.py optimize/test_news_veto_parity.py
git commit -m "feat(fa): force-flatten not-yet-profitable trades at the release window open

New NEWS_VETO exit reason threaded through both engines, following the cap_mode='eod' template.
Profit exemption: a trade survives iff unrealized profit >= news_profit_exempt_mult * stop distance,
evaluated at the single bar the window opens (the engine has no running unrealized P/L).
Same-bar tie-break: price exits win; NEWS_VETO precedes the bars/EOD caps. Documented in both files.
golden 6/6 + fast parity green.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: The null test — is any of this real?

**Files:**
- Create: `optimize/fundamentals/nulltest.py`
- Create: `optimize/fundamentals/run_nulltest.py` (CLI, prints the verdict)
- Test: `optimize/test_release_window.py` (extend)

**Interfaces:**
- Consumes: `release_calendar.load_calendar()`, `core.backtest_metrics`.
- Produces:
  - `nulltest.fake_calendar(cal: pd.DataFrame, df1: pd.DataFrame, seed: int) -> pd.DataFrame`
    → same row count, same **time-of-day** distribution, **different (random, release-free) dates**.

**This is the most important task in the plan.** Everything else could work perfectly and still be
worthless. If a *fake* calendar improves performance about as much as the real one, then we have not
discovered "news matters" — we have discovered "flattening trades sometimes helps," which is a fact
about our stop placement, not about the world.

**The design of the fake matters.** It must preserve the *time-of-day* distribution (8:30 / 10:00 /
14:00) and the event count, and change **only the dates** — to dates with no real release. Otherwise
we would be comparing "windows at 8:30" against "windows at random times of day" and would merely
rediscover that 8:30 is volatile.

- [ ] **Step 1: Write the failing test**

Append to `optimize/test_release_window.py`:

```python
def test_fake_calendar_preserves_shape_but_not_dates():
    from optimize.fundamentals import nulltest
    _, df1 = _bundle()
    cal = rc.load_calendar()
    fake = nulltest.fake_calendar(cal, df1, seed=7)

    assert len(fake) == len(cal)
    # same clock times...
    assert (fake["Date"].dt.strftime("%H:%M").value_counts().sort_index()
            .equals(cal["Date"].dt.strftime("%H:%M").value_counts().sort_index()))
    # ...but no overlap with a real release date
    real_days = set(cal["Date"].dt.normalize())
    fake_days = set(fake["Date"].dt.normalize())
    assert not (real_days & fake_days), "a fake release landed on a real release day"


def test_fake_calendar_is_deterministic_for_a_seed():
    from optimize.fundamentals import nulltest
    _, df1 = _bundle()
    cal = rc.load_calendar()
    a = nulltest.fake_calendar(cal, df1, seed=3)
    b = nulltest.fake_calendar(cal, df1, seed=3)
    assert a["Date"].equals(b["Date"])


def test_fake_calendar_produces_a_flatter_envelope_than_the_real_one():
    """The core sanity check the null test rests on: fake release minutes are NOT specially volatile."""
    from optimize.fundamentals import nulltest
    _, df1 = _bundle()
    cal = rc.load_calendar()
    real = W.measure_envelope(df1, cal, pre=30, post=30)
    fake = W.measure_envelope(df1, nulltest.fake_calendar(cal, df1, seed=11), pre=30, post=30)
    assert real.loc[0, "ratio"] > 2.0 * fake.loc[0, "ratio"], \
        "fake 'releases' look as volatile as real ones - the calendar or the fake is broken"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest optimize/test_release_window.py -q -k fake
```
Expected: **FAIL** — `No module named 'optimize.fundamentals.nulltest'`

- [ ] **Step 3: Write the implementation**

Create `optimize/fundamentals/nulltest.py`:

```python
"""The honesty harness: fake release calendars.

If the veto rule 'works' just as well on a FAKE calendar, it has not learned anything about news --
it has learned that flattening trades sometimes helps. That is a fact about our stop placement, not
about the world, and it would not generalise.

The fake preserves the event count and the TIME-OF-DAY distribution (08:30 / 10:00 / 14:00) and
changes only the DATES -- to days with no real release. Randomising the clock time too would merely
rediscover that 08:30 is a volatile minute.
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest optimize/test_release_window.py -q -k fake
```
Expected: **3 passed**

- [ ] **Step 5: Write the null-test runner**

Create `optimize/fundamentals/run_nulltest.py`:

```python
"""Run the veto rule against the REAL calendar and against N FAKE ones. Print the verdict.

  python3 optimize/fundamentals/run_nulltest.py --tf 4h --n 20 --pre 5 --post 15
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from optimize import core, data, instruments, signals        # noqa: E402
from optimize import timeframes as TF                        # noqa: E402
from optimize.fast_engine import signals_to_int              # noqa: E402
from optimize.fundamentals import nulltest                   # noqa: E402
from optimize.fundamentals import release_calendar as rc     # noqa: E402
from presets import champion_preset                          # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--pre", type=int, default=5)
    ap.add_argument("--post", type=int, default=15)
    a = ap.parse_args()

    df_dec, df1, box, vf, n_split = data.load_inputs(a.tf)
    sig = signals_to_int(signals.decision_signals(df_dec, box))
    bar_td = TF.get(a.tf).bar_td
    pv = instruments.point_value("NQ")
    base = dict(champion_preset(a.tf))
    cal = rc.load_calendar()

    def run(**over):
        core._NEWS_MEMO.clear(); core._NEWS_TGT_MEMO.clear()
        return core.backtest_metrics(df_dec, df1, box, vf, n_split,
                                     {**base, **over}, bar_td, sig_int=sig, pv=pv)

    off = run(news_veto=False)
    on = run(news_veto=True, news_pre_min=a.pre, news_post_min=a.post)
    real_delta = on["pnl"] - off["pnl"]

    print(f"baseline (veto off) : ${off['pnl']:>12,.0f}   trades={off['n_taken']}")
    print(f"REAL calendar       : ${on['pnl']:>12,.0f}   trades={on['n_taken']}"
          f"   delta=${real_delta:+,.0f}")
    print()

    deltas = []
    for s in range(a.n):
        fake = nulltest.fake_calendar(cal, df1, seed=s)
        res = run(news_veto=True, news_pre_min=a.pre, news_post_min=a.post,
                  _news_calendar_override=fake)     # see NOTE below
        d = res["pnl"] - off["pnl"]
        deltas.append(d)
        print(f"  fake seed {s:>2d}      : ${res['pnl']:>12,.0f}   delta=${d:+,.0f}")

    deltas = np.array(deltas)
    better = int((deltas >= real_delta).sum())
    p = (better + 1) / (len(deltas) + 1)

    print()
    print(f"fake delta: mean=${deltas.mean():+,.0f}  sd=${deltas.std():,.0f}"
          f"  best=${deltas.max():+,.0f}")
    print(f"real delta: ${real_delta:+,.0f}")
    print(f"{better}/{len(deltas)} fake calendars did AT LEAST AS WELL as the real one")
    print(f"empirical p-value = {p:.3f}")
    print()
    print("VERDICT:", "REAL EFFECT (p < 0.05)" if p < 0.05 else
          "*** INDISTINGUISHABLE FROM CHANCE — DO NOT SHIP ***")
    return 0 if p < 0.05 else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

> **NOTE — one small plumbing addition:** `_news_window_mask` / `_news_exit_targets` in `core.py`
> must honour an optional `params["_news_calendar_override"]` (a DataFrame) in place of
> `rc.load_calendar()`, so the null test can swap the calendar without touching the CSV. Add it to
> both functions:
> ```python
>     cal = params.get("_news_calendar_override")
>     if cal is None:
>         cal = _rc.load_calendar()
> ```
> and include it in the memo key (`id(cal)`).

- [ ] **Step 6: Run the null test — THE GATE**

```bash
python3 optimize/fundamentals/run_nulltest.py --tf 4h --n 20
```
Expected: a verdict line.

**If the verdict is `INDISTINGUISHABLE FROM CHANCE`, the milestone has failed its central test.
Do not proceed to Task 6. Report the result honestly and stop.** That is not a disaster — it is the
null test doing exactly the job it was built for, and it is far cheaper to learn it here than after
deploying capital.

- [ ] **Step 7: Commit**

```bash
git add optimize/fundamentals/nulltest.py optimize/fundamentals/run_nulltest.py optimize/test_release_window.py optimize/core.py
git commit -m "test(fa): null test — the same veto rule against fake release calendars

The fake preserves event count and time-of-day mix, changing only the dates (to release-free days).
If a fake calendar helps as much as the real one, the rule learned 'flattening sometimes helps',
not 'news matters'. Prints an empirical p-value and a ship/do-not-ship verdict.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Out-of-sample evaluation + the crude-oil thermometer

**Files:**
- Create: `optimize/fundamentals/report_m1.py`
- Modify: `docs/superpowers/specs/2026-07-11-fundamental-analysis-design.md` (record the result)

**Interfaces:**
- Consumes: everything above.
- Produces: a full dashboard-replica report (per the standing project rule: champion/optimization
  reports are **full dashboard-replica, all metrics — not a headline number**).

**The split is already defined, and the engine already reports it.** `config.YEARS = (2025, 2026)`,
and `core.backtest_metrics` returns **`pnl_2025` and `pnl_2026` as separate keys**
(`optimize/core.py:366-367`). So one run gives you both halves — no manual slicing, no chance of
getting the boundary wrong.

**The discipline that still matters:** the window bounds from Task 2 must be **re-derived on the 2025
slice alone** and then applied **unchanged** to 2026. Measuring on all data and reporting on 2026
would be measuring on the test set. `pnl_2026` is only an honest out-of-sample number if the window
that produced it never saw 2026.

**The crude-oil thermometer.** Run the identical rule on **CL** (`instrument="CL"`,
`point_value=1000.0`, 1-min data at
`/mnt/data/projects/trading/ALL_STOCKS/CANDLES/NYMEX/CL_Continuous_Data/CL_1m.csv`). We do **not**
tune anything on CL. It is a lie detector: US macro releases genuinely move crude, so the *volatility
envelope* should be visible there too. If it is completely flat on CL, our timestamps are wrong. If
the veto *helps* on NQ and *hurts badly* on CL, the effect may be an NQ-specific artifact.

- [ ] **Step 1: Re-derive the window on 2025 only**

```bash
python3 -c "
import sys; sys.path.insert(0, '.')
import pandas as pd
from optimize import data
from optimize.fundamentals import release_calendar as rc, window as W
_, df1, *_ = data.load_inputs('4h')
is_2025 = df1[df1['Date'].dt.year == 2025].reset_index(drop=True)
cal = rc.load_calendar()
cal25 = cal[cal['Date'].dt.year == 2025]
env = W.measure_envelope(is_2025, cal25)
print('IN-SAMPLE (2025) window:', W.derive_bounds(env))
"
```
Record the bounds. **These are frozen. They do not get re-tuned on 2026.**

- [ ] **Step 2: Report in-sample vs out-of-sample, NQ**

```bash
python3 optimize/fundamentals/report_m1.py --tf 4h --instrument NQ --pre <N> --post <N>
```
The report must print, for **2025 (in-sample)** and **2026 (out-of-sample)** separately, with the
veto **off** and **on**: total P/L, max drawdown, trades taken, win rate, profit factor, and the count
of `NEWS_VETO` exits. Full dashboard-replica — every metric, not a headline.

- [ ] **Step 3: Run the crude-oil thermometer**

```bash
python3 optimize/fundamentals/report_m1.py --tf 4h --instrument CL --pre <N> --post <N>
```
Also print CL's volatility envelope. **Expected:** a visible spike at offset 0 (US macro moves crude).
**A completely flat CL envelope means our timestamps are wrong.**

- [ ] **Step 4: Verify through the dashboard UI**

Per the standing project rule, a new result is verified in the **browser dashboard UI** — select the
instrument and timeframe, hit Run, and confirm the exact recorded numbers appear on screen. **Not via
the API.** Always with the 1-minute indicator frame (`--ind-1min`).

**Heavy timeframes (2m/5m) must run on the server, never locally** — they have OOM-frozen the 14 GB
local box before.

- [ ] **Step 5: Write the honest verdict into the spec**

Append a "Milestone 1 — Result" section to
`docs/superpowers/specs/2026-07-11-fundamental-analysis-design.md` recording:
- the measured window (2025-derived),
- the null-test p-value,
- in-sample and out-of-sample deltas,
- the CL thermometer reading,
- **and whether the entry count fell, as §5.4 predicted it would.**

If the result is negative, **say so plainly.** A negative result here is a cheap, honest win: it means
the calendar plumbing works and the hypothesis does not, and we learned it before spending a cent on
Trading Economics or a week on the surprise-entry head.

- [ ] **Step 6: Commit**

```bash
git add optimize/fundamentals/report_m1.py docs/superpowers/specs/2026-07-11-fundamental-analysis-design.md
git commit -m "report(fa): milestone 1 result — window measured on 2025, tested on 2026, CL thermometer

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7 (independent — can run in parallel): audit the Trading Economics point-in-time claim

**Files:**
- Create: `optimize/fundamentals/audit_te_pit.py`

**Why now, even though nothing depends on it yet.** Head 4 (surprise entry) is the only head that
needs paid data, and its entire value rests on one vendor claim: that Trading Economics' point-in-time
endpoint returns *"the original values before any subsequent revisions."* **That is marketing copy,
not an audit.** Testing it costs an afternoon and a trial key. Discovering it is false *after*
building Head 4 would cost far more.

**The test.** For a specific 2025 Non-Farm Payrolls release:
1. Pull it from Trading Economics' point-in-time endpoint, as-of the release date.
2. Pull the **first-print** value from **ALFRED** (`realtime_start` = `realtime_end` = the release
   date), which the St. Louis Fed maintains as the official vintage archive.
3. **They must match.** If TE's "actual" equals the *later revised* value instead, the point-in-time
   guarantee is worthless and we plan Head 4 around ALFRED + a separate consensus source.

The research pass surfaced a concrete illustration of the stakes: **January 2021 payrolls printed at
49,000, was revised to 166,000, then to 233,000.** Three different numbers for one event. Backtesting
against 233,000 trades on a number nobody had that morning.

- [ ] **Step 1: Pull the ALFRED first-print (free, no vendor needed)**

```bash
export FRED_API_KEY=<your key>
python3 -c "
import os, json, urllib.request
key = os.environ['FRED_API_KEY']
# PAYEMS = Total Nonfarm Payrolls. Ask for the vintage AS OF a 2025 release date.
url = ('https://api.stlouisfed.org/fred/series/observations?series_id=PAYEMS'
       f'&api_key={key}&file_type=json'
       '&realtime_start=2025-03-07&realtime_end=2025-03-07'
       '&observation_start=2025-01-01&observation_end=2025-02-28')
print(json.dumps(json.load(urllib.request.urlopen(url)), indent=1))
"
```
This is the number **as it stood on 2025-03-07** — the first print. Record it.

- [ ] **Step 2: Pull the same release from Trading Economics point-in-time**

Requires a TE trial key. Endpoint documented at
<https://docs.tradingeconomics.com/economic_calendar/point-in-time/>.
Query the same date range, `country=United States`, and read the `Actual` field.

- [ ] **Step 3: Diff and record the verdict**

Write the finding into the spec's Appendix A:
- **If they match** → TE's point-in-time guarantee is real. Head 4 can be planned around it.
- **If TE returns the revised value** → **the guarantee is false.** Head 4 must use ALFRED for the
  actual and find a separate, verifiable source for the pre-release consensus. Record this loudly.

- [ ] **Step 4: Commit**

```bash
git add optimize/fundamentals/audit_te_pit.py docs/superpowers/specs/2026-07-11-fundamental-analysis-design.md
git commit -m "audit(fa): test Trading Economics' point-in-time claim against ALFRED first-print vintages

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Definition of Done (the whole milestone)

1. `optimize/fundamentals/us_high_impact.csv` committed, covering 2025-01-01 → 2026-06-30.
2. Volatility envelope measured; **it peaks at offset 0** (which is what proves the calendar).
3. Window bounds derived from the **2025** slice and frozen.
4. Veto wired into the composite `entry_gate` in **both** engines.
5. `NEWS_VETO` force-exit + profit exemption in **both** engines, same-bar tie-break documented in both.
6. `python3 perf/check_golden.py` → **✅ 6/6 byte-identical** with the feature off.
7. `python3 optimize/test_fast_parity.py` → **parity holds** with the feature on.
8. **`run_nulltest.py` verdict is `REAL EFFECT (p < 0.05)`.** If not — stop and report.
9. Result holds **out-of-sample on 2026**.
10. **CL thermometer** recorded.
11. **Dashboard UI verification** (browser, select instrument + timeframe, hit Run, exact numbers on
    screen — not the API), with `--ind-1min`.
12. Honest verdict written into the spec — **including whether entries fell, as predicted.**

**Reminder of the standing expectation (spec §5.4): this milestone will most likely REDUCE entries and
REDUCE drawdown.** That is the trade we knowingly accepted. The entry-increasing heads are 2 and 4.
