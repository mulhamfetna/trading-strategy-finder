# NSGA-II Multi-Objective Optimisation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dashboard-driven multi-objective parameter optimiser for `BoxStrategy` that explores `(sl_soft_points, sl_hard_points, tp_target_points)` and surfaces a live Pareto front of profit-factor vs max-drawdown candidates.

**Architecture:** New `src/optimization/` Python package wrapping Optuna's `NSGAIISampler` with SQLite persistence; SSE streams trial-by-trial progress to a new `/optimize` route on the Vue 3 frontend. Apply-and-Backtest single-click flow splices chosen params into the settings store and triggers the existing backtest endpoint.

**Tech Stack:** Python (Optuna + SQLAlchemy for SQLite), FastAPI SSE, Vue 3 + Pinia + Chart.js for the scatter UI.

**Source spec:** `docs/superpowers/specs/2026-05-23-nsga2-optimization-design.md`
**Target branch:** `dev`

---

## File structure

### Backend — new files

```
src/optimization/__init__.py        — package marker (empty)
src/optimization/walk_forward.py    — equal-time-span fold splitter
src/optimization/objective.py        — per-trial evaluate() function
src/optimization/persistence.py      — list/scan SQLite studies
src/optimization/study.py            — NSGAIISampler study lifecycle + run loop
src/optimization/sse_bridge.py       — Optuna callback → queue.Queue → SSE frames
```

### Backend — modified files

```
src/api/schemas.py                   — add OptimizeRequest, SearchSpace, etc.
src/api/app.py                        — add 4 endpoints + _opt_event_stream
requirements.txt                      — add optuna
.gitignore                            — add optuna_studies.db
```

### Frontend — new files

```
frontend/src/components/OptimizePanel.vue
frontend/src/components/ParetoScatter.vue
frontend/src/components/StudyContinueCard.vue
frontend/src/stores/optimize.ts
frontend/src/services/optimize_sse.ts
frontend/tests/optimize_panel.test.ts
frontend/tests/optimize_presets.test.ts
frontend/tests/optimize_sse_parser.test.ts
```

### Frontend — modified files

```
frontend/src/types.ts                — add OptimizeRequest, TrialResult, ParetoPoint
frontend/src/router.ts (or App.vue)  — add /optimize route
frontend/package.json                 — add chart.js + vue-chartjs
```

### Tests — new files

```
tests/test_walk_forward_splits.py
tests/test_walk_forward_state_isolation.py
tests/test_objective_edge_cases.py
tests/test_nsga2_study_runs.py
tests/test_api_optimize_sse.py
tests/test_optimize_persistence.py
```

---

## Phase A — Setup

### Task A.1: Add Optuna dependency + gitignore the studies DB

**Files:**
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Add optuna to requirements.txt**

Edit `requirements.txt`, appending:

```
optuna>=3.5.0
```

- [ ] **Step 2: Install**

Run: `pip install -r requirements.txt`
Expected: pulls `optuna`, `sqlalchemy`, `alembic` (transitive). Verify with `pip show optuna`.

- [ ] **Step 3: Gitignore the studies database file**

Append to `.gitignore`:

```
# Optuna persistence
optuna_studies.db
optuna_studies.db-journal
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt .gitignore
git commit -m "build(deps): add optuna for NSGA-II multi-objective optimiser"
```

---

## Phase B — Pydantic schemas

### Task B.1: Add OptimizeRequest + SearchSpace + TrialResult + StudySummary models

**Files:**
- Modify: `src/api/schemas.py` (append at end)
- Test: `tests/test_optimize_schemas.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_optimize_schemas.py`:

```python
"""Schema validation tests for the NSGA-II optimiser endpoints.

No-fallback rule: every field is required. A request missing any field
must raise pydantic.ValidationError; a complete request must validate.
"""

import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api.schemas import (
    OptimizeBudget,
    OptimizeFoldsConfig,
    OptimizeRequest,
    OptimizeSearchSpace,
    ParetoPoint,
    StudySummary,
    TrialResult,
)
from tests._fixtures import box_params_dict


def _complete_search_space() -> dict:
    return {
        'sl_soft_points': [50.0, 300.0],
        'sl_hard_delta': [50.0, 600.0],
        'tp_target_points': [75.0, 250.0],
    }


def test_optimize_request_accepts_complete_payload():
    body = {
        'baseline_params': box_params_dict(),
        'search_space': _complete_search_space(),
        'budget': {'population_size': 40, 'generations': 15},
        'folds': {'count': 3, 'min_trades_per_fold': 15},
        'data_path': 'NQ_4h.csv',
        'week_data_path': 'NQ_week_data_shifted.csv',
        'month_data_path': 'NQ_month_data_shifted.csv',
        'max_duration_s': 1800,
    }
    req = OptimizeRequest(**body)
    assert req.budget.population_size == 40
    assert req.folds.count == 3


def test_optimize_request_rejects_missing_budget():
    body = {
        'baseline_params': box_params_dict(),
        'search_space': _complete_search_space(),
        # 'budget' missing
        'folds': {'count': 3, 'min_trades_per_fold': 15},
        'data_path': 'NQ_4h.csv',
        'week_data_path': 'NQ_week_data_shifted.csv',
        'month_data_path': 'NQ_month_data_shifted.csv',
        'max_duration_s': 1800,
    }
    with pytest.raises(ValidationError):
        OptimizeRequest(**body)


def test_search_space_rejects_inverted_range():
    # sl_soft_points lower > upper
    with pytest.raises(ValidationError):
        OptimizeSearchSpace(
            sl_soft_points=[300.0, 50.0],
            sl_hard_delta=[50.0, 600.0],
            tp_target_points=[75.0, 250.0],
        )


def test_trial_result_complete_shape():
    tr = TrialResult(
        trial_number=42,
        params={'sl_soft_points': 180.0, 'sl_hard_points': 280.0, 'tp_target_points': 175.0},
        values=[1.84, -2300.0],
        state='complete',
        pruned_reason=None,
    )
    assert tr.state == 'complete'


def test_pareto_point_requires_all_fields():
    with pytest.raises(ValidationError):
        ParetoPoint(trial_number=1, params={'a': 1.0})  # values missing


def test_study_summary_describes_resumable_study():
    s = StudySummary(
        study_id='abc123',
        trials_done=247,
        trials_total=600,
        started_at='2026-05-23T18:42:00Z',
        is_complete=False,
        pareto_size=12,
    )
    assert s.is_complete is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_optimize_schemas.py -v`
Expected: ImportError — schemas not defined yet.

- [ ] **Step 3: Append the schemas to src/api/schemas.py**

Append at the very end of `src/api/schemas.py`:

```python
# ---- /api/optimize/box (NSGA-II multi-objective optimiser, SSE-streamed) ----

from pydantic import field_validator


class OptimizeSearchSpace(BaseModel):
    """Per-parameter [lower, upper] search bounds.

    `sl_hard_delta` encodes the constraint sl_hard >= sl_soft + 50 structurally —
    Optuna suggests `sl_hard = sl_soft + delta` where delta lies in this range.
    """
    sl_soft_points: List[float] = Field(..., min_length=2, max_length=2)
    sl_hard_delta:  List[float] = Field(..., min_length=2, max_length=2)
    tp_target_points: List[float] = Field(..., min_length=2, max_length=2)

    @field_validator('sl_soft_points', 'sl_hard_delta', 'tp_target_points')
    @classmethod
    def _bounds_ordered(cls, v: List[float]) -> List[float]:
        if v[0] >= v[1]:
            raise ValueError(f'lower must be strictly less than upper, got {v}')
        return v


class OptimizeBudget(BaseModel):
    population_size: int = Field(..., gt=0, description="NSGA-II population per generation.")
    generations:     int = Field(..., gt=0, description="Number of generations.")


class OptimizeFoldsConfig(BaseModel):
    count: int = Field(..., ge=2, description="Walk-forward fold count.")
    min_trades_per_fold: int = Field(..., ge=1, description="Floor below which a fold prunes the trial.")


class OptimizeRequest(BaseModel):
    """Request body for POST /api/optimize/box. Every field required."""
    baseline_params: BoxParamsModel
    search_space:    OptimizeSearchSpace
    budget:          OptimizeBudget
    folds:           OptimizeFoldsConfig
    data_path:       str
    week_data_path:  str
    month_data_path: str
    max_duration_s:  int = Field(..., gt=0)


class TrialResult(BaseModel):
    """Payload of `event: trial` (and of pareto-front entries)."""
    trial_number: int
    params:       dict
    values:       List[float] = Field(..., min_length=2, max_length=2)
    state:        Literal['complete', 'pruned']
    pruned_reason: Optional[str] = Field(...)


class ParetoPoint(BaseModel):
    trial_number: int
    params:       dict
    values:       List[float] = Field(..., min_length=2, max_length=2)


class StudySummary(BaseModel):
    """Payload for GET /api/optimize/studies and `event: study_started`."""
    study_id:     str
    trials_done:  int
    trials_total: int
    started_at:   str
    is_complete:  bool
    pareto_size:  int


class StudiesListResponse(BaseModel):
    studies: List[StudySummary]
```

Also add this import at the top of `src/api/schemas.py` (already has Pydantic imports — just confirm `Literal` is there; it is):

No new import line needed — `field_validator` is imported inline above.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_optimize_schemas.py -v`
Expected: 5 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/schemas.py tests/test_optimize_schemas.py
git commit -m "feat(optimize): Pydantic schemas for NSGA-II request/response"
```

---

## Phase C — Walk-forward fold splitter

### Task C.1: Implement `split_folds`

**Files:**
- Create: `src/optimization/__init__.py`
- Create: `src/optimization/walk_forward.py`
- Test:   `tests/test_walk_forward_splits.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_walk_forward_splits.py`:

```python
"""Fold-splitter correctness tests.

The splitter must:
1. Produce exactly `fold_count` non-overlapping DataFrames whose union == input.
2. Use equal calendar-time spans (not equal candle counts).
3. Raise ConfigurationError with code='invalid-fold-count' if N < 2.
4. Raise ConfigurationError with code='insufficient-data-window' if the
   input is too small for the requested fold count.
"""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.exceptions import ConfigurationError
from src.optimization.walk_forward import split_folds


def _synth_4h(n_bars: int) -> pd.DataFrame:
    timestamps = pd.date_range(start='2025-01-01', periods=n_bars, freq='4h')
    return pd.DataFrame({
        'Date':   timestamps,
        'Open':   [20000.0] * n_bars,
        'High':   [20010.0] * n_bars,
        'Low':    [19990.0] * n_bars,
        'Close':  [20005.0] * n_bars,
        'Volume': [1000] * n_bars,
    })


def test_three_folds_cover_full_range_with_no_overlap():
    df = _synth_4h(300)   # 50 calendar days @ 4h bars
    folds = split_folds(df, fold_count=3)
    assert len(folds) == 3
    # Union: every bar must appear in exactly one fold.
    total = sum(len(f) for f in folds)
    assert total == len(df)
    # No overlap: bar-set intersections are empty.
    seen = set()
    for f in folds:
        idxs = set(f['Date'].astype(str))
        assert not (idxs & seen)
        seen |= idxs


def test_five_folds_equal_time_spans():
    df = _synth_4h(500)
    folds = split_folds(df, fold_count=5)
    assert len(folds) == 5
    spans = [(f['Date'].iloc[-1] - f['Date'].iloc[0]) for f in folds if len(f) > 0]
    # Spans should be within a tolerance equal to one 4h bar gap.
    bar_gap = pd.Timedelta(hours=4)
    for s in spans:
        for t in spans:
            assert abs((s - t).total_seconds()) <= bar_gap.total_seconds() + 1


def test_rejects_fold_count_below_two():
    df = _synth_4h(100)
    with pytest.raises(ConfigurationError) as exc:
        split_folds(df, fold_count=1)
    assert exc.value.code == 'invalid-fold-count'


def test_rejects_insufficient_data_window():
    df = _synth_4h(20)    # very small input
    with pytest.raises(ConfigurationError) as exc:
        split_folds(df, fold_count=3)
    assert exc.value.code == 'insufficient-data-window'
    assert exc.value.system_status['bars'] == 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_walk_forward_splits.py -v`
