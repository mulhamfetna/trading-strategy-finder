# Design — M2 walk-forward validation

**Date:** 2026-07-01 · **Type:** research validation (hardening of the M2 result) · **Status:** design
approved, spec under review · **Anchor:** NQ 4h.

Hardens the **M2 positive result** (`docs/RESEARCH_KALMAN_FUSION_STUDY.md` → "M2 … first mechanism to beat the
champion OOS"). M2's edge was measured on a *single* 2025/2026 split; θ-selection on one split is noisy. This
validates whether the edge **survives across time** before we build M2b or wire M2 anywhere.

---

## 1. Goal & question

**Question:** deployed as a walk-forward strategy — θ learned only from history, applied forward — does M2 still
admit dropped signals that **beat the champion out-of-sample, in a majority of test quarters**? Or was the
single-split lift an artifact of picking θ on one 2026 holdout?

**Goal:** a decisive per-fold + aggregate walk-forward table (M2 test P/L vs champion test P/L per quarter) and a
✅/❌ verdict. Not a bigger number — a *robustness* read (the discipline that made the ES verdict and l2v3
rejection trustworthy).

**Non-goals:** no exit changes; no wide config/hyperparameter search (that re-introduces the multiple-comparisons
risk walk-forward exists to kill — run only the two lead configs); no production wiring; M2b + dashboard are
gated on this verdict.

## 2. Scheme — expanding-window, quarterly

- Partition the data span (2025Q1 → 2026Q2) into calendar quarters (by `C["d"]["Date"]`).
- For each **test quarter** from **2025Q3** onward (first fold has ≥2 quarters of train history): **train** = all
  decision bars strictly before the quarter (expanding); **test** = the quarter's bars. ~4 folds.
- Respects causality: a fold's train always precedes its test; θ is chosen on train only.

## 3. Per-fold procedure

For fold with test quarter `Q` (train = bars `[0, q_start)`, test = `[q_start, q_end)`):
1. **Select θ\* on train.** Build the |z|-quantile grid over the **train-window dropped signals** (`i < q_start`);
   sweep; pick `θ* = argmax` of the **train-window** total P/L (combined book restricted to train-entry trades),
   for the given `(frame, mode)`.
2. **Score test.** Run the deployed book with `θ*` applied to *all* dropped signals (one consistent policy); sum
   only trades **entering in `[q_start, q_end)`** → M2 test Metrics.
3. **Baseline.** Run the champion book (engine gate, no admits); sum only its `Q`-entry trades → champion test
   Metrics. Compare M2 vs champion on identical out-of-sample bars.

Run for the **two lead configs**: `4h · filter` and `combined · redirect`.

## 4. Verdict criterion

- ✅ **Edge is real** if aggregated walk-forward test P/L (Σ over folds) beats the champion over the same
  quarters, **in a majority of folds**, at win-rate above the 57.5% breakeven.
- ❌ **Single-split was lucky** if positive in only one quarter / negative in aggregate → the magnitude was
  overstated; record it, don't size M2, and reconsider before M2b.

## 5. Modules, tests, deliverable

**New (`research/kalman_fusion/`):**
- `m2_walkforward.py` —
  - `quarter_folds(C) -> list[dict]` — per fold: `{q, q_start, q_end}` bar-index bounds (expanding train implied
    by `q_start`), test quarters 2025Q3 → 2026Q2.
  - `select_theta_train(C, z, mode, train_hi) -> float` — θ\* by argmax train-window P/L over the train
    |z|-quantile grid (dropped signals with `i < train_hi`).
  - `evaluate_quarter(C, z, theta, mode, q_start, q_end) -> (m2_metrics, champ_metrics)` — window-scored M2 vs
    champion for the quarter.
  - `walk_forward(C, z, mode) -> dict` — per-fold rows + aggregate (`sum_m2_pnl`, `sum_champ_pnl`,
    `folds_m2_wins`, `n_folds`).
- `run_m2_wf.py` — CLI: run `4h·filter` + `combined·redirect`, print per-fold table + verdict.

**Tests (`test_m2_wf.py`, TDD):**
1. `quarter_folds`: folds are causal (train precedes test), expanding (`q_start` increases), cover 2025Q3→2026Q2.
2. `evaluate_quarter`: θ=∞ reproduces the champion's *own* trades in that quarter (M2==champ, admits none); the
   per-quarter M2 test P/L for a fixed θ sums (over all quarters) to the full-period book's total for that θ.
3. `select_theta_train`: θ\* is unchanged when a *test-quarter* signal's z is perturbed (depends on train only).
4. `walk_forward`: returns `n_folds` rows + aggregate; `folds_m2_wins ≤ n_folds`.

**Deliverable:** extend `docs/RESEARCH_KALMAN_FUSION_STUDY.md` with the walk-forward table (per fold: quarter,
θ\*, M2 test P/L, champion test P/L, M2 win%) + aggregate + the ✅/❌ verdict.

**Compute:** cheap (reuses `rig.run_book`/`fast_backtest`); local single-process. Golden gate untouched
(research off-path).

## 6. Success criteria & risks

**Success:** a clear per-fold + aggregate walk-forward result and an unambiguous verdict on whether M2's edge is
time-robust. **Risk:** the test quarters are small (~90 dropped signals each) → per-quarter estimates are noisy;
the aggregate + majority-of-folds rule mitigates this, and a split verdict (e.g. 2/4 folds) is itself the honest
answer ("promising but not proven — needs more data / a longer forward test"). The θ-on-train step can still pick
a noisy θ; that is exactly the failure mode we want to expose.
