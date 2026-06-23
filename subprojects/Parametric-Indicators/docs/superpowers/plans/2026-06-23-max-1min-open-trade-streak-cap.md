# max-1min-open-trade-streak-cap (TIME_CAP exit) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-layer `cap_1min` parameter that force-closes an open trade at the Nth 1-minute bar's close as a new `TIME_CAP` exit when no SL/TP/soft-SL fired; `0` disables it (default), keeping results byte-identical.

**Architecture:** Model the cap as a 4th, lowest-priority exit candidate in BOTH engines — vectorized index in `optimize/fast_engine.py`, a per-trade bars-since-entry counter in `engine.py`'s 1-min walk — kept trade-for-trade identical by `test_fast_parity`. Thread `cap_1min` through the layer params; the new exit surfaces in the verbose log/CSV/dashboard automatically.

**Tech Stack:** Python 3 (numpy/pandas/dataclasses), pytest, vanilla-JS dashboard.

## Global Constraints

- **Default `cap_1min = 0` everywhere ⇒ no cap candidate ⇒ byte-identical.** `perf/check_golden.py` and the parity anchors must stay green with **no re-lock**.
- **Both engines stay trade-for-trade identical** (`optimize/test_fast_parity.py`), cap on and off.
- **Counting:** bar 1 = first 1-min bar with timestamp ≥ `entry_time`; TIME_CAP fires at the **close** of bar `N=cap_1min` if no higher-priority exit fired on bars 1..N. Precedence: hard-SL > hard-TP > soft-SL > TIME_CAP.
- **No change** to entry logic or the other exits.
- `cap_1min` is a **non-negative int**.

---

## File Structure

- `optimize/fast_engine.py` — **modify**: `R_TIME_CAP` constant + name; `cap_1min` arg; `t_cap` candidate appended to `order`.
- `engine.py` — **modify**: `'TIME_CAP'` in `ExitReason`; `cap_1min` field on `SimpleStrategyParams`; bars-since-entry counter + 4th check in `_walk_exit_for_4h`.
- `optimize/l2/l1_runner.py` — **modify**: pass `cap_1min` into `fast_backtest(...)`.
- `optimize/l2/engine.py` (L2) + `optimize/l2/payload.py` — **modify**: accept/thread `cap_1min` in layer params (`validate_layer_params`, `_layer_from_strategy`).
- `frontend/dashboard.html` — **modify**: "Max hold (1-min bars)" field in L1+L2 forms; `setLayer`/`collectLayer`; TIME_CAP chip styling.
- Tests: `optimize/test_fast_parity.py`, a new `optimize/test_time_cap.py`, `optimize/l2/test_logbook.py`.

---

## Task 1: fast_engine — TIME_CAP candidate

**Files:**
- Modify: `optimize/fast_engine.py` (reason consts ~line 29-31; `fast_backtest` signature ~49-56; candidate slice ~104-123)
- Test: `optimize/test_time_cap.py` (new)

**Interfaces:**
- Produces: `fast_backtest(..., cap_1min: int = 0)` — when `cap_1min>0`, a trade with no SL/TP/soft exit by bar `cap_1min` ends with `exit_reason="TIME_CAP"`, `exit_price` = close of that bar.

- [ ] **Step 1: Write the failing test**

