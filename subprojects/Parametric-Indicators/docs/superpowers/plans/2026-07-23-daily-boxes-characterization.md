# Daily Boxes (NQ) Characterization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether the discarded daily (`D*`) box zones on NQ add tradeable signal supply and carry real
information, and emit a verdict of **go B** / **go C** / **close permanently**.

**Architecture:** A self-contained study package under `subprojects/Parametric-Indicators/research/daily_boxes/`
that **edits no production file**. It reimplements the champion Stage-1 rule with the level list as a *required*
argument, proves fidelity by reproducing `optimize.signals.decision_signals` element-for-element on the
weekly+monthly set, then re-runs it with the daily zones added to count new supply, tests how much survives the
champion's gate, and measures whether price behaves differently at daily zones than at two dumb controls.

**Tech Stack:** Python 3, numpy, pandas, pytest. No new dependencies.

## Global Constraints

- **No production file may be modified.** `box_lookup.py`, `engine.py`, `optimize/signals.py`, `optimize/data.py`
  and the champion registry are read-only for this work.
- **`pairs` is always a required argument.** No default level set, no `dict.get(key, default)` for any
  measurement or strategy parameter — a silent default here measures a different thing and has invalidated
  results in this repo before.
- **Every parameter is printed as used** on every run (level set, timeframe, horizons, seed, control draws, bar
  count).
- **The champion Stage-1 rule is touch-and-close-beyond**, not `BoxLookup`'s traversal state machine:
  green = `close>open`, red = `close<open`, doji ⇒ hold; a pair contributes only if both columns are non-NaN
  *and* the bar's `[low,high]` overlaps `[lower,upper]`; long iff `green & touched & close>upper`; short iff
  `red & touched & close<lower`; **long wins ties**.
- **Windows:** M1/M2 = 2,119 4h bars (2025-01-01 → 2026-05-19, the champion frame). M3 = 3,663 bars
  (2024-01-01 → 2026-05-19), reported both ways.
- **Compute location:** unit tests run locally on synthetic frames (fast). Anything touching real champion data
  or the 1-min frame runs **on the server** — never locally.
- **Golden gate 6/6** is run as evidence that nothing production-side moved.
- NQ point value = **$20/point** for all dollar framing.

---

## File Structure

All new files under `subprojects/Parametric-Indicators/`:

| File | Responsibility |
|---|---|
| `research/daily_boxes/__init__.py` | Package marker |
| `research/daily_boxes/levels.py` | `DAILY_LEVELS` — the 8 daily zone-pairs |
| `research/daily_boxes/study_signals.py` | The Stage-1 rule with `pairs` required |
| `research/daily_boxes/measure.py` | M1 supply, M2 gate survival |
| `research/daily_boxes/informativeness.py` | M3 forward returns, both controls, bootstrap CI, power |
| `research/daily_boxes/extended_frame.py` | The M3-only 2024–26 frame + assertions |
| `research/daily_boxes/run_study.py` | CLI entry point; parameter echo; CSV output |
| `tests/test_daily_boxes_levels.py` | Task 1 tests |
| `tests/test_daily_boxes_signals.py` | Task 2 tests |
| `tests/test_daily_boxes_measure.py` | Task 3–4 tests |
| `tests/test_daily_boxes_informativeness.py` | Task 5 tests |
| `tests/test_daily_boxes_extended_frame.py` | Task 6 tests |

Working directory for every command below: `/mnt/data/projects/trading/.worktrees/research-daily-boxes/subprojects/Parametric-Indicators`

---

## Task 1: Daily level constants

**Files:**
- Create: `research/daily_boxes/__init__.py`
- Create: `research/daily_boxes/levels.py`
- Test: `tests/test_daily_boxes_levels.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `DAILY_LEVELS: list[tuple[str, str, str]]` — 8 `(upper_col, lower_col, label)` triples, same shape as
  `box_lookup._WEEKLY_LEVELS`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_daily_boxes_levels.py
"""DAILY_LEVELS must mirror the weekly level structure exactly and name only real CSV columns."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from box_lookup import _WEEKLY_LEVELS                       # noqa: E402
from research.daily_boxes.levels import DAILY_LEVELS        # noqa: E402


def test_daily_levels_mirror_weekly_shape():
    assert len(DAILY_LEVELS) == len(_WEEKLY_LEVELS) == 8
    for (du, dl, dlab), (wu, wl, wlab) in zip(DAILY_LEVELS, _WEEKLY_LEVELS):
        assert du == "D" + wu[1:], f"{du} should mirror {wu}"
        assert dl == "D" + wl[1:], f"{dl} should mirror {wl}"
        assert dlab == "D" + wlab[1:], f"{dlab} should mirror {wlab}"


def test_daily_level_columns_all_exist_in_real_box_csv():
    import config
    box_csv = config.DATA_ROOT / "full_data" / "NQ_full_data.csv"
    if not box_csv.exists():
        pytest.skip(f"box csv not present: {box_csv}")
    cols = set(pd.read_csv(box_csv, nrows=1).columns)
    missing = [c for u, l, _ in DAILY_LEVELS for c in (u, l) if c not in cols]
    assert not missing, f"columns missing from box CSV: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily_boxes_levels.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.daily_boxes'`

- [ ] **Step 3: Write minimal implementation**

```python
# research/daily_boxes/__init__.py
"""Daily-box characterization study (2026-07-23). Read-only: edits no production module."""
```

