# End-of-Day Exit Cap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-layer `cap_mode` (`none|bars|eod`); the new `eod` mode force-closes an open trade at its trading-day end (full days N min before the 17:00 close, default 15; partial days exactly at the session's last bar).

**Architecture:** Approach A — a pure `optimize/trading_days.py` classifier emits per-1min-bar EOD target indices; both engines consume the same arrays as a 5th earliest-wins exit candidate (`END_OF_DAY`), so they stay trade-for-trade identical. Threads through the existing `cap_1min` seams. Default-off path byte-identical (golden safe).

**Tech Stack:** Python 3 (numpy, pandas), vanilla JS dashboard, pytest, Playwright.

## Global Constraints

- **No behaviour change when off.** `cap_mode` defaults to `"none"`; `perf/check_golden.py` must stay ✅ ALL MATCH.
- **Two engines byte-identical** (`optimize/test_fast_parity.py`) — both consume the SAME `trading_days.eod_targets(...)` output.
- **Interpreter `python3`**; activate venv if present (`[ -d .venv ] && source .venv/bin/activate`); run from `/mnt/data/projects/trading/subprojects/Parametric-Indicators`.
- **Data anchors (NQ 4h-aligned 1-min):** 342 full sessions, 14 partial, 1 abnormal (truncated tail); full days end 16:59 (no 17:00 bar); the 16:45 bar exists on 100% of full days.
- **Param model:** `cap_mode: str="none"`, `eod_margin_min: int=15`, `cap_1min: int=0` (unchanged, used only when `mode=bars`). A bare `cap_1min>0` with no mode normalises to `bars`.
- **Exit reason** `END_OF_DAY`; fill = exit bar's **close**. Precedence lowest: hard-SL ▸ hard-TP ▸ soft-SL ▸ (bars|eod).
- Commit footer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

### Task E1: Trading-day classifier

**Files:**
- Create: `optimize/trading_days.py`
- Test: `optimize/test_trading_days.py`

**Interfaces:**
- Consumes: `optimize.signals._box_dates_vec(DatetimeIndex) -> DatetimeIndex` (session key); `optimize.data.load_inputs("4h") -> (df_dec, df1, box, vf, n_split)`.
- Produces: `trading_days.eod_targets(m_dates: np.ndarray, margin_min: int) -> tuple[np.ndarray, np.ndarray]` → `(eod_target, session_last)`, both int64 len(m_dates), global 1-min indices. `eod_target[i] = -1` for abnormal sessions.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_trading_days.py
"""trading_days.eod_targets — per-1min-bar end-of-day exit targets, locked to the data study anchors."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd
from optimize import trading_days, data as data_mod
from optimize.signals import _box_dates_vec


def _md():
    _, df1, _, _, _ = data_mod.load_inputs("4h")
    return df1["Date"].to_numpy()


def test_eod_targets_anchors():
    md = _md()
    et, sl = trading_days.eod_targets(md, 15)
    assert et.shape == md.shape == sl.shape
    ts = pd.DatetimeIndex(md)
    tod = (ts.hour * 60 + ts.minute).to_numpy()
    box = pd.DatetimeIndex(_box_dates_vec(ts)).asi8
    starts = np.concatenate(([0], np.flatnonzero(np.diff(box)) + 1))
    ends = np.concatenate((np.flatnonzero(np.diff(box)) + 1, [len(md)]))
    last_tod = tod[ends - 1]
    targets = et[starts]                                   # one target per session
    n_full = int(((last_tod >= 16 * 60 + 55) & (last_tod <= 17 * 60 + 5)).sum())
    n_partial = int((last_tod < 16 * 60).sum())
    n_abnormal = int((targets < 0).sum())
    assert n_full == 342 and n_partial == 14 and n_abnormal == 1
    # every FULL-day target lands on the 16:45 bar (1005 min)
    full_mask = (last_tod >= 16 * 60 + 55) & (last_tod <= 17 * 60 + 5)
    assert set(tod[targets[full_mask]].tolist()) == {16 * 60 + 45}
    # every PARTIAL-day target is that session's last bar
    part_mask = last_tod < 16 * 60
    assert np.array_equal(targets[part_mask], (ends - 1)[part_mask])
    # session_last is always >= the bar index, and constant within a session
    assert (sl >= np.arange(len(md))).all() or (sl[starts] == ends - 1).all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_trading_days.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'optimize.trading_days'`

- [ ] **Step 3: Write minimal implementation**

```python
# optimize/trading_days.py
"""Trading-day calendar for the end-of-day exit cap. Sessions follow the box-date rule (hour>=18 ->
next day), matching the engine's day mapping. Pure; no engine state."""
from __future__ import annotations

