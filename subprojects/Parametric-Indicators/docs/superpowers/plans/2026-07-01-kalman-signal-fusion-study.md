# Kalman/Fusion Study — Phase 1 Implementation Plan (shared rig + M0 ceiling)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the parity-safe research rig and compute the **M0 ceiling** — the best achievable (entry-rate × payoff × total-P/L) if we admitted the currently-dropped box signals with a perfect director — for NQ 4h. This is the decisive gate: if the ceiling isn't promising, we stop before building M1/M2/M3.

**Architecture:** A new **additive research package `research/kalman_fusion/`**, off the production `optimize/` path, that *imports the parity-locked engine as a library*. It reuses `optimize/counterfactual_pause.py` (champion loader + `simulate_one` counterfactual-entry primitive) and `optimize/fast_engine.fast_backtest`. New code is only: Pareto **metrics**, the **opposite-direction/oracle** extension, a reusable **rig** (`evaluate(policy)`), and the **M0 ceiling** aggregation. Nothing in `optimize/` or `frontend/` is modified, so the golden gate is untouched.

**Tech Stack:** Python 3, numpy, pandas, pytest. Reuses `optimize.counterfactual_pause`, `optimize.fast_engine.fast_backtest`, `optimize.l2.l1_runner.build_state_timeline`, `config.NQ_POINT_VALUE`.

## Global Constraints

- **Off the production path:** create only files under `research/kalman_fusion/`. Do NOT modify anything in `optimize/`, `frontend/`, `indicators/`, `perf/`. Golden 6/6 must remain byte-identical (verified in the last task).
- **Server-only for heavy runs:** unit tests are light and run locally; the full NQ 4h ceiling run (Task 7) runs **on the AMD server** (`amd-trading`), never a heavy local job.
- **Reuse, don't re-implement:** all trade P/L comes from `fast_backtest` via the existing champion args (`counterfactual_pause._bt_args`). Never re-derive fills or P/L.
- **Point value:** P/L in dollars = `pnl_points * pv`, `pv = config.NQ_POINT_VALUE` (already carried on the champion context as `C["pv"]`).
- **Run tests from the subproject root** `subprojects/Parametric-Indicators/` so `optimize`/`config` import (that dir is on `sys.path`). Package modules also self-insert the root (pattern copied from `counterfactual_pause.py`).
- **M0 is an ORACLE, not a strategy:** it deliberately uses realized trade outcomes to pick the better direction — it is an upper bound, explicitly non-causal. Causality guards apply to the M1/M2/M3 estimators (later plans), not to M0.

---

## File structure (Phase 1)

| File | Responsibility |
|---|---|
| `research/kalman_fusion/__init__.py` | package marker + `sys.path` root insert |
| `research/kalman_fusion/metrics.py` | pure Pareto metrics: `payoff_ratio`, `max_drawdown`, `summarize` → `Metrics` |
| `research/kalman_fusion/rig.py` | reusable evaluator: `evaluate(C, admit, direction) → Metrics` (runs `fast_backtest` once); champion-parity anchor |
| `research/kalman_fusion/ceiling.py` | M0: `eligible_mask`, `simulate_dir`, `oracle_ledger`, `ceiling_report` |
| `research/kalman_fusion/run_ceiling.py` | CLI entrypoint: build the NQ 4h ceiling + write CSV + markdown |
| `research/kalman_fusion/test_metrics.py` | fixture tests for metrics |
| `research/kalman_fusion/test_rig.py` | champion-parity test (rig reproduces champion numbers) |
| `research/kalman_fusion/test_ceiling.py` | oracle ≥ native, eligibility, aggregation tests |

---

### Task 1: Scaffold the research package + champion loader smoke test

**Files:**
- Create: `research/kalman_fusion/__init__.py`
- Create: `research/kalman_fusion/test_loader.py`

**Interfaces:**
- Consumes: `optimize.counterfactual_pause.load_champion(tf="4h") -> dict C` with keys `d, d1, box, n, sig, vol_gate, veto, confirm, params, pv, bar_td, gate_pct, K`.
- Produces: the package import root; confirms the canonical NQ champion loads (anchor for all later tasks).

- [ ] **Step 1: Create the package `__init__.py` with the path insert**