```python
# optimize/test_time_cap.py
import sys; from pathlib import Path
_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path: sys.path.insert(0, str(_PI))
import numpy as np
from optimize.fast_engine import fast_backtest, signals_to_int

def _frames():
    # 3 decision bars; a long signal at bar0 → enter at d_close[0]=100 on bar1.
    d_dates = np.array([0, 60, 120], dtype="int64").astype("datetime64[s]")
    d_close = np.array([100.0, 100.0, 100.0])
    sig = np.array([1, 0, 0], dtype=np.int64)          # long signal at idx0 (read at idx1)
    # 1-min bars from entry: flat price 100 (never hits SL 90 / TP 110 / soft 95)
    m_dates = (np.arange(0, 600, 60)).astype("datetime64[s]")  # 10 one-min bars at/after entry
    m = np.full(10, 100.0)
    return d_dates, d_close, sig, m_dates, m

def test_time_cap_fires_at_nth_bar_close_long():
    d_dates, d_close, sig, m_dates, m = _frames()
    tr = fast_backtest(d_dates, d_close, sig, None, m_dates, m, m, m,
                       sl_soft=5, sl_hard=10, tp=10, flip=False, cap_1min=4)
    assert len(tr) == 1
    t = tr[0]
    assert t["exit_reason"] == "TIME_CAP"
    # bar 1 = m_dates[entry]; cap=4 → exit at the 4th bar (index 3 from entry)
    assert t["exit_price"] == 100.0
    assert t["pnl_points"] == 0.0

def test_cap_zero_is_disabled():
    d_dates, d_close, sig, m_dates, m = _frames()
    tr = fast_backtest(d_dates, d_close, sig, None, m_dates, m, m, m,
                       sl_soft=5, sl_hard=10, tp=10, flip=False, cap_1min=0)
    # no SL/TP/soft and no cap → trade never closes → OPEN dropped → no completed trade
    assert tr == []
```

- [ ] **Step 2: Run — expect FAIL** (`TypeError: unexpected keyword 'cap_1min'`)

Run: `python3 -m pytest optimize/test_time_cap.py -v`

- [ ] **Step 3: Add the reason constant + name** (fast_engine.py ~29-31)

```python
R_SL_HARD, R_TP_HARD, R_SL_SOFT, R_TP_SOFT, R_TIME_CAP = 0, 1, 2, 3, 4
REASON_NAME = {R_SL_HARD: "STOP_LOSS_HARD", R_TP_HARD: "TAKE_PROFIT_HARD",
               R_SL_SOFT: "STOP_LOSS_SOFT", R_TP_SOFT: "TAKE_PROFIT_SOFT",
               R_TIME_CAP: "TIME_CAP"}
```

- [ ] **Step 4: Add `cap_1min` to the signature** (after `short_tp` kwarg, ~line 56)

```python
                  short_tp: float | None = None, cap_1min: int = 0) -> list[dict]:
```

- [ ] **Step 5: Compute `t_cap` and append to `order`** (after the `t_soft` block ~line 118, before `order =`)

```python
        # time cap (task: max hold): the Nth 1-min bar from entry (bar 1 = slice index 0). Lowest priority.
        t_cap = (cap_1min - 1) if (cap_1min and 0 <= cap_1min - 1 < len(cl)) else -1
        order = [(t_slh, R_SL_HARD, slh_line), (t_tph, R_TP_HARD, tph_line),
                 (t_soft, R_SL_SOFT, None), (t_cap, R_TIME_CAP, None)]
```