```python
# research/daily_boxes/levels.py
"""The daily (D*) box zones that box_lookup.py discards at load time.

Mirrors box_lookup._WEEKLY_LEVELS exactly, tier letter swapped W -> D. Note the sub-zone column ORDER is
asymmetric in the weekly list and is reproduced verbatim: the TH sub-zone is ('*TH2', '*TH1') while the TL
sub-zone is ('*TL1', '*TL2').
"""
from __future__ import annotations

from typing import List, Tuple

# (upper_col, lower_col, label) — same shape as box_lookup._WEEKLY_LEVELS
DAILY_LEVELS: List[Tuple[str, str, str]] = [
    ('DTHU', 'DTHD', 'D-TH'),
    ('DTH2', 'DTH1', 'D-TH sub'),
    ('DRHU', 'DRHD', 'D-RH'),
    ('DIHU', 'DIHD', 'D-IH'),
    ('DILU', 'DILD', 'D-IL'),
    ('DRLU', 'DRLD', 'D-RL'),
    ('DTLU', 'DTLD', 'D-TL'),
    ('DTL1', 'DTL2', 'D-TL sub'),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily_boxes_levels.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add research/daily_boxes/__init__.py research/daily_boxes/levels.py tests/test_daily_boxes_levels.py
git commit -m "feat(daily-boxes): DAILY_LEVELS mirroring the weekly zone structure"
```

---

## Task 2: The Stage-1 rule with a required level set, plus the parity gate

**Files:**
- Create: `research/daily_boxes/study_signals.py`
- Test: `tests/test_daily_boxes_signals.py`

**Interfaces:**
- Consumes: `DAILY_LEVELS` (Task 1); `optimize.signals._box_dates_vec` and `optimize.signals.decision_signals`
  (read-only imports); `engine._LEVEL_PAIRS`.
- Produces: `study_signals(df_dec: pd.DataFrame, box: pd.DataFrame, pairs: list) -> np.ndarray` returning a
  dtype=object array of `'long' | 'short' | 'hold'`, aligned 1:1 with `df_dec` rows. `pairs` is **positional and
  required**.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_daily_boxes_signals.py
"""study_signals must reproduce the production rule EXACTLY when handed the production level set,
and must refuse to run without an explicit `pairs` argument."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from engine import _LEVEL_PAIRS                                   # noqa: E402
from optimize.signals import decision_signals                     # noqa: E402
from research.daily_boxes.study_signals import study_signals      # noqa: E402


def _synthetic(seed: int, n_bars: int = 400):
    """Random-but-deterministic decision frame + box frame covering it."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-02 18:00", periods=n_bars, freq="4h")
    close = 20000 + np.cumsum(rng.normal(0, 25, n_bars))
    open_ = close + rng.normal(0, 15, n_bars)
    high = np.maximum(open_, close) + np.abs(rng.normal(0, 10, n_bars))
    low = np.minimum(open_, close) - np.abs(rng.normal(0, 10, n_bars))
    df_dec = pd.DataFrame({"Date": dates, "Open": open_, "High": high,
                           "Low": low, "Close": close})

    box_dates = pd.date_range("2025-01-01", periods=n_bars, freq="D").normalize()
    mid = 20000 + np.cumsum(rng.normal(0, 30, len(box_dates)))
    box = pd.DataFrame({"Date": box_dates})
    # every W/M/D column the rule may look at, as a band around `mid`
    for u, l, _lab in _LEVEL_PAIRS:
        half = rng.uniform(10, 60, len(box_dates))
        box[u] = mid + half
        box[l] = mid - half
    return df_dec, box.set_index("Date", drop=False)


def test_pairs_argument_is_required():
    df_dec, box = _synthetic(0)
    with pytest.raises(TypeError):
        study_signals(df_dec, box)          # type: ignore[call-arg]


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_matches_production_on_the_production_level_set(seed):
    df_dec, box = _synthetic(seed)
    got = study_signals(df_dec, box, _LEVEL_PAIRS)
    ref = decision_signals(df_dec, box)
    assert len(got) == len(ref) == len(df_dec)
    mismatch = [(i, g, r) for i, (g, r) in enumerate(zip(got, ref)) if g != r]
    assert not mismatch, f"seed={seed}: {len(mismatch)} mismatches, first={mismatch[:3]}"


def test_empty_frame_returns_empty():
    _, box = _synthetic(0)
    empty = pd.DataFrame({"Date": [], "Open": [], "High": [], "Low": [], "Close": []})
    assert len(study_signals(empty, box, _LEVEL_PAIRS)) == 0


def test_subset_of_pairs_produces_no_more_signals_than_the_full_set():
    df_dec, box = _synthetic(7)
    full = study_signals(df_dec, box, _LEVEL_PAIRS)
    half = study_signals(df_dec, box, _LEVEL_PAIRS[:4])
    assert (half != "hold").sum() <= (full != "hold").sum()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily_boxes_signals.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.daily_boxes.study_signals'`

- [ ] **Step 3: Write minimal implementation**