import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
import pandas as pd


def eod_targets(m_dates: np.ndarray, margin_min: int) -> tuple[np.ndarray, np.ndarray]:
    """(eod_target, session_last) per 1-min bar (global indices). Full day: last bar with
    time <= 17:00-margin. Partial (last bar < 16:00): the session's last bar. Abnormal: -1."""
    from optimize.signals import _box_dates_vec
    n = len(m_dates)
    if n == 0:
        return np.array([], dtype=np.int64), np.array([], dtype=np.int64)
    ts = pd.DatetimeIndex(m_dates)
    tod = (ts.hour * 60 + ts.minute).to_numpy()
    box = pd.DatetimeIndex(_box_dates_vec(ts)).asi8
    starts = np.concatenate(([0], np.flatnonzero(np.diff(box)) + 1))
    ends = np.concatenate((np.flatnonzero(np.diff(box)) + 1, [n]))
    eod_target = np.full(n, -1, dtype=np.int64)
    session_last = np.zeros(n, dtype=np.int64)
    cutoff_full = 17 * 60 - int(margin_min)
    for lo, hi in zip(starts, ends):
        last = hi - 1
        session_last[lo:hi] = last
        last_tod = tod[last]
        if 16 * 60 + 55 <= last_tod <= 17 * 60 + 5:          # full day
            seg = tod[lo:hi]
            ok = np.flatnonzero(seg <= cutoff_full)
            eod_target[lo:hi] = (lo + int(ok[-1])) if ok.size else last
        elif last_tod < 16 * 60:                              # partial / early close
            eod_target[lo:hi] = last
        else:                                                 # abnormal (truncated tail)
            eod_target[lo:hi] = -1
    return eod_target, session_last
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_trading_days.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add optimize/trading_days.py optimize/test_trading_days.py
git commit -m "feat(eod): trading-day classifier — per-bar end-of-day exit targets

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task E2: fast_engine END_OF_DAY candidate

**Files:**
- Modify: `optimize/fast_engine.py:29-32` (reason codes), `:50-57` (signature), `:121-136` (candidate assembly)
- Test: `optimize/test_eod_cap.py`

**Interfaces:**
- Consumes: `trading_days.eod_targets`.
- Produces: `fast_backtest(..., cap_1min=0, cap_mode="none", eod_target=None, session_last=None)` emits trades with `exit_reason == "END_OF_DAY"` when `cap_mode=="eod"`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_eod_cap.py
"""END_OF_DAY exit-cap behaviour in fast_backtest (synthetic single session)."""
import sys
from pathlib import Path

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))

import numpy as np
from optimize.fast_engine import fast_backtest


