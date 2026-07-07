# Intra-Candle Vetoed Entry — Phase 2 (optimizer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans / subagent-driven-development. TDD, checkbox steps.

**Goal:** Re-optimize L1 **with the intra-candle feature enabled** and compare the re-optimized champion to the current one — the fair test of the feature (Phase-1 bolt-on onto fixed champion params understated it; breakeven is a function of the exits, which re-optimization frees). Validate out-of-sample.

**Why:** Phase-1 result (`docs/INTRACANDLE_VETO_ENTRY_PHASE1_RESULTS.md`): feature ~2× entries but rescued trades win 50–57% vs the champion's fixed 57.5% breakeven; force-close recovered ~$22k. The optimizer can (1) lower the breakeven by re-tuning SL/TP and (2) raise win% via searched N / force-close / K / admission. User-approved: full build, server run.

**Architecture:** The optimizer uses `optimize/fast_engine.fast_backtest` (a fast per-decision-bar loop), which currently has NO intra-candle logic. Port the exact-engine feature into it with **trade-for-trade parity** as the gate (extend `optimize/test_fast_parity.py`). Then expose the feature params to the search, run on the AMD server (fresh prefix), and OOS-validate.

## Global Constraints
- **Parity is the gate:** `fast_backtest` with the feature ON must match `engine.SimpleStrategy.backtest` with the feature ON, trade-for-trade (extend `test_fast_parity`). With the feature OFF, both remain byte-identical (golden 6/6 + existing parity unchanged).
- **Server for the optimization run** (no heavy local compute). New study prefix (never reuse — `wsh-pg` precedent).
- **OOS discipline:** in-sample gains must survive walk-forward before we trust them (Kalman + l2v3 lesson).
- Constants/semantics identical to the exact engine (`engine.py` intra-candle block): full gate `¬veto ∧ ≥K confirms` per 1-min bar, vetoed+vol-passed scope, flat-at-candle-start, box direction, one armed, force-close = normal entry closes an open rescued trade.

---

### Task 2a: Port basic intra-candle entry into `fast_engine` (parity)
**Files:** Modify `optimize/fast_engine.py` (add `intracandle_gate_by_dir`, `intracandle_vol_gate`, `intracandle_max_wait`, `intracandle_veto_mask` args + the entry logic); Test: `optimize/test_intracandle_parity.py`.
**Interfaces — Produces:** `fast_backtest(..., intracandle_gate_by_dir=None, intracandle_vol_gate=None, intracandle_veto_mask=None, intracandle_max_wait=240, intracandle_force_close=False)`.

- [ ] Step 1 — Failing parity test: build the champion inputs both ways (exact via `strategy.build_payload` with `intracandle_veto_entry=True`; fast via `fast_backtest` with the same gate), assert equal trade lists (entry_time, direction, exit_reason, pnl_points) for N=240, force_close=False.
- [ ] Step 2 — Run: `pytest optimize/test_intracandle_parity.py -q` → FAIL.
- [ ] Step 3 — Implement in `fast_backtest`: when `intracandle_gate_by_dir` is set and `gate[idx]` is False, and `intracandle_veto_mask[idx]` is True and `intracandle_vol_gate[idx]` is True and the signal is directional: scan the candle's 1-min bars `[e_start, e_end)` for the first `intracandle_gate_by_dir[d][t]` True within `intracandle_max_wait`; if found, set `e=t, ep=m_close[t], et=m_dates[t]` and resolve exits from there; else `idx+=1; continue`. (candle bounds via `searchsorted(m_dates, d_dates[idx])` / `d_dates[idx+1]`.)
- [ ] Step 4 — Run parity test → PASS.
- [ ] Step 5 — Commit.

### Task 2b: Force-close in `fast_engine` (parity)
**Files:** Modify `optimize/fast_engine.py`; extend `optimize/test_intracandle_parity.py`.
- [ ] Step 1 — Failing parity test: force_close=True case, fast vs exact.
- [ ] Step 2 — Run → FAIL.
- [ ] Step 3 — Implement: after a rescued entry, before taking its natural exit, find the earliest later decision-bar boundary `b` where a normal entry qualifies (`gate[b]` True, directional); if that boundary's 1-min index < the natural exit index, force-close at the boundary (`FORCE_CLOSE`, fill = `d_close[b-1]`) and set `idx=b`.
- [ ] Step 4 — Run → PASS.
- [ ] Step 5 — Commit + re-run golden 6/6 (feature off) + full `test_fast_parity`.

### Task 2c: Expose feature params to the optimizer search space
**Files:** Modify `optimize/optimizer.py` (+ `optimize/core.py` if it builds the fast-engine call) — add search dims `intracandle_veto_entry` (bool), `intracandle_max_wait` (choice e.g. {30,60,120,240}), `intracandle_force_close` (bool); build `intracandle_gate_by_dir` once per trial's indicator config (reuse `runner.intracandle_gate_arrays`) and pass to `fast_backtest`. Objectives unchanged (P/L, DD, and entries — the entry-increasing goal). Test: a unit test that a trial with the flag on runs and differs from off.
- [ ] Steps 1–5 (TDD) + commit.

### Task 2d: Server optimization run + OOS
- [ ] Sync to server; launch a fresh study (new prefix, e.g. `wshic1`) with the feature in the search, objectives = max P/L, min DD, max entries (or the current 3rd-objective choice), on NQ 4h L1.
- [ ] Extract champion; compare to the current champion (entries, P/L, DD, hold-time). Target: ~2× entries at breakeven-or-better.
- [ ] **Walk-forward / OOS validate** the re-optimized champion before any promotion. Record verdict in the Phase-1 results doc.

## Verification
1. `pytest optimize/test_intracandle_parity.py optimize/test_fast_parity.py -q` → all pass (fast==exact, feature on and off).
2. `python3 perf/check_golden.py` → 6/6 (feature off).
3. Server study completes; champion compared + OOS-checked; verdict recorded.