Expected: ImportError — `split_folds` not defined.

- [ ] **Step 3: Create the package marker**

Create `src/optimization/__init__.py` (empty file):

```python
"""NSGA-II multi-objective parameter optimisation package."""
```

- [ ] **Step 4: Implement `split_folds`**

Create `src/optimization/walk_forward.py`:

```python
"""Walk-forward fold splitter.

Splits a 4h DataFrame into N equal-calendar-time-span folds. Each fold is a
contiguous slice of the input (no overlap, no gaps within the input range).

Per the no-fallback rule, every argument is required and inputs that
can't support the requested fold count raise ConfigurationError with a
structured code + system_status payload.
"""
from __future__ import annotations

from typing import List

import pandas as pd

from src.exceptions import ConfigurationError


# Minimum bars per fold for the optimiser to have any chance of running.
# Operational floor; not a strategy decision. Documented; not user-tunable.
_MIN_BARS_PER_FOLD = 30


def split_folds(df: pd.DataFrame, fold_count: int) -> List[pd.DataFrame]:
    """Split `df` into `fold_count` equal-time-span folds.

    Args:
        df: DataFrame with a 'Date' column (pandas Timestamps), already
            sorted ascending.
        fold_count: Number of folds. Must be >= 2.

    Returns:
        A list of `fold_count` DataFrames. Each fold's bars are reset-indexed.
        Folds are time-disjoint; their union equals `df` (modulo row order).

    Raises:
        ConfigurationError(code='invalid-fold-count') when `fold_count` < 2.
        ConfigurationError(code='insufficient-data-window') when the input
            has fewer than `fold_count * _MIN_BARS_PER_FOLD` bars.
    """
    if fold_count < 2:
        raise ConfigurationError(
            f'fold_count must be >= 2, got {fold_count}.',
            code='invalid-fold-count',
            system_status={'fold_count': fold_count, 'min_required': 2},
        )
    min_required_bars = fold_count * _MIN_BARS_PER_FOLD
    if len(df) < min_required_bars:
        raise ConfigurationError(
            f'Insufficient data window: {len(df)} bars for {fold_count} '
            f'folds (need at least {min_required_bars}).',
            code='insufficient-data-window',
            system_status={
                'bars': len(df),
                'fold_count': fold_count,
                'min_bars_per_fold': _MIN_BARS_PER_FOLD,
                'min_required_total': min_required_bars,
            },
        )

    df = df.sort_values('Date').reset_index(drop=True)
    start_ts = df['Date'].iloc[0]
    end_ts   = df['Date'].iloc[-1]
    total_span = end_ts - start_ts
    fold_span = total_span / fold_count

    folds: List[pd.DataFrame] = []
    for i in range(fold_count):
        lo = start_ts + fold_span * i
        if i < fold_count - 1:
            hi = start_ts + fold_span * (i + 1)
            mask = (df['Date'] >= lo) & (df['Date'] < hi)
        else:
            # Last fold is inclusive of end_ts so the final bar is captured.
            mask = (df['Date'] >= lo) & (df['Date'] <= end_ts)
        folds.append(df[mask].reset_index(drop=True))
    return folds
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_walk_forward_splits.py -v`
Expected: 4 PASS.

- [ ] **Step 6: Commit**

```bash
git add src/optimization/__init__.py src/optimization/walk_forward.py tests/test_walk_forward_splits.py
git commit -m "feat(optimize): equal-time-span walk-forward fold splitter"
```

---

### Task C.2: State-isolation test (BoxLookup across folds)

**Files:**
- Test: `tests/test_walk_forward_state_isolation.py`

- [ ] **Step 1: Write the test**

Create `tests/test_walk_forward_state_isolation.py`:

```python
"""Locks the determinism claim that a single BoxLookup, when used across
multiple BoxStrategy.backtest() calls, yields identical per-fold trade lists
as a fresh BoxLookup instance would."""

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.optimization.walk_forward import split_folds
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy
from tests._fixtures import box_strategy_params


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _box_csv(path, cols, **levels):
    row = {c: levels.get(c) for c in cols}
    pd.DataFrame({'Date': ['2025-01-01'], **{c: [v] for c, v in row.items()}}).to_csv(path, index=False)


def _synth_4h(n_bars: int) -> pd.DataFrame:
    timestamps = pd.date_range(start='2025-01-01', periods=n_bars, freq='4h')
    base = 20000.0
    # Sawtooth pattern so the close crosses through the box repeatedly.
    closes = [base + 200 * (i % 4 - 1.5) for i in range(n_bars)]
    return pd.DataFrame({
        'Date':  timestamps,
        'Open':  [base] * n_bars,
        'High':  [c + 10 for c in closes],
        'Low':   [c - 10 for c in closes],
        'Close': closes,
        'Volume': [1000] * n_bars,
    })


def test_back_to_back_backtests_on_shared_lookup_match_fresh_instances(tmp_path):
    week_csv = tmp_path / 'w.csv'
    month_csv = tmp_path / 'm.csv'
    _box_csv(week_csv, _W_COLS, WRHU=20100.0, WRHD=20000.0)
    _box_csv(month_csv, _M_COLS)

    df = _synth_4h(120)
    folds = split_folds(df, fold_count=3)

    shared_lookup = BoxLookup(
        week_path=str(week_csv), month_path=str(month_csv),
        tick_threshold=0.75, weekly_window_days=7, monthly_window_days=30,
    )
    params = box_strategy_params()

    shared_results = []
    for f in folds:
        strat = BoxStrategy(params=params, box_lookup=shared_lookup)
        trades, _state = strat.backtest(f)
        shared_results.append(len(trades))

    fresh_results = []
    for f in folds:
        fresh_lookup = BoxLookup(
            week_path=str(week_csv), month_path=str(month_csv),
            tick_threshold=0.75, weekly_window_days=7, monthly_window_days=30,
        )
        strat = BoxStrategy(params=params, box_lookup=fresh_lookup)
        trades, _state = strat.backtest(f)
        fresh_results.append(len(trades))

    assert shared_results == fresh_results, (
        f'shared-lookup trades={shared_results} != fresh-lookup trades={fresh_results}; '
        f'reset_state() is not isolating folds.'
    )
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_walk_forward_state_isolation.py -v`
Expected: PASS (BoxStrategy.backtest already calls `reset_state()`; this is a regression lock).

- [ ] **Step 3: Commit**

```bash
git add tests/test_walk_forward_state_isolation.py
git commit -m "test(optimize): lock BoxLookup state isolation across folds"
```

---

## Phase D — Objective function

### Task D.1: Implement `evaluate()` + edge case tests

**Files:**
- Create: `src/optimization/objective.py`
- Test:   `tests/test_objective_edge_cases.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_objective_edge_cases.py`:

```python
"""Objective function edge-case tests.

Locked decisions:
- PF=None → optuna.TrialPruned (Q3.1)
- PF=0 → returns (0.0, max_dd) — let NSGA-II dominate normally
- total_trades < min_trades_per_fold → optuna.TrialPruned (Q3.2)
- ConfigurationError(code='malformed-box-geometry') → optuna.TrialPruned
- ConfigurationError(code='missing-candle-columns') → re-raises (study-fatal)
- ConfigurationError(any other code) → optuna.TrialPruned

See docs/superpowers/specs/2026-05-23-nsga2-optimization-design.md §4.3.
"""

import os
import sys
from dataclasses import asdict

import optuna
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.exceptions import ConfigurationError
from src.optimization.objective import evaluate
from src.strategy.box_lookup import BoxLookup
from tests._fixtures import box_strategy_params


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _box_csv(path, cols, **levels):
    row = {c: levels.get(c) for c in cols}
    pd.DataFrame({'Date': ['2025-01-01'], **{c: [v] for c, v in row.items()}}).to_csv(path, index=False)


def _lookup(tmp_path, **w_levels):
    _box_csv(tmp_path / 'w.csv', _W_COLS, **w_levels)
    _box_csv(tmp_path / 'm.csv', _M_COLS)
    return BoxLookup(
        week_path=str(tmp_path / 'w.csv'),
        month_path=str(tmp_path / 'm.csv'),
        tick_threshold=0.75,
        weekly_window_days=7,
        monthly_window_days=30,
    )


def _flat_4h(n_bars: int, close: float = 20050.0) -> pd.DataFrame:
    return pd.DataFrame({
        'Date':  pd.date_range(start='2025-01-01', periods=n_bars, freq='4h'),
        'Open':  [close] * n_bars,
        'High':  [close + 10] * n_bars,
        'Low':   [close - 10] * n_bars,
        'Close': [close] * n_bars,
        'Volume': [1000] * n_bars,
    })


def test_insufficient_trades_prunes(tmp_path):
    # Flat price never crosses the box → zero trades.
    lookup = _lookup(tmp_path, WRHU=21000.0, WRHD=20900.0)
    fold = _flat_4h(100)
    suggested = {'sl_soft_points': 200.0, 'sl_hard_points': 300.0, 'tp_target_points': 150.0}
    with pytest.raises(optuna.TrialPruned):
        evaluate(
            suggested_params=suggested,
            baseline_params=box_strategy_params(),
            folds=[fold, fold, fold],
            min_trades_per_fold=15,
            box_lookup=lookup,
        )


def test_malformed_box_geometry_prunes(tmp_path):
    # Box with upper <= lower triggers ConfigurationError('malformed-box-geometry')
    # on first signal evaluation → trial is pruned, study continues.
    lookup = _lookup(tmp_path, WRHU=100.0, WRHD=200.0)  # swapped
    fold = pd.DataFrame({
        'Date':  pd.date_range(start='2025-01-01', periods=50, freq='4h'),
        'Open':  [150.0] * 50,
        'High':  [160.0] * 50,
        'Low':   [140.0] * 50,
        'Close': [150.0] * 50,
        'Volume': [1000] * 50,
    })
    with pytest.raises(optuna.TrialPruned):
        evaluate(
            suggested_params={'sl_soft_points': 50.0, 'sl_hard_points': 100.0, 'tp_target_points': 50.0},
            baseline_params=box_strategy_params(),
            folds=[fold],
            min_trades_per_fold=1,
            box_lookup=lookup,
        )


def test_missing_candle_columns_re_raises(tmp_path):
    """Study-fatal: re-raise so the worker can abort the entire study."""
    lookup = _lookup(tmp_path, WRHU=21000.0, WRHD=20900.0)
    # DataFrame without Volume column.
    fold = pd.DataFrame({
        'Date':  pd.date_range(start='2025-01-01', periods=50, freq='4h'),
        'Open':  [20000.0] * 50,
        'High':  [20010.0] * 50,
        'Low':   [19990.0] * 50,
        'Close': [20000.0] * 50,
    })
    # NOTE: BoxStrategy.backtest itself doesn't validate Volume — that's
    # _candles_from_df's job. To reproduce the study-fatal path we manually
    # raise the corresponding ConfigurationError from a fake lookup. Use the
    # generic mechanism: pass a fold-shape that triggers a fatal error.
    # For this minimum-viable test we just assert that if our objective
    # encounters code='missing-candle-columns' it re-raises rather than prunes.
    # Simulate by monkey-patching evaluate's helper. Simpler: use a fold that
    # produces a non-malformed-box ConfigurationError via missing-data-file path.
    # Concretely test: if a config error has code='missing-candle-columns'
    # the evaluator re-raises.
    from src.optimization import objective as obj_mod

    class _FakeStrat:
        def __init__(self, *a, **kw):
            pass
        def backtest(self, df, on_progress=None):
            raise ConfigurationError(
                'simulated missing columns',
                code='missing-candle-columns',
                system_status={'missing_columns': ['Volume']},
            )

    obj_mod._build_strategy = lambda baseline, suggested, lookup: _FakeStrat()
    try:
        with pytest.raises(ConfigurationError) as exc:
            evaluate(
                suggested_params={'sl_soft_points': 50.0, 'sl_hard_points': 100.0, 'tp_target_points': 50.0},
                baseline_params=box_strategy_params(),
                folds=[fold],
                min_trades_per_fold=1,
                box_lookup=lookup,
            )
        assert exc.value.code == 'missing-candle-columns'
    finally:
        # Restore the real implementation for other tests.
        import importlib
        importlib.reload(obj_mod)


def test_returns_tuple_for_normal_path(tmp_path):
    """Sanity: a fold with enough trades and a finite PF returns a (pf, dd) tuple."""
    # Sawtooth that traverses the box repeatedly.
    n = 240
    closes = [20000.0 + 200.0 * (i % 4 - 1.5) for i in range(n)]
    fold = pd.DataFrame({
        'Date':  pd.date_range(start='2025-01-01', periods=n, freq='4h'),
        'Open':  [20000.0] * n,
        'High':  [c + 20 for c in closes],
        'Low':   [c - 20 for c in closes],
        'Close': closes,
        'Volume': [1000] * n,
    })
    lookup = _lookup(tmp_path, WRHU=20100.0, WRHD=19900.0)
    suggested = {'sl_soft_points': 200.0, 'sl_hard_points': 300.0, 'tp_target_points': 150.0}
    result = evaluate(
        suggested_params=suggested,
        baseline_params=box_strategy_params(),
        folds=[fold, fold],
        min_trades_per_fold=1,
        box_lookup=lookup,
    )
    assert isinstance(result, tuple) and len(result) == 2
    pf, dd = result
    assert isinstance(pf, float) and isinstance(dd, float)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_objective_edge_cases.py -v`