```python
# research/daily_boxes/study_signals.py
"""The champion Stage-1 box rule, with the level set as a REQUIRED argument.

This is a faithful reimplementation of `optimize.signals.decision_signals`, which hardcodes
`engine._LEVEL_PAIRS` (= weekly + monthly). The only difference is that the level list is passed in, so the
study can ask "what if the daily zones were included?" WITHOUT editing any production module.

Fidelity is not assumed — tests/test_daily_boxes_signals.py asserts this function equals decision_signals
element-for-element when handed _LEVEL_PAIRS.

The rule (verbatim from decision_signals' docstring):
  - color: green = close>open, red = close<open; a doji (close==open) => hold.
  - a pair contributes only if BOTH columns are present and non-NaN ('valid') AND the bar's [low,high]
    overlaps [lower,upper] ('touched').
  - long iff green & touched & close>upper; short iff red & touched & close<lower (any pair).
  - long WINS ties; missing box row / NaN levels => that pair invalid => hold.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
import pandas as pd

from optimize.signals import _box_dates_vec

LevelPairs = Sequence[Tuple[str, str, str]]


def study_signals(df_dec: pd.DataFrame, box: pd.DataFrame, pairs: LevelPairs) -> np.ndarray:
    """Stage-1 signals over an EXPLICIT level-pair list.

    `pairs` is required on purpose: there is no default level set, so a caller can never silently measure a
    different zone universe than it intended.
    """
    if pairs is None:
        raise ValueError("pairs must be an explicit list of (upper, lower, label) triples")

    n = len(df_dec)
    out = np.empty(n, dtype=object)
    if n == 0:
        return out

    O = df_dec["Open"].to_numpy(dtype=float)
    H = df_dec["High"].to_numpy(dtype=float)
    L = df_dec["Low"].to_numpy(dtype=float)
    C = df_dec["Close"].to_numpy(dtype=float)

    sub = box.reindex(_box_dates_vec(pd.DatetimeIndex(df_dec["Date"])))

    green = C > O
    red = C < O
    has_long = np.zeros(n, dtype=bool)
    has_short = np.zeros(n, dtype=bool)

    for upper_col, lower_col, _label in pairs:
        if upper_col not in sub.columns or lower_col not in sub.columns:
            continue
        up = sub[upper_col].to_numpy(dtype=float)
        lo = sub[lower_col].to_numpy(dtype=float)
        valid = ~np.isnan(up) & ~np.isnan(lo)
        touched = valid & (L <= up) & (H >= lo)
        has_long |= green & touched & (C > up)
        has_short |= red & touched & (C < lo)

    out[:] = "hold"
    out[has_short] = "short"
    out[has_long] = "long"        # long assigned last => long wins ties (matches the production rule)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily_boxes_signals.py -v`
Expected: PASS (8 passed — 5 parametrized + 3 others)

- [ ] **Step 5: Commit**

```bash
git add research/daily_boxes/study_signals.py tests/test_daily_boxes_signals.py
git commit -m "feat(daily-boxes): Stage-1 rule with required level set + parity gate vs decision_signals"
```

---

## Task 3: M1 — supply measurement

**Files:**
- Create: `research/daily_boxes/measure.py`
- Test: `tests/test_daily_boxes_measure.py`

**Interfaces:**
- Consumes: `study_signals` (Task 2).
- Produces: `supply_stats(df_dec, box, base_pairs, daily_pairs) -> dict` with keys
  `base_signals, daily_signals, combined_signals, new_signals, new_mask (np.ndarray[bool]),
  days_total, days_with_base_signal, days_scarce, days_rescued_by_daily`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_daily_boxes_measure.py
