# End-of-Day Exit Cap — Design Spec

**Date:** 2026-06-25 · **Status:** approved (brainstorm) · **Approach:** A (precomputed per-bar EOD target)

## Goal

Add a SECOND time-cap mode — an **end-of-trading-day exit** — alongside the existing 1-min-count cap.
A layer (L1 / L2 independently) selects one of: **none · max 1-min bars · end-of-day**. The end-of-day
cap force-closes an open trade at the end of its **trading day** (the 18:00→17:00 session, NOT the
calendar day): **full days** exit a configurable N minutes before the close (default 15); **partial /
early-close days** exit exactly at the session's last bar. Additive; default-off path is byte-identical
to today (golden unchanged).

## Background — current system (from the code + data study)

- **Exit walk (both engines).** `optimize/fast_engine.py:fast_backtest` slices `m_high/m_low/m_close[e:]`
  from the entry bar and assembles exit candidates in an earliest-wins `order` list
  (`hard-SL ▸ hard-TP ▸ soft-SL ▸ time-cap`, `fast_engine.py:106-136`); `engine.py:_walk_exit_for_4h`
  mirrors it bar-by-bar with `bars_held`/`cap` (`engine.py:286,325`). Both have each 1-min bar's absolute
  timestamp (`m_dates` / `md_arr`). The two engines are locked trade-for-trade by `test_fast_parity.py`.
- **`cap_1min` threading seams** (the new params follow the SAME path): `SimpleStrategyParams`
  (`engine.py:94`) → `validate_layer_params` (`optimize/l2/payload.py:160`) → `_layer_from_strategy`
  (`payload.py:324`) → `run_l1` call (`l1_runner.py:178`) / `run_l2` call (`optimize/l2/engine.py:120`) →
  `fast_backtest`. Dashboard field at `dashboard.html:82,117`, `LAYER_FIELDS` (`:167`), `collectLayer`
  (`:172`). Taxonomy exit leaves in `optimize/l2/taxonomy.py:_EXIT_KEYS`.
- **Data reality (NQ 1-min, `NQ_1m.csv`, 357 sessions).** 342 full / 14 partial / 1 truncated tail.
  **There is no 17:00 bar** — a full session's last bar is **16:59**; "15 min before the 17:00 close" is
  the **16:45 bar**, present on **100%** of full days. Partial days have **no 16:59 bar** and end at one
  of 4 times (12:59, 13:14, 09:29, 09:14). ⇒ the robust rule is **"last bar with time ≤ cutoff"**, never
  an exact-timestamp match. Full/partial is cleanly derivable from a session's last-bar time-of-day.

## Decisions (locked during brainstorm)

1. **Configurable margin** — the "minutes before close" for full days is a field, **default 15**.
2. **3-way mode selector** per layer: `none | bars | eod`, mutually exclusive.
3. **Exit reason** = `END_OF_DAY` (new taxonomy leaf, with a win/loss split like `TIME_CAP`).
4. **Fill** = the exit bar's **close** (identical convention to `TIME_CAP`).
5. **Partial "exactly at end"** = the **close of the session's last bar**.

## Parameter model (golden-safe)

Add to the layer params (and `SimpleStrategyParams`):
- `cap_mode: str = "none"` ∈ `{"none","bars","eod"}`.
- `eod_margin_min: int = 15` — minutes before the 17:00 close to exit on full days (used when `eod`).
- `cap_1min: int = 0` — UNCHANGED; used only when `cap_mode == "bars"`.

Backward compatibility: `cap_mode` defaults to `"none"`. A saved profile with `cap_1min > 0` and no
`cap_mode` is normalised to `cap_mode = "bars"` in `validate_layer_params` (so existing time-cap
profiles keep working). Default `none` + `cap_1min=0` ⇒ no cap candidate ⇒ byte-identical to today.

## Component 1 — Trading-day classifier (`optimize/trading_days.py`, NEW)