Expected: ImportError — `evaluate` not defined.

- [ ] **Step 3: Implement objective.evaluate()**

Create `src/optimization/objective.py`:

```python
"""Objective function for the NSGA-II optimiser.

`evaluate()` runs one trial across all walk-forward folds, aggregates the
metrics, and returns `(median_PF, max_MaxDD)` for Optuna to minimise/maximise.

Edge-case routing (locked by Q3.1 / Q3.2 + v3.1 update notes):

  PF=None                    → optuna.TrialPruned
  PF=0.0                     → return (0.0, max_dd) — NSGA-II dominates normally
  total_trades < min_floor   → optuna.TrialPruned
  malformed-box-geometry     → optuna.TrialPruned
  missing-candle-columns     → re-raise (study-fatal)
  missing-data-file          → re-raise (study-fatal)
  missing-parameter          → re-raise (study-fatal)
  any other ConfigurationError → optuna.TrialPruned

See docs/superpowers/specs/2026-05-23-nsga2-optimization-design.md §4.3.
"""
from __future__ import annotations

import statistics
from dataclasses import asdict
from typing import List, Tuple

import optuna
import pandas as pd

from src.exceptions import ConfigurationError
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategy, BoxStrategyParams


# Codes that abort the entire study instead of pruning a single trial.
_STUDY_FATAL_CODES = frozenset({
    'missing-candle-columns',
    'missing-data-file',
    'missing-parameter',
})


def _build_strategy(
    baseline: BoxStrategyParams,
    suggested: dict,
    lookup: BoxLookup,
) -> BoxStrategy:
    """Splice the searched params into the baseline; return a BoxStrategy."""
    params_dict = {**asdict(baseline), **suggested}
    return BoxStrategy(params=BoxStrategyParams(**params_dict), box_lookup=lookup)


def _compute_pf_and_dd(trades: List[dict]) -> Tuple[float, float]:
    """Compute (profit_factor, max_drawdown) for a single fold.

    profit_factor is None when there are zero losing trades. max_drawdown
    is always a non-positive float (worst peak-to-trough cumulative dollar PnL).
    """
    if not trades:
        return None, 0.0  # zero-trade fold — caller decides what to do

    gross_profit = sum(t['profit_dollars'] for t in trades if t['profit_dollars'] > 0)
    gross_loss = sum(-t['profit_dollars'] for t in trades if t['profit_dollars'] < 0)
    pf = (gross_profit / gross_loss) if gross_loss > 0 else None

    # Max drawdown via cumulative dollar PnL.
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        cum += t['profit_dollars']
        peak = max(peak, cum)
        max_dd = min(max_dd, cum - peak)
    return pf, max_dd


def evaluate(
    suggested_params: dict,
    baseline_params: BoxStrategyParams,
    folds: List[pd.DataFrame],
    min_trades_per_fold: int,
    box_lookup: BoxLookup,
) -> Tuple[float, float]:
    """Per-trial evaluation across `folds`. Returns (median_pf, max_dd).

    Raises:
        optuna.TrialPruned: when this candidate should be removed from the front.
        ConfigurationError: when a study-fatal error occurs (re-raises).
    """
    fold_pfs: List[float] = []
    fold_dds: List[float] = []

    for fold_idx, df_fold in enumerate(folds):
        try:
            strat = _build_strategy(baseline_params, suggested_params, box_lookup)
            trades, _state = strat.backtest(df_fold)
        except ConfigurationError as exc:
            if exc.code in _STUDY_FATAL_CODES:
                raise   # re-raise study-fatal errors
            raise optuna.TrialPruned(f'fold {fold_idx} prune: {exc.code}')

        if len(trades) < min_trades_per_fold:
            raise optuna.TrialPruned(
                f'fold {fold_idx} prune: {len(trades)} trades < min={min_trades_per_fold}'
            )

        pf, dd = _compute_pf_and_dd(trades)
        if pf is None:
            raise optuna.TrialPruned(f'fold {fold_idx} prune: profit_factor undefined (no losses)')

        fold_pfs.append(pf)
        fold_dds.append(dd)

    return statistics.median(fold_pfs), min(fold_dds)   # `min` because max_dd is non-positive
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_objective_edge_cases.py -v`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/optimization/objective.py tests/test_objective_edge_cases.py
git commit -m "feat(optimize): per-trial objective.evaluate with v3.1 error routing"
```

---

## Phase E — Persistence

### Task E.1: SQLite study persistence helpers

**Files:**
- Create: `src/optimization/persistence.py`
- Test:   `tests/test_optimize_persistence.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_optimize_persistence.py`:

```python
"""Optuna SQLite persistence + auto-resume behaviour."""

import os
import sys

import optuna
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.optimization.persistence import (
    create_study,
    list_studies,
    load_study,
    storage_url,
)


def test_create_and_load_study(tmp_path):
    db_path = tmp_path / 'studies.db'
    study = create_study(study_name='test-1', db_path=str(db_path))
    assert study.study_name == 'test-1'
    # Suggest + complete one trial so the study has state.
    trial = study.ask()
    x = trial.suggest_float('x', 0.0, 1.0)
    study.tell(trial, [x, -x])

    # Re-load by name.
    reloaded = load_study(study_name='test-1', db_path=str(db_path))
    assert len(reloaded.trials) == 1


def test_list_studies_includes_summary(tmp_path):
    db_path = tmp_path / 'studies.db'
    s1 = create_study(study_name='alpha', db_path=str(db_path))
    s2 = create_study(study_name='beta', db_path=str(db_path))
    # Each study runs one trial.
    for s in (s1, s2):
        t = s.ask()
        v = t.suggest_float('x', 0.0, 1.0)
        s.tell(t, [v, -v])

    studies = list_studies(db_path=str(db_path))
    names = {s['study_id'] for s in studies}
    assert names == {'alpha', 'beta'}


def test_storage_url_format(tmp_path):
    db_path = tmp_path / 'foo.db'
    url = storage_url(str(db_path))
    assert url.startswith('sqlite:///')
    assert url.endswith('foo.db')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_optimize_persistence.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement persistence.py**

Create `src/optimization/persistence.py`:

```python
"""SQLite persistence for Optuna studies.

Studies are stored in a SQLite DB shared across studies (single file).
Study names double as `study_id` — opaque to the caller but human-readable
when inspected with sqlite3.

The optimiser writes every trial to the DB so that server restarts can
auto-resume in-progress studies (see GET /api/optimize/studies).
"""
from __future__ import annotations

from typing import Dict, List

import optuna


def storage_url(db_path: str) -> str:
    """Translate a filesystem path into an Optuna-friendly RFC 1738 SQLite URL."""
    return f'sqlite:///{db_path}'


def create_study(study_name: str, db_path: str) -> optuna.Study:
    """Create a new persistent multi-objective study using NSGA-II.

    Both objectives are minimised internally; the caller is responsible for
    flipping signs (PF passed as positive value with directions=['maximize',
    'minimize']).
    """
    return optuna.create_study(
        study_name=study_name,
        storage=storage_url(db_path),
        sampler=optuna.samplers.NSGAIISampler(),
        directions=['maximize', 'minimize'],   # PF up, MaxDD up (less negative)
        load_if_exists=False,
    )


def load_study(study_name: str, db_path: str) -> optuna.Study:
    """Re-attach to an existing study by name."""
    return optuna.load_study(
        study_name=study_name,
        storage=storage_url(db_path),
    )


def list_studies(db_path: str) -> List[Dict]:
    """Return a summary record for every study in the DB.

    Each record: {study_id, trials_done, trials_total, started_at, is_complete,
                  pareto_size}. trials_total comes from the user attribute set
                  at study creation; pareto_size from `study.best_trials`.
    """
    summaries: List[Dict] = []
    for summary in optuna.get_all_study_summaries(storage=storage_url(db_path)):
        try:
            study = load_study(study_name=summary.study_name, db_path=db_path)
        except KeyError:
            continue
        trials_done = sum(
            1 for t in study.trials
            if t.state in (
                optuna.trial.TrialState.COMPLETE,
                optuna.trial.TrialState.PRUNED,
                optuna.trial.TrialState.FAIL,
            )
        )
        trials_total = study.user_attrs.get('trials_total', trials_done)
        started_at = study.user_attrs.get('started_at', '')
        try:
            pareto_size = len(study.best_trials)
        except (ValueError, RuntimeError):
            pareto_size = 0
        summaries.append({
            'study_id': summary.study_name,
            'trials_done': trials_done,
            'trials_total': int(trials_total),
            'started_at': started_at,
            'is_complete': trials_done >= int(trials_total),
            'pareto_size': pareto_size,
        })
    return summaries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_optimize_persistence.py -v`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add src/optimization/persistence.py tests/test_optimize_persistence.py
git commit -m "feat(optimize): SQLite persistence helpers for Optuna studies"
```

---

## Phase F — Study lifecycle

### Task F.1: `run_study()` orchestrator

**Files:**
- Create: `src/optimization/study.py`
- Test:   `tests/test_nsga2_study_runs.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_nsga2_study_runs.py`:

```python
"""End-to-end mini study run. Pop=4 × Gen=2 × Folds=2 = 16 trials max.

Verifies: study terminates, Pareto front is non-empty, every emitted
value is a float, study state is persisted to SQLite.
"""

import os
import sys

import optuna
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.optimization.persistence import list_studies
from src.optimization.study import run_study
from src.strategy.box_lookup import BoxLookup
from tests._fixtures import box_strategy_params


_W_COLS = ['WTHU', 'WTHD', 'WTH1', 'WTH2', 'WRHU', 'WRHD',
           'WIHU', 'WIHD', 'WILU', 'WILD', 'WRLU', 'WRLD',
           'WTLU', 'WTLD', 'WTL1', 'WTL2']
_M_COLS = ['MTHU', 'MTHD', 'MTH1', 'MTH2', 'MRHU', 'MRHD',
           'MIHU', 'MIHD', 'MILU', 'MILD', 'MRLU', 'MRLD',
           'MTLU', 'MTLD', 'MTL1', 'MTL2']


def _box_csv(path, cols, **levels):
    row = {c: levels.get(c) for c in cols}
    pd.DataFrame({'Date': ['2025-01-01'], **{c: [v] for c, v in row.items()}}).to_csv(path, index=False)


def _synth_4h(n_bars: int) -> pd.DataFrame:
    timestamps = pd.date_range(start='2025-01-01', periods=n_bars, freq='4h')
    closes = [20000.0 + 250.0 * (i % 4 - 1.5) for i in range(n_bars)]
    return pd.DataFrame({
        'Date':   timestamps,
        'Open':   [20000.0] * n_bars,
        'High':   [c + 50 for c in closes],
        'Low':    [c - 50 for c in closes],
        'Close':  closes,
        'Volume': [1000] * n_bars,
    })