def test_eod_exits_at_session_target_bar():
    # 1 decision bar at t0; 6 one-minute bars; SL/TP far away so only EOD can fire.
    d_dates = np.array([0], dtype="int64").astype("datetime64[s]")
    d_close = np.array([100.0])
    sig = np.array([1], dtype=np.int64)
    m_dates = np.arange(0, 360, 60).astype("datetime64[s]")     # 6 bars
    m = np.full(6, 100.0)
    eod_target = np.array([3, 3, 3, 3, 3, 3], dtype=np.int64)   # session target = bar index 3
    session_last = np.array([5, 5, 5, 5, 5, 5], dtype=np.int64)
    tr = fast_backtest(d_dates, d_close, sig, None, m_dates, m, m, m,
                       sl_soft=50, sl_hard=90, tp=90, flip=False,
                       cap_mode="eod", eod_target=eod_target, session_last=session_last)
    assert len(tr) == 1 and tr[0]["exit_reason"] == "END_OF_DAY"
    # entry slice index e=0, target slice index = 3 -> exit at m_dates[3]
    assert np.datetime64(tr[0]["exit_time"]) == m_dates[3]


def test_eod_off_by_default_no_exit():
    d_dates = np.array([0], dtype="int64").astype("datetime64[s]")
    sig = np.array([1], dtype=np.int64)
    m_dates = np.arange(0, 360, 60).astype("datetime64[s]")
    m = np.full(6, 100.0)
    tr = fast_backtest(d_dates, np.array([100.0]), sig, None, m_dates, m, m, m,
                       sl_soft=50, sl_hard=90, tp=90, flip=False)
    assert tr == []          # no cap, SL/TP never hit -> OPEN -> dropped
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest optimize/test_eod_cap.py -q`
Expected: FAIL with `TypeError: fast_backtest() got an unexpected keyword argument 'cap_mode'`

- [ ] **Step 3: Write minimal implementation**

In `optimize/fast_engine.py`, extend the reason codes (line 29-32):

```python
R_SL_HARD, R_TP_HARD, R_SL_SOFT, R_TP_SOFT, R_TIME_CAP, R_END_OF_DAY = 0, 1, 2, 3, 4, 5
REASON_NAME = {R_SL_HARD: "STOP_LOSS_HARD", R_TP_HARD: "TAKE_PROFIT_HARD",
               R_SL_SOFT: "STOP_LOSS_SOFT", R_TP_SOFT: "TAKE_PROFIT_SOFT",
               R_TIME_CAP: "TIME_CAP", R_END_OF_DAY: "END_OF_DAY"}
```

Extend the signature (line 57 — append after `cap_1min: int = 0`):

```python
                  short_tp: float | None = None, cap_1min: int = 0,
                  cap_mode: str = "none",
                  eod_target: np.ndarray | None = None,
                  session_last: np.ndarray | None = None) -> list[dict]:
```

Replace the `t_cap`/`order` block (lines 125-127) with:

```python
        # back-compat: a bare cap_1min (existing tests/golden) is the bars cap.
        mode = "bars" if (cap_mode == "none" and cap_1min) else cap_mode
        if mode == "eod" and eod_target is not None:
            g = int(eod_target[e])
            if g < 0:
                t_cap = -1
            else:
                if g < e:
                    g = int(session_last[e])
                t_cap = (g - e) if 0 <= (g - e) < len(cl) else -1
            cap_reason = R_END_OF_DAY
        else:
            t_cap = (cap_1min - 1) if (cap_1min and 0 <= cap_1min - 1 < len(cl)) else -1
            cap_reason = R_TIME_CAP
        order = [(t_slh, R_SL_HARD, slh_line), (t_tph, R_TP_HARD, tph_line),
                 (t_soft, R_SL_SOFT, None), (t_cap, cap_reason, None)]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest optimize/test_eod_cap.py optimize/test_time_cap.py -q`
Expected: PASS (existing time-cap tests still green via the back-compat normalisation)

- [ ] **Step 5: Commit**

```bash
git add optimize/fast_engine.py optimize/test_eod_cap.py
git commit -m "feat(eod): fast_engine END_OF_DAY candidate (cap_mode + eod target)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task E3: engine.py walk + params + parity