"""Supply accounting must be exact on a frame whose answer is known by construction."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.daily_boxes.measure import supply_stats           # noqa: E402

# One bar per day, 3 days. Bars are green (close>open) and close above the WEEKLY upper on day 1 only,
# and above the DAILY upper on days 1 and 2. Day 3 touches nothing.
_PAIRS_W = [("WU", "WL", "W")]
_PAIRS_D = [("DU", "DL", "D")]


def _frame():
    df_dec = pd.DataFrame({
        "Date":  pd.to_datetime(["2025-01-02 08:00", "2025-01-03 08:00", "2025-01-06 08:00"]),
        "Open":  [100.0, 100.0, 100.0],
        "High":  [130.0, 130.0, 130.0],
        "Low":    [90.0,  90.0,  90.0],
        "Close": [125.0, 115.0, 101.0],
    })
    box = pd.DataFrame({
        "Date": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-01-06"]),
        "WU":   [120.0, 120.0, 500.0],     # day1 close 125 > 120 -> weekly fires; day2 115 < 120 -> no
        "WL":   [110.0, 110.0, 490.0],
        "DU":   [110.0, 110.0, 500.0],     # day1 AND day2 close above 110 -> daily fires both
        "DL":   [105.0, 105.0, 490.0],
    })
    return df_dec, box.set_index("Date", drop=False)


def test_supply_counts_are_exact():
    df_dec, box = _frame()
    s = supply_stats(df_dec, box, _PAIRS_W, _PAIRS_D)
    assert s["base_signals"] == 1          # only day 1
    assert s["daily_signals"] == 2         # days 1 and 2
    assert s["new_signals"] == 1           # day 2 only (day 1 already covered by weekly)
    assert s["combined_signals"] == 2
    assert list(s["new_mask"]) == [False, True, False]


def test_scarcity_rescue_is_counted():
    df_dec, box = _frame()
    s = supply_stats(df_dec, box, _PAIRS_W, _PAIRS_D)
    assert s["days_total"] == 3
    assert s["days_with_base_signal"] == 1
    assert s["days_scarce"] == 2                 # days 2 and 3 have no weekly signal
    assert s["days_rescued_by_daily"] == 1       # daily creates one on day 2 only


def test_new_signals_never_exceed_daily_signals():
    df_dec, box = _frame()
    s = supply_stats(df_dec, box, _PAIRS_W, _PAIRS_D)
    assert s["new_signals"] <= s["daily_signals"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily_boxes_measure.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.daily_boxes.measure'`

- [ ] **Step 3: Write minimal implementation**

```python
# research/daily_boxes/measure.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily_boxes_measure.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add research/daily_boxes/measure.py tests/test_daily_boxes_measure.py
git commit -m "feat(daily-boxes): M1 supply accounting (new-signal + scarcity-rescue counts)"
```

---

## Task 4: M2 — gate survival and the uplift ratio

**Files:**
- Modify: `research/daily_boxes/measure.py` (append)
- Test: `tests/test_daily_boxes_measure.py` (append)

**Interfaces:**
- Consumes: `new_mask` from `supply_stats` (Task 3).
- Produces: `gate_survival(new_mask, gate, baseline_entries) -> dict` with keys
  `new_signals, gate_surviving, uplift, verdict_band`. `verdict_band` ∈ `{"large", "gray", "negligible"}`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_daily_boxes_measure.py`:

```python
from research.daily_boxes.measure import gate_survival          # noqa: E402


def test_gate_survival_counts_and_uplift():
    new_mask = np.array([True, True, True, False])
    gate = np.array([True, False, True, True])
    r = gate_survival(new_mask, gate, baseline_entries=10)
    assert r["new_signals"] == 3
    assert r["gate_surviving"] == 2          # bars 0 and 2
    assert r["uplift"] == 0.2                # 2/10


def test_verdict_bands_use_the_prefixed_thresholds():
    gate = np.ones(100, dtype=bool)
    # 25 surviving / 100 baseline = 25% -> large
    assert gate_survival(np.array([True]*25 + [False]*75), gate, 100)["verdict_band"] == "large"
    # 10/100 = 10% -> gray
    assert gate_survival(np.array([True]*10 + [False]*90), gate, 100)["verdict_band"] == "gray"
    # 3/100 = 3% -> negligible
    assert gate_survival(np.array([True]*3 + [False]*97), gate, 100)["verdict_band"] == "negligible"


def test_zero_baseline_entries_is_an_error_not_a_divide_by_zero():
    import pytest as _pytest
    with _pytest.raises(ValueError):
        gate_survival(np.array([True]), np.array([True]), baseline_entries=0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily_boxes_measure.py -v -k gate or verdict or baseline`
Expected: FAIL — `ImportError: cannot import name 'gate_survival'`

- [ ] **Step 3: Write minimal implementation**

Append to `research/daily_boxes/measure.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily_boxes_measure.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add research/daily_boxes/measure.py tests/test_daily_boxes_measure.py
git commit -m "feat(daily-boxes): M2 gate survival + pre-committed verdict bands"
```

---

## Task 5: M3 — informativeness, two controls, bootstrap CI, power

**Files:**
- Create: `research/daily_boxes/informativeness.py`
- Test: `tests/test_daily_boxes_informativeness.py`

**Interfaces:**
- Consumes: `study_signals` (Task 2).
- Produces:
  - `directional_forward_returns(df_dec, sig, horizon) -> np.ndarray` (NaN where no signal or no future bar)
  - `control_location(box, pairs, rng, frac=0.02) -> pd.DataFrame`
  - `control_date(box, pairs, rng) -> pd.DataFrame`
  - `block_bootstrap_ci(x, block, n_boot, alpha, rng) -> tuple[float, float]`
  - `min_detectable_effect(x, power=0.80, alpha=0.05) -> float`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_daily_boxes_informativeness.py
"""Forward-return mechanics, both dumb controls, bootstrap CI and the power floor."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.daily_boxes.informativeness import (               # noqa: E402
    block_bootstrap_ci, control_date, control_location,
    directional_forward_returns, min_detectable_effect,
)

_PAIRS = [("DU", "DL", "D")]


def test_directional_forward_returns_signs_and_nans():
    df = pd.DataFrame({
        "Date": pd.date_range("2025-01-02", periods=4, freq="4h"),
        "Close": [100.0, 110.0, 105.0, 130.0],
    })
    sig = np.array(["long", "short", "hold", "long"], dtype=object)
    r = directional_forward_returns(df, sig, horizon=1)
    assert r[0] == 10.0          # long, +10 -> +10
    assert r[1] == 5.0           # short, price fell 5 -> +5 in signal direction
    assert np.isnan(r[2])        # hold -> no measurement
    assert np.isnan(r[3])        # no bar after the last one


def test_control_location_preserves_zone_width():
    box = pd.DataFrame({"Date": pd.date_range("2025-01-02", periods=5, freq="D"),
                        "DU": np.full(5, 110.0), "DL": np.full(5, 100.0)}).set_index("Date", drop=False)
    out = control_location(box, _PAIRS, np.random.default_rng(0), frac=0.02)
    width_in = (box["DU"] - box["DL"]).to_numpy()
    width_out = (out["DU"] - out["DL"]).to_numpy()
    assert np.allclose(width_in, width_out)                      # width preserved
    assert not np.allclose(box["DU"].to_numpy(), out["DU"].to_numpy())   # location moved


def test_control_date_is_a_permutation_of_the_same_rows():
    box = pd.DataFrame({"Date": pd.date_range("2025-01-02", periods=6, freq="D"),
                        "DU": np.arange(6, dtype=float) + 100,
                        "DL": np.arange(6, dtype=float) + 90}).set_index("Date", drop=False)
    out = control_date(box, _PAIRS, np.random.default_rng(1))
    assert sorted(out["DU"].tolist()) == sorted(box["DU"].tolist())      # same multiset
    assert out.index.equals(box.index)                                    # dates unchanged


def test_block_bootstrap_ci_brackets_the_mean_of_a_constant_series():
    x = np.full(200, 7.0)
    lo, hi = block_bootstrap_ci(x, block=20, n_boot=200, alpha=0.10,
                                rng=np.random.default_rng(2))
    assert lo <= 7.0 <= hi


def test_block_bootstrap_ci_is_deterministic_for_a_fixed_seed():
    x = np.random.default_rng(9).normal(0, 1, 300)
    a = block_bootstrap_ci(x, 20, 200, 0.10, np.random.default_rng(3))
    b = block_bootstrap_ci(x, 20, 200, 0.10, np.random.default_rng(3))
    assert a == b


