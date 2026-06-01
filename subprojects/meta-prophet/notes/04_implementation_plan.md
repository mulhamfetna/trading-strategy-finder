# Meta-Prophet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 4-model walk-forward forecasting tournament (naive / Prophet / ARIMA / NeuralProphet) on NQ 4h log-returns, with a common eval harness, ranked by RMSE / MAE / MAPE / lift-vs-naive on the 2026 held-out window.

**Architecture:** Shared causal-feature + walk-forward harness in `scripts/common/`; one driver script per model writes a uniform per-bar predictions CSV; final phase compiles all per-model CSVs into a single leaderboard. Models forecast log-returns; price reconstruction `close_hat_t = close_{t-1} · exp(yhat_return)` is done in the harness so every model is scored on the same reconstructed-price metric.

**Tech Stack:** Python 3.14 (already in `.venv`), pandas 3.0, numpy 2.4, matplotlib 3.10, prophet 1.3, pmdarima (TBA), neuralprophet (TBA), pytest.

**Spec:** `subprojects/meta-prophet/notes/03_design.md`.

---

## Pre-flight

All commands run from the **subproject root**: `cd /mnt/data/projects/trading/subprojects/meta-prophet`. The venv is `.venv/`. Activate or invoke directly:

```bash
PYTHON=/mnt/data/projects/trading/subprojects/meta-prophet/.venv/bin/python
PYTEST=/mnt/data/projects/trading/subprojects/meta-prophet/.venv/bin/pytest
```

All file paths below are **relative to the subproject root** unless noted.

---

## Phase 1 — Harness skeleton + naive baseline

Builds the shared eval harness. Naive baseline lights up every metric and locks the API the other three models will plug into.

### Task 1: requirements.txt + verify deps

**Files:**
- Create: `requirements.txt`
- Modify: `.venv` (install missing deps)

- [ ] **Step 1: Create `requirements.txt`**

```
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
prophet>=1.1
pmdarima>=2.0
neuralprophet>=0.8
pytest>=7.0
```

- [ ] **Step 2: Install into the subproject venv**

Run:
```bash
cd /mnt/data/projects/trading/subprojects/meta-prophet
.venv/bin/pip install -r requirements.txt
```

Expected: all packages installed, no errors. If `pmdarima` build fails on Python 3.14, pin to `pmdarima==2.0.4` or fall back to `statsmodels` (note in `06_phase3_arima.md` if substitution made).

- [ ] **Step 3: Sanity import check**

Run:
```bash
.venv/bin/python -c "import pandas, numpy, matplotlib, prophet, pmdarima, neuralprophet, pytest; print('ok')"
```

Expected: `ok`. If any import fails, stop and resolve before proceeding.

- [ ] **Step 4: Commit**

```bash
git add subprojects/meta-prophet/requirements.txt
git commit -m "meta-prophet: pin tournament dependencies"
```

---

### Task 2: `common/data.py` — load + log-return transform

**Files:**
- Create: `scripts/common/__init__.py`
- Create: `scripts/common/data.py`
- Create: `tests/__init__.py`
- Create: `tests/test_data_load.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_data_load.py`:

```python
"""Verify CSV loading + log-return computation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.common.data import load_4h_csv, add_log_return, train_eval_split

DATA = Path(__file__).resolve().parents[1]


def test_load_4h_csv_returns_typed_frame():
    df = load_4h_csv(DATA / "NQ_4h_2025.csv")
    assert list(df.columns) == ["datetime", "open", "high", "low", "close", "volume"]
    assert df["datetime"].dtype == "datetime64[ns]"
    assert df["close"].dtype == float
    assert len(df) == 1534
    assert df["datetime"].is_monotonic_increasing


def test_add_log_return_first_row_is_nan():
    df = pd.DataFrame({"close": [100.0, 101.0, 102.0]})
    out = add_log_return(df)
    assert np.isnan(out["log_return"].iloc[0])
    assert out["log_return"].iloc[1] == pytest.approx(np.log(101 / 100))
    assert out["log_return"].iloc[2] == pytest.approx(np.log(102 / 101))


def test_train_eval_split_disjoint_and_complete():
    df_25 = load_4h_csv(DATA / "NQ_4h_2025.csv")
    df_26 = load_4h_csv(DATA / "NQ_4h_2026.csv")
    train, evalp = train_eval_split(df_25, df_26)
    assert len(train) == 1534
    assert len(evalp) == 585
    assert train["datetime"].max() < evalp["datetime"].min()
    assert train["datetime"].is_monotonic_increasing
    assert evalp["datetime"].is_monotonic_increasing
```

- [ ] **Step 2: Run test, confirm fail**

Run: `.venv/bin/pytest tests/test_data_load.py -v`
Expected: `ModuleNotFoundError: No module named 'scripts.common.data'`.

- [ ] **Step 3: Implement minimal `common/data.py`**

Create `scripts/common/__init__.py` (empty).

Create `tests/__init__.py` (empty).

Create `scripts/common/data.py`:

```python
"""CSV loading + log-return transform + train/eval split for the tournament."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def load_4h_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df = df.sort_values("datetime").reset_index(drop=True)
    return df


def add_log_return(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    out = df.copy()
    out["log_return"] = np.log(out[price_col] / out[price_col].shift(1))
    return out


def train_eval_split(
    df_train_pool: pd.DataFrame,
    df_eval_pool: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df_train_pool.sort_values("datetime").reset_index(drop=True)
    evalp = df_eval_pool.sort_values("datetime").reset_index(drop=True)
    if train["datetime"].max() >= evalp["datetime"].min():
        raise ValueError("train_eval_split: train pool overlaps eval pool")
    return train, evalp
```

- [ ] **Step 4: Run test, confirm pass**

Run: `.venv/bin/pytest tests/test_data_load.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add subprojects/meta-prophet/scripts/common/__init__.py \
        subprojects/meta-prophet/scripts/common/data.py \
        subprojects/meta-prophet/tests/__init__.py \
        subprojects/meta-prophet/tests/test_data_load.py
git commit -m "meta-prophet: data loader + log-return + train/eval split"
```

---

### Task 3: `common/metrics.py` — RMSE/MAE/MAPE/hit-rate/lift

**Files:**
- Create: `scripts/common/metrics.py`
- Create: `tests/test_metrics.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_metrics.py`:

```python
"""Verify metric formulas. Hand-computed expected values."""
from __future__ import annotations

import numpy as np
import pytest

from scripts.common.metrics import (
    rmse, mae, mape, hit_rate, lift_vs_naive, compute_all,
)


def test_rmse_basic():
    y_true = np.array([100.0, 200.0, 300.0])
    y_hat  = np.array([110.0, 190.0, 305.0])
    assert rmse(y_true, y_hat) == pytest.approx(np.sqrt((100 + 100 + 25) / 3))


def test_mae_basic():
    y_true = np.array([100.0, 200.0, 300.0])
    y_hat  = np.array([110.0, 190.0, 305.0])
    assert mae(y_true, y_hat) == pytest.approx((10 + 10 + 5) / 3)


def test_mape_basic_percent():
    y_true = np.array([100.0, 200.0])
    y_hat  = np.array([110.0, 190.0])
    # |10|/100 + |10|/200 = 0.10 + 0.05 = 0.15 / 2 = 0.075 -> 7.5%
    assert mape(y_true, y_hat) == pytest.approx(7.5)


def test_hit_rate_directional():
    y_true_ret = np.array([0.01, -0.005, 0.002, -0.003])
    y_hat_ret  = np.array([0.02, -0.001, -0.004, 0.001])
    # signs: +/+ -/- +/- -/+   -> 2 hits / 4
    assert hit_rate(y_true_ret, y_hat_ret) == pytest.approx(50.0)


def test_lift_vs_naive_positive_means_model_better():
    # naive RMSE 100, model RMSE 80 -> lift = (100-80)/100 = 20%
    assert lift_vs_naive(rmse_model=80.0, rmse_naive=100.0) == pytest.approx(20.0)


def test_lift_vs_naive_negative_when_worse():
    assert lift_vs_naive(rmse_model=120.0, rmse_naive=100.0) == pytest.approx(-20.0)


def test_compute_all_returns_dict_with_expected_keys():
    y_true_price = np.array([100.0, 200.0, 300.0])
    y_hat_price  = np.array([110.0, 190.0, 305.0])
    y_true_ret   = np.array([0.01, -0.005, 0.002])
    y_hat_ret    = np.array([0.02, -0.001, -0.004])
    out = compute_all(y_true_price, y_hat_price, y_true_ret, y_hat_ret, rmse_naive=10.0)
    assert set(out.keys()) == {"rmse", "mae", "mape", "hit_rate", "lift_vs_naive"}
    assert out["rmse"] == pytest.approx(np.sqrt((100 + 100 + 25) / 3))
```

- [ ] **Step 2: Run test, confirm fail**

Run: `.venv/bin/pytest tests/test_metrics.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `common/metrics.py`**

Create `scripts/common/metrics.py`:

```python
"""RMSE / MAE / MAPE / directional-hit-rate / lift-vs-naive."""
from __future__ import annotations

from typing import Mapping

import numpy as np