def test_mini_study_completes_and_persists(tmp_path):
    week_csv = tmp_path / 'w.csv'
    month_csv = tmp_path / 'm.csv'
    _box_csv(week_csv, _W_COLS, WRHU=20100.0, WRHD=19900.0)
    _box_csv(month_csv, _M_COLS)

    lookup = BoxLookup(
        week_path=str(week_csv), month_path=str(month_csv),
        tick_threshold=0.75, weekly_window_days=7, monthly_window_days=30,
    )

    db_path = tmp_path / 'studies.db'
    df = _synth_4h(240)

    events = []
    def collect(event_type, payload):
        events.append((event_type, payload))

    summary = run_study(
        study_name='mini-test',
        baseline_params=box_strategy_params(),
        box_lookup=lookup,
        df=df,
        search_space={
            'sl_soft_points': (100.0, 250.0),
            'sl_hard_delta':  (50.0, 200.0),
            'tp_target_points': (75.0, 200.0),
        },
        population_size=4,
        generations=2,
        fold_count=2,
        min_trades_per_fold=1,
        db_path=str(db_path),
        on_event=collect,
        should_stop=lambda: False,
    )

    assert summary['total_trials'] >= 1
    assert 'pareto_front' in summary
    assert all(isinstance(v, float) for trial in summary['pareto_front'] for v in trial['values'])

    # Persistence: listed by `list_studies`.
    studies = list_studies(db_path=str(db_path))
    assert any(s['study_id'] == 'mini-test' for s in studies)

    # At least one progress + one trial + one complete event were emitted.
    types = {e[0] for e in events}
    assert 'study_started' in types
    assert 'trial' in types
    assert 'complete' in types
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_nsga2_study_runs.py -v`
Expected: ImportError — `run_study` not defined.

- [ ] **Step 3: Implement study.py**

Create `src/optimization/study.py`:

```python
"""Study lifecycle for the NSGA-II optimiser.

`run_study()` is the worker entry point. It:
  1. Creates (or resumes) an Optuna study with SQLite storage.
  2. Iterates trials up to `population_size × generations`.
  3. Calls `objective.evaluate()` per trial.
  4. Emits SSE-ready events via `on_event(event_type, payload)`.
  5. Polls `should_stop()` between trials for graceful cancellation.

The caller (FastAPI endpoint) wires `on_event` to a queue.Queue and runs
this function inside a daemon thread.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Tuple

import optuna
import pandas as pd

from src.exceptions import ConfigurationError
from src.optimization.objective import evaluate as evaluate_trial
from src.optimization.persistence import create_study, load_study
from src.optimization.walk_forward import split_folds
from src.strategy.box_lookup import BoxLookup
from src.strategy.box_strategy import BoxStrategyParams


SearchSpaceRange = Tuple[float, float]
EventEmitter = Callable[[str, Dict[str, Any]], None]
StopFlag = Callable[[], bool]


def _suggest(trial: optuna.Trial, search_space: Dict[str, SearchSpaceRange]) -> Dict[str, float]:
    """Suggest one trial's params. Encodes the sl_hard >= sl_soft + 50 constraint
    via reparameterisation (sl_hard = sl_soft + delta)."""
    sl_soft_lo, sl_soft_hi = search_space['sl_soft_points']
    delta_lo, delta_hi     = search_space['sl_hard_delta']
    tp_lo, tp_hi           = search_space['tp_target_points']

    sl_soft = trial.suggest_float('sl_soft_points', sl_soft_lo, sl_soft_hi)
    delta   = trial.suggest_float('sl_hard_delta',  delta_lo,  delta_hi)
    sl_hard = sl_soft + delta
    tp      = trial.suggest_float('tp_target_points', tp_lo, tp_hi)

    return {
        'sl_soft_points': sl_soft,
        'sl_hard_points': sl_hard,
        'tp_target_points': tp,
    }


def _pareto_payload(study: optuna.Study) -> List[Dict[str, Any]]:
    """Return the current Pareto front as a serialisable list."""
    try:
        best = study.best_trials
    except (ValueError, RuntimeError):
        return []
    return [
        {
            'trial_number': t.number,
            'params': dict(t.params),
            'values': [float(v) for v in t.values],
        }
        for t in best
    ]


def run_study(
    study_name: str,
    baseline_params: BoxStrategyParams,
    box_lookup: BoxLookup,
    df: pd.DataFrame,
    search_space: Dict[str, SearchSpaceRange],
    population_size: int,
    generations: int,
    fold_count: int,
    min_trades_per_fold: int,
    db_path: str,
    on_event: EventEmitter,
    should_stop: StopFlag,
    resume: bool = False,
    max_duration_s: int = 1800,
) -> Dict[str, Any]:
    """Run an NSGA-II study end-to-end.

    Returns a `complete` payload (same shape as the SSE `event: complete`).

    The caller passes a daemon-thread context: `on_event` is called from this
    function's thread; `should_stop` is read between trials.
    """
    # Set up study + folds.
    if resume:
        study = load_study(study_name=study_name, db_path=db_path)
    else:
        study = create_study(study_name=study_name, db_path=db_path)
        study.set_user_attr('trials_total', population_size * generations)
        study.set_user_attr('started_at', _now_iso())

    folds = split_folds(df, fold_count=fold_count)
    trials_total = int(study.user_attrs['trials_total'])
    trials_done_at_start = sum(
        1 for t in study.trials
        if t.state in (
            optuna.trial.TrialState.COMPLETE,
            optuna.trial.TrialState.PRUNED,
            optuna.trial.TrialState.FAIL,
        )
    )

    on_event('study_started', {
        'study_id': study_name,
        'trials_total': trials_total,
        'started_at': study.user_attrs['started_at'],
        'resumed': resume,
    })

    start_wall = time.perf_counter()
    pruned_count = 0
    fatal_error: Dict[str, Any] = None
    trials_remaining = trials_total - trials_done_at_start
    trials_in_this_run = 0

    for _ in range(trials_remaining):
        if should_stop():
            break
        if (time.perf_counter() - start_wall) > max_duration_s:
            on_event('warning', {
                'code': 'max-duration-exceeded',
                'message': f'study halted after {max_duration_s}s wall-clock limit',
                'system_status': {'elapsed_s': time.perf_counter() - start_wall},
            })
            break

        trial = study.ask()
        suggested = _suggest(trial, search_space)
        try:
            values = evaluate_trial(
                suggested_params=suggested,
                baseline_params=baseline_params,
                folds=folds,
                min_trades_per_fold=min_trades_per_fold,
                box_lookup=box_lookup,
            )
            study.tell(trial, list(values))
            on_event('trial', {
                'trial_number': trial.number,
                'params': dict(trial.params),
                'values': [float(v) for v in values],
                'state': 'complete',
                'pruned_reason': None,
            })
        except optuna.TrialPruned as exc:
            study.tell(trial, state=optuna.trial.TrialState.PRUNED)
            pruned_count += 1
            on_event('trial', {
                'trial_number': trial.number,
                'params': dict(trial.params),
                'values': [],
                'state': 'pruned',
                'pruned_reason': str(exc),
            })
        except ConfigurationError as exc:
            fatal_error = exc.to_payload()
            on_event('error', fatal_error)
            break
        trials_in_this_run += 1

        # Emit a progress event after every trial.
        on_event('progress', {
            'trials_done': trials_done_at_start + trials_in_this_run,
            'trials_total': trials_total,
            'percent': 100.0 * (trials_done_at_start + trials_in_this_run) / trials_total,
            'current_generation': (trials_done_at_start + trials_in_this_run) // population_size,
            'pareto_size': len(_pareto_payload(study)),
            'elapsed_ms': int((time.perf_counter() - start_wall) * 1000),
        })

        # Generation boundary event.
        if (trials_done_at_start + trials_in_this_run) % population_size == 0:
            on_event('generation', {
                'generation': (trials_done_at_start + trials_in_this_run) // population_size,
                'pareto_front': _pareto_payload(study),
            })

    pareto = _pareto_payload(study)
    pf_sorted = sorted(pareto, key=lambda p: -p['values'][0])  # PF desc
    dd_sorted = sorted(pareto, key=lambda p: p['values'][1])   # MaxDD asc (more negative first)

    complete_payload = {
        'study_id': study_name,
        'pareto_front': pareto,
        'top_5_by_pf': pf_sorted[:5],
        'top_5_by_min_dd': dd_sorted[:5],
        'total_trials': trials_done_at_start + trials_in_this_run,
        'pruned_count': pruned_count,
        'elapsed_ms': int((time.perf_counter() - start_wall) * 1000),
    }
    if fatal_error is None:
        on_event('complete', complete_payload)
    return complete_payload


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_nsga2_study_runs.py -v`
Expected: 1 PASS. (May take ~5-15 seconds.)

- [ ] **Step 5: Commit**

```bash
git add src/optimization/study.py tests/test_nsga2_study_runs.py
git commit -m "feat(optimize): NSGA-II study lifecycle with SSE event emission"
```

---

## Phase G — SSE bridge

### Task G.1: Optuna → queue.Queue → SSE adapter

**Files:**
- Create: `src/optimization/sse_bridge.py`

(No new test file — exercised end-to-end by `tests/test_api_optimize_sse.py` in Phase H.)

- [ ] **Step 1: Implement sse_bridge.py**

Create `src/optimization/sse_bridge.py`:

```python
"""Bridge between Optuna study events and an SSE event queue.

Reuses the producer/consumer pattern from `_box_event_stream` in src/api/app.py:
  1. A daemon worker thread runs `run_study()` and pushes events into a Queue.
  2. The HTTP request generator pops events and serialises them as SSE frames.
"""
from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Dict


_SENTINEL_DONE = object()


class StudyEventBridge:
    """Holds the queue + stop flag for one study run."""

    def __init__(self, maxsize: int = 512) -> None:
        self.q: queue.Queue = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()

    def on_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Producer-side callback. Pushes onto the queue."""
        self.q.put((event_type, payload))

    def should_stop(self) -> bool:
        return self._stop.is_set()

    def request_stop(self) -> None:
        self._stop.set()

    def signal_done(self) -> None:
        """Producer marks the queue as drained."""
        self.q.put(_SENTINEL_DONE)

    def drain(self):
        """Consumer-side generator. Yields (event_type, payload) until SENTINEL."""
        while True:
            item = self.q.get()
            if item is _SENTINEL_DONE:
                return
            yield item


def make_worker(
    target: Callable[[], None],
    bridge: StudyEventBridge,
) -> threading.Thread:
    """Wrap `target` so it always signals done, even on exception."""
    def run():
        try:
            target()
        finally:
            bridge.signal_done()
    return threading.Thread(target=run, daemon=True)
```

- [ ] **Step 2: Commit**

```bash
git add src/optimization/sse_bridge.py
git commit -m "feat(optimize): producer/consumer SSE bridge for study events"
```

---

## Phase H — API endpoints

### Task H.1: POST /api/optimize/box (start a study)

**Files:**
- Modify: `src/api/app.py`
- Test:   `tests/test_api_optimize_sse.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_api_optimize_sse.py`:

```python
"""End-to-end SSE tests for /api/optimize/box and friends."""

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient

from src.api.app import app
from tests._fixtures import box_params_dict


client = TestClient(app)


def _write_synth_4h_csv(path, n_rows=240):
    timestamps = pd.date_range(start='2025-01-01 00:00:00', periods=n_rows, freq='4h')
    closes = [20000.0 + 250.0 * (i % 4 - 1.5) for i in range(n_rows)]
    df = pd.DataFrame({
        'datetime': timestamps.strftime('%Y-%m-%d %H:%M:%S'),
        'open':   [20000.0] * n_rows,
        'high':   [c + 50 for c in closes],
        'low':    [c - 50 for c in closes],
        'close':  closes,
        'volume': [1000] * n_rows,
    })
    df.to_csv(path, index=False)


def _write_box_csv(path, kind):
    prefix = 'W' if kind == 'week' else 'M'
    cols = [f'{prefix}{suffix}' for suffix in
            ['THU', 'THD', 'TH1', 'TH2', 'RHU', 'RHD',
             'IHU', 'IHD', 'ILU', 'ILD', 'RLU', 'RLD',
             'TLU', 'TLD', 'TL1', 'TL2']]
    row = {c: None for c in cols}
    row[f'{prefix}RHU'] = 20100.0
    row[f'{prefix}RHD'] = 19900.0
    pd.DataFrame({'Date': ['2025-01-01'], **{c: [v] for c, v in row.items()}}).to_csv(path, index=False)