def test_min_detectable_effect_shrinks_as_n_grows():
    rng = np.random.default_rng(4)
    small = min_detectable_effect(rng.normal(0, 1, 100))
    large = min_detectable_effect(rng.normal(0, 1, 10000))
    assert large < small
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily_boxes_informativeness.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.daily_boxes.informativeness'`

- [ ] **Step 3: Write minimal implementation**

```python
# research/daily_boxes/informativeness.py
"""M3 — do daily zones mark anything real?

Operationalized to match what the strategy actually trades: after a signal fires at a zone, does price CONTINUE
in the signal's direction? Measured against two dumb controls, with a block-bootstrap CI (returns are
autocorrelated, so an i.i.d. bootstrap would understate the interval) and an explicit power floor for nulls.
"""
from __future__ import annotations

from typing import Sequence, Tuple

import numpy as np
import pandas as pd

from research.daily_boxes.study_signals import LevelPairs


def directional_forward_returns(df_dec: pd.DataFrame, sig: np.ndarray, horizon: int) -> np.ndarray:
    """Points gained IN THE SIGNAL'S DIRECTION `horizon` bars after each signal.

    long  -> (close[i+h] - close[i])
    short -> (close[i] - close[i+h])
    hold / no future bar -> NaN (excluded from every statistic)
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    C = df_dec["Close"].to_numpy(dtype=float)
    n = len(C)
    fwd = np.full(n, np.nan)
    if n > horizon:
        fwd[: n - horizon] = C[horizon:] - C[: n - horizon]
    direction = np.where(sig == "long", 1.0, np.where(sig == "short", -1.0, np.nan))
    return fwd * direction


def control_location(box: pd.DataFrame, pairs: LevelPairs, rng: np.random.Generator,
                     frac: float) -> pd.DataFrame:
    """CONTROL 1 — keep each zone's WIDTH, move its LOCATION by a random offset.

    Offset is drawn per (row, pair) as Uniform(-frac, +frac) * |zone midpoint|, so it scales with price. Kills
    the "any line looks meaningful" explanation while holding zone geometry fixed.
    """
    out = box.copy()
    for upper, lower, _label in pairs:
        if upper not in out.columns or lower not in out.columns:
            continue
        up = out[upper].to_numpy(dtype=float)
        lo = out[lower].to_numpy(dtype=float)
        mid = (up + lo) / 2.0
        offset = rng.uniform(-frac, frac, size=len(out)) * np.abs(mid)
        out[upper] = up + offset
        out[lower] = lo + offset
    return out


def control_date(box: pd.DataFrame, pairs: LevelPairs, rng: np.random.Generator) -> pd.DataFrame:
    """CONTROL 2 — give each day ANOTHER day's zones.

    Zone geometry and the overall level distribution are preserved exactly; only the date-specific information
    is destroyed. Rows are permuted as whole units so a day's zones stay internally consistent.
    """
    out = box.copy()
    cols = [c for u, l, _ in pairs for c in (u, l) if c in out.columns]
    if not cols:
        return out
    perm = rng.permutation(len(out))
    out[cols] = out[cols].to_numpy()[perm]
    return out


def block_bootstrap_ci(x: np.ndarray, block: int, n_boot: int, alpha: float,
                       rng: np.random.Generator) -> Tuple[float, float]:
    """Two-sided (1-alpha) CI for the MEAN of `x` via a moving-block bootstrap.

    Blocks preserve short-range autocorrelation; an i.i.d. bootstrap would produce a falsely narrow interval on
    financial returns.
    """
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return (float("nan"), float("nan"))
    if block < 1:
        raise ValueError(f"block must be >= 1, got {block}")
    block = min(block, len(x))
    n_blocks = int(np.ceil(len(x) / block))
    max_start = len(x) - block + 1

    means = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        starts = rng.integers(0, max_start, size=n_blocks)
        sample = np.concatenate([x[s:s + block] for s in starts])[: len(x)]
        means[b] = sample.mean()
    lo = float(np.quantile(means, alpha / 2.0))
    hi = float(np.quantile(means, 1.0 - alpha / 2.0))
    return (lo, hi)


def min_detectable_effect(x: np.ndarray, power: float = 0.80, alpha: float = 0.05) -> float:
    """Smallest mean effect a two-sided one-sample t-test could detect at `power`, given this sample's spread.

    Reported alongside every NULL result: a null that could not have detected a tradeable effect anyway is not
    evidence of absence. Uses the normal approximation (z=1.96 at alpha=.05, z=0.84 at power=.80), which is
    accurate at the sample sizes here (n in the hundreds to thousands).
    """
    from scipy.stats import norm

    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2:
        return float("nan")
    z_alpha = norm.ppf(1.0 - alpha / 2.0)
    z_power = norm.ppf(power)
    return float((z_alpha + z_power) * x.std(ddof=1) / np.sqrt(n))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily_boxes_informativeness.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add research/daily_boxes/informativeness.py tests/test_daily_boxes_informativeness.py
git commit -m "feat(daily-boxes): M3 forward returns, location+date controls, block-bootstrap CI, power floor"
```

---

## Task 6: The M3-only extended (2024–26) frame

