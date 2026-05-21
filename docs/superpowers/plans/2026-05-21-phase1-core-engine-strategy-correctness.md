# Phase 1 Core Engine + Strategy Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regenerate correct test-dashboard artifacts and run frozen v1.0 old-strategy evaluations on requested windows with conservative in-candle SL/TP handling and standardized `output/` artifacts.

**Architecture:** Add a focused `src/main/backtest_runner.py` orchestration module that centralizes date-window execution, in-candle resolution, and artifact payload creation. Keep frozen v1.0 strategy behavior unchanged while refactoring `ultimate_dashboard.py` to call the runner. Add tests first for collision handling and date-range coverage metadata, then implement minimally to pass.

**Tech Stack:** Python 3, pandas, numpy, scikit-learn, pytest

---

## File Structure and Responsibilities

- **Create:** `src/main/backtest_runner.py` — single orchestration unit for v1.0 runs, period runs, coverage metadata, and output payload generation.
- **Create:** `src/main/__init__.py` — package marker and explicit exports.
- **Modify:** `ultimate_dashboard.py` — delegate execution to runner, switch output writes to `output/dashboard/*`.
- **Modify:** `tests/test_ultimate_dashboard.py` — add TDD coverage for in-candle SL-first and output-path expectations.
- **Modify:** `tests/test_backtest.py` — add date-window + coverage metadata tests.
- **Modify:** `README.md` — quick-start/output path updates for Phase 1 behavior.

### Task 1: Add Failing Tests for In-Candle Collision and Coverage Metadata

**Files:**
- Modify: `tests/test_ultimate_dashboard.py`
- Modify: `tests/test_backtest.py`

- [ ] **Step 1: Write failing test for conservative SL-first in same candle**

```python
def test_resolve_exit_price_when_sl_and_tp_hit_same_candle_prefers_sl():
    from src.main.backtest_runner import resolve_exit_price_and_reason

    entry_price = 100.0
    direction = 1
    stop_loss = 0.6
    take_profit = 2.4

    # Both touched: low <= SL level and high >= TP level
    high = 103.0
    low = 99.0
    close = 101.0

    exit_price, exit_reason = resolve_exit_price_and_reason(
        direction=direction,
        entry_price=entry_price,
        high=high,
        low=low,
        close=close,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )

    assert exit_reason == "SL"
    assert exit_price == 99.4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ultimate_dashboard.py::test_resolve_exit_price_when_sl_and_tp_hit_same_candle_prefers_sl -v`
Expected: FAIL with import/function-not-found error.

- [ ] **Step 3: Write failing test for coverage metadata on partial windows**

```python
def test_run_period_backtest_reports_requested_vs_actual_coverage():
    import pandas as pd
    from src.main.backtest_runner import compute_coverage_metadata

    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2025-09-05", "2025-09-06"]),
            "Open": [1, 1],
            "High": [1, 1],
            "Low": [1, 1],
            "Close": [1, 1],
            "Volume": [1, 1],
        }
    )

    coverage = compute_coverage_metadata(
        df=df,
        requested_start="2025-09-01",
        requested_end="2025-12-31",
    )

    assert coverage["requested_start"] == "2025-09-01"
    assert coverage["requested_end"] == "2025-12-31"
    assert coverage["actual_start"] == "2025-09-05"
    assert coverage["actual_end"] == "2025-09-06"
    assert coverage["has_gap"] is True
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_backtest.py::test_run_period_backtest_reports_requested_vs_actual_coverage -v`
Expected: FAIL with import/function-not-found error.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ultimate_dashboard.py tests/test_backtest.py
git commit -m "test: add failing tests for candle-collision and coverage metadata"
```

### Task 2: Implement `src/main/backtest_runner.py` Minimal Core

**Files:**
- Create: `src/main/backtest_runner.py`
- Create: `src/main/__init__.py`
- Test: `tests/test_ultimate_dashboard.py`
- Test: `tests/test_backtest.py`

- [ ] **Step 1: Implement exit resolver and coverage helpers**

```python
# src/main/backtest_runner.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple
import pandas as pd


