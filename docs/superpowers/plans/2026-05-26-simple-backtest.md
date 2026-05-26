# Implementation plan — Simple Backtest engine

**Date:** 2026-05-26
**Spec:** `backtest_updates.md` (user note) + `docs/superpowers/specs/2026-05-26-simple-backtest/notes.md` (Q&A)
**Status:** approved — ready to execute on `dev`.

---

## 0. Locked decisions (from notes.md)

| # | Decision |
|---|---|
| Q1 | Entry price = **4h close** of the signal-firing candle |
| Q2 | Single SL line; fires on **1 close past the line** |
| Q3 | TP fires on **1-min close past the TP line** (not a wick touch) |
| Q4 | Exit fill price = the **1-min `close`** that triggered |
| Q5 | **1 contract** per trade. No ladder. |
| Q6 | Stage 1 signal at candle level via **any-long → long, any-short → short, else hold** |
| Q7a/b/c | Re-entry: next 4h candle whose `start > exit_time`; **fresh Stage 1 evaluation** each candle; **no SL/TP differentiation** in gating |
| Q8 | If exit fires mid-4h, the **rest of that 4h is dead** — wait for the next 4h close |
| Q9 | Build as a **new module** `src/strategy/simple_strategy.py`; old engine stays |
| Q10 | NSGA-II searches **`(sl_points, tp_points)`** only |
| Q11 | Keep both engines alive until the simple engine has its own locks |
| Q12 | Truth-table viewer stays as historical record |

---

## 1. Goal

Replace the entry-direction layer with Stage 1's per-candle truth table, strip out the ladder / anchor_mode / big-candle / direction-flip / cooldown machinery, and add a simple SL+TP exit on 1-min bars. Old engine (`BoxStrategy` + `ScalingStrategy`) stays untouched.

End state on `dev`:
- New module `src/strategy/simple_strategy.py` exporting `SimpleStrategy`, `SimpleStrategyParams`.
- New schema `src/api/schemas.py::SimpleBacktestRequest`.
- New endpoint `POST /api/backtest/simple` (mirrors `POST /api/backtest/box`).
- Synthetic + real-data tests at `tests/test_simple_strategy.py`.
- NSGA-II objective re-pointed at `SimpleStrategy` (behind a `engine` param, default `box` for back-compat).
- 100% of existing tests still pass.

---

## 2. Engine specification

### 2.1 Inputs

| Input | Source |
|-------|--------|
| 4h OHLCV stream | `data/full_data/NQ_4h.csv` (or sub-preset) |
| 1-min OHLCV stream | `data/full_data/NQ_1m.csv` |
| Box levels CSV | `data/full_data/NQ_full_data.csv` |
| Params | `sl_points: float`, `tp_points: float`, `data_path_4h: str`, `data_path_1min: str`, `box_data_path: str` |

### 2.2 Entry rule (Stage 1, candle-level)

Re-uses Stage 1's logic verbatim. For each 4h candle, evaluate the Stage 1 truth table against every active level pair on the candle's mapped box-date row, then collapse:

```python
candle_signal =
    'long'  if any active level pair fires long
    'short' if any active level pair fires short
    'hold'  otherwise
```

Implementation: `from subprojects.signals.generate_stage1 import _emit_rows` and use the same OR-collapse pattern the windowing subprojects use. **Do not reimplement Stage 1's rule.** This keeps the entry layer canonical.

### 2.3 Exit rule

After a trade opens at time `entry_time` with `entry_price`, anchor:

- `tp_line = entry_price + tp_points`  for long; `entry_price - tp_points` for short
- `sl_line = entry_price - sl_points`  for long; `entry_price + sl_points` for short

Walk 1-min candles whose `datetime` is in the open window (i.e., `m.datetime ≥ entry_time` and within or beyond the entry 4h). For each `m`:

- **Long position:** if `m.close ≥ tp_line` → TAKE_PROFIT at `m.close`, `exit_time = m.datetime`. If `m.close ≤ sl_line` → STOP_LOSS at `m.close`, `exit_time = m.datetime`.
- **Short position:** mirrored.

Tie-break inside a single 1-min bar (both lines crossed): SL wins (pessimistic).

No other exit reasons. No carry-over special case — the loop just keeps walking 1-min bars across 4h boundaries until SL or TP fires or the dataset ends.

### 2.4 Re-entry gate

On exit, store `blocked_until_4h_after = exit_time`. The next 4h candle is signal-eligible iff its `start_time > blocked_until_4h_after`.

For the worked example in notes.md: exit at 19:43 inside 4h X (18:00–22:00). `blocked_until_4h_after = 19:43`. X+1 starts at 22:00 > 19:43, so it's eligible — the signal is evaluated at X+1's close (02:00).

### 2.5 End-of-dataset behaviour