def _parse_sse_events(text):
    events = []
    current_event = None
    current_data = []
    for line in text.splitlines():
        if line.startswith('event:'):
            current_event = line[len('event:'):].strip()
        elif line.startswith('data:'):
            current_data.append(line[len('data:'):].strip())
        elif line == '':
            if current_event and current_data:
                events.append((current_event, json.loads('\n'.join(current_data))))
            current_event = None
            current_data = []
    if current_event and current_data:
        events.append((current_event, json.loads('\n'.join(current_data))))
    return events


def _mini_body(tmp_path):
    csv = tmp_path / 'synth_4h.csv'
    week_csv = tmp_path / 'week.csv'
    month_csv = tmp_path / 'month.csv'
    _write_synth_4h_csv(csv)
    _write_box_csv(week_csv, 'week')
    _write_box_csv(month_csv, 'month')
    return {
        'baseline_params': box_params_dict(),
        'search_space': {
            'sl_soft_points': [100.0, 250.0],
            'sl_hard_delta':  [50.0, 200.0],
            'tp_target_points': [75.0, 200.0],
        },
        'budget': {'population_size': 4, 'generations': 2},
        'folds':  {'count': 2, 'min_trades_per_fold': 1},
        'data_path': str(csv),
        'week_data_path': str(week_csv),
        'month_data_path': str(month_csv),
        'max_duration_s': 120,
    }


def test_optimize_box_streams_study_started_progress_trial_complete(tmp_path, monkeypatch):
    monkeypatch.setenv('OPTUNA_DB_PATH', str(tmp_path / 'studies.db'))
    resp = client.post('/api/optimize/box', json=_mini_body(tmp_path))
    assert resp.status_code == 200
    assert resp.headers['content-type'].startswith('text/event-stream')

    events = _parse_sse_events(resp.text)
    types = [e[0] for e in events]
    assert 'study_started' in types
    assert any(t == 'trial' for t in types)
    assert any(t == 'progress' for t in types)
    assert 'complete' in types

    complete = next(e[1] for e in events if e[0] == 'complete')
    for key in ('study_id', 'pareto_front', 'top_5_by_pf', 'top_5_by_min_dd',
                'total_trials', 'pruned_count', 'elapsed_ms'):
        assert key in complete


def test_optimize_box_missing_data_path_returns_error_event(tmp_path, monkeypatch):
    monkeypatch.setenv('OPTUNA_DB_PATH', str(tmp_path / 'studies.db'))
    body = _mini_body(tmp_path)
    body['data_path'] = '/tmp/opencode/does-not-exist.csv'
    resp = client.post('/api/optimize/box', json=body)
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    errors = [e for e in events if e[0] == 'error']
    assert len(errors) >= 1
    assert errors[0][1]['code'] == 'missing-data-file'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_optimize_sse.py::test_optimize_box_streams_study_started_progress_trial_complete -v`
Expected: 404 — endpoint not yet defined.

- [ ] **Step 3: Add the endpoint to src/api/app.py**

In `src/api/app.py`, locate the import block near the top and add:

```python
from src.api.schemas import (
    # ... existing schema imports ...
    OptimizeRequest,
    StudiesListResponse,
    StudySummary,
)
from src.optimization.persistence import list_studies as _list_studies_impl, load_study
from src.optimization.sse_bridge import StudyEventBridge, make_worker
from src.optimization.study import run_study
```

Add near the end of `src/api/app.py`, after the `/api/backtest/box` endpoint block, this new section:

```python
# ---- /api/optimize/box (NSGA-II multi-objective optimisation, SSE-streamed) ----

import uuid


def _optuna_db_path() -> str:
    """Where the SQLite store lives. Env-overridable for tests."""
    return os.environ.get('OPTUNA_DB_PATH', os.path.join(os.getcwd(), 'optuna_studies.db'))


# Active studies (study_id → bridge) for stop/abrupt control.
_ACTIVE_STUDIES: Dict[str, StudyEventBridge] = {}


def _opt_event_stream(req: OptimizeRequest, study_name: str, resume: bool) -> Iterator[str]:
    """SSE stream that drives an Optuna study and yields formatted SSE frames."""

    # Load + validate the 4h CSV and the box CSVs upfront so the user gets a
    # fast error rather than a daemon-thread traceback.
    if not os.path.exists(req.data_path):
        yield _sse_format('error', MissingDataFileError(
            req.data_path, role='4h-candles'
        ).to_payload())
        return

    try:
        df = load_data(req.data_path)
    except ConfigurationError as exc:
        yield _sse_format('error', exc.to_payload())
        return
    except Exception as exc:  # noqa: BLE001
        yield _sse_format('error', {
            'code': 'data-load-failed',
            'message': f'failed to load {req.data_path}: {exc}',
            'system_status': {'data_path': req.data_path, 'exception_type': type(exc).__name__},
        })
        return

    try:
        box_lookup = BoxLookup(
            week_path=req.week_data_path,
            month_path=req.month_data_path,
            tick_threshold=req.baseline_params.box_tick_threshold,
            weekly_window_days=req.baseline_params.weekly_window_days,
            monthly_window_days=req.baseline_params.monthly_window_days,
        )
    except ConfigurationError as exc:
        yield _sse_format('error', exc.to_payload())
        return
    except Exception as exc:  # noqa: BLE001
        yield _sse_format('error', {
            'code': 'box-data-load-failed',
            'message': f'failed to load box data: {exc}',
            'system_status': {
                'week_data_path': req.week_data_path,
                'month_data_path': req.month_data_path,
                'exception_type': type(exc).__name__,
            },
        })
        return

    bridge = StudyEventBridge(maxsize=512)
    _ACTIVE_STUDIES[study_name] = bridge

    baseline = BoxStrategyParams(
        **req.baseline_params.model_dump(),
        week_data_path=req.week_data_path,
        month_data_path=req.month_data_path,
    )

    def target():
        run_study(
            study_name=study_name,
            baseline_params=baseline,
            box_lookup=box_lookup,
            df=df,
            search_space={
                'sl_soft_points': tuple(req.search_space.sl_soft_points),
                'sl_hard_delta':  tuple(req.search_space.sl_hard_delta),
                'tp_target_points': tuple(req.search_space.tp_target_points),
            },
            population_size=req.budget.population_size,
            generations=req.budget.generations,
            fold_count=req.folds.count,
            min_trades_per_fold=req.folds.min_trades_per_fold,
            db_path=_optuna_db_path(),
            on_event=bridge.on_event,
            should_stop=bridge.should_stop,
            resume=resume,
            max_duration_s=req.max_duration_s,
        )

    worker = make_worker(target, bridge)
    worker.start()
    try:
        for event_type, payload in bridge.drain():
            yield _sse_format(event_type, payload)
    finally:
        _ACTIVE_STUDIES.pop(study_name, None)