```python
# research/kalman_fusion/__init__.py
"""Kalman / signal-fusion STUDY package (research only, off the production optimize/ path).

Imports the parity-locked engine as a library to (a) compute the M0 ceiling and (b) evaluate
admit/direction policies for M1/M2/M3. Never modifies optimize/. See
docs/superpowers/specs/2026-07-01-kalman-signal-fusion-study-design.md.
"""
from __future__ import annotations
import sys
from pathlib import Path

# subproject root (…/Parametric-Indicators) on sys.path so `optimize`/`config` import.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
```

- [ ] **Step 2: Write the failing loader test**

```python
# research/kalman_fusion/test_loader.py
import research.kalman_fusion  # noqa: F401  (triggers the sys.path insert)
from optimize import counterfactual_pause as cp


def test_load_champion_returns_expected_context():
    C = cp.load_champion("4h")
    for key in ("d", "d1", "box", "n", "sig", "vol_gate", "veto", "confirm", "params", "pv"):
        assert key in C, f"missing {key}"
    assert C["n"] > 2000           # NQ 4h ~2119 decision bars
    assert C["pv"] > 0
    # engine gate is a boolean mask of length n
    g = cp._engine_gate(C)
    assert g.shape == (C["n"],)
    assert g.dtype == bool
```

- [ ] **Step 3: Run test to verify it passes (loader already exists — this is a smoke/anchor)**

Run: `python3 -m pytest research/kalman_fusion/test_loader.py -v`
Expected: PASS (if it FAILS on import of `research.kalman_fusion`, ensure you run from the subproject root).

- [ ] **Step 4: Commit**

```bash
git add research/kalman_fusion/__init__.py research/kalman_fusion/test_loader.py
git commit -m "research(kalman): scaffold study package + champion-loader anchor test"
```

---

### Task 2: Pareto metrics (`metrics.py`)

**Files:**
- Create: `research/kalman_fusion/metrics.py`
- Create: `research/kalman_fusion/test_metrics.py`

**Interfaces:**
- Produces:
  - `payoff_ratio(pnls) -> float` — avg win ÷ avg loss (0.0 if no wins; `inf` if wins but no losses).
  - `max_drawdown(pnls_in_exit_order) -> float` — max peak-to-trough of the cumulative equity.
  - `Metrics` dataclass: `n_entries:int, n_eligible:int, entry_rate:float, payoff:float, total_pnl:float, win_rate:float, pf:float, expectancy:float, max_dd:float`.
  - `summarize(pnls, n_eligible, pnls_exit_order=None) -> Metrics`.

- [ ] **Step 1: Write the failing test**

```python
# research/kalman_fusion/test_metrics.py
import math
import research.kalman_fusion  # noqa: F401
from research.kalman_fusion.metrics import payoff_ratio, max_drawdown, summarize


def test_payoff_ratio_basic():
    # wins avg = (200+100)/2 = 150 ; losses avg = 100 ; payoff = 1.5
    assert payoff_ratio([200.0, 100.0, -100.0]) == 1.5

def test_payoff_ratio_no_losses_is_inf():
    assert payoff_ratio([10.0, 20.0]) == math.inf

def test_payoff_ratio_no_wins_is_zero():
    assert payoff_ratio([-10.0, -20.0]) == 0.0

def test_max_drawdown_simple():
    # equity path: +100, +50 (peak 100→150), -200 (trough -50) → DD from 150 to -50 = 200
    assert max_drawdown([100.0, 50.0, -200.0]) == 200.0

def test_summarize_fields():
    m = summarize([200.0, -100.0, 300.0], n_eligible=12)
    assert m.n_entries == 3
    assert m.n_eligible == 12
    assert m.entry_rate == 0.25
    assert m.total_pnl == 400.0
    assert m.win_rate == 2 / 3
    assert m.payoff == 2.5          # avg win 250 / avg loss 100
    assert m.expectancy == 400.0 / 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest research/kalman_fusion/test_metrics.py -v`
Expected: FAIL with `ModuleNotFoundError: research.kalman_fusion.metrics`

- [ ] **Step 3: Write the implementation**

