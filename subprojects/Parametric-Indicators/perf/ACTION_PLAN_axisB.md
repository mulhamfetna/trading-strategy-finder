# Action Plan — Axis B: vectorize the per-decision engine signal (task #210)

**Date:** 2026-06-12 · branch `dev` · derives from `perf/INVESTIGATION_axisB_per_decision_loop.md`
**Status:** PLAN — not started. Each step is approval-gated; I will not begin coding a step until you say so.
**Languages:** professional + **baby** throughout.

> This is the executable runbook. It turns the investigation's B1/B2/B3 design into ordered, verifiable
> tasks with exact files, commands, acceptance gates, commit messages, and revert steps. The golden rule is
> unchanged: **every step must keep trades byte-identical**; any drift = revert.

---

## 0. Governing principles (apply to EVERY step)

1. **Investigate → implement → verify → document → commit.** One step = one commit = one revert point.
2. **Byte-identical or it didn't happen.** Acceptance is the golden byte-match + all parity layers green.
3. **Minimal scope.** Touch only the files a step names. No drive-by edits. Ask before extra edits.
4. **Approval gate before each step.** I present the step, you approve, I implement, I report.
5. **Clean timing only.** Wall-time numbers are taken on an idle box (no benchmark/dashboard running).
6. **Reference stays frozen.** `_stage1_candle_signal` remains the immutable spec; we change the *source*
   of the signal, never the decision logic.

**Baby:** small careful moves; after each move we check the robot still makes the exact same trades, write
down what we did and how to undo it, then save. If anything differs by even one trade, we undo.

---

## 1. Pre-flight (do once, before B1) — NO code change

**Goal:** a trustworthy clean baseline + a green starting net.

