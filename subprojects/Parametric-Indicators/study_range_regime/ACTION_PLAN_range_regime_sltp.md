# Action Plan / Spec — Price-Range Regime → Dynamic SL/TP study (+ split long/short engine)

**Date:** 2026-06-15 · **Status:** SPEC — awaiting your review before Phase E implementation. · **Decisions
fixed** in `Q1_causality.md`, `Q2_range_and_regime.md`, `Q3_tp_sl_rule.md`. · **North star:** make SL/TP react
to the price-range *regime*, but ship only if it OOS-beats the fixed champion on return/DD.

## 0. Locked decisions (from the Q-docs)
- **Q1 = A** — the rule is **causal** (uses only completed prior periods + the running current period); a
  retrospective full-period view is allowed for **charts/insight only**, never feeds a trade.
- **Q2a = relative margin, basis = % of price** — merge tolerance `margin = pct · price` (default ~5% ⇒ ≈1k at
  20k; `pct` tunable). **Per record we log the resolved margin in points.**
- **Q2b = generate all three TFs (month/quarter/year)**; the study evaluates single-TF, 2-TF intersection, and
  3-TF intersection and **ranks which to use** (it's an output, not an input).
- **Q3a = test both rule directions** (mean-reversion *and* trend-following) and rank by effectiveness.
- **Q3b = A** — study **pinned-SL first, then SL-also-dynamic**.
- **Q3c = split long/short SL/TP from the start** — careful engine change, verbose per-change docs, strict
  broken-logic tests **before** any study uses it; **registered as a post-`wsh4` edit** so a future `wsh5`
  run searches the widened (split) space.

## 1. Definitions (precise)
- **Period range box** (per month/quarter/year): `[min(Low), max(High)]` over that calendar period (intrabar
  extremes, not Close).
- **Causal extremes at decision bar t:** completed prior periods' boxes ∪ the **running** current-period box
  (extremes of `[period_start … t]` only). No future bars.
- **Merge / band identity:** a new box merges into an existing band iff `|top−band_top| ≤ margin` **and**
  `|bottom−band_bottom| ≤ margin`, `margin = pct·price_t`. Merged band = union; bigger swallows smaller. Each
  record logs `margin_pts = pct·price_t`. New box beyond margin → **NEW** band (new-high above all, new-low below).
- **new/repeat:** first time a band appears = NEW; a later bar landing in a known band = REPEAT.
- **trend label (look-back):** `LOW-TREND` = most recent extreme was a low and current range sits higher
  (rising from a low); `HIGH-TREND` = most recent extreme was a high and current range sits lower (falling from
  a high). Computed per TF.
- **TP rule (both tested):** *mean-reversion* = widen TP on counter-trend (HIGH-TREND+long, LOW-TREND+short),
  shrink on with-trend; *trend-following* = the inverse. "widen/shrink" = multiply the base TP by a factor
  (tunable, e.g. 1.0–2.0 widen / 0.5–1.0 shrink), or by ± points — magnitude is swept.

## 2. Phases

### Phase E — Engine: per-direction (split) SL/TP  *(FIRST; hard-gated; no study uses it until green)*
- **E1 — `StrategyParams` + engine line math.** Add optional `long_sl_soft/long_sl_hard/long_tp_soft/
  long_tp_hard` and `short_*` fields. In `engine.py` where entry lines are built (the long vs short branch),
  pick the direction's split values; **if a split field is absent, fall back to the shared `sl_soft_points/…`
  ⇒ byte-identical.** Validate ordering per side (`*_sl_hard ≥ *_sl_soft`, `*_tp_hard ≥ *_tp_soft`). Handle the
  **flip** layer correctly (split applies to the FINAL post-flip direction).
- **E2 — Thread through** `fast_engine` + `optimize/core.backtest_metrics` + the optimizer search space
  (`optimizer._suggest...`: long & short SL/TP bounds), all behind the same fall-back.
- **E3 — Tests + docs (STRICT, before use):**
  - **T1 (parity):** split fields absent ⇒ `check_golden.py` MATCH on all 6 TFs (byte-identical).
  - **T2 (degenerate split):** `long_*==short_*==shared` ⇒ identical to shared (golden).
  - **T3 (direction-consistency):** a long-only and short-only scenario with deliberately different long vs
    short points produces the expected per-side lines (targeted unit test).
  - **T4:** fast vs exact engine parity preserved with split (extend `test_fast_parity`).
  - Verbose `UPDATE_engine_split_sltp.md` — every changed line + why + revert steps.
  - **Registry:** append to the "post-`wsh4` edits" list so `wsh5` includes split bounds (wider search space).
  - **GATE:** all of T1–T4 + golden green before Phase S consumes split.

### Phase S — The regime study  *(causal)*
- **S1 — Causal feature builder** (`regime_features.py`): per TF (M/Q/Y) → running extremes, %-price merge →
  band id, new/repeat, low/high-trend; **logs `margin_pts` per record**. Emits a per-decision-bar table
  (+ the 3-TF intersection columns).
- **S2 — Retrospective charts** (`regime_charts.py`, insight-only, labelled non-tradeable): bands, new
  highs/lows, regime ribbon over 2024–26.
- **S3 — Rule-grid evaluation** (`regime_eval.py`): sweep
  `{TF combo: M | Q | Y | M∩Q | M∩Y | Q∩Y | M∩Q∩Y} × {mean-rev | trend-follow} × {SL pinned | SL dynamic} ×
  {shared | split}` → walk-forward / OOS vs fixed champion, scored on **return/DD**; **ranked effectiveness
  table** (this answers Q2b & Q3a empirically).
- **S4 — Report** (`STUDY_range_regime.md`): ranked results, which combo (if any) OOS-beats fixed, recommendation.

### Phase O — Optimizer integration
- **O1.** Run `wsh5` with the split (and optional regime-TP knobs) in the search space — "repeat the optimizer,
  wider variable space," per Q3c. Pre-registered adopt rule: only swap the champion if it OOS-dominates.

## 3. Guardrails (every phase)
Causal features only · walk-forward + ranked OOS · judge on **return/DD not raw PnL** · **golden byte-match
re-run after every engine touch** · verbose per-change docs + revert steps · fixed champion stays deployed
until something OOS-dominates · split is additive/back-compat (absent ⇒ identical).

## 4. Deliverables
`regime_features.py`, `regime_charts.py`, `regime_eval.py`, `STUDY_range_regime.md`,
`UPDATE_engine_split_sltp.md`, engine/fast_engine/core/optimizer edits + new tests, ranked-results CSV.

## 5. Risks
Small data (17 months → few yearly/quarterly regime points) — mitigated by ranking + walk-forward + the
return/DD bar; engine split touches the hot path — mitigated by the T1–T4 gate before any use; look-ahead —
mitigated by the causal builder + a parity anchor that the regime rule with neutral params reproduces fixed.