If the loop hits EOF with a trade still open, emit it with `exit_reason = 'OPEN'`, `exit_time = None`, `exit_price = None`, `pnl = None`. (Same convention as the existing engine.)

---

## 3. File / module layout

```
src/strategy/
├── simple_strategy.py      NEW — SimpleStrategy + SimpleStrategyParams + backtest()
├── box_strategy.py         UNCHANGED — old engine
├── scaling_strategy.py     UNCHANGED — old engine
└── box_lookup.py           UNCHANGED — both engines call into this for box geometry

src/api/
├── schemas.py              ADD — SimpleBacktestRequest (mirrors BoxBacktestRequest but param subset)
└── app.py                  ADD — POST /api/backtest/simple endpoint

src/optimization/
├── objective.py            EDIT — accept `engine='box'|'simple'` param; route to the right strategy
└── (other files unchanged)

tests/
├── test_simple_strategy.py            NEW — synthetic + real-data locks
└── test_blueprint_examples.py         UNCHANGED — old engine's blueprint
```

---

## 4. Task breakdown

### P1 — Engine

| # | Task | File | Estimate |
|---|------|------|---|
| P1.1 | Define `SimpleStrategyParams` dataclass (sl_points, tp_points, data_path_4h, data_path_1min, box_data_path) | `src/strategy/simple_strategy.py` | 15 min |
| P1.2 | Implement `_evaluate_stage1_signal(candle, box_row) -> Literal['long','short','hold']` using the existing `_emit_rows` collapse pattern | same | 30 min |
| P1.3 | Implement `_exit_check(position, one_min_bar) -> Optional[exit_dict]` | same | 30 min |
| P1.4 | Implement `SimpleStrategy.backtest(df_4h, df_1min, box_lookup) -> (trades, state)` — the main loop with re-entry gate | same | 90 min |
| P1.5 | Edge cases: no signal ever fires (zero trades) / trade open at EOF (emit OPEN) / 1-min data missing for a 4h window (skip exits, carry) | same | 30 min |

### P2 — Tests

| # | Task | File | Estimate |
|---|------|------|---|
| P2.1 | Synthetic test: long signal at 4h close → TP hit on 1-min `close` past line → exit, then re-entry gate | `tests/test_simple_strategy.py` | 30 min |
| P2.2 | Synthetic test: short signal → SL hit → exit | same | 20 min |
| P2.3 | Synthetic test: signal at 4h close X, exit mid-4h X, then **X+1 close evaluates fresh signal** (matches Q7a) | same | 30 min |
| P2.4 | Synthetic test: trade open at EOF → exit_reason='OPEN', pnl=None | same | 15 min |
| P2.5 | Real-data smoke test on `full` preset: assert non-zero trade count, all `exit_reason ∈ {TAKE_PROFIT, STOP_LOSS, OPEN}`, all entry_times align to 4h closes | same | 30 min |
| P2.6 | Real-data lock: capture (n_trades, n_TP, n_SL, n_OPEN, total_pnl) on `full` with `sl=100, tp=150` and pin those numbers | same | 20 min |

### P3 — API

| # | Task | File | Estimate |
|---|------|------|---|
| P3.1 | Define `SimpleBacktestRequest` Pydantic model | `src/api/schemas.py` | 20 min |
| P3.2 | Define `SimpleBacktestResponse` (trades + summary) | same | 15 min |
| P3.3 | Add `POST /api/backtest/simple` handler (mirror box endpoint structure) | `src/api/app.py` | 45 min |
| P3.4 | Unit-test the endpoint with a tiny synthetic dataset | `tests/test_api_simple.py` (new) | 30 min |

### P4 — NSGA-II re-target

| # | Task | File | Estimate |
|---|------|------|---|
| P4.1 | Add `engine: Literal['box','simple'] = 'box'` to `OptimizerStartRequest` schema | `src/api/schemas.py` | 15 min |
| P4.2 | Edit `evaluate()` in `objective.py` to branch on `engine` and use single-objective `total_profit` (not Pareto) when `engine='simple'` | `src/optimization/objective.py` | 60 min |
| P4.3 | Edit `_suggest()` in `study.py` to skip `sl_hard_delta` when `engine='simple'`; just suggest `(sl_points, tp_points)` | `src/optimization/study.py` | 30 min |
| P4.4 | Update Optuna sampler config — single objective, `direction='maximize'` when `engine='simple'` | `src/optimization/persistence.py` (`create_study`) | 30 min |
| P4.5 | Per-direction search switch: add `direction_scope: Literal['both','long_only','short_only'] = 'both'` param; filter Stage 1 signals accordingly in `evaluate()` | `src/optimization/objective.py` | 45 min |

### P5 — Verification