- [ ] **PF-1** Wait for benchmark `manual_bg` (PID 14065) to finish → records clean per-TF baseline in
      `perf/bench_history.json` (4h/2h/1h/15m/5m/**2m**). Confirm via `perf/logs/backtest_latest.log`.
- [ ] **PF-2** Run the current safety net green (records the "before" state):
      `python3 -m pytest -q` (expect **148 passed**) and `python3 perf/check_golden.py 4h 2h 1h 15m 5m 2m`
      (expect ALL MATCH).
- [ ] **PF-3** Capture a clean cProfile of 15m **and** 5m (idle box) → archive the `tottime` tables into the
      investigation doc's evidence section (so before/after is apples-to-apples).

**Exit PF:** clean baseline numbers recorded + net green. No commit (nothing changed).

---

## 2. STEP B1 — vectorized numpy `decision_signals` (+ equivalence test)  ·  RISK: LOW

**Why first:** zero risk to live results — it adds a function and a test; **no path the backtester runs
changes until B2 wires it in.** It also independently speeds the optimizer's signal precompute.

### 2.1 Tasks
- [ ] **T1.1** Freeze the current `decision_signals` as the reference: add `decision_signals_ref` (verbatim
      copy of the per-bar pandas loop) to `optimize/signals.py` (or `indicators/_reference.py` style), so the
      equivalence test compares against an immutable original.
- [ ] **T1.2** Implement `decision_signals_vec(df_dec, box)` — numpy, per §5.1 of the investigation:
      - gather per-bar box level-pair matrix via `_candle_to_box_date` + cached `box.loc` (once per unique
        date), columns from `engine._LEVEL_PAIRS`, NaN where absent;
      - vectorized green/red/doji, per-pair `touched/long/short`, OR-reduce across pairs, `where`-collapse
        with **long-wins-ties**;
      - return the **same** `dtype=object` `'long'/'short'/'hold'` array shape as the original.
- [ ] **T1.3** Point `decision_signals` at the vectorized impl (keep the name/signature stable so
      `runner.py`, `optimizer.py`, `core.py`, `sl_tp_bounds.py` callers are unchanged).
- [ ] **T1.4** Add `tests/test_axisB_signal_equiv.py`:
      - real frames: 4h, 1h, 15m (+ 5m if fast enough) → `decision_signals_vec == decision_signals_ref`
        **element-for-element** (exact, not `isclose`);
      - adversarial synthetic frames: constant, monotonic-up/down, doji-heavy (`close==open`), leading-NaN
        levels, mid-NaN levels, missing level columns, exact-boundary touches (`low==upper`, `close==upper`);
      - assert dtype + length + NaN/None handling identical.

### 2.2 Verification gate (all must pass)
- [ ] `python3 -m pytest -q tests/test_axisB_signal_equiv.py` → all pass
- [ ] `python3 -m pytest -q` → **≥148 passed** (no regressions; new tests add to count)
- [ ] `python3 perf/check_golden.py 4h 2h 1h` → ALL MATCH (signal feeds `fast_engine` via the optimizer
      path; golden must be untouched)
- [ ] `python3 optimize/test_fast_parity.py` + `optimize/test_indicator_parity.py` → OK (these *use*
      `decision_signals` — the strongest proof the vectorized version is faithful)
- [ ] micro-bench: time `decision_signals_vec` vs `_ref` on the 15m frame (expect large speedup, exact output)

### 2.3 Deliverables
- [ ] `perf/UPDATE_step_B1_vectorized_signal.md` — before/after, the exact math, equivalence evidence,
      code links, **revert steps**.
- [ ] Commit: `perf(engine): vectorize decision_signals (Axis B · Step B1) — bit-identical, +equiv test (task #210)`
- [ ] **Revert:** `git revert <B1_SHA>` (isolated; nothing depends on it yet).

**Approval gate → proceed to B2 only on your go.**

---

## 3. STEP B2 — feed the precomputed signal into the engine  ·  RISK: MED

**Why:** removes the ~27 s `_stage1_candle_signal` per-bar cost from `build_payload`. This is the first step
that **changes the backtester's hot path**, so the golden + parity gate is the real test.

### 3.1 Tasks
- [ ] **T2.1** Add an optional `signals=None` (object array, length `len(df_4h)`) parameter to
      `engine.SimpleStrategy.backtest`. **Default `None` ⇒ current behaviour verbatim** (calls
      `_stage1_candle_signal` inline — unchanged parity for every existing caller/test).
- [ ] **T2.2** When `signals` is provided: in the entry branch read `signal = signals[idx-1]` instead of the
      `df_4h.iloc[idx-1]` + `box.loc` + `_stage1_candle_signal` trio. **All downstream logic (flip, scope,
      gate, veto, carry-mode, lines, exit walk) is byte-for-byte unchanged.**
- [ ] **T2.3** In `strategy.build_payload`, precompute `sig = decision_signals(d4, box)` once and pass
      `signals=sig` to `.backtest(...)`. (The box `.loc` for the signal is now done once, vectorized.)
- [ ] **T2.4** Guard: assert `len(signals) == len(df_4h)`; on mismatch raise (no silent fallback).

### 3.2 Verification gate (all must pass — this is the safety-critical step)
- [ ] `python3 perf/check_golden.py 4h 2h 1h 15m 5m 2m` → **ALL 6 MATCH** (summary bytes + trades-SHA +
      vote-SHA). This is the hard acceptance.
- [ ] `python3 optimize/test_parity.py` → `$7,735 / $3,670 / n=66`
- [ ] `python3 optimize/test_fast_parity.py` + `test_indicator_parity.py` → OK
- [ ] `python3 -m pytest -q` → all pass
- [ ] Clean micro-bench 15m + 5m + 2m before/after (idle box) → record the drop.

### 3.3 Deliverables
- [ ] `perf/UPDATE_step_B2_engine_signal_inject.md` — before/after wall times per TF, the diff summary,
      proof of byte-identity, code links, **revert steps**.
- [ ] Commit: `perf(engine): inject precomputed signal into backtest (Axis B · Step B2) — byte-identical, fine-TF speedup (task #210)`
- [ ] **Revert:** `git revert <B2_SHA>` (restores inline `_stage1_candle_signal`; B1 stays).

**Approval gate → proceed to B3 only on your go.**

---

## 4. STEP B3 — numpy-fy the remaining per-bar row/exit access  ·  RISK: MED-HIGH

**Why:** removes the ~26 s `fast_xs` (`df.iloc[idx]`) row construction and the `_walk_exit_for_4h`
`iloc[lo:hi]`+`itertuples` overhead — the rest of the Axis-B tax. Largest engine surface → most caution.

### 4.1 Tasks (each sub-task is independently golden-checked; split into B3a/B3b if preferred)
- [ ] **T3.1 (B3a)** Pre-extract `df_4h` columns to numpy once at the top of `backtest`: `dates = …to_numpy()`,
      `O/H/L/C` arrays. Replace `candle = df_4h.iloc[idx]` / `candle['Close']` / `df_4h.iloc[idx-1]` reads
      with array indexing. Timestamps via the prebuilt `dates` array.
- [ ] **T3.2 (B3b)** Pre-extract `df_1min` `Date/High/Low/Close` to numpy once; in `_walk_exit_for_4h`
      iterate `range(lo, hi)` over the arrays instead of `df_1min.iloc[lo:hi].itertuples()`. Keep the exact
      same per-bar exit priority + soft-consec logic.
- [ ] **T3.3** Re-confirm the entry-price / entry-time values are produced from the arrays identically
      (the `float(signal_candle['Close'])` → `C[idx-1]`, etc.).

### 4.2 Verification gate (per sub-task)
- [ ] `python3 perf/check_golden.py 4h 2h 1h 15m 5m 2m` → ALL 6 MATCH (after **each** of B3a, B3b)
- [ ] `optimize/test_parity.py` + `test_fast_parity.py` + `test_indicator_parity.py` → OK
- [ ] `python3 -m pytest -q` → all pass
- [ ] Clean micro-bench 15m/5m/2m → record cumulative drop.

### 4.3 Deliverables
- [ ] `perf/UPDATE_step_B3_engine_numpy_rows.md` — cumulative before/after across all 6 TFs, code links,
      **revert steps**.
- [ ] Commit(s): `perf(engine): numpy row + exit-walk access (Axis B · Step B3a/B3b) — byte-identical (task #210)`
- [ ] **Revert:** `git revert <B3x_SHA>` per sub-task.

---

## 5. Phase boundary (after B3) — sign-off

- [ ] **PB-1** Full 6-TF golden check + full `pytest` + all parity tests green together.
- [ ] **PB-2** Re-run `perf/bench.py axisB_done` → append the final clean 6-TF numbers; build the
      before/after scorecard (baseline `manual_bg` → `axisB_done`).
- [ ] **PB-3** Update `perf/STATUS_optimization.md`: new commit table rows (B1/B2/B3), the fine-TF results,
      plan status, and the cumulative picture.
- [ ] **PB-4** Update `perf/REPORT_optimization_roi_and_decision.md` §5 ("is it efficient enough") with the
      new fine-TF reality.

---

## 6. Global rollback map

| To undo | Command | Keeps |
|---------|---------|-------|
| just B3b | `git revert <B3b_SHA>` | B1+B2+B3a |
| just B3a | `git revert <B3a_SHA>` | B1+B2 |
| just B2 (restore inline signal) | `git revert <B2_SHA>` | B1 |
| just B1 | `git revert <B1_SHA>` | pre-Axis-B |
| ALL Axis-B | `git revert <B3b>..<B1>` (or `git reset --hard <pre-B1_SHA>`) | D/A1/A2/E/C′ intact |
| nuclear (pre-optimization) | `git reset --hard f9d6f36` | Phase-0 anchor |

Every step is one commit on `dev`, nothing pushed. Worst case is a one-command revert with the net proving
restoration.

---

## 7. Success criteria (definition of done)

- ✅ Fine-TF single backtests materially faster (target 15m ~44 s → ~15–20 s; 5m/2m largest absolute drop).
- ✅ **All 6 golden baselines byte-identical at every step** (summary + trades-SHA + vote-SHA).
- ✅ All parity layers + full pytest green throughout.
- ✅ One verbose `UPDATE_step_B*.md` per step (before/after + revert) + `STATUS`/`ROI` docs refreshed.
- ✅ Optimizer + dashboard behaviour unchanged (only faster); no feature lost (retrace/veto/blocked-log/lines
  all preserved).

---

## 8. Sequencing & estimate

```
PF (pre-flight, ~now)
  └─ B1  vectorized signal + equiv test        [LOW]    ← you approved; awaiting "start coding"
       └─ B2  inject signal into engine         [MED]    ← approval gate
            └─ B3a df_4h numpy rows             [MED-HIGH]← approval gate
                 └─ B3b 1-min exit-walk numpy   [MED-HIGH]← approval gate
                      └─ Phase boundary sign-off + docs
```
Rough effort: B1 small, B2 small-medium, B3 medium (the most careful). Each gated by your approval and the
byte-identical net. No timeline pressure — correctness first.

---

## 9. Open decisions for you
1. **Commit cadence:** one commit per step (B1, B2, B3a, B3b) — confirm, or you prefer squashing.
2. **Start point:** begin **PF + B1 coding** now, or hold for review of this plan?
3. **Track as tasks?** I can register B1/B2/B3 as tracked subtasks under #210 if you want them in the task list.