def resolve_exit_price_and_reason(
    direction: int,
    entry_price: float,
    high: float,
    low: float,
    close: float,
    stop_loss: float,
    take_profit: float,
) -> Tuple[float, str | None]:
    sl_price = entry_price * (1 - stop_loss / 100) if direction == 1 else entry_price * (1 + stop_loss / 100)
    tp_price = entry_price * (1 + take_profit / 100) if direction == 1 else entry_price * (1 - take_profit / 100)

    sl_hit = low <= sl_price if direction == 1 else high >= sl_price
    tp_hit = high >= tp_price if direction == 1 else low <= tp_price

    if sl_hit and tp_hit:
        return sl_price, "SL"  # conservative policy
    if sl_hit:
        return sl_price, "SL"
    if tp_hit:
        return tp_price, "TP"
    return close, None


def compute_coverage_metadata(df: pd.DataFrame, requested_start: str, requested_end: str) -> Dict:
    if df.empty:
        return {
            "requested_start": requested_start,
            "requested_end": requested_end,
            "actual_start": None,
            "actual_end": None,
            "rows": 0,
            "has_gap": True,
        }

    dates = pd.to_datetime(df["Date"])
    actual_start = dates.min().strftime("%Y-%m-%d")
    actual_end = dates.max().strftime("%Y-%m-%d")

    return {
        "requested_start": requested_start,
        "requested_end": requested_end,
        "actual_start": actual_start,
        "actual_end": actual_end,
        "rows": int(len(df)),
        "has_gap": actual_start != requested_start or actual_end != requested_end,
    }
```

- [ ] **Step 2: Add package export**

```python
# src/main/__init__.py
from .backtest_runner import resolve_exit_price_and_reason, compute_coverage_metadata

__all__ = ["resolve_exit_price_and_reason", "compute_coverage_metadata"]
```

- [ ] **Step 3: Run targeted tests**

Run:  
`pytest tests/test_ultimate_dashboard.py::test_resolve_exit_price_when_sl_and_tp_hit_same_candle_prefers_sl -v`  
`pytest tests/test_backtest.py::test_run_period_backtest_reports_requested_vs_actual_coverage -v`

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/main/backtest_runner.py src/main/__init__.py
git commit -m "feat(backtest): add candle-collision and coverage helpers"
```

### Task 3: Move 15m Backtest Execution to Candle-Aware Resolver

**Files:**
- Modify: `ultimate_dashboard.py` (existing `run_backtest_15min`)
- Modify: `tests/test_ultimate_dashboard.py`

- [ ] **Step 1: Write failing integration-style test for same-candle collision in 15m runner**

```python
def test_run_backtest_15min_uses_conservative_sl_when_tp_and_sl_hit_same_candle():
    import numpy as np
    import pandas as pd
    from ultimate_dashboard import run_backtest_15min

    signals = np.array([1, 0])
    closes = np.array([100.0, 101.0])
    df = pd.DataFrame(
        {
            "High": [100.0, 103.0],
            "Low": [100.0, 99.0],
            "Close": closes,
        }
    )

    trades, _ = run_backtest_15min(
        signals=signals,
        closes=closes,
        df=df,
        initial_capital=10000.0,
        stop_loss=0.6,
        take_profit=2.4,
        fee_per_trade=10.0,
        point_value=2.0,
    )

    assert len(trades) == 1
    assert trades[0]["exit_reason"] == "SL"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ultimate_dashboard.py::test_run_backtest_15min_uses_conservative_sl_when_tp_and_sl_hit_same_candle -v`
Expected: FAIL because current logic exits by close-based threshold check only.

- [ ] **Step 3: Update `run_backtest_15min` to call resolver when High/Low is available**

```python
from src.main.backtest_runner import resolve_exit_price_and_reason

# inside run_backtest_15min loop
high_i = float(df.iloc[i]["High"]) if df is not None and "High" in df.columns else float(closes[i])
low_i = float(df.iloc[i]["Low"]) if df is not None and "Low" in df.columns else float(closes[i])
close_i = float(closes[i])

exit_price, exit_reason = resolve_exit_price_and_reason(
    direction=in_pos,
    entry_price=entry_price,
    high=high_i,
    low=low_i,
    close=close_i,
    stop_loss=stop_loss,
    take_profit=take_profit,
)

if exit_reason is not None:
    pnl_pct = (exit_price - entry_price) / entry_price * 100 if in_pos == 1 else (entry_price - exit_price) / entry_price * 100
    points_moved = (exit_price - entry_price) if in_pos == 1 else (entry_price - exit_price)
    pnl_dollars = (points_moved * point_value) - fee_per_trade
```