(The existing earliest-index / lowest-rank selection makes TIME_CAP lose ties to SL/TP/soft — exactly the desired precedence. `line is None` ⇒ fill = `cl[t_cap]` = that bar's close.)

- [ ] **Step 6: Run — expect PASS**

Run: `python3 -m pytest optimize/test_time_cap.py -v`

- [ ] **Step 7: Commit**

```bash
git add optimize/fast_engine.py optimize/test_time_cap.py
git commit -m "feat(fast_engine): TIME_CAP exit candidate (cap_1min, lowest priority)"
```

---

## Task 2: engine.py — TIME_CAP in the 1-min walk + SimpleStrategyParams

**Files:**
- Modify: `engine.py` (`ExitReason` ~54-60; `SimpleStrategyParams` ~64-92; `_walk_exit_for_4h` ~267-328; the `nonlocal`/entry reset where `soft_consec_count = 0` ~475)
- Test: `optimize/test_fast_parity.py` (extend with a cap case)

**Interfaces:**
- Consumes: the cap semantics from Task 1 (must match trade-for-trade).
- Produces: `SimpleStrategyParams(..., cap_1min: int = 0)`; the engine emits `exit_reason='TIME_CAP'` identically to fast_engine.

- [ ] **Step 1: Add the parity case (failing test)** — append to `optimize/test_fast_parity.py`'s case list a `cap_1min` scenario. Find how the file builds `SimpleStrategyParams` + calls `fast_backtest` (it already iterates parameter cases) and add one with `cap_1min=20` (both engines), asserting `engine == fast` trade-for-trade and that at least one `TIME_CAP` appears.

```python
# in optimize/test_fast_parity.py — add to the cases (mirror an existing case dict, add cap_1min=20)
# and ensure both the SimpleStrategyParams construction and the fast_backtest(...) call pass cap_1min.
# Assert: engine trades == fast trades (entry/exit/reason/pnl) AND any(t.exit_reason=='TIME_CAP').
```

- [ ] **Step 2: Run — expect FAIL** (`SimpleStrategyParams` has no `cap_1min` / mismatch)

Run: `python3 optimize/test_fast_parity.py 4h`

- [ ] **Step 3: Add `'TIME_CAP'` to `ExitReason`** (engine.py ~54-60)

```python
ExitReason = Literal[
    'STOP_LOSS_HARD',
    'STOP_LOSS_SOFT',
    'TAKE_PROFIT_HARD',
    'TAKE_PROFIT_SOFT',
    'TIME_CAP',
    'OPEN',
]
```

- [ ] **Step 4: Add `cap_1min` to `SimpleStrategyParams`** (append at the END, after `short_tp_hard_points`, ~line 92)

```python
    cap_1min: int = 0   # max hold in 1-min bars; 0 = off. Force-close at the Nth bar close as TIME_CAP.
```

- [ ] **Step 5: Init the counter at entry** — find where `soft_consec_count = 0` is set on a new entry (~line 475) and the matching `nonlocal` in `_walk_exit_for_4h` (~271). Add a `bars_held` counter:

In `_walk_exit_for_4h`'s `nonlocal` line (271): add `, bars_held`.
At entry reset (~475, next to `soft_consec_count = 0`): add `bars_held = 0`.
Declare `bars_held = 0` wherever `soft_consec_count` is first declared at function scope (mirror it).
Read the cap once near the other line reads (~280): `cap = self.params.cap_1min` (confirm the param object is reachable as `self.params` — otherwise read it where `sl_soft_line` etc. come from).

- [ ] **Step 6: Increment + the 4th check** — inside the `for t in range(lo, hi)` loop, after the `if md_arr[t] < entry_time_np: continue` skip (so only at/after-entry bars count), increment, and after the soft-SL block add the cap check:

```python
            for t in range(lo, hi):
                if md_arr[t] < entry_time_np:
                    continue
                bars_held += 1
                ...
                # (existing hard-SL > hard-TP > soft-SL block sets exit_reason/fill) ...
                if exit_reason is None and cap > 0 and bars_held >= cap:
                    exit_reason, fill, resets_counter = 'TIME_CAP', m_close, True
```

(Place the cap check AFTER the long/short SL/TP/soft block and BEFORE the `if exit_reason is not None` finaliser. `bars_held` resets with the trade because it's reset at the next entry.)

- [ ] **Step 7: Run — expect PASS** (engine == fast, TIME_CAP present)

Run: `python3 optimize/test_fast_parity.py 4h`
Expected: `FAST-PARITY OK ✓`

- [ ] **Step 8: Commit**

```bash
git add engine.py optimize/test_fast_parity.py
git commit -m "feat(engine): TIME_CAP exit in 1-min walk + cap_1min param (engine==fast parity)"
```

---

## Task 3: Thread cap_1min through the layer params + causal path

**Files:**
- Modify: `optimize/l2/l1_runner.py` (the `fast_backtest(...)` call ~153-159), `optimize/l2/engine.py` (L2's backtest call), `optimize/l2/payload.py` (`validate_layer_params`, `_layer_from_strategy`)
- Test: `optimize/l2/test_logbook.py`

**Interfaces:**
- Consumes: `fast_backtest(..., cap_1min)` (Task 1), `SimpleStrategyParams.cap_1min` (Task 2).
- Produces: a layer param dict may carry `cap_1min`; `run_causal` emits `TIME_CAP` rows when `cap_1min>0`.

- [ ] **Step 1: Write the failing test**

```python
# optimize/l2/test_logbook.py
def test_cap_1min_produces_time_cap_exits():
    base = dict(payload.l1_default_params("4h"))
    capped = dict(base, cap_1min=3)            # very tight cap → most trades hit the time cap
    res = logbook.run_causal(capped, dict(payload.PERMISSIVE), "4h")
    reasons = {r.exit_reason for r in res.log if r.decision == "entry"}
    assert "TIME_CAP" in reasons
    # default (no cap) has none
    res0 = logbook.run_causal(payload.l1_default_params("4h"), dict(payload.PERMISSIVE), "4h")
    assert "TIME_CAP" not in {r.exit_reason for r in res0.log if r.decision == "entry"}
```

- [ ] **Step 2: Run — expect FAIL** (`TIME_CAP` not produced — param not threaded)

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_cap_1min_produces_time_cap_exits -v`

- [ ] **Step 3: Pass `cap_1min` into `fast_backtest` in `l1_runner.run_l1`** (~line 153-159). The call already forwards split args via a dict comprehension; add `cap_1min`:

```python
        params["sl_soft"], params["sl_hard"], params["tp"], params["flip"],
        cap_1min=int(params.get("cap_1min", 0) or 0),
        **{k: params.get(k) for k in ("long_sl_soft", "long_sl_hard", "long_tp",
                                      "short_sl_soft", "short_sl_hard", "short_tp")})
```

- [ ] **Step 4: Thread `cap_1min` in L2's engine** — in `optimize/l2/engine.py`, find its `fast_backtest(...)` (or `SimpleStrategyParams(...)`) construction for the L2 layer and pass `cap_1min=int(l2_params.get("cap_1min", 0) or 0)` the same way. (Read the file; mirror the L1 pattern.)

- [ ] **Step 5: Accept `cap_1min` in the layer schema** — `optimize/l2/payload.py::validate_layer_params`: allow integer `cap_1min` (default 0, reject negatives), and `_layer_from_strategy` map the dashboard field through. Mirror how `cooldown`/`k` are validated/mapped.

- [ ] **Step 6: Run — expect PASS**

Run: `python3 -m pytest optimize/l2/test_logbook.py::test_cap_1min_produces_time_cap_exits -v`

- [ ] **Step 7: Golden + anchors unchanged (default off)**

Run: `python3 perf/check_golden.py 4h && python3 -m pytest optimize/l2/test_parity_anchor.py -q`
Expected: golden ✅ ALL MATCH; anchors pass (no champion sets `cap_1min`).

- [ ] **Step 8: Commit**

```bash
git add optimize/l2/l1_runner.py optimize/l2/engine.py optimize/l2/payload.py optimize/l2/test_logbook.py
git commit -m "feat(l2): thread cap_1min through L1/L2 layer params + causal log"
```

---

## Task 4: Dashboard field + TIME_CAP label

**Files:**
- Modify: `frontend/dashboard.html` (L1+L2 entry/exit param groups; `setLayer`/`collectLayer`; exit-reason styling)
- Test: manual (Playwright)

**Interfaces:**
- Consumes: the layer param `cap_1min` (Task 3).

- [ ] **Step 1: Add the field to both forms** — in the L1 and L2 "Entry / exit (points)" groups, add (mirror the `cooldown` field markup):

```html
<div class="fld"><label>Max hold (1-min bars, 0=off)</label><input id="l1_cap_1min" type="number" step="1" min="0" value="0"></div>
```
and the `l2_cap_1min` twin.

- [ ] **Step 2: Wire setLayer/collectLayer** — add `cap_1min` to the layer field list the boot uses to fill (`setLayer`) and to collect (`collectLayer`/`collectStrategy`). Find `LAYER_FIELDS` (frontend/dashboard.html ~line 165: `['sl_soft','sl_hard','tp','gate_pct','dd_limit','cooldown','k']`) and add `'cap_1min'`. Confirm the collector reads `$(pfx+'_cap_1min').value` as an int.

- [ ] **Step 3: TIME_CAP styling (optional polish)** — add a CSS rule so a `TIME_CAP` exit row/reason reads distinctly, mirroring existing exit-reason colors. (No new data wiring — the verbose log already shows the value.)

- [ ] **Step 4: Syntax-check**

Run:
```bash
python3 -c "import re;h=open('frontend/dashboard.html').read();b=max(re.findall(r'<script(?![^>]*src=)[^>]*>(.*?)</script>',h,re.S),key=len);open('/tmp/d.js','w').write(b)"
node --check /tmp/d.js
```
Expected: no error.

- [ ] **Step 5: Playwright verify** — start `python3 server.py --port 8292`; drive headless (executablePath `/usr/bin/google-chrome-stable`): assert `#l1_cap_1min` and `#l2_cap_1min` exist and default `"0"`; set `l2_cap_1min=3`, Run, confirm the L2 log shows `TIME_CAP` rows and a normal Run (cap 0) shows none. Screenshot.

- [ ] **Step 6: Commit**

```bash
git add -f frontend/dashboard.html
git commit -m "feat(dashboard): Max-hold (cap_1min) field on L1/L2 forms + TIME_CAP styling"
```

---

## Task 5: Docs + bundle follow-up note

**Files:**
- Modify: `docs/LOG_FIELDS.md` (note `TIME_CAP` as an exit reason) and/or `docs/PNL_EXPLAINED.md` (add TIME_CAP to the exit table)

- [ ] **Step 1:** Add `TIME_CAP` to the exit-reason list in `docs/PNL_EXPLAINED.md` §4 (fill = Nth-bar close; precedence lowest) and note `cap_1min` as a per-layer setting. Note in `docs/LOG_FIELDS.md` that the shareable bundles need the same `cap_1min` port in a follow-up.

- [ ] **Step 2: Commit**

```bash
git add docs/PNL_EXPLAINED.md docs/LOG_FIELDS.md
git commit -m "docs: document TIME_CAP exit + cap_1min (bundle port noted as follow-up)"
```

---

## Self-Review

- **Spec coverage:** §1 param/schema → Tasks 2 (SimpleStrategyParams) + 3 (layer schema) + 4 (dashboard). §2 engine walk → Task 2. §3 fast_engine parity → Task 1 (+ Task 2 parity test). §4 plumbing/defaults/tests → Tasks 3-4; docs → Task 5. ✓
- **Default-off byte-identical** verified in Task 3 Step 7 (golden + anchors) and by the cap=0 tests in Tasks 1 & 3.
- **Type consistency:** `cap_1min: int` everywhere; `R_TIME_CAP=4` / `REASON_NAME[R_TIME_CAP]="TIME_CAP"` (Task 1) == `'TIME_CAP'` in `ExitReason` (Task 2) == the string asserted in Tasks 3-4. The fast_engine kwarg `cap_1min` (Task 1) matches the `l1_runner` call (Task 3).
- **Placeholder scan:** the L2-engine threading (Task 3 Step 4) and `LAYER_FIELDS`/`collectLayer` (Task 4 Step 2) say "read the file, mirror the existing `cooldown`/split pattern" — intentional, because the exact call site mirrors a known existing pattern; all engine/fast_engine code is given verbatim.