@app.post("/api/optimize/box")
def optimize_box(req: OptimizeRequest):
    """Kick off a fresh NSGA-II study. Returns an SSE stream."""
    study_name = str(uuid.uuid4())
    return StreamingResponse(
        _opt_event_stream(req, study_name=study_name, resume=False),
        media_type='text/event-stream',
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_optimize_sse.py::test_optimize_box_streams_study_started_progress_trial_complete -v`
Expected: 1 PASS. (May take 10-30 seconds.)

Then run the second test:

Run: `pytest tests/test_api_optimize_sse.py::test_optimize_box_missing_data_path_returns_error_event -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/api/app.py tests/test_api_optimize_sse.py
git commit -m "feat(optimize): POST /api/optimize/box SSE endpoint"
```

---

### Task H.2: POST /api/optimize/<id>/stop (graceful + abrupt)

**Files:**
- Modify: `src/api/app.py`
- Test: append to `tests/test_api_optimize_sse.py`

- [ ] **Step 1: Add the test**

Append to `tests/test_api_optimize_sse.py`:

```python
def test_stop_endpoint_acknowledges_unknown_study():
    """Stop on a non-existent study returns 404 (no silent fallback to OK)."""
    resp = client.post('/api/optimize/nonexistent/stop')
    assert resp.status_code == 404
    body = resp.json()
    assert body['detail']['code'] == 'unknown-study'
```

- [ ] **Step 2: Add the endpoint**

In `src/api/app.py`, append after the `/api/optimize/box` endpoint:

```python
@app.post("/api/optimize/{study_id}/stop")
def optimize_stop(study_id: str, abrupt: bool = False):
    """Stop a running study.

    Default is graceful — the worker finishes the current trial then emits
    `complete`. With `?abrupt=true`, request_stop is set immediately AND the
    queue is drained-to-sentinel so the stream closes faster (the trial in
    flight may still complete since we can't kill an in-flight call cleanly).
    """
    bridge = _ACTIVE_STUDIES.get(study_id)
    if bridge is None:
        raise HTTPException(
            status_code=404,
            detail={
                'code': 'unknown-study',
                'message': f"No active study named '{study_id}'.",
                'system_status': {'active_study_ids': list(_ACTIVE_STUDIES.keys())},
            },
        )
    bridge.request_stop()
    if abrupt:
        bridge.signal_done()
    return {'study_id': study_id, 'stopped': True, 'abrupt': abrupt}
```

- [ ] **Step 3: Run the test**

Run: `pytest tests/test_api_optimize_sse.py::test_stop_endpoint_acknowledges_unknown_study -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/api/app.py tests/test_api_optimize_sse.py
git commit -m "feat(optimize): POST /api/optimize/<id>/stop with abrupt override"
```

---

### Task H.3: POST /api/optimize/<id>/resume

**Files:**
- Modify: `src/api/app.py`
- Test: append to `tests/test_api_optimize_sse.py`

- [ ] **Step 1: Add the test**

Append to `tests/test_api_optimize_sse.py`:

```python
def test_resume_endpoint_streams_study_started_with_resumed_true(tmp_path, monkeypatch):
    """Resume on a study that already exists in the DB should re-attach and
    emit `study_started` with resumed=True."""
    db_path = str(tmp_path / 'studies.db')
    monkeypatch.setenv('OPTUNA_DB_PATH', db_path)

    # Manually create a study in the DB by running a quick study first.
    body = _mini_body(tmp_path)
    body['budget']['population_size'] = 2
    body['budget']['generations'] = 1
    resp = client.post('/api/optimize/box', json=body)
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    study_started = next(e for e in events if e[0] == 'study_started')
    study_id = study_started[1]['study_id']

    # Now resume that study.
    resp = client.post(
        f'/api/optimize/{study_id}/resume',
        json={
            'baseline_params': body['baseline_params'],
            'search_space':   body['search_space'],
            'budget':         body['budget'],
            'folds':          body['folds'],
            'data_path':      body['data_path'],
            'week_data_path': body['week_data_path'],
            'month_data_path': body['month_data_path'],
            'max_duration_s': body['max_duration_s'],
        },
    )
    assert resp.status_code == 200
    events = _parse_sse_events(resp.text)
    started = next(e[1] for e in events if e[0] == 'study_started')
    assert started['resumed'] is True
```

- [ ] **Step 2: Add the endpoint**

In `src/api/app.py`, append:

```python
@app.post("/api/optimize/{study_id}/resume")
def optimize_resume(study_id: str, req: OptimizeRequest):
    """Resume an in-progress study by name. Body matches POST /api/optimize/box
    so the worker can re-attach with identical configuration."""
    return StreamingResponse(
        _opt_event_stream(req, study_name=study_id, resume=True),
        media_type='text/event-stream',
    )
```

- [ ] **Step 3: Run the test**

Run: `pytest tests/test_api_optimize_sse.py::test_resume_endpoint_streams_study_started_with_resumed_true -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/api/app.py tests/test_api_optimize_sse.py
git commit -m "feat(optimize): POST /api/optimize/<id>/resume (auto-resume on restart)"
```

---

### Task H.4: GET /api/optimize/studies (list resumable studies)

**Files:**
- Modify: `src/api/app.py`
- Test: append to `tests/test_api_optimize_sse.py`

- [ ] **Step 1: Add the test**

Append to `tests/test_api_optimize_sse.py`:

```python
def test_studies_list_includes_recently_started(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'studies.db')
    monkeypatch.setenv('OPTUNA_DB_PATH', db_path)

    body = _mini_body(tmp_path)
    body['budget']['population_size'] = 2
    body['budget']['generations'] = 1
    client.post('/api/optimize/box', json=body)

    resp = client.get('/api/optimize/studies')
    assert resp.status_code == 200
    payload = resp.json()
    assert 'studies' in payload
    assert len(payload['studies']) >= 1
    s = payload['studies'][0]
    for k in ('study_id', 'trials_done', 'trials_total', 'started_at', 'is_complete', 'pareto_size'):
        assert k in s
```

- [ ] **Step 2: Add the endpoint**

In `src/api/app.py`, append:

```python
@app.get("/api/optimize/studies", response_model=StudiesListResponse)
def optimize_list_studies():
    """Return every persisted study summary. Used by OptimizePanel on mount
    to offer 'Continue?' cards for incomplete studies."""
    raw = _list_studies_impl(db_path=_optuna_db_path())
    return StudiesListResponse(studies=[StudySummary(**s) for s in raw])
```

- [ ] **Step 3: Run the test**

Run: `pytest tests/test_api_optimize_sse.py::test_studies_list_includes_recently_started -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/api/app.py tests/test_api_optimize_sse.py
git commit -m "feat(optimize): GET /api/optimize/studies (resumable studies list)"
```

---

## Phase I — Frontend dependencies + types

### Task I.1: Add Chart.js + vue-chartjs

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install**

Run from `frontend/`:

```bash
npm install chart.js@^4.4.0 vue-chartjs@^5.3.0
```

Expected: `package.json` and `package-lock.json` updated.

- [ ] **Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "build(frontend): add chart.js + vue-chartjs for Pareto scatter"
```

---

### Task I.2: Add TypeScript types for the optimiser

**Files:**
- Modify: `frontend/src/types.ts` (append at end)

- [ ] **Step 1: Append types to frontend/src/types.ts**

```typescript

// ---- NSGA-II optimisation ----

export interface OptimizeSearchSpace {
  sl_soft_points: [number, number];
  sl_hard_delta:  [number, number];
  tp_target_points: [number, number];
}

export interface OptimizeBudget {
  population_size: number;
  generations: number;
}

export interface OptimizeFoldsConfig {
  count: number;
  min_trades_per_fold: number;
}

export interface OptimizeRequest {
  baseline_params: BoxParams;
  search_space: OptimizeSearchSpace;
  budget: OptimizeBudget;
  folds: OptimizeFoldsConfig;
  data_path: string;
  week_data_path: string;
  month_data_path: string;
  max_duration_s: number;
}

export interface TrialResult {
  trial_number: number;
  params: Record<string, number>;
  values: [number, number];   // [PF_median, MaxDD_max]
  state: 'complete' | 'pruned';
  pruned_reason: string | null;
}

export interface ParetoPoint {
  trial_number: number;
  params: Record<string, number>;
  values: [number, number];
}

export interface StudySummary {
  study_id: string;
  trials_done: number;
  trials_total: number;
  started_at: string;
  is_complete: boolean;
  pareto_size: number;
}

export interface OptimizeStudyStarted {
  study_id: string;
  trials_total: number;
  started_at: string;
  resumed: boolean;
}

export interface OptimizeProgress {
  trials_done: number;
  trials_total: number;
  percent: number;
  current_generation: number;
  pareto_size: number;
  elapsed_ms: number;
}

export interface OptimizeGeneration {
  generation: number;
  pareto_front: ParetoPoint[];
}

export interface OptimizeCompletePayload {
  study_id: string;
  pareto_front: ParetoPoint[];
  top_5_by_pf: ParetoPoint[];
  top_5_by_min_dd: ParetoPoint[];
  total_trials: number;
  pruned_count: number;
  elapsed_ms: number;
}

export type OptimizeStreamEvent =
  | { type: 'study_started'; data: OptimizeStudyStarted }
  | { type: 'progress';      data: OptimizeProgress }
  | { type: 'trial';         data: TrialResult }
  | { type: 'generation';    data: OptimizeGeneration }
  | { type: 'complete';      data: OptimizeCompletePayload }
  | { type: 'warning';       data: { code: string; message: string; system_status: any } }
  | { type: 'error';         data: { code: string; message: string; system_status: any } };
```

- [ ] **Step 2: Type-check**

Run from `frontend/`: `npm run build`
Expected: clean build.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat(optimize-frontend): TypeScript types mirroring optimiser schemas"
```

---

## Phase J — Frontend SSE service

### Task J.1: optimize_sse.ts with reusable parser

**Files:**
- Create: `frontend/src/services/optimize_sse.ts`
- Create: `frontend/tests/optimize_sse_parser.test.ts`

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/optimize_sse_parser.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { parseOptimizeSseFrame } from '../src/services/optimize_sse';

describe('parseOptimizeSseFrame', () => {
  it('parses a study_started frame', () => {
    const raw = 'event: study_started\ndata: {"study_id":"abc","trials_total":600,"started_at":"2026-01-01","resumed":false}';
    const ev = parseOptimizeSseFrame(raw);
    expect(ev?.type).toBe('study_started');
    if (ev?.type === 'study_started') {
      expect(ev.data.study_id).toBe('abc');
      expect(ev.data.resumed).toBe(false);
    }
  });

  it('parses a trial frame', () => {
    const raw = 'event: trial\ndata: {"trial_number":42,"params":{"sl_soft_points":150},"values":[1.5,-2000],"state":"complete","pruned_reason":null}';
    const ev = parseOptimizeSseFrame(raw);
    expect(ev?.type).toBe('trial');
    if (ev?.type === 'trial') {
      expect(ev.data.values).toEqual([1.5, -2000]);
    }
  });

  it('parses an error frame using shared schema', () => {
    const raw = 'event: error\ndata: {"code":"missing-data-file","message":"x","system_status":{}}';
    const ev = parseOptimizeSseFrame(raw);
    expect(ev?.type).toBe('error');
  });

  it('returns null for unknown event types', () => {
    const raw = 'event: unknown\ndata: {}';
    const ev = parseOptimizeSseFrame(raw);
    expect(ev).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from `frontend/`: `npx vitest run tests/optimize_sse_parser.test.ts`
Expected: cannot find module.

- [ ] **Step 3: Implement optimize_sse.ts**

Create `frontend/src/services/optimize_sse.ts`:

```typescript
/**
 * SSE consumer for /api/optimize/box and /resume.
 *
 * Mirrors the fetch+ReadableStream pattern used by services/sse.ts.
 */

import type { OptimizeRequest, OptimizeStreamEvent } from '../types';


export function streamOptimization(
  body: OptimizeRequest,
  signal?: AbortSignal,
): AsyncGenerator<OptimizeStreamEvent, void, unknown> {
  return _streamSse('/api/optimize/box', body, signal);
}


export function streamOptimizationResume(
  studyId: string,
  body: OptimizeRequest,
  signal?: AbortSignal,
): AsyncGenerator<OptimizeStreamEvent, void, unknown> {
  return _streamSse(`/api/optimize/${encodeURIComponent(studyId)}/resume`, body, signal);
}


async function* _streamSse(
  endpoint: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<OptimizeStreamEvent, void, unknown> {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Optimize SSE failed: ${response.status} ${response.statusText}`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const parsed = parseOptimizeSseFrame(frame);
      if (parsed) yield parsed;
      boundary = buffer.indexOf('\n\n');
    }
  }
  const tail = parseOptimizeSseFrame(buffer);
  if (tail) yield tail;
}


export function parseOptimizeSseFrame(raw: string): OptimizeStreamEvent | null {
  if (!raw.trim()) return null;
  let eventType: string | null = null;
  const dataLines: string[] = [];
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:'))   eventType = line.slice('event:'.length).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice('data:'.length).trim());
  }
  if (!eventType || dataLines.length === 0) return null;
  try {
    const data = JSON.parse(dataLines.join('\n'));
    switch (eventType) {
      case 'study_started': return { type: 'study_started', data };
      case 'progress':      return { type: 'progress',      data };
      case 'trial':         return { type: 'trial',         data };
      case 'generation':    return { type: 'generation',    data };
      case 'complete':      return { type: 'complete',      data };
      case 'warning':       return { type: 'warning',       data };
      case 'error':         return { type: 'error',         data };
      default:              return null;
    }
  } catch {
    return null;
  }
}


export async function stopStudy(studyId: string, abrupt: boolean): Promise<void> {
  const url = `/api/optimize/${encodeURIComponent(studyId)}/stop${abrupt ? '?abrupt=true' : ''}`;
  const resp = await fetch(url, { method: 'POST' });
  if (!resp.ok) throw new Error(`stop failed: ${resp.status}`);
}


export async function listStudies(): Promise<import('../types').StudySummary[]> {
  const resp = await fetch('/api/optimize/studies');
  if (!resp.ok) throw new Error(`studies list failed: ${resp.status}`);
  const body = await resp.json();
  return body.studies;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run from `frontend/`: `npx vitest run tests/optimize_sse_parser.test.ts`
Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/optimize_sse.ts frontend/tests/optimize_sse_parser.test.ts
git commit -m "feat(optimize-frontend): SSE consumer + frame parser"
```

---

## Phase K — Pinia store

### Task K.1: optimize.ts store

**Files:**
- Create: `frontend/src/stores/optimize.ts`

- [ ] **Step 1: Implement the store**

Create `frontend/src/stores/optimize.ts`:

```typescript
/**
 * Optimisation state: tracks the current study, the live Pareto front, and
 * the selected point. Consumed by OptimizePanel.vue.
 */

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

import type {
  OptimizeCompletePayload,
  OptimizeRequest,
  OptimizeStreamEvent,
  ParetoPoint,
  StudySummary,
  TrialResult,
} from '../types';
import {
  listStudies as listStudiesService,
  parseOptimizeSseFrame,
  stopStudy as stopStudyService,
  streamOptimization,
  streamOptimizationResume,
} from '../services/optimize_sse';


export const useOptimizeStore = defineStore('optimize', () => {
  // ---- Reactive state ----
  const studyId       = ref<string | null>(null);
  const trialsDone    = ref(0);
  const trialsTotal   = ref(0);
  const elapsedMs     = ref(0);
  const allTrials     = ref<TrialResult[]>([]);
  const paretoFront   = ref<ParetoPoint[]>([]);
  const completePayload = ref<OptimizeCompletePayload | null>(null);
  const isRunning     = ref(false);
  const selectedTrial = ref<TrialResult | ParetoPoint | null>(null);
  const lastError     = ref<string | null>(null);
  const resumableStudies = ref<StudySummary[]>([]);

  let abortController: AbortController | null = null;

  // ---- Computed ----
  const percent = computed(() =>
    trialsTotal.value > 0 ? (trialsDone.value / trialsTotal.value) * 100 : 0,
  );

  // ---- Actions ----
  function reset() {
    studyId.value = null;
    trialsDone.value = 0;
    trialsTotal.value = 0;
    elapsedMs.value = 0;
    allTrials.value = [];
    paretoFront.value = [];
    completePayload.value = null;
    isRunning.value = false;
    selectedTrial.value = null;
    lastError.value = null;
  }

  async function runOptimization(req: OptimizeRequest) {
    reset();
    isRunning.value = true;
    abortController = new AbortController();
    try {
      for await (const ev of streamOptimization(req, abortController.signal)) {
        applyEvent(ev);
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') lastError.value = String(e?.message || e);
    } finally {
      isRunning.value = false;
      abortController = null;
    }
  }

  async function resumeOptimization(studyIdToResume: string, req: OptimizeRequest) {
    reset();
    isRunning.value = true;
    abortController = new AbortController();
    try {
      for await (const ev of streamOptimizationResume(studyIdToResume, req, abortController.signal)) {
        applyEvent(ev);
      }
    } catch (e: any) {
      if (e?.name !== 'AbortError') lastError.value = String(e?.message || e);
    } finally {
      isRunning.value = false;
      abortController = null;
    }
  }

  async function stopStudy(abrupt: boolean) {
    if (!studyId.value) return;
    await stopStudyService(studyId.value, abrupt);
    if (abrupt && abortController) abortController.abort();
  }

  async function refreshResumableStudies() {
    resumableStudies.value = (await listStudiesService()).filter(s => !s.is_complete);
  }

  function selectTrial(t: TrialResult | ParetoPoint) {
    selectedTrial.value = t;
  }

  function applyEvent(ev: OptimizeStreamEvent) {
    switch (ev.type) {
      case 'study_started':
        studyId.value = ev.data.study_id;
        trialsTotal.value = ev.data.trials_total;
        break;
      case 'progress':
        trialsDone.value = ev.data.trials_done;
        trialsTotal.value = ev.data.trials_total;
        elapsedMs.value = ev.data.elapsed_ms;
        break;
      case 'trial':
        allTrials.value.push(ev.data);
        break;
      case 'generation':
        paretoFront.value = ev.data.pareto_front;
        break;
      case 'complete':
        completePayload.value = ev.data;
        paretoFront.value = ev.data.pareto_front;
        break;
      case 'warning':
        // Non-fatal — keep going.
        break;
      case 'error':
        lastError.value = `${ev.data.code}: ${ev.data.message}`;
        break;
    }
  }

  return {
    // state
    studyId,
    trialsDone,
    trialsTotal,
    elapsedMs,
    allTrials,
    paretoFront,
    completePayload,
    isRunning,
    selectedTrial,
    lastError,
    resumableStudies,
    // computed
    percent,
    // actions
    reset,
    runOptimization,
    resumeOptimization,
    stopStudy,
    refreshResumableStudies,
    selectTrial,
    applyEvent,
    parseOptimizeSseFrame,
  };
});
```

- [ ] **Step 2: Build check**

Run from `frontend/`: `npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/optimize.ts
git commit -m "feat(optimize-frontend): Pinia store for live study state"
```

---

## Phase L — Vue components

### Task L.1: ParetoScatter.vue (Chart.js wrapper)

**Files:**
- Create: `frontend/src/components/ParetoScatter.vue`

- [ ] **Step 1: Implement the component**

Create `frontend/src/components/ParetoScatter.vue`:

```vue
<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Scatter } from 'vue-chartjs';
import {
  Chart as ChartJS,
  PointElement,
  LineElement,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js';

import type { ParetoPoint, TrialResult } from '../types';

ChartJS.register(PointElement, LineElement, LinearScale, Tooltip, Legend);

const props = defineProps<{
  trials: TrialResult[];
  paretoFront: ParetoPoint[];
  selectedTrialNumber: number | null;
}>();

const emit = defineEmits<{
  (e: 'select', trial: TrialResult | ParetoPoint): void;
}>();

const chartData = computed(() => {
  // Dominated points (all non-pareto, non-pruned trials).
  const paretoNumbers = new Set(props.paretoFront.map(p => p.trial_number));
  const dominated = props.trials.filter(
    t => t.state === 'complete' && !paretoNumbers.has(t.trial_number),
  );

  // Sort the Pareto front by MaxDD (x) so the connecting line is monotonic.
  const sortedFront = [...props.paretoFront].sort((a, b) => a.values[1] - b.values[1]);

  return {
    datasets: [
      {
        label: 'Dominated',
        data: dominated.map(t => ({ x: t.values[1], y: t.values[0], trialRef: t })),
        backgroundColor: 'rgba(120,120,120,0.5)',
        pointRadius: 3,
      },
      {
        label: 'Pareto front',
        data: sortedFront.map(p => ({ x: p.values[1], y: p.values[0], trialRef: p })),
        backgroundColor: 'rgba(76,175,80,0.95)',
        pointRadius: 6,
        showLine: true,
        borderColor: 'rgba(76,175,80,0.6)',
        borderDash: [4, 4],
      },
    ],
  };
});

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: { title: { display: true, text: 'Max Drawdown ($)' } },
    y: { title: { display: true, text: 'Profit Factor (median across folds)' } },
  },
  plugins: {
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          const t = ctx.raw.trialRef;
          return `#${t.trial_number}  PF=${t.values[0].toFixed(2)}  DD=$${t.values[1].toFixed(0)}`;
        },
      },
    },
  },
  onClick: (_e: any, elements: any[]) => {
    if (elements.length === 0) return;
    const el = elements[0];
    const dataset = chartData.value.datasets[el.datasetIndex];
    const point = (dataset.data as any[])[el.index];
    if (point?.trialRef) emit('select', point.trialRef);
  },
}));
</script>

