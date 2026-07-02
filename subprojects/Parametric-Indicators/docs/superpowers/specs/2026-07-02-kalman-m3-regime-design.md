# Design — M3 vol-regime exits & admission

**Date:** 2026-07-02 · **Type:** research (final mechanism of the Kalman/fusion study) · **Status:** design
approved, spec under review · **Anchor:** NQ 4h.

Final untested idea in `docs/RESEARCH_KALMAN_FUSION_STUDY.md`. M0 established payoff-per-trade is **pinned by the
fixed exits** (breakeven win-rate = 1/(1+0.74) = **57.5%**); M1 (discrete multi-TF votes) failed OOS; M2 (Kalman
trend) beat the champion on a single split but **deflated to marginal under walk-forward**. M3 is the only idea
that can move the **payoff** lever rather than just admit more signals: let the **volatility regime** decide both
how we *exit* trades and which dropped signals we *admit*.

---

## 1. Goal & question

**Question:** does the market's realized-vol **regime** carry exploitable information — (3a) about the *right exit*
for trades we already take, and (3b) about which dropped signals are tradeable in their native direction — that
**survives walk-forward** out-of-sample?

**Goal:** a decisive per-fold walk-forward table for **3a exits-first**, a ✅/❌ verdict, and — only if 3a
survives — the same for **3b admission**. Not a bigger single-split number; a robustness read, the discipline that
made the ES verdict, the l2v3 rejection, and the M2 deflation trustworthy.

**Non-goals:** no production wiring; no wide hyperparameter sweep (a-priori exit schemes only — the
multiple-comparisons risk walk-forward exists to kill); golden path untouched (all code off-path under
`research/kalman_fusion/`).

## 2. Regime signal (shared by 3a & 3b)

- **Regime = realized-vol tercile of `vf`** (the HAR-RV forecast already aligned 1:1 with decision bars, surfaced
  from the champion context).
- **Causality:** tercile cut-points (`q33`, `q67`) frozen on the **train slice only** (`vf[:train_hi]`), applied
  forward. Never re-fit on test bars. (Same discipline that fixed the M2 θ-scaling bug.)
- Three regimes {LO, MID, HI} — finest cut that keeps each fold's per-regime sample above the ~30-trade floor.

## 3. 3a — regime-scaled EXITS (decisive gate, runs first)

**Population:** the champion's own taken trades (~214 @ 4h) — asks "could we have exited these *better* per
regime," not "take more."

**A-priori exit schemes** (multipliers on champion `(sl_soft, sl_hard, tp)`, fixed before seeing results):
- `TIGHT` = ×0.75 · `BASE` = ×1.0 (null / champion) · `WIDE` = ×1.5.

**Per-fold procedure** (expanding-quarter folds, reused from `m2_walkforward`):
1. Label each trade's entry-bar regime (frozen train terciles).
2. Re-simulate each trade in **isolation** under each scheme via `simulate_one_custom` (real 1-min path, real
   entry, only exit lines move ⇒ no look-ahead).
3. **On train only:** pick P/L-max scheme **per regime** → mapping `{LO→?, MID→?, HI→?}`.
4. **On test:** apply frozen mapping; score vs champion's actual exits on the same test-quarter trades.

**Decision rule:** if the learned mapping does not beat `BASE`-everywhere OOS across folds, **3a is dead and 3b is
abandoned** (regime can't improve exits on good trades ⇒ won't rescue marginal ones).

## 4. 3b — regime-gated ADMISSION (only if 3a survives)

Reuse the M0/M2 rig. Per regime, on **train**, measure native-direction win-rate of eligible-dropped signals.
Admit a regime only if train win-rate clears **57.5% breakeven** with margin. Exit admitted trades via 3a's
regime→scheme mapping. Score on test, walk-forward, vs champion.

## 5. Modules (all under `research/kalman_fusion/`, off production path)

- `counterfactual_pause.py` — **additive:** surface `vf`, `n_split` in the `C` dict; add
  `simulate_one_custom(C, idx, sls, slh, tp, flip)` (existing `simulate_one` with exit params exposed).
- `m3_regime.py` — `regime_labels(vf, train_hi)`; `EXIT_SCHEMES`; `rescore_trade(C, trade, scheme)`;
  `learn_exit_map(C, trades, regimes, train_mask)`; `apply_exit_map(...)`; `admit_by_regime(...)`.
- `m3_walkforward.py` — `walk_forward_3a(C)`, `walk_forward_3b(C)` (reuse `quarter_folds`).
- `run_m3.py` — CLI: per-fold 3a table + verdict, then 3b only if 3a survived.

## 6. Tests (`test_m3.py`, TDD — written first)

1. Regime causality — train labels depend only on `vf[:train_hi]`.
2. Tercile balance — ~1/3 each on train slice.
3. `BASE` re-sim identity — ×1.0 rescore reproduces champion trade P/L.
4. No look-ahead — rescored P/L uses only that trade's own forward path.
5. Exit-map train-only — `learn_exit_map` never reads test-masked bars.
6. Breakeven gate — 60% regime admits, 55% doesn't.

## 7. Reporting

Walk-forward only. The **single** headline is the aggregated per-fold OOS result. 3a verdict gates 3b; if 3a
fails, M3 closes and the study closes with it.