```python
# research/kalman_fusion/metrics.py
"""Pure Pareto metrics for the study rig — no engine imports, trivially testable."""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np


@dataclass
class Metrics:
    n_entries: int
    n_eligible: int
    entry_rate: float
    payoff: float        # avg win / avg loss
    total_pnl: float
    win_rate: float
    pf: float            # gross win / gross loss
    expectancy: float    # mean per-trade P/L
    max_dd: float


def payoff_ratio(pnls) -> float:
    a = np.asarray(pnls, dtype=float)
    wins = a[a > 0]; losses = a[a < 0]
    avg_w = wins.mean() if wins.size else 0.0
    avg_l = -losses.mean() if losses.size else 0.0
    if avg_l > 0:
        return float(avg_w / avg_l)
    return math.inf if avg_w > 0 else 0.0


def max_drawdown(pnls_in_exit_order) -> float:
    a = np.asarray(pnls_in_exit_order, dtype=float)
    if a.size == 0:
        return 0.0
    eq = np.cumsum(a)
    peak = np.maximum.accumulate(eq)
    return float((peak - eq).max())


def summarize(pnls, n_eligible: int, pnls_exit_order=None) -> Metrics:
    a = np.asarray(pnls, dtype=float)
    n = int(a.size)
    wins = a[a > 0]; losses = a[a < 0]
    gross_w = float(wins.sum()); gross_l = float(-losses.sum())
    pf = (gross_w / gross_l) if gross_l > 0 else (math.inf if gross_w > 0 else 0.0)
    dd = max_drawdown(pnls_exit_order if pnls_exit_order is not None else pnls)
    return Metrics(
        n_entries=n,
        n_eligible=int(n_eligible),
        entry_rate=(n / n_eligible) if n_eligible else 0.0,
        payoff=payoff_ratio(a),
        total_pnl=float(a.sum()),
        win_rate=(float((a > 0).sum()) / n) if n else 0.0,
        pf=pf,
        expectancy=(float(a.mean()) if n else 0.0),
        max_dd=dd,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest research/kalman_fusion/test_metrics.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add research/kalman_fusion/metrics.py research/kalman_fusion/test_metrics.py
git commit -m "research(kalman): Pareto metrics (payoff, entry-rate, drawdown, summarize)"
```

---

### Task 3: Reusable rig `evaluate()` + champion-parity anchor

**Files:**
- Create: `research/kalman_fusion/rig.py`
- Create: `research/kalman_fusion/test_rig.py`