<template>
  <div class="pareto-scatter">
    <Scatter :data="chartData" :options="chartOptions" />
  </div>
</template>

<style scoped>
.pareto-scatter {
  width: 100%;
  height: clamp(300px, 50vh, 600px);
}
</style>
```

- [ ] **Step 2: Build check**

Run from `frontend/`: `npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ParetoScatter.vue
git commit -m "feat(optimize-frontend): ParetoScatter.vue (Chart.js wrapper)"
```

---

### Task L.2: StudyContinueCard.vue

**Files:**
- Create: `frontend/src/components/StudyContinueCard.vue`

- [ ] **Step 1: Implement**

Create `frontend/src/components/StudyContinueCard.vue`:

```vue
<script setup lang="ts">
import type { StudySummary } from '../types';

const props = defineProps<{ study: StudySummary }>();
const emit = defineEmits<{ (e: 'continue', study: StudySummary): void }>();
</script>

<template>
  <div class="rounded border border-tv-border bg-tv-panel p-3 flex items-center justify-between gap-4">
    <div class="text-sm">
      <div class="font-mono text-tv-text">#{{ props.study.study_id.slice(0, 8) }}</div>
      <div class="text-tv-muted">
        {{ props.study.trials_done }}/{{ props.study.trials_total }} done · pareto={{ props.study.pareto_size }}
        · started {{ props.study.started_at }}
      </div>
    </div>
    <button class="px-3 py-1 rounded bg-tv-accent text-white" @click="emit('continue', props.study)">
      Continue
    </button>
  </div>
</template>
```

- [ ] **Step 2: Build check**

Run from `frontend/`: `npm run build`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/StudyContinueCard.vue
git commit -m "feat(optimize-frontend): StudyContinueCard.vue for auto-resume"
```

---

### Task L.3: OptimizePanel.vue (main panel) + presets

**Files:**
- Create: `frontend/src/components/OptimizePanel.vue`
- Test:   `frontend/tests/optimize_presets.test.ts`

- [ ] **Step 1: Write the failing preset-algorithm test**

Create `frontend/tests/optimize_presets.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import {
  pickAggressive,
  pickBalanced,
  pickConservative,
} from '../src/components/OptimizePanel.presets';
import type { ParetoPoint } from '../src/types';


function _point(num: number, pf: number, dd: number): ParetoPoint {
  return { trial_number: num, params: {}, values: [pf, dd] };
}

const FRONT: ParetoPoint[] = [
  _point(1, 1.2, -500),    // conservative
  _point(2, 1.6, -1500),   // balanced-ish
  _point(3, 2.5, -3500),   // aggressive
];

describe('preset pickers', () => {
  it('conservative picks the smallest |MaxDD|', () => {
    const p = pickConservative(FRONT);
    expect(p.trial_number).toBe(1);
  });

  it('aggressive picks the highest PF', () => {
    const p = pickAggressive(FRONT);
    expect(p.trial_number).toBe(3);
  });

  it('balanced picks the knee point (min L2 to utopia after normalisation)', () => {
    const p = pickBalanced(FRONT);
    expect([2, 1, 3]).toContain(p.trial_number);   // typically #2
    expect(p.trial_number).toBe(2);
  });

  it('handles single-point front', () => {
    const single = [_point(99, 1.0, -100)];
    expect(pickConservative(single).trial_number).toBe(99);
    expect(pickAggressive(single).trial_number).toBe(99);
    expect(pickBalanced(single).trial_number).toBe(99);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from `frontend/`: `npx vitest run tests/optimize_presets.test.ts`
Expected: import fails.

- [ ] **Step 3: Implement preset algorithms**

Create `frontend/src/components/OptimizePanel.presets.ts`:

```typescript
import type { ParetoPoint } from '../types';


export function pickConservative(front: ParetoPoint[]): ParetoPoint {
  // Smallest |MaxDD| (least-negative dd).
  return [...front].sort((a, b) => b.values[1] - a.values[1])[0];
}


export function pickAggressive(front: ParetoPoint[]): ParetoPoint {
  // Highest PF.
  return [...front].sort((a, b) => b.values[0] - a.values[0])[0];
}