def rmse(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    err = np.asarray(y_true, dtype=float) - np.asarray(y_hat, dtype=float)
    return float(np.sqrt(np.mean(err ** 2)))


def mae(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    err = np.asarray(y_true, dtype=float) - np.asarray(y_hat, dtype=float)
    return float(np.mean(np.abs(err)))


def mape(y_true: np.ndarray, y_hat: np.ndarray) -> float:
    yt = np.asarray(y_true, dtype=float)
    yh = np.asarray(y_hat, dtype=float)
    return float(np.mean(np.abs((yt - yh) / yt)) * 100.0)


def hit_rate(y_true_ret: np.ndarray, y_hat_ret: np.ndarray) -> float:
    yt = np.sign(np.asarray(y_true_ret, dtype=float))
    yh = np.sign(np.asarray(y_hat_ret, dtype=float))
    return float(np.mean(yt == yh) * 100.0)


def lift_vs_naive(rmse_model: float, rmse_naive: float) -> float:
    return float((rmse_naive - rmse_model) / rmse_naive * 100.0)


def compute_all(
    y_true_price: np.ndarray,
    y_hat_price: np.ndarray,
    y_true_ret: np.ndarray,
    y_hat_ret: np.ndarray,
    rmse_naive: float,
) -> Mapping[str, float]:
    rmse_v = rmse(y_true_price, y_hat_price)
    return {
        "rmse":          rmse_v,
        "mae":           mae(y_true_price, y_hat_price),
        "mape":          mape(y_true_price, y_hat_price),
        "hit_rate":      hit_rate(y_true_ret, y_hat_ret),
        "lift_vs_naive": lift_vs_naive(rmse_v, rmse_naive),
    }
```

- [ ] **Step 4: Run test, confirm pass**

Run: `.venv/bin/pytest tests/test_metrics.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add subprojects/meta-prophet/scripts/common/metrics.py \
        subprojects/meta-prophet/tests/test_metrics.py
git commit -m "meta-prophet: metric primitives + tests"
```

---

### Task 4: `common/features.py` — bar-open-known regressors (no look-ahead)

**Files:**
- Create: `scripts/common/features.py`
- Create: `tests/test_features.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_features.py`:

```python
"""Verify causal feature computation. No look-ahead allowed."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.common.data import add_log_return
from scripts.common.features import build_features


def _toy(n: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    close = 100.0 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.1, 0.5, n)
    low = close - rng.uniform(0.1, 0.5, n)
    return pd.DataFrame({
        "datetime": pd.date_range("2025-01-01", periods=n, freq="4h"),
        "open": close, "high": high, "low": low, "close": close, "volume": rng.uniform(1e3, 1e5, n),
    })


def test_build_features_expected_columns():
    df = add_log_return(_toy())
    feats = build_features(df)
    expected = {"prior_log_return", "prior_range", "rolling_20bar_vol",
                "tod_asia", "tod_eu", "tod_rth_open", "tod_lunch", "tod_rth_close",
                "dow_mon", "dow_tue", "dow_wed", "dow_thu", "dow_fri", "dow_sat", "dow_sun"}
    assert expected.issubset(set(feats.columns))


def test_prior_log_return_is_shifted_log_return():
    df = add_log_return(_toy())
    feats = build_features(df)
    # prior_log_return at row i must equal log_return at row i-1
    np.testing.assert_array_equal(
        feats["prior_log_return"].iloc[2:].to_numpy(),
        df["log_return"].iloc[1:-1].to_numpy(),
    )


def test_rolling_vol_uses_only_past():
    df = add_log_return(_toy())
    feats = build_features(df)
    # rolling_20bar_vol at row 25 must equal std of log_return[5..24] (20 bars, all before row 25)
    expected = df["log_return"].iloc[5:25].std()
    assert feats["rolling_20bar_vol"].iloc[25] == pytest.approx(expected, nan_ok=False)


def test_no_lookahead_features_dont_use_current_bar_close():
    """If we change row N's close, only features at row >= N+1 may change."""
    df = add_log_return(_toy())
    feats_orig = build_features(df)
    df_mod = df.copy()
    df_mod.loc[30, "close"] = df_mod.loc[30, "close"] * 1.1
    df_mod = add_log_return(df_mod.drop(columns=["log_return"]))
    feats_mod = build_features(df_mod)
    # feature row 30 must NOT be affected by changing close[30]
    cols = ["prior_log_return", "prior_range", "rolling_20bar_vol"]
    for c in cols:
        v_orig = feats_orig[c].iloc[30]
        v_mod  = feats_mod[c].iloc[30]
        if np.isnan(v_orig) and np.isnan(v_mod):
            continue
        assert v_orig == pytest.approx(v_mod), f"{c} at row 30 leaked future data"


def test_tod_buckets_one_hot_per_row():
    df = add_log_return(_toy())
    feats = build_features(df)
    tod_cols = [c for c in feats.columns if c.startswith("tod_")]
    row_sums = feats[tod_cols].sum(axis=1)
    assert (row_sums == 1).all()
```

- [ ] **Step 2: Run test, confirm fail**

Run: `.venv/bin/pytest tests/test_features.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `common/features.py`**

Create `scripts/common/features.py`:

```python
"""Bar-open-known regressors. Computed strictly from bars with close_time <= bar_open_time."""
from __future__ import annotations

import numpy as np
import pandas as pd

_TOD_LABELS = ("asia", "eu", "rth_open", "lunch", "rth_close")
_DOW_LABELS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _time_of_day_bucket(hour: int) -> str:
    """Coarse 4h NQ session bucket — labels are five disjoint buckets covering 24h."""
    if 18 <= hour < 22:   return "asia"        # 18:00 -> Asia open
    if 22 <= hour or hour < 2:  return "eu"   # 22:00, 02:00 (next day) -> Asia/EU overlap
    if 2 <= hour < 6:     return "eu"
    if 6 <= hour < 10:    return "rth_open"    # 06:00, 10:00 (ET pre-mkt / NY open)
    if 10 <= hour < 14:   return "lunch"       # 10:00, 14:00 NY lunch
    return "rth_close"                          # 14:00+ -> NY afternoon


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add regressor columns. df MUST already have a `log_return` column."""
    if "log_return" not in df.columns:
        raise ValueError("build_features requires a `log_return` column (call add_log_return first)")
    out = df.copy()

    # prior-bar features (shift by 1 so they use only bars strictly before current)
    out["prior_log_return"] = out["log_return"].shift(1)
    prior_range = (out["high"] - out["low"]) / out["close"]
    out["prior_range"] = prior_range.shift(1)

    # rolling 20-bar volatility computed on log_return up to row i-1 (window of 20 past bars).
    out["rolling_20bar_vol"] = out["log_return"].shift(1).rolling(window=20, min_periods=20).std()

    # time-of-day one-hot
    hours = out["datetime"].dt.hour
    tod = hours.apply(_time_of_day_bucket)
    for label in _TOD_LABELS:
        out[f"tod_{label}"] = (tod == label).astype(int)

    # day-of-week one-hot
    dow_num = out["datetime"].dt.dayofweek  # mon=0..sun=6
    for i, label in enumerate(_DOW_LABELS):
        out[f"dow_{label}"] = (dow_num == i).astype(int)

    return out


REGRESSOR_COLUMNS: tuple[str, ...] = (
    "prior_log_return",
    "prior_range",
    "rolling_20bar_vol",
    *(f"tod_{l}" for l in _TOD_LABELS),
    *(f"dow_{l}" for l in _DOW_LABELS),
)
```

- [ ] **Step 4: Run test, confirm pass**

Run: `.venv/bin/pytest tests/test_features.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add subprojects/meta-prophet/scripts/common/features.py \
        subprojects/meta-prophet/tests/test_features.py
git commit -m "meta-prophet: causal regressor features + no-lookahead tests"
```

---

### Task 5: `common/walkforward.py` — rolling-origin retrain harness

**Files:**
- Create: `scripts/common/walkforward.py`
- Create: `tests/test_walkforward.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_walkforward.py`:

```python
"""Verify the walk-forward harness contract: causality + retrain cadence + output shape."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.common.data import add_log_return
from scripts.common.walkforward import walk_forward, Forecaster


class ConstantReturnModel(Forecaster):
    """Predicts a constant log-return = mean of training history's log_return."""
    def __init__(self) -> None:
        self._mean: float = 0.0
        self.fit_calls = 0

    def fit(self, history: pd.DataFrame) -> None:
        self.fit_calls += 1
        self._mean = float(history["log_return"].dropna().mean())

    def predict_one(self, target_row: pd.Series) -> float:
        return self._mean


def _toy(n: int) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    close = 100.0 + np.cumsum(rng.normal(0, 0.5, n))
    return add_log_return(pd.DataFrame({
        "datetime": pd.date_range("2025-01-01", periods=n, freq="4h"),
        "open": close, "high": close, "low": close, "close": close, "volume": 1e4,
    }))


def test_walk_forward_output_shape():
    train = _toy(50)
    evalp = _toy(20)
    evalp["datetime"] = pd.date_range("2025-02-01", periods=20, freq="4h")
    model = ConstantReturnModel()
    preds = walk_forward(train, evalp, lambda: model, retrain_every=5)
    assert len(preds) == 20
    assert list(preds.columns) == ["datetime", "y_true_price", "y_hat_price", "y_true_return", "y_hat_return"]


def test_walk_forward_retrains_at_expected_cadence():
    train = _toy(50)
    evalp = _toy(20); evalp["datetime"] = pd.date_range("2025-02-01", periods=20, freq="4h")
    holder = {"m": None}
    def factory():
        holder["m"] = ConstantReturnModel()
        return holder["m"]
    walk_forward(train, evalp, factory, retrain_every=5)
    # 20 eval bars, retrain_every=5 -> exactly 4 retrains
    assert holder["m"].fit_calls == 1  # last instance fit once


def test_walk_forward_first_prediction_uses_train_only():
    """Model must not see eval-row 0's close when predicting eval-row 0."""
    train = _toy(50)
    evalp = _toy(20); evalp["datetime"] = pd.date_range("2025-02-01", periods=20, freq="4h")

    seen_dates: list[pd.Timestamp] = []
    class Spy(Forecaster):
        def fit(self, history: pd.DataFrame) -> None:
            seen_dates.append(history["datetime"].max())
        def predict_one(self, target_row): return 0.0
    walk_forward(train, evalp, Spy, retrain_every=5)
    # first fit must see only train (last date = train's last)
    assert seen_dates[0] == train["datetime"].iloc[-1]


def test_walk_forward_price_reconstruction():
    """y_hat_price[t] must equal previous-actual-close * exp(y_hat_return[t])."""
    train = _toy(50)
    evalp = _toy(20); evalp["datetime"] = pd.date_range("2025-02-01", periods=20, freq="4h")
    model = ConstantReturnModel()
    preds = walk_forward(train, evalp, lambda: model, retrain_every=20)
    # at first eval bar: previous close = train's last close
    expected_first = train["close"].iloc[-1] * np.exp(preds["y_hat_return"].iloc[0])
    assert preds["y_hat_price"].iloc[0] == pytest.approx(expected_first)
    # at second eval bar: previous close = eval bar 0's actual close
    expected_second = evalp["close"].iloc[0] * np.exp(preds["y_hat_return"].iloc[1])
    assert preds["y_hat_price"].iloc[1] == pytest.approx(expected_second)
```

- [ ] **Step 2: Run test, confirm fail**

Run: `.venv/bin/pytest tests/test_walkforward.py -v`
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `common/walkforward.py`**

Create `scripts/common/walkforward.py`:

```python
"""Rolling-origin walk-forward harness. Identical for every model in the tournament."""
from __future__ import annotations

from typing import Callable, Protocol

import numpy as np
import pandas as pd


class Forecaster(Protocol):
    def fit(self, history: pd.DataFrame) -> None: ...
    def predict_one(self, target_row: pd.Series) -> float: ...


def walk_forward(
    train_pool: pd.DataFrame,
    eval_pool: pd.DataFrame,
    model_factory: Callable[[], Forecaster],
    retrain_every: int = 20,
) -> pd.DataFrame:
    """
    Walk forward through eval_pool, retraining every `retrain_every` bars.

    At each eval bar t:
      1. The model has been fit on history containing all bars with datetime <= prev eval bar's datetime
         (i.e., it has NOT seen the current bar t).
      2. predict_one returns the model's log-return forecast for bar t.
      3. y_hat_price[t] = close[t-1] * exp(yhat_return[t]) where close[t-1] is the realised
         previous-bar close (train-pool last for the first eval bar; eval-bar i-1 for i >= 1).
      4. After recording, the realised bar t is appended to history.

    Returns a DataFrame with columns:
      datetime, y_true_price, y_hat_price, y_true_return, y_hat_return.
    """
    if retrain_every < 1:
        raise ValueError("retrain_every must be >= 1")

    history = train_pool.copy()
    records: list[dict] = []
    model: Forecaster | None = None

    for i in range(len(eval_pool)):
        if i % retrain_every == 0:
            model = model_factory()
            model.fit(history)
        assert model is not None  # for type checker

        target = eval_pool.iloc[i]
        yhat_return = float(model.predict_one(target))

        prev_close = float(history["close"].iloc[-1])
        yhat_price = prev_close * float(np.exp(yhat_return))

        y_true_price = float(target["close"])
        # actual realised return between previous close and target close
        y_true_return = float(np.log(y_true_price / prev_close))

        records.append({
            "datetime":      target["datetime"],
            "y_true_price":  y_true_price,
            "y_hat_price":   yhat_price,
            "y_true_return": y_true_return,
            "y_hat_return":  yhat_return,
        })

        # append the realised bar to history (with its log_return recomputed against current last close)
        new_row = target.copy()
        if "log_return" in history.columns:
            new_row["log_return"] = y_true_return
        history = pd.concat([history, new_row.to_frame().T], ignore_index=True)

    return pd.DataFrame.from_records(records)
```

- [ ] **Step 4: Run test, confirm pass**

Run: `.venv/bin/pytest tests/test_walkforward.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add subprojects/meta-prophet/scripts/common/walkforward.py \
        subprojects/meta-prophet/tests/test_walkforward.py
git commit -m "meta-prophet: rolling-origin walk-forward harness + causality tests"
```

---

### Task 6: `01_baseline_naive.py` — naive model + first leaderboard row

**Files:**
- Create: `scripts/01_baseline_naive.py`

- [ ] **Step 1: Implement the naive driver**

Create `scripts/01_baseline_naive.py`:

```python
"""Naive baseline: yhat_return = 0 ⇒ yhat_price = previous_close.

Writes outputs/01_naive.csv with the standard per-bar prediction schema.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward


class NaiveModel(Forecaster):
    def fit(self, history: pd.DataFrame) -> None:
        pass  # nothing to learn

    def predict_one(self, target_row: pd.Series) -> float:
        return 0.0  # log-return = 0 ⇒ price = previous close


def main() -> None:
    df_25 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2025.csv"))
    df_26 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2026.csv"))
    train, evalp = train_eval_split(df_25, df_26)

    preds = walk_forward(train, evalp, NaiveModel, retrain_every=20)

    out_path = ROOT / "outputs" / "01_naive.csv"
    preds.to_csv(out_path, index=False)
    print(f"wrote {out_path}  ({len(preds)} rows)")

    # naive's own RMSE is the baseline for "lift_vs_naive"; pass it as itself so lift = 0.
    rmse_self = rmse(preds["y_true_price"].to_numpy(), preds["y_hat_price"].to_numpy())
    metrics = compute_all(
        y_true_price=preds["y_true_price"].to_numpy(),
        y_hat_price=preds["y_hat_price"].to_numpy(),
        y_true_ret=preds["y_true_return"].to_numpy(),
        y_hat_ret=preds["y_hat_return"].to_numpy(),
        rmse_naive=rmse_self,
    )
    print("metrics:")
    for k, v in metrics.items():
        print(f"  {k:<14} {v:>10.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the naive driver**

Run:
```bash
cd /mnt/data/projects/trading/subprojects/meta-prophet
.venv/bin/python scripts/01_baseline_naive.py
```

Expected: prints `wrote .../outputs/01_naive.csv (585 rows)` plus a metrics block. `lift_vs_naive` should be exactly `0.0000`. RMSE should be small (likely $100-200, vs the misleading $5,625 in the legacy eval).

- [ ] **Step 3: Spot-check the output**

Run:
```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_csv('outputs/01_naive.csv')
print(df.head())
print('shape:', df.shape)
# y_hat_price[0] should equal train_pool last close (25,434.75); y_hat_return[0] = 0
assert abs(df['y_hat_return']).max() < 1e-12
print('naive invariants OK')
"
```

Expected: `naive invariants OK`, head shows datetimes starting 2026-01-01.

- [ ] **Step 4: Write `notes/04_phase1_baseline.md`**

Create `notes/04_phase1_baseline.md`:

```markdown
# Phase 1 — Naive baseline + harness

> Scripts: `scripts/01_baseline_naive.py`, `scripts/common/{data,features,metrics,walkforward}.py`
> Tests: `tests/test_{data_load,metrics,features,walkforward}.py` — all green
> Output: `outputs/01_naive.csv`

## What the harness does

Walk-forward, rolling-origin, retrain every 20 bars. At each eval bar t:
- model.fit(history)  — history = train_pool + realised eval bars 0..t-1
- yhat_return = model.predict_one(target_row)   # target_row carries datetime + regressors
- yhat_price = realised_close[t-1] * exp(yhat_return)

The naive model always returns yhat_return = 0, so yhat_price = realised previous close.

## Headline numbers

| metric | value |
|---|---:|
| RMSE  | <fill in> |
| MAE   | <fill in> |
| MAPE  | <fill in> |
| hit_rate | <fill in> |
| lift_vs_naive | 0.00 (by definition) |

## What this means

This is the floor every other model has to beat. Any model that can't beat ~ this RMSE on
the same walk-forward protocol is contributing zero. Both ARIMA on log-returns and Prophet
on log-returns will tend toward this number, because returns are nearly uncorrelated bar-to-bar.
```

Fill in the metric values from the Step 2 run.

- [ ] **Step 5: Commit**

```bash
git add subprojects/meta-prophet/scripts/01_baseline_naive.py \
        subprojects/meta-prophet/outputs/01_naive.csv \
        subprojects/meta-prophet/notes/04_phase1_baseline.md
git commit -m "meta-prophet: phase 1 — naive baseline + harness contract"
```

---

## Phase 2 — Prophet (tuned)

Plugs Prophet into the harness from Phase 1. Tier 1: search on 2025. Tier 2: walk-forward on 2026 with locked config.

### Task 7: `02_prophet_tuned.py` — search + walk-forward

**Files:**
- Create: `scripts/02_prophet_tuned.py`

- [ ] **Step 1: Implement the Prophet driver**

Create `scripts/02_prophet_tuned.py`:

```python
"""Phase 2 — Prophet with log-return target, regressors, CV-tuned changepoint_prior_scale.

Tier 1: cross_validation on 2025 over hyperparam grid -> lock best config.
Tier 2: walk-forward on 2026 using locked config, retrain every 20 bars.
"""
from __future__ import annotations

import itertools
import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split
from scripts.common.features import REGRESSOR_COLUMNS, build_features
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward  # type: ignore

logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")


GRID = {
    "changepoint_prior_scale":  [0.001, 0.01, 0.05, 0.1, 0.5],
    "seasonality_prior_scale":  [0.01, 0.1, 1.0, 10.0],
    "seasonality_mode":         ["additive", "multiplicative"],
}


def _build_prophet(params: dict) -> Prophet:
    m = Prophet(
        growth="flat",
        daily_seasonality=False,
        weekly_seasonality=False,
        yearly_seasonality=False,
        changepoint_prior_scale=params["changepoint_prior_scale"],
        seasonality_prior_scale=params["seasonality_prior_scale"],
        seasonality_mode=params["seasonality_mode"],
    )
    m.add_seasonality(name="intraday_4h", period=1.0, fourier_order=4)        # 1-day = 6 bars
    m.add_seasonality(name="weekly_4h",   period=7.0, fourier_order=3)        # 7-day cycle
    for col in REGRESSOR_COLUMNS:
        m.add_regressor(col, standardize=True)
    return m


def _to_prophet_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Map our schema -> Prophet's (ds, y, regressors). df must have log_return + features."""
    out = df.rename(columns={"datetime": "ds", "log_return": "y"}).copy()
    keep = ["ds", "y", *REGRESSOR_COLUMNS]
    return out[keep].dropna(subset=["y", *REGRESSOR_COLUMNS]).reset_index(drop=True)


def tier1_search(df_train_feat: pd.DataFrame) -> dict:
    """Grid search on 2025 via Prophet's cross_validation. Returns the winning param dict."""
    pf = _to_prophet_frame(df_train_feat)
    best = (np.inf, None)
    results = []
    for cps, sps, sm in itertools.product(GRID["changepoint_prior_scale"],
                                          GRID["seasonality_prior_scale"],
                                          GRID["seasonality_mode"]):
        params = {"changepoint_prior_scale": cps,
                  "seasonality_prior_scale": sps,
                  "seasonality_mode": sm}
        m = _build_prophet(params)
        m.fit(pf)
        cv = cross_validation(m, initial="180 days", period="14 days",
                              horizon="4 hours", parallel=None, disable_tqdm=True)
        pm = performance_metrics(cv, rolling_window=1)
        score = float(pm["rmse"].iloc[0])
        results.append({**params, "rmse_cv": score})
        if score < best[0]:
            best = (score, params)
        print(f"  cps={cps:<6} sps={sps:<6} mode={sm:<14} -> rmse_cv={score:.6f}")
    return best[1] | {"_search_results": results, "_winner_rmse_cv": best[0]}


class ProphetForecaster(Forecaster):
    def __init__(self, params: dict) -> None:
        self.params = params
        self._model: Prophet | None = None

    def fit(self, history: pd.DataFrame) -> None:
        pf = _to_prophet_frame(history)
        self._model = _build_prophet(self.params)
        self._model.fit(pf)

    def predict_one(self, target_row: pd.Series) -> float:
        assert self._model is not None
        future = pd.DataFrame({"ds": [target_row["datetime"]]})
        for col in REGRESSOR_COLUMNS:
            future[col] = float(target_row[col])
        forecast = self._model.predict(future)
        return float(forecast["yhat"].iloc[0])


def main() -> None:
    df_25 = build_features(add_log_return(load_4h_csv(ROOT / "NQ_4h_2025.csv")))
    df_26 = build_features(add_log_return(load_4h_csv(ROOT / "NQ_4h_2026.csv")))
    train, evalp = train_eval_split(df_25, df_26)

    print("Tier 1: hyperparam search on 2025 ...")
    locked = tier1_search(train)
    print(f"\nLocked params: {{cps={locked['changepoint_prior_scale']}, "
          f"sps={locked['seasonality_prior_scale']}, mode={locked['seasonality_mode']}}}  "
          f"CV-rmse={locked['_winner_rmse_cv']:.6f}\n")

    with open(ROOT / "outputs" / "02_prophet_search.json", "w") as f:
        json.dump(locked, f, indent=2, default=str)

    print("Tier 2: walk-forward on 2026 ...")
    preds = walk_forward(train, evalp,
                         lambda: ProphetForecaster({k: locked[k] for k in (
                             "changepoint_prior_scale", "seasonality_prior_scale", "seasonality_mode")}),
                         retrain_every=20)
    out_path = ROOT / "outputs" / "02_prophet.csv"
    preds.to_csv(out_path, index=False)

    naive = pd.read_csv(ROOT / "outputs" / "01_naive.csv")
    rmse_naive = rmse(naive["y_true_price"].to_numpy(), naive["y_hat_price"].to_numpy())
    metrics = compute_all(
        y_true_price=preds["y_true_price"].to_numpy(),
        y_hat_price=preds["y_hat_price"].to_numpy(),
        y_true_ret=preds["y_true_return"].to_numpy(),
        y_hat_ret=preds["y_hat_return"].to_numpy(),
        rmse_naive=rmse_naive,
    )
    print(f"wrote {out_path}  ({len(preds)} rows)")
    print("metrics vs naive baseline:")
    for k, v in metrics.items():
        print(f"  {k:<14} {v:>10.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the Prophet driver** (expect 30-90 min runtime)

Run:
```bash
cd /mnt/data/projects/trading/subprojects/meta-prophet
.venv/bin/python scripts/02_prophet_tuned.py 2>&1 | tee logs/02_prophet.log
```

Expected: tier-1 search log of 40 configs with `rmse_cv` per row, locked params, then walk-forward output. `outputs/02_prophet.csv` written, metrics printed.

- [ ] **Step 3: Write `notes/05_phase2_prophet_tuned.md`**

Create `notes/05_phase2_prophet_tuned.md`:

```markdown
# Phase 2 — Prophet tuned

## Tier 1 — hyperparam search on 2025

Grid: changepoint_prior_scale × seasonality_prior_scale × seasonality_mode (5 × 4 × 2 = 40).

Locked config:  cps=<fill>, sps=<fill>, mode=<fill>, CV-rmse=<fill>.

Search log: `outputs/02_prophet_search.json`.

## Tier 2 — walk-forward on 2026

Retrain every 20 bars. Regressors: prior_log_return, prior_range, rolling_20bar_vol,
tod_* (5), dow_* (7). `growth='flat'` on log-return target.

| metric | naive | prophet | lift |
|---|---:|---:|---:|
| RMSE  | <naive> | <prophet> | <lift>% |
| MAE   | ... | ... | ... |
| MAPE  | ... | ... | ... |
| hit_rate | ... | ... | ... |

## Honest read

<one paragraph: did Prophet beat naive? Was the lift positive? If not, what does that tell us?>
```

Fill in numbers from the Step 2 run.

- [ ] **Step 4: Commit**

```bash
git add subprojects/meta-prophet/scripts/02_prophet_tuned.py \
        subprojects/meta-prophet/outputs/02_prophet.csv \
        subprojects/meta-prophet/outputs/02_prophet_search.json \
        subprojects/meta-prophet/notes/05_phase2_prophet_tuned.md
git commit -m "meta-prophet: phase 2 — tuned Prophet + tier-1 search log"
```

---

## Phase 3 — ARIMA

### Task 8: `03_arima.py` — auto-ARIMA on log-returns

**Files:**
- Create: `scripts/03_arima.py`

- [ ] **Step 1: Implement the ARIMA driver**

Create `scripts/03_arima.py`:

```python
"""Phase 3 — auto_arima on log-returns. d=0 forced (returns are stationary)."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from pmdarima import auto_arima

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward

warnings.filterwarnings("ignore")


class ARIMAForecaster(Forecaster):
    def __init__(self) -> None:
        self._model = None

    def fit(self, history: pd.DataFrame) -> None:
        y = history["log_return"].dropna().to_numpy()
        self._model = auto_arima(
            y, start_p=0, start_q=0, max_p=5, max_q=5, d=0, max_d=0,
            seasonal=False, stepwise=True, suppress_warnings=True, error_action="ignore",
            information_criterion="aic",
        )

    def predict_one(self, target_row: pd.Series) -> float:
        assert self._model is not None
        return float(self._model.predict(n_periods=1)[0])


def main() -> None:
    df_25 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2025.csv"))
    df_26 = add_log_return(load_4h_csv(ROOT / "NQ_4h_2026.csv"))
    train, evalp = train_eval_split(df_25, df_26)

    print("Phase 3 — ARIMA walk-forward (auto_arima refits every 20 bars) ...")
    preds = walk_forward(train, evalp, ARIMAForecaster, retrain_every=20)
    out_path = ROOT / "outputs" / "03_arima.csv"
    preds.to_csv(out_path, index=False)

    naive = pd.read_csv(ROOT / "outputs" / "01_naive.csv")
    rmse_naive = rmse(naive["y_true_price"].to_numpy(), naive["y_hat_price"].to_numpy())
    metrics = compute_all(
        y_true_price=preds["y_true_price"].to_numpy(),
        y_hat_price=preds["y_hat_price"].to_numpy(),
        y_true_ret=preds["y_true_return"].to_numpy(),
        y_hat_ret=preds["y_hat_return"].to_numpy(),
        rmse_naive=rmse_naive,
    )
    print(f"wrote {out_path}  ({len(preds)} rows)")
    for k, v in metrics.items():
        print(f"  {k:<14} {v:>10.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run ARIMA driver** (expect 10-30 min)

Run:
```bash
.venv/bin/python scripts/03_arima.py 2>&1 | tee logs/03_arima.log
```

Expected: walk-forward through 585 bars, `outputs/03_arima.csv` written, metrics printed.

- [ ] **Step 3: Write `notes/06_phase3_arima.md`**

Create `notes/06_phase3_arima.md`:

```markdown
# Phase 3 — ARIMA

`auto_arima` over (p∈[0,5], q∈[0,5], d=0), AIC-selected per retrain.
Walk-forward retrain_every=20 on 2026.

| metric | naive | arima | lift |
|---|---:|---:|---:|
| RMSE  | <fill> | <fill> | <fill>% |
| MAE   | ... | ... | ... |
| MAPE  | ... | ... | ... |
| hit_rate | ... | ... | ... |

## Honest read
<one paragraph>
```

Fill in numbers.

- [ ] **Step 4: Commit**

```bash
git add subprojects/meta-prophet/scripts/03_arima.py \
        subprojects/meta-prophet/outputs/03_arima.csv \
        subprojects/meta-prophet/notes/06_phase3_arima.md
git commit -m "meta-prophet: phase 3 — auto-ARIMA on log-returns"
```

---

## Phase 4 — NeuralProphet

### Task 9: `04_neuralprophet.py` — AR-Net on log-returns

**Files:**
- Create: `scripts/04_neuralprophet.py`

- [ ] **Step 1: Implement the NeuralProphet driver**

Create `scripts/04_neuralprophet.py`:

```python
"""Phase 4 — NeuralProphet with AR-Net on log-returns + same regressors as Phase 2."""
from __future__ import annotations

import itertools
import json
import logging
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from neuralprophet import NeuralProphet, set_log_level

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.data import add_log_return, load_4h_csv, train_eval_split
from scripts.common.features import REGRESSOR_COLUMNS, build_features
from scripts.common.metrics import compute_all, rmse
from scripts.common.walkforward import Forecaster, walk_forward

set_log_level("ERROR")
logging.getLogger("NP").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")


GRID = {
    "n_lags":         [10, 15, 20],
    "learning_rate":  [1e-3, 1e-2],
    "ar_layers":      [[], [16]],
}


def _to_np_frame(df: pd.DataFrame) -> pd.DataFrame:
    out = df.rename(columns={"datetime": "ds", "log_return": "y"}).copy()
    keep = ["ds", "y", *REGRESSOR_COLUMNS]
    return out[keep].dropna(subset=["y", *REGRESSOR_COLUMNS]).reset_index(drop=True)


def _build_np(params: dict) -> NeuralProphet:
    m = NeuralProphet(
        n_lags=params["n_lags"],
        n_forecasts=1,
        ar_layers=params["ar_layers"],
        learning_rate=params["learning_rate"],
        epochs=50,
        daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=False,
        growth="off",
    )
    for c in REGRESSOR_COLUMNS:
        m.add_lagged_regressor(name=c)
    return m


def tier1_search(df_train_feat: pd.DataFrame) -> dict:
    pf = _to_np_frame(df_train_feat)
    # simple 80/20 chrono split for tier-1 (NeuralProphet's CV is slow)
    cut = int(0.8 * len(pf))
    tr, va = pf.iloc[:cut], pf.iloc[cut:]
    best = (np.inf, None); results = []
    for n_lags, lr, ar_layers in itertools.product(GRID["n_lags"], GRID["learning_rate"], GRID["ar_layers"]):
        params = {"n_lags": n_lags, "learning_rate": lr, "ar_layers": ar_layers}
        m = _build_np(params)
        m.fit(tr, freq="4h", progress=None)
        future = m.make_future_dataframe(tr, regressors_df=va[["ds", *REGRESSOR_COLUMNS]],
                                          periods=len(va), n_historic_predictions=False)
        fc = m.predict(future)
        yhat = fc["yhat1"].to_numpy()[-len(va):]
        y    = va["y"].to_numpy()
        score = float(np.sqrt(np.mean((y - yhat) ** 2)))
        results.append({**params, "rmse_val": score})
        if score < best[0]: best = (score, params)
        print(f"  n_lags={n_lags:<3} lr={lr:<5} ar_layers={ar_layers}  -> rmse_val={score:.6f}")
    return best[1] | {"_search_results": results, "_winner_rmse_val": best[0]}


class NPForecaster(Forecaster):
    def __init__(self, params: dict) -> None:
        self.params = params
        self._model: NeuralProphet | None = None
        self._history_np: pd.DataFrame | None = None

    def fit(self, history: pd.DataFrame) -> None:
        self._history_np = _to_np_frame(history)
        self._model = _build_np(self.params)
        self._model.fit(self._history_np, freq="4h", progress=None)

    def predict_one(self, target_row: pd.Series) -> float:
        assert self._model is not None and self._history_np is not None
        future_row = pd.DataFrame({"ds": [target_row["datetime"]],
                                    **{c: [float(target_row[c])] for c in REGRESSOR_COLUMNS}})
        fc_df = self._model.make_future_dataframe(self._history_np, regressors_df=future_row,
                                                   periods=1, n_historic_predictions=False)
        fc = self._model.predict(fc_df)
        return float(fc["yhat1"].iloc[-1])


def main() -> None:
    df_25 = build_features(add_log_return(load_4h_csv(ROOT / "NQ_4h_2025.csv")))
    df_26 = build_features(add_log_return(load_4h_csv(ROOT / "NQ_4h_2026.csv")))
    train, evalp = train_eval_split(df_25, df_26)

    print("Tier 1: hyperparam search on 2025 (80/20 split) ...")
    locked = tier1_search(train)
    print(f"\nLocked params: {locked}")
    with open(ROOT / "outputs" / "04_neuralprophet_search.json", "w") as f:
        json.dump(locked, f, indent=2, default=str)

    print("\nTier 2: walk-forward on 2026 ...")
    locked_runtime = {k: locked[k] for k in ("n_lags", "learning_rate", "ar_layers")}
    preds = walk_forward(train, evalp, lambda: NPForecaster(locked_runtime), retrain_every=20)
    out_path = ROOT / "outputs" / "04_neuralprophet.csv"
    preds.to_csv(out_path, index=False)
    naive = pd.read_csv(ROOT / "outputs" / "01_naive.csv")
    rmse_naive = rmse(naive["y_true_price"].to_numpy(), naive["y_hat_price"].to_numpy())
    metrics = compute_all(
        y_true_price=preds["y_true_price"].to_numpy(),
        y_hat_price=preds["y_hat_price"].to_numpy(),
        y_true_ret=preds["y_true_return"].to_numpy(),
        y_hat_ret=preds["y_hat_return"].to_numpy(),
        rmse_naive=rmse_naive,
    )
    print(f"wrote {out_path}  ({len(preds)} rows)")
    for k, v in metrics.items(): print(f"  {k:<14} {v:>10.4f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run NeuralProphet** (expect 30-90 min)

Run:
```bash
.venv/bin/python scripts/04_neuralprophet.py 2>&1 | tee logs/04_neuralprophet.log
```

Expected: tier-1 search of 12 configs, lock, walk-forward, metrics. If runtime > 2h, reduce `retrain_every` to 40 (note the change in `07_phase4_neuralprophet.md`).

- [ ] **Step 3: Write `notes/07_phase4_neuralprophet.md`**

Create `notes/07_phase4_neuralprophet.md`:

```markdown
# Phase 4 — NeuralProphet (AR-Net)

Tier 1: 12-config search (n_lags × lr × ar_layers) on 80/20 chrono split of 2025.
Tier 2: walk-forward retrain_every=20 on 2026.

Locked params: n_lags=<>, lr=<>, ar_layers=<>.

| metric | naive | neuralprophet | lift |
|---|---:|---:|---:|
| RMSE  | ... | ... | ...% |
| MAE   | ... | ... | ... |
| MAPE  | ... | ... | ... |
| hit_rate | ... | ... | ... |

## Honest read
<one paragraph>
```

Fill in numbers.

- [ ] **Step 4: Commit**

```bash
git add subprojects/meta-prophet/scripts/04_neuralprophet.py \
        subprojects/meta-prophet/outputs/04_neuralprophet.csv \
        subprojects/meta-prophet/outputs/04_neuralprophet_search.json \
        subprojects/meta-prophet/notes/07_phase4_neuralprophet.md
git commit -m "meta-prophet: phase 4 — NeuralProphet AR-Net + tier-1 search log"
```

---

## Phase 5 — Leaderboard + final report

### Task 10: `05_compile_leaderboard.py` — consolidate outputs + plots

**Files:**
- Create: `scripts/05_compile_leaderboard.py`

- [ ] **Step 1: Implement the leaderboard compiler**

Create `scripts/05_compile_leaderboard.py`:

```python
"""Phase 5 — consolidate per-model outputs into leaderboard.csv + plots."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.common.metrics import compute_all, rmse

MODELS = [
    ("naive",          "outputs/01_naive.csv"),
    ("prophet",        "outputs/02_prophet.csv"),
    ("arima",          "outputs/03_arima.csv"),
    ("neuralprophet",  "outputs/04_neuralprophet.csv"),
]


def main() -> None:
    # naive's RMSE is the reference for lift
    naive_df = pd.read_csv(ROOT / "outputs" / "01_naive.csv")
    rmse_naive = rmse(naive_df["y_true_price"].to_numpy(), naive_df["y_hat_price"].to_numpy())

    rows = []
    per_model: dict[str, pd.DataFrame] = {}
    for name, path in MODELS:
        p = ROOT / path
        if not p.exists():
            print(f"  [skip] {name}: {path} missing")
            continue
        df = pd.read_csv(p)
        per_model[name] = df
        m = compute_all(
            y_true_price=df["y_true_price"].to_numpy(),
            y_hat_price=df["y_hat_price"].to_numpy(),
            y_true_ret=df["y_true_return"].to_numpy(),
            y_hat_ret=df["y_hat_return"].to_numpy(),
            rmse_naive=rmse_naive,
        )
        rows.append({"model": name, **m})

    leaderboard = pd.DataFrame(rows).sort_values("rmse")
    leaderboard.to_csv(ROOT / "outputs" / "leaderboard.csv", index=False)
    print(leaderboard.to_string(index=False))

    # leaderboard bar chart
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for ax, col, title in zip(axes,
                              ["rmse", "mape", "lift_vs_naive"],
                              ["RMSE ($)", "MAPE (%)", "Lift vs naive (%)"]):
        ax.bar(leaderboard["model"], leaderboard[col])
        ax.set_title(title); ax.tick_params(axis="x", rotation=20); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(ROOT / "plots" / "leaderboard.png", dpi=120); plt.close(fig)

    # per-model trajectory plots
    for name, df in per_model.items():
        df["datetime"] = pd.to_datetime(df["datetime"])
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df["datetime"], df["y_true_price"], label="actual", linewidth=0.8)
        ax.plot(df["datetime"], df["y_hat_price"],  label=name, linewidth=0.8, alpha=0.8)
        ax.set_title(f"{name} — 2026 walk-forward"); ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout(); fig.savefig(ROOT / "plots" / f"{name}_trajectory.png", dpi=120); plt.close(fig)

    # error distribution overlay
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, df in per_model.items():
        err = np.abs(df["y_true_price"] - df["y_hat_price"])
        ax.hist(err, bins=50, alpha=0.5, label=name)
    ax.set_xlabel("|error|  ($)"); ax.set_ylabel("count"); ax.set_title("Per-bar abs-error distribution")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(ROOT / "plots" / "error_distribution.png", dpi=120); plt.close(fig)

    print("plots saved to plots/")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the compiler**

Run:
```bash
.venv/bin/python scripts/05_compile_leaderboard.py
```

Expected: prints the leaderboard table sorted by RMSE; writes `outputs/leaderboard.csv`, `plots/leaderboard.png`, `plots/<model>_trajectory.png` (×4), `plots/error_distribution.png`.

- [ ] **Step 3: Write the final report**

Create `notes/08_final_report.md`:

```markdown
# Meta-Prophet — Final Report

> Companion docs: `00_research_report.md`, `01_data_jump_investigation.md`,
> `02_mape_and_relative_error_explained.md`, `03_design.md`, `04_phase1_baseline.md` ... `07_phase4_neuralprophet.md`.

## Leaderboard (sorted by RMSE on 2026 walk-forward)

| Model         | RMSE | MAE | MAPE | Hit-rate | Lift vs naive |
|---|---:|---:|---:|---:|---:|
| <fill from outputs/leaderboard.csv>

## Verdict

<one paragraph: which model won; was the lift over naive material; what does the result
imply about Prophet's structural fit to this data; recommend whether to deploy any of them>

## Per-bar plots
- `plots/leaderboard.png` — RMSE / MAPE / Lift bar chart
- `plots/<model>_trajectory.png` — actual vs forecast on 2026
- `plots/error_distribution.png` — abs-error histogram

## Caveats specific to this study

1. n = 1 regime change observed (2025 V-shape into 2026 continuation).
2. The +8.21% 4h bar on 2025-04-09 (tariff pause) dominates 2025 in-sample fits.
3. Hyperparam search was tier-1 only — no nested CV — to keep runtime tractable.
4. Retrain cadence default = 20 bars (~3 days). Sensitivity to 1 / 100 not exhaustively swept.

## What to do if no model beat naive

<one paragraph: alternative targets (volatility / direction), alternative models, or
"forecasting NQ price level at 4h cadence is structurally hard and Prophet was not
the limiting factor">
```

Fill the leaderboard table from `outputs/leaderboard.csv`. Write the verdict & "what to do" paragraphs from the actual numbers.

- [ ] **Step 4: Update README**

Create or overwrite `README.md`:

```markdown
# Meta-Prophet — Forecasting tournament

Read-only research subproject. Compares **naive / Prophet / ARIMA / NeuralProphet** on a
**1-bar-ahead walk-forward** forecast of NQ 4h close (target: log-returns; price reconstructed
for eval).

## Final result

See `notes/08_final_report.md`.

## Phase status

| # | Phase | Status |
|---|---|---|
| 0 | Scaffold | ✅ done |
| 1 | Naive baseline + harness | ✅ done |
| 2 | Prophet tuned (tier-1 search + tier-2 walk-forward) | ✅ done |
| 3 | ARIMA (auto_arima on log-returns) | ✅ done |
| 4 | NeuralProphet (AR-Net) | ✅ done |
| 5 | Leaderboard + final report | ✅ done |

## Reproduce

```bash
cd subprojects/meta-prophet
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/01_baseline_naive.py        # ~30s
.venv/bin/python scripts/02_prophet_tuned.py         # ~30-90 min
.venv/bin/python scripts/03_arima.py                 # ~10-30 min
.venv/bin/python scripts/04_neuralprophet.py         # ~30-90 min
.venv/bin/python scripts/05_compile_leaderboard.py   # ~10s
```

Tests (~30s):
```bash
.venv/bin/pytest tests/ -v
```
```

- [ ] **Step 5: Commit**

```bash
git add subprojects/meta-prophet/scripts/05_compile_leaderboard.py \
        subprojects/meta-prophet/outputs/leaderboard.csv \
        subprojects/meta-prophet/plots/*.png \
        subprojects/meta-prophet/notes/08_final_report.md \
        subprojects/meta-prophet/README.md
git commit -m "meta-prophet: phase 5 — leaderboard + plots + final report"
```

---

## Final sweep

### Task 11: Verify everything is reproducible

- [ ] **Step 1: Run the full test suite**

Run:
```bash
cd /mnt/data/projects/trading/subprojects/meta-prophet
.venv/bin/pytest tests/ -v
```

Expected: all tests in `test_data_load.py`, `test_metrics.py`, `test_features.py`, `test_walkforward.py` pass.

- [ ] **Step 2: Verify outputs exist**

Run:
```bash
ls outputs/ && ls plots/
```

Expected: `01_naive.csv`, `02_prophet.csv`, `03_arima.csv`, `04_neuralprophet.csv`, `02_prophet_search.json`, `04_neuralprophet_search.json`, `leaderboard.csv`; plots show 6 PNGs (1 leaderboard + 4 trajectory + 1 error_distribution).

- [ ] **Step 3: Verify the no-lookahead invariant one more time**

Run:
```bash
.venv/bin/pytest tests/test_features.py::test_no_lookahead_features_dont_use_current_bar_close \
                 tests/test_walkforward.py::test_walk_forward_first_prediction_uses_train_only -v
```

Expected: 2 passed.

- [ ] **Step 4: Final commit (if anything changed)**

```bash
git status
# if clean → done. Otherwise:
git add -A subprojects/meta-prophet/
git commit -m "meta-prophet: final cleanup"
```

---

## Spec coverage self-check

| Spec section | Covered by |
|---|---|
| §1 problem statement (1-bar walk-forward, lift-vs-naive) | Tasks 6, 7, 8, 9, 10 |
| §2 data (log-return target, 2025 train pool, 2026 eval pool) | Tasks 2, 6, 7, 8, 9 |
| §3 subproject layout | Pre-existing (scaffold) + every file path matches Tasks 1-10 |
| §4 walk-forward protocol (causality + retrain) | Tasks 4, 5, 7, 9 |
| §5 hyperparam two-tier protocol | Tasks 7, 9 (tier-1 search + tier-2 walk-forward) |
| §6 metrics (RMSE/MAE/MAPE/hit-rate/lift) | Task 3 |
| §7 phase plan | Tasks 6 → phase 1, 7 → 2, 8 → 3, 9 → 4, 10 → 5 |
| §8 risks (auto_arima d>0, NeuralProphet runtime) | Task 8 (d=0 forced), Task 9 step 2 (cadence fallback note) |
| §9 success criteria | Task 10 (final report explicitly answers all 5 questions) |
| §10 out of scope | Plan does not address; preserved as documented exclusions |

No gaps.