```python
def eod_targets(m_dates: np.ndarray, margin_min: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-1min-bar end-of-day exit targets. Returns (eod_target, session_last), both int64 arrays
    of len(m_dates), giving GLOBAL 1-min indices.

    Sessions: grouped by the box-date rule (hour>=18 -> next day), the engine's day mapping.
    Per session, classify by the LAST bar's time-of-day:
      full     : last bar time in [16:55, 17:05]  -> eod_target = last bar with time <= time(17,0)-margin
      partial  : last bar time <  16:00            -> eod_target = session's last bar (exact close)
      abnormal : otherwise (e.g. truncated tail)   -> eod_target = -1 (no EOD; trade runs to data end)
    session_last[i] = the session's last bar index (fallback for the rare entry-after-cutoff case).
    All bars in a session share the same eod_target / session_last value.
    """
```

- Vectorised: derive box-dates with the same helper `optimize/signals._box_dates_vec` (or
  `box_lookup._candle_to_box_date` vectorised); sessions are contiguous runs of equal box-date.
- `time(17,0) - margin_min` → for margin 15 = 16:45; margin 0 = 17:00 (⇒ the 16:59 last bar). Cutoff
  compares against each bar's `time-of-day`; pick the last index `< session_end` with `tod <= cutoff`.
- Pure, no engine state. Locked by test to data anchors (342 full / 14 partial / 1 abnormal; 16:45
  present on all full days).

## Component 2 — Engine wiring (parity-locked)

`fast_backtest(...)` gains `cap_mode: str = "none"`, `eod_target: np.ndarray | None = None`,
`session_last: np.ndarray | None = None`. New exit-reason constant `R_END_OF_DAY = 5`,
`REASON_NAME[R_END_OF_DAY] = "END_OF_DAY"`. After `t_soft`:

```python
# back-compat: a bare cap_1min arg (existing tests/golden call fast_backtest(..., cap_1min=N) with no
# cap_mode) is the bars cap. Normalise so those locked cases keep firing unchanged.
if cap_mode == "none" and cap_1min:
    cap_mode = "bars"

t_eod = -1
if cap_mode == "eod" and eod_target is not None:
    g = int(eod_target[e])                       # global index of this session's EOD exit bar
    if g < 0:                                    # abnormal session -> no EOD
        t_eod = -1
    else:
        if g < e:                                # entry after cutoff (only at very large margins)
            g = int(session_last[e])
        t_eod = g - e if (g - e) < len(cl) else -1
elif cap_mode == "bars":
    t_eod = (cap_1min - 1) if (cap_1min and 0 <= cap_1min - 1 < len(cl)) else -1
# the cap candidate (bars or eod) is the 4th entry, reason chosen by mode:
cap_reason = R_END_OF_DAY if cap_mode == "eod" else R_TIME_CAP
order = [(t_slh, R_SL_HARD, slh_line), (t_tph, R_TP_HARD, tph_line),
         (t_soft, R_SL_SOFT, None), (t_eod, cap_reason, None)]
```

(The existing pure-`cap_1min` arg is retained for back-compat call sites; when `cap_mode` is absent it
behaves exactly as today — `cap_mode` defaults to `"none"`, and the bars path is selected only when
`cap_mode=="bars"`. Tests/golden that pass `cap_1min=N` with no mode keep working by normalising
`cap_1min>0 → cap_mode="bars"` at the call sites in `run_l1`/`run_l2`, matching `validate_layer_params`.)

`engine.py:_walk_exit_for_4h`: precompute `eod_target`/`session_last` once (like `start_1m`) via the
shared `trading_days.eod_targets`. In the loop, after the SL/TP/soft checks and the existing
`bars_held>=cap` branch:

```python
if exit_reason is None and self.params.cap_mode == "eod" and eod_g >= 0 and t >= eod_g:
    exit_reason, fill, resets_counter = 'END_OF_DAY', m_close, True
```