export function pickBalanced(front: ParetoPoint[]): ParetoPoint {
  // Normalise both axes to [0,1] then minimise L2 distance to utopia corner
  // (max PF, min |DD|). Utopia is (1, 1) in the normalised frame.
  if (front.length === 1) return front[0];
  const pfs = front.map(p => p.values[0]);
  const dds = front.map(p => p.values[1]);   // negative numbers
  const pfMin = Math.min(...pfs);
  const pfMax = Math.max(...pfs);
  const ddMin = Math.min(...dds);
  const ddMax = Math.max(...dds);

  const normPf = (v: number) => (pfMax === pfMin ? 1 : (v - pfMin) / (pfMax - pfMin));
  const normDd = (v: number) => (ddMax === ddMin ? 1 : (v - ddMin) / (ddMax - ddMin));

  let best = front[0];
  let bestDist = Infinity;
  for (const p of front) {
    const x = normPf(p.values[0]);
    const y = normDd(p.values[1]);
    const dist = Math.hypot(1 - x, 1 - y);
    if (dist < bestDist) {
      best = p;
      bestDist = dist;
    }
  }
  return best;
}
```

- [ ] **Step 4: Verify presets test passes**

Run from `frontend/`: `npx vitest run tests/optimize_presets.test.ts`
Expected: 4 PASS.

- [ ] **Step 5: Implement OptimizePanel.vue**

Create `frontend/src/components/OptimizePanel.vue`:

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import ParetoScatter from './ParetoScatter.vue';
import StudyContinueCard from './StudyContinueCard.vue';
import { pickAggressive, pickBalanced, pickConservative } from './OptimizePanel.presets';

import { useOptimizeStore } from '../stores/optimize';
import { useSettingsStore } from '../stores/settings';
import { useBacktestStore } from '../stores/backtest';
import type { OptimizeRequest, ParetoPoint, StudySummary } from '../types';


const emit = defineEmits<{ (e: 'navigateBack'): void }>();

const optimize = useOptimizeStore();
const settings = useSettingsStore();
const backtest = useBacktestStore();

// Form bindings — each has explicit initial values; the form always sends a
// complete payload (frontend pre-population, not engine fallback).
const slSoftMin = ref(50);
const slSoftMax = ref(300);
const slHardDeltaMin = ref(50);
const slHardDeltaMax = ref(600);
const tpMin = ref(75);
const tpMax = ref(250);
const minTradesPerFold = ref(15);
const foldCount = ref(3);
const maxDurationS = ref(1800);

type BudgetPreset = 'light' | 'standard' | 'heavy';
const budgetPreset = ref<BudgetPreset>('light');
const BUDGETS: Record<BudgetPreset, { population_size: number; generations: number }> = {
  light:    { population_size: 40, generations: 15 },
  standard: { population_size: 60, generations: 30 },
  heavy:    { population_size: 90, generations: 60 },
};


function buildRequest(): OptimizeRequest {
  return {
    baseline_params: settings.params,
    search_space: {
      sl_soft_points: [slSoftMin.value, slSoftMax.value],
      sl_hard_delta:  [slHardDeltaMin.value, slHardDeltaMax.value],
      tp_target_points: [tpMin.value, tpMax.value],
    },
    budget: BUDGETS[budgetPreset.value],
    folds: { count: foldCount.value, min_trades_per_fold: minTradesPerFold.value },
    data_path: settings.dataPath,
    week_data_path: settings.weekDataPath,
    month_data_path: settings.monthDataPath,
    max_duration_s: maxDurationS.value,
  };
}


onMounted(() => {
  optimize.refreshResumableStudies();
});


async function onRun() {
  await optimize.runOptimization(buildRequest());
}


async function onStop(abrupt: boolean) {
  await optimize.stopStudy(abrupt);
}


async function onContinue(study: StudySummary) {
  await optimize.resumeOptimization(study.study_id, buildRequest());
}


function applyPreset(picker: (front: ParetoPoint[]) => ParetoPoint) {
  if (optimize.paretoFront.length === 0) return;
  const point = picker(optimize.paretoFront);
  optimize.selectTrial(point);
}


async function onApplyAndBacktest() {
  if (!optimize.selectedTrial) return;
  const p = optimize.selectedTrial.params;
  settings.updateParam('sl_soft_points', p.sl_soft_points);
  settings.updateParam('sl_hard_points', p.sl_hard_points);
  settings.updateParam('tp_target_points', p.tp_target_points);
  await backtest.run();
  emit('navigateBack');
}


const isResumable = computed(() => optimize.resumableStudies.length > 0);
</script>


<template>
  <div class="optimize-panel p-4 space-y-4">
    <!-- Search ranges + budget -->
    <section class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-xs text-tv-muted">sl_soft_points</label>
        <input type="number" v-model.number="slSoftMin" class="w-20 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" /> –
        <input type="number" v-model.number="slSoftMax" class="w-20 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" />
      </div>
      <div>
        <label class="block text-xs text-tv-muted">sl_hard_delta (= sl_hard - sl_soft)</label>
        <input type="number" v-model.number="slHardDeltaMin" class="w-20 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" /> –
        <input type="number" v-model.number="slHardDeltaMax" class="w-20 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" />
      </div>
      <div>
        <label class="block text-xs text-tv-muted">tp_target_points</label>
        <input type="number" v-model.number="tpMin" class="w-20 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" /> –
        <input type="number" v-model.number="tpMax" class="w-20 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" />
      </div>
      <div>
        <label class="block text-xs text-tv-muted">min trades / fold</label>
        <input type="number" v-model.number="minTradesPerFold" class="w-20 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" />
      </div>
      <div>
        <label class="block text-xs text-tv-muted">fold count</label>
        <input type="number" v-model.number="foldCount" class="w-20 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" />
      </div>
      <div>
        <label class="block text-xs text-tv-muted">max duration (sec)</label>
        <input type="number" v-model.number="maxDurationS" class="w-24 px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm" />
      </div>
      <div>
        <label class="block text-xs text-tv-muted">budget</label>
        <select v-model="budgetPreset" class="px-2 py-1 bg-tv-panel border border-tv-border rounded text-sm">
          <option value="light">Light (600 trials)</option>
          <option value="standard">Standard (1,800)</option>
          <option value="heavy">Heavy (5,400)</option>
        </select>
      </div>
      <div class="flex items-end gap-2">
        <button class="px-3 py-1 rounded bg-tv-accent text-white" :disabled="optimize.isRunning" @click="onRun">
          Run optimisation
        </button>
        <button class="px-3 py-1 rounded bg-tv-border text-tv-text" :disabled="!optimize.isRunning" @click="onStop(false)">
          Stop (graceful)
        </button>
        <button class="px-3 py-1 rounded bg-tv-border text-tv-text" :disabled="!optimize.isRunning" @click="onStop(true)">
          Abrupt
        </button>
      </div>
    </section>

    <!-- Continue? cards -->
    <section v-if="isResumable" class="space-y-2">
      <h3 class="text-sm text-tv-muted">Continue an incomplete study</h3>
      <StudyContinueCard
        v-for="s in optimize.resumableStudies"
        :key="s.study_id"
        :study="s"
        @continue="onContinue"
      />
    </section>

    <!-- Live progress -->
    <section v-if="optimize.studyId" class="text-sm text-tv-muted">
      Study {{ optimize.studyId.slice(0, 8) }} —
      {{ optimize.trialsDone }}/{{ optimize.trialsTotal }}
      ({{ optimize.percent.toFixed(1) }}%) ·
      pareto={{ optimize.paretoFront.length }}
    </section>

    <!-- Scatter + detail panel -->
    <section class="grid grid-cols-3 gap-4">
      <div class="col-span-2">
        <ParetoScatter
          :trials="optimize.allTrials"
          :paretoFront="optimize.paretoFront"
          :selectedTrialNumber="optimize.selectedTrial?.trial_number ?? null"
          @select="optimize.selectTrial"
        />
      </div>
      <div class="space-y-2">
        <h3 class="text-sm text-tv-muted">Selected trial</h3>
        <div v-if="!optimize.selectedTrial" class="text-tv-muted">(click a point or pick a preset)</div>
        <div v-else class="font-mono text-sm space-y-1">
          <div>#{{ optimize.selectedTrial.trial_number }}</div>
          <div>PF: {{ optimize.selectedTrial.values[0].toFixed(2) }}</div>
          <div>MaxDD: ${{ optimize.selectedTrial.values[1].toFixed(0) }}</div>
          <div class="border-t border-tv-border pt-2">
            <div>sl_soft: {{ optimize.selectedTrial.params.sl_soft_points?.toFixed(0) }}</div>
            <div>sl_hard: {{ optimize.selectedTrial.params.sl_hard_points?.toFixed(0) }}</div>
            <div>tp_target: {{ optimize.selectedTrial.params.tp_target_points?.toFixed(0) }}</div>
          </div>
        </div>
        <button class="px-3 py-1 rounded bg-tv-accent text-white w-full" :disabled="!optimize.selectedTrial" @click="onApplyAndBacktest">
          Apply + Backtest
        </button>
      </div>
    </section>

    <!-- Presets -->
    <section class="flex gap-2 text-sm">
      <button class="px-3 py-1 rounded bg-tv-border" :disabled="optimize.paretoFront.length === 0" @click="applyPreset(pickConservative)">
        Conservative
      </button>
      <button class="px-3 py-1 rounded bg-tv-border" :disabled="optimize.paretoFront.length === 0" @click="applyPreset(pickBalanced)">
        Balanced
      </button>
      <button class="px-3 py-1 rounded bg-tv-border" :disabled="optimize.paretoFront.length === 0" @click="applyPreset(pickAggressive)">
        Aggressive
      </button>
    </section>

    <div v-if="optimize.lastError" class="text-tv-error text-sm font-mono">
      {{ optimize.lastError }}
    </div>
  </div>
</template>
```

- [ ] **Step 6: Build + verify**

Run from `frontend/`:
```bash
npm run build
npx vitest run tests/optimize_presets.test.ts tests/optimize_sse_parser.test.ts
```
Expected: clean build + 8 tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/OptimizePanel.vue frontend/src/components/OptimizePanel.presets.ts frontend/tests/optimize_presets.test.ts
git commit -m "feat(optimize-frontend): OptimizePanel.vue with presets + Apply+Backtest"
```

---

## Phase M — Router + integration test

### Task M.1: Add /optimize route

**Files:**
- Modify: `frontend/src/App.vue` (or wherever the top-level routing lives)

Note: check the existing App.vue first to see how routes are handled. The trading dashboard may use a simple panel-switch rather than vue-router. If so, follow that pattern.

- [ ] **Step 1: Inspect current routing pattern**

Run: `grep -n "route\|router\|RouterView" frontend/src/App.vue frontend/src/main.ts | head -20`

If no router exists, the simplest pattern is a top-level `view` ref in `App.vue` switched between `'backtest'` and `'optimize'`.

- [ ] **Step 2: Add view toggle to App.vue**

In `frontend/src/App.vue`, add (inside the `<script setup>`):

```typescript
import { ref } from 'vue';
import OptimizePanel from './components/OptimizePanel.vue';

const view = ref<'backtest' | 'optimize'>('backtest');
```

Add a navigation tab to the existing header markup (look for the title/header area):

```vue
<nav class="flex gap-2 text-sm">
  <button :class="view === 'backtest' ? 'underline' : ''" @click="view = 'backtest'">Backtest</button>
  <button :class="view === 'optimize' ? 'underline' : ''" @click="view = 'optimize'">Optimise</button>
</nav>
```

Wrap the existing dashboard markup in a `v-if="view === 'backtest'"` guard, and add the optimise view:

```vue
<OptimizePanel v-else-if="view === 'optimize'" @navigateBack="view = 'backtest'" />
```

- [ ] **Step 3: Build + smoke test**

Run from `frontend/`: `npm run build && npm test`
Expected: clean build + all tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat(optimize-frontend): add /optimize view toggle to App.vue"
```

---

### Task M.2: OptimizePanel component smoke test

**Files:**
- Create: `frontend/tests/optimize_panel.test.ts`

- [ ] **Step 1: Implement the smoke test**

Create `frontend/tests/optimize_panel.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';

import OptimizePanel from '../src/components/OptimizePanel.vue';
import { useOptimizeStore } from '../src/stores/optimize';


describe('OptimizePanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ studies: [] }),
    } as any);
  });

  it('renders with no resumable studies', async () => {
    const wrapper = mount(OptimizePanel);
    expect(wrapper.text()).toContain('Run optimisation');
    expect(wrapper.text()).not.toContain('Continue an incomplete study');
  });

  it('shows progress when a study runs', async () => {
    const wrapper = mount(OptimizePanel);
    const store = useOptimizeStore();
    store.applyEvent({
      type: 'study_started',
      data: { study_id: 'abc12345-0000-0000-0000-000000000000', trials_total: 600, started_at: '', resumed: false },
    });
    store.applyEvent({
      type: 'progress',
      data: { trials_done: 100, trials_total: 600, percent: 16.7, current_generation: 2, pareto_size: 5, elapsed_ms: 30000 },
    });
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Study abc12345');
    expect(wrapper.text()).toContain('100/600');
  });

  it('disables Apply+Backtest when no trial is selected', () => {
    const wrapper = mount(OptimizePanel);
    const btn = wrapper.findAll('button').find(b => b.text().includes('Apply + Backtest'));
    expect(btn?.attributes('disabled')).toBeDefined();
  });
});
```

- [ ] **Step 2: Run the test**

Run from `frontend/`: `npx vitest run tests/optimize_panel.test.ts`
Expected: 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/tests/optimize_panel.test.ts
git commit -m "test(optimize-frontend): OptimizePanel smoke tests"
```

---

## Phase N — Final verification

### Task N.1: Full sweep

- [ ] **Step 1: Backend tests**

Run: `pytest tests/ -v`
Expected: all backend tests pass (existing 55 + new ~22 = ~77).

- [ ] **Step 2: Frontend tests**

Run from `frontend/`: `npm test`
Expected: existing 77 + new ~7 = ~84 tests pass.

- [ ] **Step 3: Frontend build**

Run from `frontend/`: `npm run build`
Expected: clean.

- [ ] **Step 4: Manual smoke test (optional but recommended)**

Run: `uvicorn src.api.app:app --reload --port 8000` in one terminal and `cd frontend && npm run dev` in another. Open the dashboard, click **Optimise**, run a Light study against `NQ_4h.csv` + the box CSVs, verify trials scatter on the chart, pick a preset, click Apply+Backtest, observe the dashboard's metrics card refresh.

- [ ] **Step 5: Final commit (if any cleanup was needed)**

```bash
git status
# If clean: nothing more to commit. Otherwise:
git add <files>
git commit -m "chore(optimize): final cleanup pass"
```

---

## Spec coverage check

| Spec section | Implementing tasks |
|---|---|
| §1 Goal | All phases |
| §2 Decision log Q1–Q6.2 | Encoded in Phases B (schemas), D (objective routing), F (study), L (preset algos) |
| §3 Architecture | Phases C–H create `src/optimization/`; Phase H wires endpoints |
| §4 Data flow | Task F.1 implements the per-trial flow; Tasks H.1/H.3 implement the request body |
| §5 SSE event protocol | Tasks F.1 (emission) + H.1 (consumer test) + J.1 (frontend parser) |
| §6 Frontend UX | Phase L (components) + Task M.1 (route) |
| §7 Failure modes | Task D.1 (objective error routing) + Task H.1 (upfront file checks) |
| §8 Test plan | Six backend test files + two frontend test files across all phases |
| §9 File-level deliverables | All matching files in "File structure" section above |

No spec section is uncovered. The plan is complete and self-contained.