**Files:**
- Modify: `engine.py:94` (params), `engine.py:240-260` (precompute eod arrays), `engine.py:270-335` (walk branch), entry block (capture entry global index)
- Test: `optimize/test_fast_parity.py:88-107` (add an eod case)

**Interfaces:**
- Consumes: `trading_days.eod_targets`; `SimpleStrategyParams.cap_mode`, `.eod_margin_min`.
- Produces: `engine.py` emits `END_OF_DAY` trades identical to `fast_backtest` under `cap_mode="eod"`.

- [ ] **Step 1: Write the failing test (parity eod case)**

Append inside the cap-parity loop in `optimize/test_fast_parity.py` (after the existing two cap cases, mirror their structure). Add an `eod` case that builds the eod arrays and passes them to fast:

```python
    # END_OF_DAY parity: engine must match fast trade-for-trade with cap_mode='eod', and EOD must fire.
    from optimize import trading_days
    et, sl_arr = trading_days.eod_targets(MD, 15)
    sp = SimpleStrategyParams(sl_soft_points=60, sl_hard_points=120, tp_hard_points=150,
                              data_path_4h="", data_path_1min="", box_data_path="",
                              flip_entry_direction=False, cap_mode="eod", eod_margin_min=15)
    E0, _ = SimpleStrategy(sp).backtest(df, df1, box, entry_gate=gate(0))
    E = [t for t in E0 if t.get("exit_reason") not in (None, "OPEN")]
    F = fast_backtest(DD, DC, sig_int, gate(0), MD, MH, ML, MC, 60, 120, 150, False,
                      cap_mode="eod", eod_target=et, session_last=sl_arr)
    diffs = sum(1 for e, f in zip(E, F)
                if pd.Timestamp(e["entry_time"]) != pd.Timestamp(f["entry_time"])
                or e["direction"] != f["direction"] or e["exit_reason"] != f["exit_reason"]
                or pd.Timestamp(e["exit_time"]) != pd.Timestamp(f["exit_time"])
                or abs(e["pnl_points"] - f["pnl_points"]) > 1e-6)
    ok = len(E) == len(F) and diffs == 0 and any(t["exit_reason"] == "END_OF_DAY" for t in F)
    print(f"{'eod g0 60/120/150':24} engine={len(E):4} fast={len(F):4} mismatch={diffs:3}  {'OK' if ok else 'FAIL'}")
    assert ok
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 optimize/test_fast_parity.py 2>&1 | tail -5`
Expected: FAIL — `SimpleStrategyParams` has no `cap_mode` (TypeError), or engine emits no `END_OF_DAY`.

- [ ] **Step 3: Implement engine.py**

Add fields to `SimpleStrategyParams` (after `cap_1min: int = 0` at engine.py:94):

```python
    cap_mode: str = "none"        # none | bars | eod
    eod_margin_min: int = 15      # minutes before 17:00 close to exit on full days (eod mode)
```

In `backtest(...)`, where the 1-min arrays are prepared (near engine.py:248, after `md_arr = ts_1m_arr`), precompute the eod arrays once:

```python
            if self.params.cap_mode == "eod":
                from optimize.trading_days import eod_targets
                eod_target_arr, session_last_arr = eod_targets(md_arr, self.params.eod_margin_min)
            else:
                eod_target_arr = session_last_arr = None
```

Capture the entry global 1-min index on the open trade. In the entry block where `open_trade = {...}` is built (the dict with `'entry_time'`, `'entry_price'`, ...), add `'entry_e': int(start_1m[idx])` — `start_1m[idx]` is the first 1-min bar of the entry decision bar `idx`, which equals the walk's first at/after-entry bar (`idx` is the decision-bar loop variable in scope here; `start_1m` was built near engine.py:242).

In `_walk_exit_for_4h`, add `eod_target_arr`/`session_last_arr` to the `nonlocal`/closure scope, and after the existing `bars_held >= cap` TIME_CAP branch (engine.py:325-326) add:

```python
                if exit_reason is None and self.params.cap_mode == "eod" and eod_target_arr is not None:
                    e0 = open_trade['entry_e']
                    eg = int(eod_target_arr[e0])
                    if eg >= 0:
                        if eg < e0:
                            eg = int(session_last_arr[e0])
                        if t >= eg:
                            exit_reason, fill, resets_counter = 'END_OF_DAY', m_close, True
```

Add `'END_OF_DAY'` to the `ExitReason` Literal (engine.py:54-61).

- [ ] **Step 4: Run to verify parity passes**

Run: `python3 optimize/test_fast_parity.py 2>&1 | tail -6`
Expected: all cases `OK`, including `eod g0 60/120/150`, ending `FAST-PARITY OK ✓`.

- [ ] **Step 5: Commit**

```bash
git add engine.py optimize/test_fast_parity.py
git commit -m "feat(eod): engine.py walk END_OF_DAY branch + cap_mode params (parity)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task E4: Thread cap_mode / eod_margin_min through layers + payload

**Files:**
- Modify: `optimize/l2/payload.py:160` (`validate_layer_params`), `:324` (`_layer_from_strategy`); `optimize/l2/l1_runner.py:173-180` (fast call); `optimize/l2/engine.py:114-120` (fast call)
- Test: `optimize/l2/test_logbook.py` (an eod run produces END_OF_DAY rows)

**Interfaces:**
- Consumes: `trading_days.eod_targets`; layer params dict with `cap_mode`, `eod_margin_min`.
- Produces: `run_l1`/`run_l2` pass `cap_mode`, `eod_target`, `session_last` into `fast_backtest`; causal log carries `exit_reason == "END_OF_DAY"`.

- [ ] **Step 1: Write the failing test**

```python
# add to optimize/l2/test_logbook.py
def test_cap_mode_eod_produces_end_of_day_exits():
    from optimize.l2 import logbook, payload
    p = dict(payload.l1_default_params("4h"), cap_mode="eod", eod_margin_min=15)
    res = logbook.run_causal(p, dict(payload.PERMISSIVE), "4h")
    reasons = {r.exit_reason for r in res.log if r.decision == "entry"}
    assert "END_OF_DAY" in reasons
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_cap_mode_eod_produces_end_of_day_exits -q`
Expected: FAIL — no `END_OF_DAY` (params not threaded).

- [ ] **Step 3: Implement threading**

`validate_layer_params` (payload.py:160) — after the `cap_1min` line add:

```python
    p["cap_mode"] = str(p.get("cap_mode") or "none")
    if p["cap_mode"] == "none" and int(p.get("cap_1min") or 0) > 0:
        p["cap_mode"] = "bars"
    p["eod_margin_min"] = int(num("eod_margin_min", 15)) if p.get("eod_margin_min") not in (None, "") else 15
```

`_layer_from_strategy` (payload.py:324) — beside the `cap_1min` extraction add:

```python
        "cap_mode": sp.get("cap_mode", "none") or "none",
        "eod_margin_min": int(sp.get("eod_margin_min", 15) or 15),