where `eod_g = eod_target[e]` (resolved to `session_last[e]` if `< e`) is captured at entry. Both engines
consume the SAME `eod_targets(...)` output ⇒ trade-for-trade identical (locked by `test_fast_parity`).

Precedence (unchanged ordering): **hard-SL ▸ hard-TP ▸ soft-SL ▸ (bars-cap | eod-cap)**. Lowest priority.

## Component 3 — Surface

- **Dashboard** (`frontend/dashboard.html`, L1 + L2 forms): replace the bare "Max hold" input with a
  **Cap-mode `<select>`** (`none` / `max 1-min bars` / `end-of-day`). A small JS toggle shows the bars
  field (existing `l1_cap_1min`/`l2_cap_1min`) when `bars`, or a new **"Exit N min before full-day
  close"** number field (`l1_eod_margin_min` / `l2_eod_margin_min`, default 15) when `eod`. Extend
  `LAYER_FIELDS` with `cap_mode`, `eod_margin_min`; `collectLayer` emits both.
- **Taxonomy** (`optimize/l2/taxonomy.py`): add `END_OF_DAY → end_of_day_exit` to `_EXIT_KEYS`, plus
  `end_of_day_win` / `end_of_day_loss` (mirroring the TIME_CAP win/loss split). The exit-partition
  invariant becomes `tp + sl_soft + sl_hard + time_cap + end_of_day == entered`. Combined roll-up gains
  the same leaves. Additive — no existing number moves (default off ⇒ zero EOD trades).
- **Dashboard Totals/taxonomy cards**: add the `end_of_day_*` cards next to the time-cap cards.
- **Log/CSV**: `exit_reason == "END_OF_DAY"` flows through unchanged (no schema change).

## Component 4 — Testing & gates

- `optimize/test_trading_days.py` (NEW): assert the classifier over real 4h-aligned 1-min data — counts
  (342 full / 14 partial / 1 abnormal), a known full day's `eod_target` lands on its 16:45 bar, a known
  partial day (e.g. 2025-07-04, ends 12:59) targets its last bar, abnormal → −1.
- `optimize/test_fast_parity.py`: add an `eod` case — build `SimpleStrategyParams(..., cap_mode="eod",
  eod_margin_min=15)`, run both engines, assert trade-for-trade parity AND `any(exit_reason ==
  "END_OF_DAY")`.
- `optimize/test_time_cap.py` (or a new `test_eod_cap.py`): behavioural — a long-held trade with SL/TP
  far away exits `END_OF_DAY` at the expected session bar; `cap_mode="none"` fires nothing.
- `optimize/l2/test_taxonomy.py`: `end_of_day_*` leaves + the updated exit-partition invariant.
- `perf/check_golden.py`: ✅ ALL MATCH (default-off path unchanged — no re-lock).
- Playwright: the mode `<select>` toggles the right field; an `eod` run shows `END_OF_DAY` exits + cards.

## Files

- Create: `optimize/trading_days.py`, `optimize/test_trading_days.py` (and possibly `test_eod_cap.py`).
- Modify: `optimize/fast_engine.py`, `engine.py`, `optimize/l2/payload.py` (`validate_layer_params`,
  `_layer_from_strategy`), `optimize/l2/l1_runner.py`, `optimize/l2/engine.py`, `optimize/l2/taxonomy.py`,
  `frontend/dashboard.html`, `optimize/test_fast_parity.py`, `optimize/l2/test_taxonomy.py`,
  `docs/LOG_FIELDS.md`, `docs/PNL_EXPLAINED.md`.

## Out of scope (YAGNI)

- No external holiday calendar (full/partial derived from the 1-min data itself).
- No EOD in the optimizer search space (separate later task, like `cap_1min`).
- No bundle port in this change (deliberate follow-up, as with prior work).
- Modes stay mutually exclusive — no "both caps active" combination.