- [ ] **Step 4: Run relevant tests**

Run: `pytest tests/test_ultimate_dashboard.py -v`
Expected: PASS including existing regression tests.

- [ ] **Step 5: Commit**

```bash
git add ultimate_dashboard.py tests/test_ultimate_dashboard.py
git commit -m "fix(backtest): add conservative in-candle sl/tp resolution"
```

### Task 4: Add Period Backtest Execution for Requested Windows

**Files:**
- Modify: `src/main/backtest_runner.py`
- Modify: `tests/test_backtest.py`

- [ ] **Step 1: Write failing test for period-run output shape**

```python
def test_run_period_backtest_returns_metrics_trades_and_coverage():
    import pandas as pd
    from src.main.backtest_runner import run_period_backtest

    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2025-09-05", "2025-09-06", "2025-09-07"]),
            "Time": ["10:00:00", "10:15:00", "10:30:00"],
            "Open": [100, 100, 100],
            "High": [101, 101, 101],
            "Low": [99, 99, 99],
            "Close": [100, 100.5, 100.2],
            "Volume": [10, 10, 10],
        }
    )

    result = run_period_backtest(df=df, requested_start="2025-09-01", requested_end="2025-12-31")
    assert "metrics" in result
    assert "trades" in result
    assert "coverage" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backtest.py::test_run_period_backtest_returns_metrics_trades_and_coverage -v`
Expected: FAIL with missing function.

- [ ] **Step 3: Implement `run_period_backtest` in runner**

```python
def run_period_backtest(df: pd.DataFrame, requested_start: str, requested_end: str) -> Dict:
    from ultimate_dashboard import (
        resample_15min, prepare_data, train_ml, apply_ml_filter,
        apply_rsi_entry_filters, run_backtest_15min
    )
    from src.backtest.metrics import calculate_metrics

    date_series = pd.to_datetime(df["Date"])
    mask = (date_series >= pd.Timestamp(requested_start)) & (date_series <= pd.Timestamp(requested_end))
    subset = df.loc[mask].copy()

    coverage = compute_coverage_metadata(subset, requested_start, requested_end)
    if subset.empty:
        return {"metrics": calculate_metrics([], 10000), "trades": [], "coverage": coverage}

    subset_15 = resample_15min(subset.reset_index(drop=True))
    prep = prepare_data(subset_15)
    ml_data = train_ml(prep, rsi_thresh=25)
    signals = apply_ml_filter(prep, ml_data)
    signals = apply_rsi_entry_filters(signals, prep["rsi_5"].values, oversold=25, overbought=75)

    trades, final_capital = run_backtest_15min(
        signals=signals,
        closes=subset_15["Close"].values,
        df=prep,
        initial_capital=10000,
        stop_loss=0.6,
        take_profit=2.4,
        fee_per_trade=10.0,
        point_value=2.0,
    )
    metrics = calculate_metrics(trades, 10000)
    return {"metrics": metrics, "trades": trades, "coverage": coverage, "final_capital": final_capital}
```

- [ ] **Step 4: Run updated backtest tests**

Run: `pytest tests/test_backtest.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/main/backtest_runner.py tests/test_backtest.py
git commit -m "feat(backtest): add period runs with coverage metadata"
```

### Task 5: Route Test Dashboard Generation Through Runner and `output/`

**Files:**
- Modify: `ultimate_dashboard.py`
- Modify: `tests/test_ultimate_dashboard.py`

- [ ] **Step 1: Add failing test for output path contract**

```python
def test_create_ultimate_dashboard_writes_output_dashboard_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import os
    os.makedirs("output/dashboard", exist_ok=True)
    # Call minimal write path helper extracted from create_ultimate_dashboard
    from ultimate_dashboard import save_dashboard_payload

    payload = {"metrics": {"total_trades": 0}, "trades": [], "logs": [], "insights": {"key_findings": [], "recommendations": []}, "chart_data": {"dates": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": [], "ema_5": [], "ema_15": [], "rsi": [], "volume_spike": [], "trade_markers": []}, "params": {}, "final_capital": 10000, "total_return": 0}
    save_dashboard_payload(payload, output_dir="output/dashboard")

    assert (tmp_path / "output" / "dashboard" / "dashboard_data_test.json").exists()
    assert (tmp_path / "output" / "dashboard" / "ultimate_trading_dashboard_test.html").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ultimate_dashboard.py::test_create_ultimate_dashboard_writes_output_dashboard_files -v`