**Files:**
- Create: `research/daily_boxes/extended_frame.py`
- Test: `tests/test_daily_boxes_extended_frame.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `load_extended(tf_name: str) -> tuple[pd.DataFrame, pd.DataFrame]` returning `(df_dec, box)` spanning
  2024-01-01 → 2026-05-19, with `Date/Open/High/Low/Close` on `df_dec` and a Date-indexed `box`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_daily_boxes_extended_frame.py
"""The M3 extension must be a clean, assertion-guarded concatenation - or fail loudly."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from research.daily_boxes.extended_frame import _concat_checked, load_extended   # noqa: E402


def test_concat_rejects_overlapping_dates():
    a = pd.DataFrame({"Date": pd.to_datetime(["2024-01-01", "2024-01-02"]), "v": [1, 2]})
    b = pd.DataFrame({"Date": pd.to_datetime(["2024-01-02", "2024-01-03"]), "v": [3, 4]})
    with pytest.raises(ValueError, match="duplicate"):
        _concat_checked(a, b, "test")


def test_concat_rejects_schema_mismatch():
    a = pd.DataFrame({"Date": pd.to_datetime(["2024-01-01"]), "v": [1]})
    b = pd.DataFrame({"Date": pd.to_datetime(["2024-01-02"]), "w": [2]})
    with pytest.raises(ValueError, match="schema"):
        _concat_checked(a, b, "test")


def test_concat_sorts_and_preserves_all_rows():
    a = pd.DataFrame({"Date": pd.to_datetime(["2024-01-03", "2024-01-01"]), "v": [3, 1]})
    b = pd.DataFrame({"Date": pd.to_datetime(["2024-01-02"]), "v": [2]})
    out = _concat_checked(a, b, "test")
    assert len(out) == 3
    assert out["v"].tolist() == [1, 2, 3]
    assert out["Date"].is_monotonic_increasing


@pytest.mark.slow
def test_load_extended_real_data_spans_2024_to_2026():
    try:
        df_dec, box = load_extended("4h")
    except FileNotFoundError as e:
        pytest.skip(f"real data not present: {e}")
    assert df_dec["Date"].min().year == 2024
    assert df_dec["Date"].max().year == 2026
    assert len(df_dec) == 3663, f"expected 3663 4h bars, got {len(df_dec)}"
    assert {"Open", "High", "Low", "Close"}.issubset(df_dec.columns)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_daily_boxes_extended_frame.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'research.daily_boxes.extended_frame'`

- [ ] **Step 3: Write minimal implementation**

```python
# research/daily_boxes/extended_frame.py
"""The 2024-2026 frame used ONLY by M3.

M1/M2 must run on the champion frame (2,119 bars, 2025-2026) because they depend on champion gate arrays.
M3 depends on no champion, so it takes the extra year of data for statistical power. The two windows are
reported separately and never mixed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

import config
from loader import load_data

_CANDLE_2024 = "NQ_{tf}_2024.csv"
_BOX_2024 = "NQ_full_data_2024.csv"


def _concat_checked(older: pd.DataFrame, newer: pd.DataFrame, label: str) -> pd.DataFrame:
    """Concatenate two date-keyed frames, refusing anything that would silently corrupt the study."""
    if set(older.columns) != set(newer.columns):
        only_a = sorted(set(older.columns) - set(newer.columns))
        only_b = sorted(set(newer.columns) - set(older.columns))
        raise ValueError(f"{label}: schema mismatch; only-in-older={only_a} only-in-newer={only_b}")
    out = pd.concat([older, newer[older.columns]], ignore_index=True)
    dupes = out["Date"].duplicated().sum()
    if dupes:
        raise ValueError(f"{label}: {dupes} duplicate Date rows after concat")
    return out.sort_values("Date").reset_index(drop=True)


def _read_candles(path: Path) -> pd.DataFrame:
    """Reuse the PRODUCTION loader so the study's frame is built exactly like the champion's.

    loader.load_data handles the datetime->Date and open/high/low/close->Title-case renaming, column
    stripping and Date parsing. Hand-rolling that here would risk silently diverging from production.
    """
    df = load_data(str(path)).sort_values("Date").reset_index(drop=True)
    return df[["Date", "Open", "High", "Low", "Close"]]


def load_extended(tf_name: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return (df_dec, box) spanning 2024-01-01 -> 2026-05-19 for the given decision timeframe."""
    root = Path(config.DATA_ROOT)
    c_2024 = root / "2024_data" / _CANDLE_2024.format(tf=tf_name)
    c_main = root / "full_data" / f"NQ_{tf_name}.csv"
    b_2024 = root / "2024_data" / _BOX_2024
    b_main = root / "full_data" / "NQ_full_data.csv"
    for p in (c_2024, c_main, b_2024, b_main):
        if not p.exists():
            raise FileNotFoundError(p)

    df_dec = _concat_checked(_read_candles(c_2024), _read_candles(c_main), "candles")

    box_a = pd.read_csv(b_2024)
    box_b = pd.read_csv(b_main)
    for b in (box_a, box_b):
        b["Date"] = pd.to_datetime(b["Date"]).dt.normalize()
    common = [c for c in box_a.columns if c in set(box_b.columns)]
    box = _concat_checked(box_a[common].drop_duplicates(subset=["Date"]),
                          box_b[common].drop_duplicates(subset=["Date"]), "box")
    return df_dec, box.set_index("Date", drop=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_daily_boxes_extended_frame.py -v`
Expected: PASS (3 passed, 1 skipped locally — the `slow` real-data test runs on the server)

- [ ] **Step 5: Commit**

```bash
git add research/daily_boxes/extended_frame.py tests/test_daily_boxes_extended_frame.py
git commit -m "feat(daily-boxes): assertion-guarded 2024-26 frame for the M3 power extension"
```

---

## Task 7: CLI entry point with mandatory parameter echo

**Files:**
- Create: `research/daily_boxes/run_study.py`