```

`l1_runner.run_l1` (l1_runner.py:173-180) — before the `fast_backtest(` call, build the eod arrays once and pass them:

```python
    _cap_mode = str(params.get("cap_mode") or "none")
    if _cap_mode == "eod":
        from optimize.trading_days import eod_targets
        _eod_t, _eod_sl = eod_targets(df1["Date"].to_numpy(), int(params.get("eod_margin_min", 15) or 15))
    else:
        _eod_t = _eod_sl = None
```

and add to the `fast_backtest(...)` kwargs:

```python
        cap_1min=int(params.get("cap_1min", 0) or 0),
        cap_mode=_cap_mode, eod_target=_eod_t, session_last=_eod_sl,
```

`engine.run_l2` (engine.py:114-120) — mirror it using the L2 frame `l1.df1["Date"]`:

```python
    _cap_mode = str(l2_params.get("cap_mode") or "none")
    if _cap_mode == "eod":
        from optimize.trading_days import eod_targets
        _eod_t, _eod_sl = eod_targets(l1.df1["Date"].to_numpy(), int(l2_params.get("eod_margin_min", 15) or 15))
    else:
        _eod_t = _eod_sl = None
```

and add `cap_mode=_cap_mode, eod_target=_eod_t, session_last=_eod_sl` to that `fast_backtest(...)` call.

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_cap_mode_eod_produces_end_of_day_exits -q`
Expected: PASS

- [ ] **Step 5: Golden gate (default-off unchanged)**

Run: `python3 perf/check_golden.py 2>&1 | tail -2`
Expected: `✅ ALL GOLDEN BASELINES MATCH`

- [ ] **Step 6: Commit**

```bash
git add optimize/l2/payload.py optimize/l2/l1_runner.py optimize/l2/engine.py optimize/l2/test_logbook.py
git commit -m "feat(eod): thread cap_mode/eod_margin_min through L1/L2 + causal log

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task E5: Taxonomy END_OF_DAY leaf + win/loss

**Files:**
- Modify: `optimize/l2/taxonomy.py:18` (`_EXIT_KEYS`), `:31-40` (`_exit_boxes`), `:_COMBINED_LEAVES`
- Test: `optimize/l2/test_taxonomy.py`

**Interfaces:**
- Produces: taxonomy gains `end_of_day_exit`, `end_of_day_win`, `end_of_day_loss`; exit-partition invariant includes `end_of_day`.

- [ ] **Step 1: Write the failing test**

```python
# add to optimize/l2/test_taxonomy.py
def test_eod_exit_leaves_and_partition():
    import json
    p = dict(payload.l1_default_params(_TF), cap_mode="eod", eod_margin_min=15)
    res = logbook.run_causal(p, dict(payload.PERMISSIVE), _TF)
    t = taxonomy.taxonomy_l1(res)
    exits = ["tp_exit", "sl_soft_exit", "sl_hard_exit", "time_cap_exit", "end_of_day_exit"]
    assert sum(t[k]["count"] for k in exits) == t["entered"]["count"]
    assert t["end_of_day_exit"]["count"] > 0
    assert t["end_of_day_win"]["count"] + t["end_of_day_loss"]["count"] == t["end_of_day_exit"]["count"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py::test_eod_exit_leaves_and_partition -q`
Expected: FAIL with `KeyError: 'end_of_day_exit'`

- [ ] **Step 3: Implement**

`_EXIT_KEYS` (taxonomy.py:18) — add the EOD entry:

```python
_EXIT_KEYS = {"TAKE_PROFIT_HARD": "tp_exit", "STOP_LOSS_SOFT": "sl_soft_exit",
              "STOP_LOSS_HARD": "sl_hard_exit", "TIME_CAP": "time_cap_exit",
              "END_OF_DAY": "end_of_day_exit"}
```

In `_exit_boxes`, add an EOD win/loss accumulator mirroring `time_cap_win/loss`:

```python
    tcw = [0, 0.0]; tcl = [0, 0.0]
    eodw = [0, 0.0]; eodl = [0, 0.0]
    for r in entries:
        k = r.exit_reason
        if k in agg:
            agg[k][0] += 1; agg[k][1] += r.pnl
        if k == "TIME_CAP":
            (tcw if r.pnl > 0 else tcl)[0] += 1
            (tcw if r.pnl > 0 else tcl)[1] += r.pnl
        if k == "END_OF_DAY":
            (eodw if r.pnl > 0 else eodl)[0] += 1
            (eodw if r.pnl > 0 else eodl)[1] += r.pnl
    out = {name: _box(agg[k][0], agg[k][1]) for k, name in _EXIT_KEYS.items()}
    out["time_cap_win"] = _box(tcw[0], tcw[1]); out["time_cap_loss"] = _box(tcl[0], tcl[1])
    out["end_of_day_win"] = _box(eodw[0], eodw[1]); out["end_of_day_loss"] = _box(eodl[0], eodl[1])
    return out
```

Add the EOD leaves to `_COMBINED_LEAVES`:

```python
_COMBINED_LEAVES = ("entered", "tp_exit", "sl_soft_exit", "sl_hard_exit",
                    "time_cap_exit", "time_cap_win", "time_cap_loss",
                    "end_of_day_exit", "end_of_day_win", "end_of_day_loss", "l1_entry_exit")
```

- [ ] **Step 4: Run to verify it passes**

Run: `python3 -m pytest optimize/l2/test_taxonomy.py -q`
Expected: PASS (all taxonomy tests, including the existing partition tests now that EOD is in the exit set)

- [ ] **Step 5: Commit**

```bash
git add optimize/l2/taxonomy.py optimize/l2/test_taxonomy.py
git commit -m "feat(eod): taxonomy END_OF_DAY leaf + win/loss split + partition

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task E6: Dashboard cap-mode selector + EOD card

**Files:**
- Modify: `frontend/dashboard.html:82,117` (forms), `:167` (LAYER_FIELDS), `:172` (collectLayer), the taxonomy renderers (`_txL1`/`_txL2`/combined exits) + Totals
- Test: Playwright

**Interfaces:**
- Consumes: `meta.taxonomy.end_of_day_*`. New form ids `l1_cap_mode`/`l2_cap_mode`, `l1_eod_margin_min`/`l2_eod_margin_min`.

- [ ] **Step 1: Replace the Max-hold field with a mode selector (both L1 and L2)**

For L1 (line 82) replace the single `.fld` with:

```html
        <div class="fld" title="Exit cap: none · max N traded 1-min bars · end-of-trading-day (full days exit N min before the 17:00 close, partial days at the session close).">
          <label>Exit cap mode</label>
          <select id="l1_cap_mode" onchange="capModeToggle('l1')">
            <option value="none">none</option><option value="bars">max 1-min bars</option><option value="eod">end-of-day</option>
          </select></div>
        <div class="fld" id="l1_cap_bars_fld"><label>Max hold (traded 1-min bars)</label><input id="l1_cap_1min" type="number" step="1" min="0" value="0"></div>
        <div class="fld" id="l1_cap_eod_fld" style="display:none"><label>Exit N min before full-day close</label><input id="l1_eod_margin_min" type="number" step="1" min="0" value="15"></div>
```

Mirror for L2 (line 117) with `l2_` ids and `capModeToggle('l2')`.

- [ ] **Step 2: Add the toggle JS + thread the fields**

Near the other form helpers, add:

```javascript
function capModeToggle(pfx){ const m=$(pfx+'_cap_mode').value;
  $(pfx+'_cap_bars_fld').style.display = m==='bars' ? '' : 'none';
  $(pfx+'_cap_eod_fld').style.display  = m==='eod'  ? '' : 'none'; }
```

Extend `LAYER_FIELDS` (line 167):

```javascript
const LAYER_FIELDS=['sl_soft','sl_hard','tp','gate_pct','dd_limit','cooldown','k','cap_1min','cap_mode','eod_margin_min'];
```

In `collectLayer` (line 172) add (note `cap_mode` is a string, not `+`):

```javascript
    cap_1min:+v('cap_1min').value||0, cap_mode:v('cap_mode').value||'none', eod_margin_min:+v('eod_margin_min').value||15,
```

(Confirm `collectLayer`'s field reader handles a `<select>` — `v(id).value` works for both input and select. If a profile-apply path sets fields by id, it sets `.value` which also works for `<select>`.)

- [ ] **Step 3: Add END_OF_DAY taxonomy cards**

In `_txL1` (the "entered → exits" group) add after the time-cap card:

```javascript
  _txCard(t.end_of_day_exit,'end-of-day')+
```

and a new group after the time-cap win/loss group:

```javascript
  grp(pfx+' — end-of-day → win/loss')+
  _txCard(t.end_of_day_win,'end-of-day win')+
  _txCard(t.end_of_day_loss,'end-of-day loss')+
```

Mirror in `_txL2` and the combined `combined_exits` block (`ce.end_of_day_exit` / `_win` / `_loss`).

- [ ] **Step 4: Manual smoke (restart server, HTTP 200)**

```bash
pkill -f "server.py --port 8200"
```
```bash
nohup python3 server.py --port 8200 >/tmp/claude-1000/-mnt-data-projects-trading/1b0c327e-d5ba-4f42-a76c-a193dc4330d6/scratchpad/srv.log 2>&1 & disown
```
```bash
sleep 3; curl -s -o /dev/null -w "HTTP %{code}\n" http://localhost:8200/
```
Expected: `HTTP 200`.

- [ ] **Step 5: Playwright verify**

Write `/tmp/claude-1000/-mnt-data-projects-trading/1b0c327e-d5ba-4f42-a76c-a193dc4330d6/scratchpad/verify_eod.cjs`: load the page, set `#l1_cap_mode` to `eod`, assert `#l1_cap_eod_fld` becomes visible, click Run, wait for `VIEWS.l1`, assert `VIEWS.l1.meta.taxonomy.end_of_day_exit.count >= 0` and the cards text (lowercased) contains `end-of-day`, no pageerrors. Run:

```bash
node /tmp/claude-1000/-mnt-data-projects-trading/1b0c327e-d5ba-4f42-a76c-a193dc4330d6/scratchpad/verify_eod.cjs
```
Expected: visible-field toggle true, no console errors. (Retry once warm if the first run flakes on cold-start.)

- [ ] **Step 6: Commit**

```bash
git add frontend/dashboard.html
git commit -m "feat(eod): dashboard cap-mode selector (none/bars/eod) + END_OF_DAY cards

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task E7: Docs + final gate

**Files:**
- Modify: `docs/LOG_FIELDS.md`, `docs/PNL_EXPLAINED.md`

- [ ] **Step 1: Document the EOD cap**

Append to `docs/LOG_FIELDS.md` (after the TIME_CAP section) a paragraph: the `cap_mode` param (`none|bars|eod`), the `eod_margin_min` default 15, the trading-day rule (18→17 session; full → 16:45 / configurable; partial → session close; abnormal → none), the `END_OF_DAY` exit reason + taxonomy leaves, and that it's computed in `optimize/trading_days.py`, locked by `optimize/test_trading_days.py`.

Add a one-line pointer to `docs/PNL_EXPLAINED.md` exit-reason table: a row `| END_OF_DAY | open at the trading-day close cutoff (full: N min before 17:00; partial: session close) | that bar's close | trading_days.eod_targets |`.

- [ ] **Step 2: Final gate — affected suites + golden**

Run: `python3 -m pytest optimize/test_trading_days.py optimize/test_eod_cap.py optimize/l2/test_taxonomy.py optimize/l2/test_logbook.py -q 2>&1 | tail -3 && python3 optimize/test_fast_parity.py 2>&1 | tail -2 && python3 perf/check_golden.py 2>&1 | tail -2`
Expected: all pass; `FAST-PARITY OK ✓`; `✅ ALL GOLDEN BASELINES MATCH`.

- [ ] **Step 3: Commit**

```bash
git add docs/LOG_FIELDS.md docs/PNL_EXPLAINED.md
git commit -m "docs(eod): document end-of-day exit cap + trading-day calendar

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Completion

After E7, announce: "I'm using the finishing-a-development-branch skill to complete this work." and present the merge/PR/keep options (work is on `dev`).