Expected: FAIL with missing helper/path mismatch.

- [ ] **Step 3: Implement output writer helper and switch creation flow**

```python
def save_dashboard_payload(dashboard_data, output_dir="output/dashboard"):
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "dashboard_data_test.json")
    html_path = os.path.join(output_dir, "ultimate_trading_dashboard_test.html")

    with open(json_path, "w") as f:
        json.dump(dashboard_data, f, default=str)

    generate_html(dashboard_data)
    legacy_html = os.path.join("docs", "ultimate_trading_dashboard.html")
    if os.path.exists(legacy_html):
        shutil.copyfile(legacy_html, html_path)
```

- [ ] **Step 4: Run suite for touched area**

Run: `pytest tests/test_ultimate_dashboard.py tests/test_backtest.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ultimate_dashboard.py tests/test_ultimate_dashboard.py
git commit -m "refactor(dashboard): route outputs to output/dashboard"
```

### Task 6: Generate Requested Artifacts and Update Docs

**Files:**
- Modify: `README.md`
- Create: `output/backtests/old_strategy_2025-09_2025-12.json`
- Create: `output/backtests/old_strategy_2026-01_2026-06.json`
- Create: `output/dashboard/dashboard_data_test.json`
- Create: `output/dashboard/ultimate_trading_dashboard_test.html`

- [ ] **Step 1: Add README run commands for Phase 1 outputs**

```markdown
## Phase 1 Outputs

Run:
- `python3 ultimate_dashboard.py`
- `python3 - <<'PY'\nimport json, os\nfrom src.data.loader import load_data\nfrom src.main.backtest_runner import run_period_backtest\nos.makedirs('output/backtests', exist_ok=True)\ndf = load_data('1min.csv')\njson.dump(run_period_backtest(df, '2025-09-01', '2025-12-31'), open('output/backtests/old_strategy_2025-09_2025-12.json', 'w'), default=str)\njson.dump(run_period_backtest(df, '2026-01-01', '2026-06-30'), open('output/backtests/old_strategy_2026-01_2026-06.json', 'w'), default=str)\nPY`

Generated files:
- `output/dashboard/dashboard_data_test.json`
- `output/dashboard/ultimate_trading_dashboard_test.html`
- `output/backtests/old_strategy_2025-09_2025-12.json`
- `output/backtests/old_strategy_2026-01_2026-06.json`
```

- [ ] **Step 2: Execute generation commands**

Run:
```bash
python3 ultimate_dashboard.py
python3 - <<'PY'
import json
import os
from src.data.loader import load_data
from src.main.backtest_runner import run_period_backtest

os.makedirs("output/backtests", exist_ok=True)
df = load_data("1min.csv")

result_2025 = run_period_backtest(df, "2025-09-01", "2025-12-31")
with open("output/backtests/old_strategy_2025-09_2025-12.json", "w") as f:
    json.dump(result_2025, f, default=str)

result_2026 = run_period_backtest(df, "2026-01-01", "2026-06-30")
with open("output/backtests/old_strategy_2026-01_2026-06.json", "w") as f:
    json.dump(result_2026, f, default=str)
PY
```

Expected:
- Dashboard files created in `output/dashboard/`.
- Backtest report files created in `output/backtests/`.
- Coverage metadata present in both backtest JSON files.

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add README.md output/dashboard output/backtests
git commit -m "docs+build: generate phase1 outputs and update run docs"
```

---

## Spec-to-Plan Coverage Check

- Regenerate test dashboard artifacts: **Task 5 + Task 6**
- Old strategy runs for 2025-09→12 and 2026-01→06: **Task 4 + Task 6**
- Conservative in-candle SL-first handling: **Task 1 + Task 2 + Task 3**
- Coverage gap reporting when data missing: **Task 1 + Task 2 + Task 4**
- Output standardization under `output/`: **Task 5 + Task 6**