**Interfaces:**
- Consumes: every module above; `optimize.counterfactual_pause.load_champion` / `_engine_gate`;
  `engine._LEVEL_PAIRS`.
- Produces: a CLI writing `results/daily_boxes/{tf}_supply.csv`, `{tf}_informativeness.csv`, and a printed
  summary block.

- [ ] **Step 1: Write the implementation**

```python
# research/daily_boxes/run_study.py
"""Run the daily-box characterization. SERVER ONLY (loads champion + 1-min data).

Usage:
  python3 -m research.daily_boxes.run_study --tf 4h --horizons 1,3,6 --seed 20260723 --draws 1000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_PROJ = Path(__file__).resolve().parents[2]
if str(_PROJ) not in sys.path:
    sys.path.insert(0, str(_PROJ))

from engine import _LEVEL_PAIRS                                          # noqa: E402
from optimize import counterfactual_pause as cp                          # noqa: E402
from optimize.signals import decision_signals                            # noqa: E402
from research.daily_boxes.extended_frame import load_extended            # noqa: E402
from research.daily_boxes.informativeness import (                       # noqa: E402
    block_bootstrap_ci, control_date, control_location,
    directional_forward_returns, min_detectable_effect,
)
from research.daily_boxes.levels import DAILY_LEVELS                     # noqa: E402
from research.daily_boxes.measure import gate_survival, supply_stats     # noqa: E402
from research.daily_boxes.study_signals import study_signals             # noqa: E402

_EXPECTED_BARS = {"4h": 2119}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", required=True)
    ap.add_argument("--horizons", required=True, help="comma-separated bar counts, e.g. 1,3,6")
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--draws", type=int, required=True, help="control draws / bootstrap resamples")
    ap.add_argument("--block", type=int, required=True, help="bootstrap block length in bars")
    ap.add_argument("--loc-frac", type=float, required=True, help="control-1 offset as a fraction of price")
    ap.add_argument("--out", default="results/daily_boxes")
    a = ap.parse_args()
    horizons = [int(h) for h in a.horizons.split(",")]

    # ---- MANDATORY parameter echo: no silent defaults, ever.
    print("=" * 72)
    print("DAILY-BOX CHARACTERIZATION -- parameters actually used")
    print(f"  timeframe        : {a.tf}")
    print(f"  horizons (bars)  : {horizons}")
    print(f"  seed             : {a.seed}")
    print(f"  control draws    : {a.draws}")
    print(f"  bootstrap block  : {a.block}")
    print(f"  loc control frac : {a.loc_frac}")
    print(f"  base level pairs : {[p[2] for p in _LEVEL_PAIRS]}")
    print(f"  daily level pairs: {[p[2] for p in DAILY_LEVELS]}")
    print("=" * 72)

    rng = np.random.default_rng(a.seed)
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # ================= M1 + M2 : champion window =================
    C = cp.load_champion(a.tf)
    df_dec, box, gate = C["d"], C["box"], cp._engine_gate(C)
    n_bars = len(df_dec)
    print(f"\n[M1/M2] champion frame: {n_bars} bars "
          f"{df_dec['Date'].min()} -> {df_dec['Date'].max()}")
    if a.tf in _EXPECTED_BARS and n_bars != _EXPECTED_BARS[a.tf]:
        raise SystemExit(f"ABORT: expected {_EXPECTED_BARS[a.tf]} bars for {a.tf}, got {n_bars}. "
                         "The champion frame moved; the baseline comparison would be invalid.")

    # fidelity gate -- our rule must equal production's on the production level set
    ours = study_signals(df_dec, box, _LEVEL_PAIRS)
    prod = decision_signals(df_dec, box)
    n_mismatch = int((ours != prod).sum())
    if n_mismatch:
        raise SystemExit(f"ABORT: parity gate failed -- {n_mismatch} bars differ from decision_signals.")
    print(f"[parity] study_signals == decision_signals on all {n_bars} bars  OK")

    s = supply_stats(df_dec, box, _LEVEL_PAIRS, DAILY_LEVELS)
    baseline_entries = int(len(cp.champion_taken_trades(C)))
    g = gate_survival(s["new_mask"], gate, baseline_entries)

    print(f"\n[M1] base={s['base_signals']}  daily={s['daily_signals']}  "
          f"combined={s['combined_signals']}  NEW={s['new_signals']}")
    print(f"[M1] days: total={s['days_total']} with-base={s['days_with_base_signal']} "
          f"scarce={s['days_scarce']} rescued-by-daily={s['days_rescued_by_daily']}")
    print(f"[M2] baseline entries={baseline_entries}  new gate-surviving={g['gate_surviving']}  "
          f"uplift={g['uplift']:.1%}  band={g['verdict_band']}")
    print("[M2] NOTE: upper bound -- ignores position-carry, cooldown and breaker.")

    pd.DataFrame([{**{k: v for k, v in s.items() if k != "new_mask"},
                   **g, "tf": a.tf, "bars": n_bars,
                   "baseline_entries": baseline_entries}]).to_csv(
        outdir / f"{a.tf}_supply.csv", index=False)

    # ================= M3 : both windows =================
    rows = []
    for window, (dd, bx) in {
        "champion_2025_2026": (df_dec, box),
        "extended_2024_2026": load_extended(a.tf),
    }.items():
        real = study_signals(dd, bx, DAILY_LEVELS)
        c1 = study_signals(dd, control_location(bx, DAILY_LEVELS, rng, a.loc_frac), DAILY_LEVELS)
        c2 = study_signals(dd, control_date(bx, DAILY_LEVELS, rng), DAILY_LEVELS)
        for h in horizons:
            for label, sg in (("real", real), ("control_location", c1), ("control_date", c2)):
                r = directional_forward_returns(dd, sg, h)
                r = r[~np.isnan(r)]
                lo, hi = block_bootstrap_ci(r, a.block, a.draws, 0.10, np.random.default_rng(a.seed))
                rows.append({
                    "window": window, "horizon": h, "arm": label, "n": len(r),
                    "mean_points": float(r.mean()) if len(r) else float("nan"),
                    "mean_dollars": float(r.mean()) * 20.0 if len(r) else float("nan"),
                    "ci90_lo": lo, "ci90_hi": hi,
                    "min_detectable_effect_points": min_detectable_effect(r),
                })
                print(f"[M3] {window:20s} h={h} {label:17s} n={len(r):6d} "
                      f"mean={rows[-1]['mean_points']:+8.2f}pt "
                      f"CI90=[{lo:+.2f},{hi:+.2f}] MDE={rows[-1]['min_detectable_effect_points']:.2f}")

    pd.DataFrame(rows).to_csv(outdir / f"{a.tf}_informativeness.csv", index=False)
    print(f"\nwrote {outdir}/{a.tf}_supply.csv and {outdir}/{a.tf}_informativeness.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify it imports and shows help (no data needed)**

Run: `python3 -m research.daily_boxes.run_study --help`
Expected: argparse help text listing `--tf --horizons --seed --draws --block --loc-frac --out`

- [ ] **Step 3: Run the whole local test suite**

Run: `python3 -m pytest tests/test_daily_boxes_*.py -v`
Expected: PASS — all tasks 1–6 green, one `slow` test skipped locally

- [ ] **Step 4: Commit**

```bash
git add research/daily_boxes/run_study.py
git commit -m "feat(daily-boxes): CLI entry point with mandatory parameter echo and parity abort"
```

---

## Task 8: Server run + golden evidence + report

**Files:**
- Create: `docs/superpowers/DAILY-BOX-01-characterization-results.md`

**Interfaces:**
- Consumes: the CSVs from Task 7.
- Produces: the report and the **go B / go C / close** verdict.

- [ ] **Step 1: Confirm nothing production-side moved**

On the server, with `WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data` and the
venv `/home/dev/Mulham/.venv/bin/python3`:

Run: `python3 perf/check_golden.py`
Expected: **6/6 MATCH**. If not, stop — something outside this study changed.

- [ ] **Step 2: Run the study on 4h (primary)**

```bash
python3 -m research.daily_boxes.run_study \
  --tf 4h --horizons 1,3,6 --seed 20260723 --draws 1000 --block 20 --loc-frac 0.02