**Interfaces:**
- Consumes: `counterfactual_pause._bt_args(C)`, `counterfactual_pause._engine_gate(C)`, `counterfactual_pause.champion_taken_trades(C)`, `fast_engine.fast_backtest(dd, cl, si, gate, md, mh, ml, mc, sls, slh, tp, flip) -> list[dict]` (trade dicts carry `pnl_points`, `direction`, `entry_time`, `exit_time`).
- Produces: `evaluate(C, admit, direction=None) -> Metrics` — the single evaluator every mechanism (M1/M2/M3) will call. `admit` = bool mask length `n` (True at an entry bar to admit that box signal). `direction` = optional int array length `n`; where non-zero it OVERRIDES the box direction feeding the entry at `idx` (set at `idx-1`, the engine's read position); where zero/None the native box direction is used.

- [ ] **Step 1: Write the failing test (rig reproduces the champion exactly = parity anchor)**

```python
# research/kalman_fusion/test_rig.py
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.rig import evaluate


def test_rig_reproduces_champion_metrics():
    C = cp.load_champion("4h")
    taken = cp.champion_taken_trades(C)                 # the engine's own trade list
    champ_pnls = [t["pnl_points"] * C["pv"] for t in taken]
    n_taken = len(taken)

    m = evaluate(C, cp._engine_gate(C), direction=None)  # rig, same gate
    assert m.n_entries == n_taken
    assert abs(m.total_pnl - sum(champ_pnls)) < 1e-6      # byte-for-byte P/L
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest research/kalman_fusion/test_rig.py -v`
Expected: FAIL with `ModuleNotFoundError: research.kalman_fusion.rig`

- [ ] **Step 3: Write the implementation**

```python
# research/kalman_fusion/rig.py
"""The shared evaluation rig. Given an admit-mask (+ optional direction override), run the ONE
parity-locked engine (fast_backtest) and return Metrics. Every mechanism plugs in here so results
are apples-to-apples and P/L is engine-computed, never re-derived."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401  (path insert)
from optimize import counterfactual_pause as cp
from optimize.fast_engine import fast_backtest
from research.kalman_fusion.metrics import Metrics, summarize


def evaluate(C, admit, direction=None, n_eligible=None) -> Metrics:
    dd, cl, si, md, mh, ml, mc, sls, slh, tp, flip = cp._bt_args(C)
    si = np.asarray(si).copy()
    if direction is not None:
        d = np.asarray(direction)
        si = np.where(d != 0, d, si)               # override where the policy specifies a direction
    admit = np.asarray(admit, dtype=bool)
    trades = fast_backtest(dd, cl, si, admit, md, mh, ml, mc, sls, slh, tp, flip)
    pnls = [t["pnl_points"] * C["pv"] for t in trades]                       # exit order (engine emits closed trades in order)
    if n_eligible is None:
        n_eligible = int(admit.sum())
    return summarize(pnls, n_eligible=n_eligible, pnls_exit_order=pnls)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest research/kalman_fusion/test_rig.py -v`
Expected: PASS (rig total P/L equals the champion's, entries equal)

- [ ] **Step 5: Commit**

```bash
git add research/kalman_fusion/rig.py research/kalman_fusion/test_rig.py
git commit -m "research(kalman): shared eval rig (fast_backtest) + champion-parity anchor"
```

---

### Task 4: Eligibility mask (flat-eligible dropped signals)

**Files:**
- Create: `research/kalman_fusion/ceiling.py` (first function)
- Create: `research/kalman_fusion/test_ceiling.py` (first test)

**Interfaces:**
- Consumes: `counterfactual_pause.attribute(sig, vol_gate, veto, confirm)`, `counterfactual_pause.champion_taken_trades(C)`, `l2.l1_runner.build_state_timeline(taken, dec_dates, n)`.
- Produces: `eligible_dropped(C) -> dict` with `idxs:list[int]` (entry bars that were blocked by `vol_gated`/`vetoed`/`confirm<K` **while the champion was flat**), `n_eligible:int` (taken + eligible-dropped), `n_taken:int`, `by_reason:dict[str,list[int]]`.

- [ ] **Step 1: Write the failing test**

```python
# research/kalman_fusion/test_ceiling.py
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import eligible_dropped


def test_eligible_dropped_shape_and_counts():
    C = cp.load_champion("4h")
    e = eligible_dropped(C)
    assert e["n_taken"] > 150                       # champion ~214 trades
    assert len(e["idxs"]) > 0                       # there ARE blocked-while-flat signals
    # every eligible idx is a real blocked cause and NOT already a taken bar
    assert set(e["by_reason"]) <= {"vol_gated", "vetoed", "confirm<K"}
    assert e["n_eligible"] == e["n_taken"] + len(e["idxs"])
    # entry-rate today is well under half
    assert e["n_taken"] / e["n_eligible"] < 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest research/kalman_fusion/test_ceiling.py::test_eligible_dropped_shape_and_counts -v`
Expected: FAIL with `ImportError: cannot import name 'eligible_dropped'`

- [ ] **Step 3: Write the implementation**

```python
# research/kalman_fusion/ceiling.py
"""M0 — the counterfactual CEILING. Reuses counterfactual_pause's champion context + fast_backtest.
Deliberately an ORACLE (peeks at realized outcome to pick the better direction): an UPPER BOUND on what
admitting the dropped flow could earn, not a deployable policy."""
from __future__ import annotations
import numpy as np
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from optimize.l2.l1_runner import build_state_timeline

_BLOCKED = ("vol_gated", "vetoed", "confirm<K")


def eligible_dropped(C) -> dict:
    """Blocked box signals that fired while the champion was FLAT (the honest 'could we have taken it?'
    denominator). Excludes bars the champion was already in a trade."""
    taken = cp.champion_taken_trades(C)
    dec_dates = C["d"]["Date"].to_numpy()
    in_pos = build_state_timeline(taken, dec_dates, C["n"])          # bool[n], True = in a trade
    cause = cp.attribute(C["sig"], C["vol_gate"], C["veto"], C["confirm"])
    by_reason = {r: [] for r in _BLOCKED}
    idxs = []
    for i in range(1, C["n"]):
        if cause[i] in _BLOCKED and not in_pos[i]:
            by_reason[cause[i]].append(i)
            idxs.append(i)
    n_taken = len(taken)
    return {"idxs": idxs, "by_reason": by_reason,
            "n_taken": n_taken, "n_eligible": n_taken + len(idxs)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest research/kalman_fusion/test_ceiling.py::test_eligible_dropped_shape_and_counts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add research/kalman_fusion/ceiling.py research/kalman_fusion/test_ceiling.py
git commit -m "research(kalman): M0 eligibility (flat-eligible dropped signals)"
```

---

### Task 5: Directional counterfactual + oracle (`simulate_dir`, per-signal oracle)

**Files:**
- Modify: `research/kalman_fusion/ceiling.py` (add `simulate_dir`, `signal_outcomes`)
- Modify: `research/kalman_fusion/test_ceiling.py` (add tests)

**Interfaces:**
- Consumes: `counterfactual_pause._bt_args(C)`, `fast_engine.fast_backtest`.
- Produces:
  - `simulate_dir(C, entry_idx, direction) -> float | None` — P/L (dollars) of entering the box signal at `entry_idx` in `direction` (+1/−1) under the champion's exits; `None` if it never closes.
  - `signal_outcomes(C, idxs) -> dict` with arrays `native`, `opposite`, `oracle` (per-idx dollar P/L; NaN where unresolved).

- [ ] **Step 1: Write the failing tests**

```python
# add to research/kalman_fusion/test_ceiling.py
import numpy as np
from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import eligible_dropped, simulate_dir, signal_outcomes


def test_simulate_dir_matches_native_simulate_one():
    C = cp.load_champion("4h")
    idx = eligible_dropped(C)["idxs"][0]
    native_trade = cp.simulate_one(C, idx)             # engine's native-direction isolated trade
    assert native_trade is not None
    native_dir = native_trade["direction"]             # +1 / -1
    got = simulate_dir(C, idx, native_dir)
    assert abs(got - native_trade["pnl_points"] * C["pv"]) < 1e-6

def test_opposite_direction_flips_sign_of_pnl_region():
    # for a symmetric SL/TP a full-TP long and the mirror short won't be exact opposites, but the
    # oracle (max of the two) must be >= the native for every resolved signal.
    C = cp.load_champion("4h")
    idxs = eligible_dropped(C)["idxs"][:200]
    o = signal_outcomes(C, idxs)
    res = ~np.isnan(o["oracle"])
    assert res.any()
    assert np.all(o["oracle"][res] >= o["native"][res] - 1e-6)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest research/kalman_fusion/test_ceiling.py -k "simulate_dir or opposite" -v`
Expected: FAIL with `ImportError: cannot import name 'simulate_dir'`

- [ ] **Step 3: Add the implementation to `ceiling.py`**

```python
# append to research/kalman_fusion/ceiling.py

def simulate_dir(C, entry_idx: int, direction: int):
    """Isolated trade at entry_idx FORCED to `direction` (+1/-1), champion exits. Dollars, or None."""
    dd, cl, si, md, mh, ml, mc, sls, slh, tp, flip = cp._bt_args(C)
    si = np.asarray(si).copy()
    # engine reads the box signal at idx-1 and applies `flip`; undo flip so `direction` is the REALISED side.
    si[entry_idx - 1] = -direction if flip else direction
    gate = np.zeros(C["n"], dtype=bool); gate[int(entry_idx)] = True
    trades = fast_backtest(dd, cl, si, gate, md, mh, ml, mc, sls, slh, tp, flip)
    if not trades:
        return None
    return float(trades[0]["pnl_points"]) * C["pv"]


def signal_outcomes(C, idxs) -> dict:
    """Per-idx native / opposite / oracle dollar P/L. NaN where the trade never closes."""
    native = np.full(len(idxs), np.nan); opposite = np.full(len(idxs), np.nan)
    for k, i in enumerate(idxs):
        up = simulate_dir(C, i, +1); dn = simulate_dir(C, i, -1)
        if up is not None:
            native[k] = up          # +1 is the "native long" reference; see note below
        if dn is not None:
            opposite[k] = dn
    # oracle = best realised side per signal (peeks — it's a ceiling)
    stack = np.vstack([native, opposite])
    oracle = np.nanmax(stack, axis=0)
    oracle[np.all(np.isnan(stack), axis=0)] = np.nan
    return {"native": native, "opposite": opposite, "oracle": oracle}
```

Note: `native` here is the +1 (long) simulation and `opposite` the −1 (short); the *box*-native direction for a given signal is whichever of the two matches `sign(sig[idx-1])`. The ceiling only needs the **oracle = best of the two**, so this labelling is sufficient for the bound. (The box-native aggregate is reported separately in Task 6 using the champion's own `sig`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest research/kalman_fusion/test_ceiling.py -v`
Expected: PASS (all ceiling tests)

- [ ] **Step 5: Commit**

```bash
git add research/kalman_fusion/ceiling.py research/kalman_fusion/test_ceiling.py
git commit -m "research(kalman): directional counterfactual + per-signal oracle"
```

---

### Task 6: Ceiling aggregation (`ceiling_report`) — box-native vs oracle Pareto points

**Files:**
- Modify: `research/kalman_fusion/ceiling.py` (add `ceiling_report`)
- Modify: `research/kalman_fusion/test_ceiling.py` (add test)

**Interfaces:**
- Consumes: `eligible_dropped`, `signal_outcomes`, `rig.evaluate`, `metrics.summarize`, `counterfactual_pause.champion_taken_trades`.
- Produces: `ceiling_report(C) -> dict` with, per stratum (`all`, and each of `vol_gated`/`vetoed`/`confirm<K`): the count, the **box-native** admit outcome (admit ALL dropped in their box direction) and the **oracle** admit outcome (best direction per signal), each as a `Metrics`-like dict at 100% admit; plus the champion baseline point. This yields the extreme (75%→100% admit) end of the Pareto front and the payoff at the ceiling.

- [ ] **Step 1: Write the failing test**

```python
# add to research/kalman_fusion/test_ceiling.py
from research.kalman_fusion.ceiling import ceiling_report


def test_ceiling_report_structure_and_bounds():
    C = cp.load_champion("4h")
    rep = ceiling_report(C)
    assert "champion" in rep and "all" in rep
    base = rep["champion"]; allc = rep["all"]
    # champion baseline entry-rate is the low-admit anchor
    assert 0.0 < base["entry_rate"] < 0.5
    # admitting ALL dropped signals pushes entry-rate toward 1.0
    assert allc["oracle"]["entry_rate"] > base["entry_rate"]
    # oracle total P/L >= box-native total P/L (best-direction dominates)
    assert allc["oracle"]["total_pnl"] >= allc["native"]["total_pnl"] - 1e-6
    # per-reason strata present
    for r in ("vol_gated", "vetoed", "confirm<K"):
        assert r in rep
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest research/kalman_fusion/test_ceiling.py::test_ceiling_report_structure_and_bounds -v`
Expected: FAIL with `ImportError: cannot import name 'ceiling_report'`

- [ ] **Step 3: Add the implementation to `ceiling.py`**

```python
# append to research/kalman_fusion/ceiling.py
from research.kalman_fusion.metrics import summarize


def _point(pnls, n_eligible):
    m = summarize(pnls, n_eligible=n_eligible)
    return {"n_entries": m.n_entries, "n_eligible": m.n_eligible, "entry_rate": m.entry_rate,
            "payoff": m.payoff, "total_pnl": m.total_pnl, "win_rate": m.win_rate,
            "pf": m.pf, "expectancy": m.expectancy, "max_dd": m.max_dd}


def ceiling_report(C) -> dict:
    ed = eligible_dropped(C)
    n_elig = ed["n_eligible"]
    taken = cp.champion_taken_trades(C)
    champ_pnls = [t["pnl_points"] * C["pv"] for t in taken]

    def stratum(idxs):
        o = signal_outcomes(C, idxs)
        # box-native = the champion's own box direction per signal (sign of sig[idx-1])
        native_box = []
        for k, i in enumerate(idxs):
            s = int(np.sign(C["sig"][i - 1]))
            v = o["native"][k] if s >= 0 else o["opposite"][k]   # +1 sim vs -1 sim
            if not np.isnan(v):
                native_box.append(float(v))
        oracle = [float(v) for v in o["oracle"] if not np.isnan(v)]
        # admitting these dropped signals ON TOP of the champion's taken trades:
        native_all = champ_pnls + native_box
        oracle_all = champ_pnls + oracle
        return {"n_dropped": len(idxs),
                "native": _point(native_all, n_elig),
                "oracle": _point(oracle_all, n_elig)}

    rep = {"champion": _point(champ_pnls, n_elig),
           "all": stratum(ed["idxs"])}
    for r, idxs in ed["by_reason"].items():
        rep[r] = stratum(idxs)
    return rep
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest research/kalman_fusion/test_ceiling.py -v`
Expected: PASS (all ceiling tests)

- [ ] **Step 5: Commit**

```bash
git add research/kalman_fusion/ceiling.py research/kalman_fusion/test_ceiling.py
git commit -m "research(kalman): M0 ceiling aggregation (box-native vs oracle strata)"
```

---

### Task 7: CLI + run the NQ 4h ceiling on the server + write the study doc + decision gate

**Files:**
- Create: `research/kalman_fusion/run_ceiling.py`
- Create: `docs/RESEARCH_KALMAN_FUSION_STUDY.md` (findings + gate decision)

**Interfaces:**
- Consumes: `ceiling.ceiling_report`, `counterfactual_pause.load_champion`.
- Produces: a CLI `python3 -m research.kalman_fusion.run_ceiling --tf 4h --out <csv>` that prints the ceiling table and writes a CSV; and the study markdown with the M0 result + the go/no-go decision.

- [ ] **Step 1: Write the CLI**

```python
# research/kalman_fusion/run_ceiling.py
"""Compute + print the M0 ceiling for a champion (default NQ 4h). Read-only; heavy run → server."""
from __future__ import annotations
import argparse, csv
import research.kalman_fusion  # noqa: F401
from optimize import counterfactual_pause as cp
from research.kalman_fusion.ceiling import ceiling_report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="4h")
    ap.add_argument("--out", default="research/kalman_fusion/ceiling_4h.csv")
    a = ap.parse_args()
    C = cp.load_champion(a.tf)
    rep = ceiling_report(C)
    rows = []
    print(f"{'stratum':12} {'n_drop':>7} {'variant':8} {'entry%':>7} {'payoff':>7} {'totalP/L':>12} {'win%':>6}")
    for key in ("champion", "all", "vol_gated", "vetoed", "confirm<K"):
        blk = rep[key]
        if key == "champion":
            p = blk
            print(f"{key:12} {'-':>7} {'base':8} {100*p['entry_rate']:6.1f}% {p['payoff']:7.2f} {p['total_pnl']:12,.0f} {100*p['win_rate']:5.1f}%")
            rows.append(dict(stratum=key, variant="base", **{k: p[k] for k in ("entry_rate","payoff","total_pnl","win_rate","n_entries")}))
            continue
        for variant in ("native", "oracle"):
            p = blk[variant]
            print(f"{key:12} {blk['n_dropped']:7} {variant:8} {100*p['entry_rate']:6.1f}% {p['payoff']:7.2f} {p['total_pnl']:12,.0f} {100*p['win_rate']:5.1f}%")
            rows.append(dict(stratum=key, variant=variant, n_dropped=blk["n_dropped"],
                             **{k: p[k] for k in ("entry_rate","payoff","total_pnl","win_rate","n_entries")}))
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r}))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Verify locally that the CLI imports and runs on a fast smoke (small, read-only — OK locally)**

Run: `python3 -c "import research.kalman_fusion.run_ceiling as r; print('import ok')"`
Expected: `import ok`

- [ ] **Step 3: Run the full NQ 4h ceiling ON THE SERVER**

Run (from the subproject root, targeting the server):
```bash
rsync -az -e "ssh -o BatchMode=yes" research/kalman_fusion/ amd-trading:/home/dev/Mulham/wsg-i/Parametric-Indicators/research/kalman_fusion/
ssh amd-trading 'cd /home/dev/Mulham/wsg-i/Parametric-Indicators && source /home/dev/Mulham/.venv/bin/activate && export WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data && python3 -m research.kalman_fusion.run_ceiling --tf 4h --out research/kalman_fusion/ceiling_4h.csv'
```
Expected: a printed table with `champion` (entry% ≈ 20–26%, its payoff) and `all/oracle` (entry% → high, payoff at the ceiling). Pull the CSV back with `rsync` for the doc.

- [ ] **Step 4: Write `docs/RESEARCH_KALMAN_FUSION_STUDY.md` with the M0 result + the gate decision**

Fill the actual numbers from Step 3 into this skeleton (a Mermaid diagram for the front; no ASCII):

```markdown
# Kalman / signal-fusion study — results

Extends docs/RESEARCH_SIGNAL_FUSION_KALMAN.md. Design: docs/superpowers/specs/2026-07-01-kalman-signal-fusion-study-design.md.

## M0 — the ceiling (NQ 4h champion)

Baseline champion: entry-rate <X>%, payoff <P>, total P/L $<PL>.

| stratum | dropped n | variant | entry-rate | payoff | total P/L |
|---|--:|---|--:|--:|--:|
| champion | – | base | <..> | <..> | <..> |
| all | <..> | box-native | <..> | <..> | <..> |
| all | <..> | oracle | <..> | <..> | <..> |
| vol_gated | <..> | oracle | <..> | <..> | <..> |
| vetoed | <..> | oracle | <..> | <..> | <..> |
| confirm<K | <..> | oracle | <..> | <..> | <..> |

## Decision gate

- If **oracle** payoff at high entry-rate stays **≥ champion payoff** with materially higher total P/L
  → the dropped flow IS rescuable; **proceed to M1/M2/M3** (each its own plan).
- If **oracle** payoff collapses below the champion floor even with a perfect director
  → admitting more cannot hold payoff; **stop** and record that no filter sophistication can rescue it.
- Note the **native vs oracle gap** = the maximum a perfect DIRECTOR (M1/M2) could add; the
  **per-reason strata** show WHERE the rescuable flow lives (vol-gated vs vetoed vs confirm<K).
```

- [ ] **Step 5: Verify golden gate untouched (off-path safety) + commit**

Run: `python3 perf/check_golden.py`
Expected: 6/6 PASS, byte-identical (the research package cannot affect it).

```bash
git add research/kalman_fusion/run_ceiling.py research/kalman_fusion/ceiling_4h.csv docs/RESEARCH_KALMAN_FUSION_STUDY.md
git commit -m "research(kalman): M0 ceiling CLI + NQ 4h result + study doc + gate decision"
```

---

## Roadmap (Phases 2–5 — GATED on M0; each becomes its own plan)

These are intentionally **not** expanded into bite-sized tasks yet: their exact design depends on M0's stratification (which dropped sub-population is rescuable, and how much a perfect director vs better timing would add). Once Task 7's decision gate says "proceed," each mechanism gets its own spec-lite → plan.

- **Phase 2 — M1 champion-signal fusion.** Loader switches to `l2.l1_runner.run_l1` per champion to collect the multi-TF/multi-layer/instrument signal streams; Kalman/factor fusion → consensus direction+conviction; `DecisionPolicy` → `rig.evaluate`; sweep θ → IS/OOS Pareto front. **Adds a mandatory causality-guard test** (input-truncation) for the fusion estimator.
- **Phase 3 — M2 price/trend state.** Local-level+trend Kalman (+ adaptive/EKF/UKF relatives, climbed only on evidence) → re-direct/re-time via the `entry_resolver` hook; Pareto front.
- **Phase 4 — M3 vol/regime state.** Own-price HMM / adaptive-vol Kalman (causal filtered posterior) → conditional admit + regime-scaled exits; report the **increment over the existing HAR-RV gate**.
- **Phase 5 — Track-A synthesis + recommendation** and generalization of the winner to ES/QQQ/SQQQ.

---

## Self-review

- **Spec coverage:** Phase 1 covers the spec's shared rig (Task 3), signal universe/eligibility (Task 4), M0 ceiling incl. native/opposite/oracle + per-reason strata (Tasks 5–6), IS/OOS is deferred to the mechanism phases (M0 is a full-period ceiling by design), server-only compute (Task 7), and golden-off-path safety (Task 7). M1/M2/M3 + Track-A are the gated roadmap, matching the spec's M0-gates-the-rest structure.
- **Placeholder scan:** the only "fill-in" is Task 7 Step 4, where real measured numbers replace `<..>` — that is data produced by Step 3, not an unwritten step. No `TODO`/`TBD` in code.
- **Type consistency:** `evaluate(C, admit, direction=None) -> Metrics` used consistently; `Metrics` fields match `summarize`; `simulate_dir(...) -> float|None`, `signal_outcomes(...) -> {native,opposite,oracle}`, `ceiling_report(...) -> {champion, all, <reason>...}` used consistently across Tasks 5–7. `_bt_args` unpacking order matches `counterfactual_pause` verbatim.
- **Parity/safety:** rig P/L is engine-computed and anchored to the champion (Task 3); golden verified (Task 7).
```
