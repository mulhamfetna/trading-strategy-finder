---
name: ws-i-progress
description: WS-I live progress tracker — phase status, what's built/verified vs remaining, test counts. Updated as increments land. Companion to WS-I_PLAN.md (the plan) and docs/INDICATOR_DECISIONS.md (frozen spec).
type: progress
status: I.4 complete — paused at I.5 (team-leader sign-off)
created: 2026-06-04
workstream: WS-I
---

# WS-I — Progress

## Phase status
| Phase | State |
|---|---|
| I.1 Understand (freeze rules) | ✅ done — `docs/INDICATOR_DECISIONS.md` (FROZEN) |
| I.2 Document | ✅ done — `docs/INDICATORS.md` |
| **I.3 Engine + manual test** | ✅ **complete** — engine/logic layer done (see WS-I.3_ENGINE_REPORT.md); 65 tests + parity locks. Only `build_payload` wiring remains, folded into I.4. |
| **I.4 Dashboard** | ✅ **complete** — see `docs/WS-I.4_DASHBOARD_REPORT.md`. Backend (`build_layer`, `build_payload`), server (`/api/config` schema), frontend (schema-built panel: enabled/mode/params/retrace/wait + K + gen), Phase-1 gen report, **vote-attribution logging** (every indicator's opinion + active flag per entry, log + chips). No silent fallback (`ParamError` → HTTP 400). **80 tests** + parity locks. |
| **I.5 Verify (team-leader sign-off)** | ✅ **APPROVED** (2026-06-08) after review changes #1–#4 (below). |
| **I.6 Full docs + PLAYBOOK** | ✅ **complete** — `docs/PLAYBOOK.md` (operating reference) + review docs. |
| I.7 Vectorize into fast_engine + parity | 🔵 next |
| I.8 NSGA-III + win-rate + extended search | ⬜ pending |
| I.9 4h smoke run · I.10 all-TF sweep | ⬜ pending |

## I.5 review changes (approved 2026-06-08)
- **#1 HAR lags** — studied; **keep 1/6/30** (empirical best fit; candle-based confirmed). `docs/HAR_LAG_REVIEW.md`. No code change.
- **#2 Golf → N-candle engulfing** — opposite-colour to all N prior + wick range-engulf + body ≥ 70% of prior span (generation-only). `docs/GOLF_ENGULFING.md`. Commit `ad3ba2a`.
- **#3 Global retrace + wait** — one value each, all indicators (single shared level). `docs/ENTRY_TIMING_CHANGES.md`. Commit `5014017`.
- **#4 Wait on 1-min bars** — wait counts 1-min armed-window bars; decision-bar debounce removed. Commit `5014017`.
- Validation: **78 tests** + PARITY OK (+$7,735/$3,670/66) + FAST-PARITY OK preserved throughout.

## I.3 — built & verified (TDD, 41 tests green)
- **`indicators/classic.py`** — 14 classic indicators (SMA/EMA/RMA/OBV/RSI/TR/ATR/MACD/Stochastic/
  CCI/Bollinger/Keltner/VWAP/MFI). Hand-computed + contract tests. *(Caught + fixed a real `rma`
  NaN-propagation bug that made ADX always-NaN.)*
- **`indicators/base.py`** — `IndicatorConfig` (strict, no silent fallback), `MarketContext`,
  `Indicator` base + vote mapping (confirm/veto/both; `BOTH` sentinel for direction-agnostic veto).
- **`indicators/votes.py`** — pure direction helpers (`stance_directions`, `rsi_directions` zones).
- **`indicators/confirm.py`** — K-rule aggregator + `build_gate` orchestrator.
- **`indicators/library.py`** — 12 Group-A indicator classes + registry/`build()`.
- **`indicators/smc.py`** — FVG (wick geometry + zones), market-structure swings, golf candle,
  **structure-trend** (HH/HL vs LH/LL), **order-block → breaker state machine**.
- **`indicators/library.py`** — 14 indicator classes (12 Group-A + `StructureTrend` + `OrderBlock`).
- **`indicators/runner.py`** — `composite_gate()`: composition into the engine entry gate, aligned to
  the just-closed signal bar.
- **`indicators/generate.py`** — `generate_structures()`: two-phase generator + generation report
  (decision #11), deterministic.
- **Parity lock (real data):** all-off composite gate == vol gate; **engine trades identical** to
  today's strategy when indicators off; enabled indicator ⇒ strict subset of the vol gate.

Tests: `test_classic`(15) · `test_confirm`(11) · `test_library`(7) · `test_smc`(6) ·
`test_integration`(4) · `test_generate`(3) = **46**.

## I.3 — remaining
1. **`wait_bars` timing** — ✅ done. 2. **Retrace-fill resolver** — ✅ done (`timing.py`).
3. **Retrace-fill ENGINE WIRING** — ✅ done (`engine.py` `entry_resolver` hook; verified-engine
   parity preserved). 4. **FVG vote class** — ✅ done (`FVGConfirm`).
5. **Runner-binding semantics** — ✅ **resolved** (RUNNER_BINDING_SEMANTICS.md + INDICATOR_DECISIONS §E2):
   Q1 ParamError, Q2 waive, Q3/Q4 **LIVE per closed decision bar (B1)** + live veto-abort, Q5
   gate=eligibility/resolver=K-count, Q6 live-reading AND wait AND retrace.
6. **Bind in `runner.py` + carry engine** — ✅ done. `runner.build_entry_resolver` (live-B1 confirm +
   K-th-confirm retrace fill). `engine.py` **carry mode** (guarded by `entry_resolver`): arms on a
   gated/non-vetoed signal, **carries an unfilled setup across HOLD bars**, **live veto-abort**
   (`veto_mask`), supersede on new signal. All-off ⇒ no arming ⇒ **parity locks still pass**.
   Verified: retrace=0 immediate, retrace=pts level fill, no-confirmers==baseline, carry-on-later-bar,
   veto aborts.
7. Wire into `strategy.build_payload` (live entrypoint) — **next**, overlaps I.4 dashboard.

**I.3 engine/logic layer is functionally complete.** Suite: **65 tests green** + original parity
locks pass (`test_classic`15 · `test_confirm`14 · `test_library`7 · `test_smc`8 ·
`test_integration`12 · `test_generate`3 · `test_timing`6).

## Invariants held throughout
Off-by-default ⇒ parity · no silent fallback (`ParamError`) · causal/no-look-ahead · OOP "build each
variant, switch by choice" · decision-TF indicators, 1-min exits.