```

Expected: the parameter echo, `[parity] ... OK`, then M1/M2/M3 lines and two CSVs.
If the parity gate aborts, the study is wrong — fix before interpreting anything.

- [ ] **Step 3: Run the study on 1h (secondary)**

```bash
python3 -m research.daily_boxes.run_study \
  --tf 1h --horizons 1,3,6 --seed 20260723 --draws 1000 --block 20 --loc-frac 0.02
```

Expected: same structure. (`_EXPECTED_BARS` has no 1h entry, so the bar-count assertion is skipped by design —
1h has no published baseline to protect.)

- [ ] **Step 4: Re-run golden as after-evidence**

Run: `python3 perf/check_golden.py`
Expected: **6/6 MATCH** — proves the study left production untouched.

- [ ] **Step 5: Write the report**

Create `docs/superpowers/DAILY-BOX-01-characterization-results.md` following the house format: plain language,
every term and column spelled out, dollar examples at $20/point, Mermaid visuals, explicit "what went well /
what went wrong", and the decision-rule table from the spec with the actual numbers filled in. State the verdict
(**go B** / **go C** / **close permanently**) and, if any result is null, its power floor.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/DAILY-BOX-01-characterization-results.md results/daily_boxes/
git commit -m "docs(daily-boxes): DAILY-BOX-01 characterization results and verdict"
```

---

## Self-Review

**Spec coverage:**

| Spec section | Covered by |
|---|---|
| §1 Goal / verdict | Task 8 |
| §2 Split windows (2,119 / 3,663) | Task 6 (extended frame), Task 7 (`_EXPECTED_BARS` assertion, both-windows M3 loop) |
| §3 No production edits + parity gate | Task 2 (parity test), Task 7 (runtime parity abort), Task 8 (golden 6/6 before & after) |
| §4 Components | Tasks 1–7, one module each |
| §5 M1 supply | Task 3 |
| §5 M2 gate survival | Task 4 |
| §5 M3 informativeness + 2 controls + CI + power | Task 5, Task 7 |
| §6 Decision rule / pre-fixed bands | Task 4 (`_LARGE_THRESHOLD`, `_NEGLIGIBLE_THRESHOLD`) |
| §7 4h primary, 1h secondary | Task 8 steps 2–3 |
| §8 Error handling / no silent defaults | Task 4 (zero-baseline raise), Task 6 (`_concat_checked`), Task 7 (all args `required=True`, parameter echo) |
| §9 Verification | Tasks 1–7 tests + Task 8 golden |
| §10 Outputs | Task 7 CSVs + Task 8 report |

No gaps.

**Placeholder scan:** no TBD/TODO; every code step contains complete runnable code; no "similar to Task N".

**Type consistency:** `LevelPairs` defined in `study_signals.py` and imported by `measure.py` and
`informativeness.py`. `supply_stats` returns `new_mask`, consumed by `gate_survival` under the same name.
`study_signals(df_dec, box, pairs)` argument order is identical at all six call sites. `load_extended` returns
`(df_dec, box)`, unpacked as such in `run_study.py`.
