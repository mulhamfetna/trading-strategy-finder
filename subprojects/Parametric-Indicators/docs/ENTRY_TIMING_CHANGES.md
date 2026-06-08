---
name: entry-timing-changes
description: WS-I review #3/#4 — retrace + wait are now GLOBAL (one value each, all indicators) and wait counts 1-MINUTE bars (not decision/4h bars). Supersedes the earlier per-indicator + decision-bar design.
type: change-note
status: implemented
created: 2026-06-08
workstream: WS-I
---

# Entry-timing redesign — global retrace + 1-minute wait (review #3/#4)

Supersedes the earlier **per-indicator** retrace/wait and the **decision-bar** wait debounce.

## #3 — retrace + wait are GLOBAL (one value each, applied to ALL indicators)
- **Before:** every indicator carried its own `retrace_amount`/`retrace_unit`/`wait_bars`; the fill
  used the **K-th confirm's own level** (N distinct pullback levels).
- **Now:** a single global `retrace_amount` + `retrace_unit` and a single global `wait_bars` (the two
  new boxes in the Confirmation panel). All confirmers share **one** pullback level
  `signal_close ∓ r` (`r` in points, or `atr_mult × ATR[signal_bar]`). The K-rule is unchanged in
  spirit: ≥K confirm-capable indicators must vote CONFIRM at the just-closed bar (live B1); then the
  single global level must be reached on the 1-min path.
- `IndicatorConfig` no longer has retrace/wait fields; `from_specs` ignores them; validation moved to
  `strategy.validate_params` (global, strict → `ParamError`/HTTP 400). `timing.resolve_retrace_entry`
  (multi-level) is retained but unused by the live path; `timing.resolve_entry_1min` is the new
  single-level resolver.

## #4 — wait counts 1-MINUTE bars, not decision (4h) bars
- **Before:** `apply_wait` debounced the **decision-timeframe** vote series — `wait=N` meant "confirm
  must persist N+1 consecutive 4h bars". (Indicator votes only exist at decision-bar resolution.)
- **Now:** `Indicator.vote` returns the **raw** per-decision-bar vote (no debounce). `wait_bars` is a
  count of **1-minute** bars inside the armed window: the entry is ineligible for the first
  `wait_bars` 1-min bars after the signal, then fills (with retrace `r>0` → at the first eligible
  1-min bar that touches the level; with `r=0` → at the wait-th 1-min bar, at `signal_close`).
  Both retrace and wait now live on the **same 1-min armed-window path** (`timing.resolve_entry_1min`).

## Parity & validation
- **Off-by-default unchanged:** no enabled indicators ⇒ `entry_resolver=None` ⇒ byte-for-byte the
  verified engine. Parity locks green: `test_parity.py` **+$7,735 / $3,670 / 66**, `test_fast_parity.py` OK.
- Global `retrace=0` **and** `wait=0` ⇒ immediate fill at signal close (same as before).
- **77 unit/integration tests pass.** Bad global params (`wait_bars<0`, bad `retrace_unit`,
  `retrace_amount<0`) → `ParamError` → HTTP 400 (no silent fallback).

## Touch points
`indicators/base.py` (config + raw vote) · `indicators/timing.py` (`resolve_entry_1min`) ·
`indicators/runner.py` (`build_layer`/`build_entry_resolver` take global retrace/wait) ·
`indicators/library.py` (`from_specs`) · `strategy.py` (validate + pass-through) ·
`frontend/index.html` (one global retrace box + one global wait box; per-row controls removed) ·
`tests/{test_confirm,test_integration}.py`.
