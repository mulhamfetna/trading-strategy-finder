# Design — L2 intra-candle entry timing for vetoed signals (E3a)

**Date:** 2026-07-03 · **Type:** feature (entry-increasing, L2) · **Status:** design approved, spec under review ·
**Anchor:** NQ 4h. L1 = frozen champion (intra-candle OFF). Experiment log: `docs/INTRACANDLE_EXPERIMENTS_LOG.md`
(this is checklist item **E3**).

Follows E2 (`INTRACANDLE_VETO_ENTRY_PHASE1_RESULTS.md`): in L1 the intra-candle feature increases entries + P/L but
**worsens L1's profit-to-drawdown ratio** and is dominated by re-tuned exits. **E3a isolates the feature in L2** —
where L2's own exits + drawdown breaker + L1-priority force-close contain the extra drawdown — so it can add value
without touching the proven L1 champion.

---

## 1. Goal & question

**Question:** does entering L2's **veto-dropped** signals with **intra-candle timing** (mid-candle, when L1's veto
clears) instead of at the 4-hour candle close — booked in L2 with L2's own settings — improve the **combined** book
(more P/L / more entries) **without** degrading the combined drawdown, keeping L1 untouched?

**Goal:** an additive, default-off L2 timing toggle + tunable wait window `N`, testable on the champion and
searchable by the L2 optimizer, with the existing L2 2025/2026 OOS split. **Non-goals:** no L1 change (champion
frozen); no change to L2's vol-gated stream; no separate force-close knob (reuse L1-priority); the "L2 rescues its
OWN vetoed signals" idea is **E3b**, a follow-on (§7), not this spec.

## 2. Today (baseline) — what L2 already does

L2 receives L1's **veto-dropped + vol-gated** signals (`l1_runner.run_l1` → `dataset.build_dataset` →
`engine.run_l2`) and enters each flat candidate **at the decision-bar (candle) close** with L2's **own**
SL/TP/gate/breaker/cooldown/flip. It's force-closed when L1 opens a trade (L1-priority). Combined anchor:
**L1 $149,989 + L2 $25,383 = $175,372 / 289 trades / $14,342 DD** (`optimize/l2/test_parity_anchor.py`).

## 3. The change — an intra-candle timing toggle on L2's VETOED stream

When `l2_intracandle` is **on**, for each **vetoed** L2 candidate (L1-vetoed, vol-passed, L1-flat), L2 enters at
the **first 1-minute bar inside the candle where L1's veto clears** (L1's champion full gate `¬veto ∧ ≥K confirms`
re-opens), within L2's wait window `N` (`l2_intracandle_max_wait`); if it never clears in the candle, that
candidate is **skipped**. L2's own exits/breaker then apply. The **vol-gated** stream is **unchanged** (the vol
gate is per-candle and cannot clear mid-candle — same scope rule as the L1 feature: vetoed-vol-passed only).

- The intra-candle gate uses **L1's champion indicators** (the veto that dropped the signal) — already computed in
  `l1_runner`; reuse `indicators.intracandle.build_resolver` + the memoised gate (`runner.intracandle_gate_arrays`
  / `core._cached_ic_gate`).
- `l2_intracandle` **off** ⇒ L2 enters at the candle close exactly as today ⇒ byte-identical.

## 4. Settings & optimization

- **New L2 params (additive, in `optimize/l2/payload.validate_layer_params`):** `l2_intracandle: bool = False`,
  `l2_intracandle_max_wait: int = 240`. Absent/off ⇒ round-trips unchanged (mirror the optional contributor block).
- **L2 optimizer (`optimize/l2/optimize.py`):** add `l2_intracandle_max_wait` (N ∈ {30,60,120,240}) — and the
  on/off (or force-on for a focused study) — to `suggest_l2_params`, guarded so the default L2 search space is
  unchanged. New study prefix **`l2ic1`** (never reuse; `l2v1`/`l2v2` untouched). Objective + feasibility
  (DD ≤ cap·P/L) + **2025-train / 2026-test windows** are the L2 optimizer's existing ones ⇒ **OOS built in**.

## 5. Golden-safety

`l2_intracandle` off in `PERMISSIVE` + `l2_default_params` (the l2v2 champion sets none of the new keys) ⇒
`validate_layer_params` round-trips ⇒ the frozen-oracle fast path + `test_parity_anchor.py` stay green
(L2 $25,383, combined $175,372). A **new anchor test** is added once an `l2ic1` champion is locked.

## 6. Components / seams (from the L2 architecture map)

- `optimize/l2/l1_runner.py` — for each vetoed dropped signal, compute the **intra-candle entry bar** (first
  1-min bar L1's veto clears within N) using L1's champion gate; tag it on the candidate.
- `optimize/l2/dataset.py` — `DroppedSignal` gains an intra-candle entry offset/timestamp field; counts updated.
- `optimize/l2/engine.run_l2` — when `l2_intracandle`, enter vetoed candidates at the intra-candle bar/price
  (not the decision-bar close) via L2's `fast_backtest` path; vol-gated unchanged; L1-priority force-close as-is.
- `optimize/l2/payload.py` — schema (validate + default off).
- `optimize/l2/optimize.py` — search dim (N) + prefix `l2ic1` + champion export.
- `optimize/l2/test_parity_anchor.py` — unchanged anchors green (off); new anchor when champion locked.

## 7. Testing & rollout

1. **Champion-first:** run L2 with `l2_intracandle` on (current L2 champion exits, sweep N ∈ {30,60,120,240})
   → report **combined** P/L, entries, and **combined DD** vs today's $175,372 / $14,342.
2. **Then optimize** (`l2ic1`, N searchable) → extract champion → compare combined P/L + DD; the L2 optimizer's
   **2026 window** is the OOS read. Promote only if combined improves at held-or-better combined DD.
3. **E3b (follow-on, own spec):** give L2 its own intra-candle rescue on **L2's own** vetoed signals (L2-as-L1).