| # | Task | Estimate |
|---|------|---|
| P5.1 | Run `pytest subprojects/signals/tests/ subprojects/signals/stage1_0_reverse_signals/tests/ subprojects/signals/stage1_1_next_signal/tests/ -q` → expect 91/91 | 1 min |
| P5.2 | Run `pytest tests/ -q` (main project) → expect all green (old engine untouched) | 1 min |
| P5.3 | Run new tests `pytest tests/test_simple_strategy.py tests/test_api_simple.py -q` → expect all green | 1 min |
| P5.4 | Manual smoke: `curl -X POST /api/backtest/simple` with `sl=100, tp=150` → confirm response shape + trade count matches the locked value | 5 min |
| P5.5 | Manual smoke: NSGA-II run with `engine='simple'` for 1 generation × 4 trials → confirm SSE events flow + Pareto/best trial emitted | 10 min |

**Total estimate: ~9 hours focused work.** P1 (engine) + P2 (tests) is the critical path; P3 (API) and P4 (NSGA-II) can be done in parallel with subagents if the user wants to compress.

---

## 5. Schema sketch

### `SimpleStrategyParams` (dataclass)

```python
@dataclass
class SimpleStrategyParams:
    sl_points: float
    tp_points: float
    data_path_4h: str
    data_path_1min: str
    box_data_path: str
    direction_scope: Literal['both', 'long_only', 'short_only'] = 'both'
```

### `SimpleBacktestRequest` (Pydantic)

```python
class SimpleBacktestRequest(BaseModel):
    sl_points: float = Field(gt=0)
    tp_points: float = Field(gt=0)
    data_path_4h: str
    data_path_1min: str
    box_data_path: str
    direction_scope: Literal['both', 'long_only', 'short_only'] = 'both'
```

### Trade dict (returned)

```python
{
    'entry_time':   pd.Timestamp,        # 4h close that fired the signal
    'entry_price':  float,                # = 4h close
    'direction':    'long' | 'short',
    'tp_line':      float,
    'sl_line':      float,
    'exit_time':    pd.Timestamp | None, # None if OPEN at EOF
    'exit_price':   float | None,         # 1-min close that triggered
    'exit_reason':  'TAKE_PROFIT' | 'STOP_LOSS' | 'OPEN',
    'pnl_points':   float | None,         # signed; positive = winning
    'pnl_dollars':  float | None,         # NQ point value × pnl_points
    'entry_box_signal': dict,             # which Stage 1 boxes fired
}
```

---

## 6. Migration / coexistence plan

- Old box endpoint `POST /api/backtest/box` stays unchanged; default in frontend stays on box for now.
- New simple endpoint `POST /api/backtest/simple` opt-in.
- Add a tiny frontend toggle later (out of scope for this plan).
- Deprecation of the old engine happens only after the simple engine has stable real-data locks across multiple param sweeps.

---

## 7. Risks / open items

| # | Risk | Mitigation |
|---|------|---|
| R1 | Stage 1's `_emit_rows` returns one row per (candle, level pair); the engine needs the **candle-level signal** | Wrap with a collapse helper in `simple_strategy.py`. Don't touch Stage 1. |
| R2 | 1-min data gaps inside a 4h window (missing minutes) — could skip a true SL/TP fire | For now: just walk the 1-min rows that exist. Document the limitation. |
| R3 | Tie inside a single 1-min bar (TP and SL both crossed) | Rule: **SL wins** (pessimistic). Documented in §2.3. |
| R4 | The "next 4h candle whose start > exit_time" rule needs the **4h candle's `start_time`**, not its `datetime` (which is the close in some conventions) | Verify which the existing CSV uses (in our data, `datetime` is the bar's *start*, e.g. `2025-01-01 18:00:00` for the 18:00–22:00 bar). Confirm and document. |
| R5 | NSGA-II currently runs Pareto two-objective `(median_pf, max_dd)`; switching to single-objective `total_profit` changes the study type | Branch on `engine` in `create_study()` — old engine keeps Pareto, simple uses single. |

---

## 8. Done definition

This plan is complete when:

1. `pytest tests/test_simple_strategy.py tests/test_api_simple.py -q` is green.
2. `pytest tests/ -q` (rest of main project) is green — no regression in the old engine.
3. `pytest subprojects/signals/**/tests/ -q` is green — no regression in Stage 1 / 1.0 / 1.1.
4. Manual smoke of the API endpoint succeeds.
5. Manual smoke of NSGA-II with `engine='simple'` succeeds.
6. Plan + code committed and pushed to `origin/dev` with the message convention used by previous commits.

---

## 9. Out of scope (deliberate)

- Frontend dashboard wiring for the new engine.
- Comparison HTML of simple vs box outputs.
- Deprecating the old engine.
- Multi-contract sizing.
- Anchor_mode toggle (gone — single anchor = entry price).
- Soft/hard SL dual-line model (Q2 picked single).
- Direction-flip exit (gone).
- Big-candle override (gone).
- Re-entry cooldown counter (replaced by time-based gate).
