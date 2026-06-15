# Study — Price-range REGIME → dynamic TP (S3 results)

**Date:** 2026-06-15 · Phase S3 of `ACTION_PLAN_range_regime_sltp.md`. Causal regime labels (`regime_features.py`,
no look-ahead) drive a widen/shrink-TP rule; each grid cell's (widen W, shrink S) magnitudes are **fit on TRAIN
(≤2025-06)** then scored on **TEST (2025-07…2026-05)** vs the fixed champion, via the exact engine + the
champion's drawdown breaker. Evaluator: `regime_eval.py` → `results/regime_eval_ranked.csv`.

> **TL;DR — promising, NOT yet proven.** On this single train/test split, **5 of 28 cells beat the fixed
> champion on out-of-sample return/DD**, and the best one **OOS-dominates** it (more profit AND less drawdown):
> **Quarterly regime · mean-reversion · both-dynamic (W2.0/S0.6)** → ret/DD **5.67 vs 4.17**, P/L **$75.8k vs
> $67.6k**, maxDD **$13.4k vs $16.2k**, n=119. **But** this is the best of 28 cells on ONE OOS window (n≈120,
> a single V-shaped regime) — the textbook selection/overfit trap the prior councils + research flagged. It is
> a **signal worth a proper multi-fold validation**, not a deploy-ready edge.

## Fixed baseline (parity-anchored; matches the prior sub-optimizer study exactly)
TEST: P/L **$67,627**, maxDD **$16,204**, ret/DD **4.17**, n=122.

## Top cells by TEST return/DD
| TF | rule | SL mode | W | S | TEST P/L | TEST DD | ret/DD | n | win% | vs fixed P/L | beats? |
|----|------|---------|--:|--:|---------:|--------:|-------:|--:|-----:|-------------:|:------:|
| **Q** | **mean_rev** | **both** | 2.0 | 0.6 | **75,774** | **13,368** | **5.67** | 119 | 68.1 | **+8,147** | ✅ |
| M&Q | mean_rev | both | 2.0 | 0.6 | 75,774 | 13,368 | 5.67 | 119 | 68.1 | +8,147 | ✅ |
| M | trend_follow | pinned | 1.25 | 1.0 | 72,435 | 16,204 | 4.47 | 121 | 66.9 | +4,808 | ✅ |
| Q | trend_follow | pinned | 1.25 | 1.0 | 69,430 | 16,204 | 4.29 | 121 | 66.9 | +1,803 | ✅ |
| M&Q | trend_follow | pinned | 1.25 | 1.0 | 69,430 | 16,204 | 4.29 | 121 | 66.9 | +1,803 | ✅ |
| FIXED | — | — | — | — | 67,627 | 16,204 | 4.17 | 122 | — | 0 | — |

## What this answers (empirically, on this split)
- **Q2b (which TF / intersection):** **month & quarter carry the signal; year does not** — every beating cell is
  M, Q, or M&Q; all Y-involving combos sit at/below fixed (year is all-NEUTRAL-dominated over 17 months → too
  coarse). The M&Q intersection equals Q here (they rarely disagree in this data), so the quarterly regime is
  the effective driver.
- **Q3a (rule direction):** **no clean winner — it interacts with the SL mode.** Mean-reversion wins when SL+TP
  both scale (the top cell); trend-following wins as a *pinned-SL, widen-only* rule (W1.25/S1.0: same DD as
  fixed, extra P/L on with-trend trades). So "widen TP on counter-trend AND scale SL" vs "widen TP on with-trend,
  keep SL" are two different, both-plausible mechanisms.
- **Q3b (SL):** both modes appear among winners; the single best uses **both-dynamic**, but the *safest* winners
  (DD unchanged) are **pinned-SL widen-only**.

## ⚠️ Why this is NOT yet a green light (the rigor)
1. **Selection across 28 cells on ONE OOS window.** With 28 cells, ~some beat fixed by chance; "best of 28" is an
   inflated estimator (Bailey & López de Prado Minimum-Backtest-Length; the same trap that inflated the ATR
   dashboard "+21%"). 5/28 (18%) beating is *encouraging but not significant* without a selection penalty.
2. **n≈120 OOS trades, one regime** (the V-shaped 2025–26). A single split can't separate edge from luck.
3. **Quarterly regime = very few quarters** (~7–10) → the label is coarse; one or two quarters' alignment can
   drive the result.
4. **Magnitudes were train-fit (good, no look-ahead there); cell *selection* was not cross-validated.**

This is **materially better than the ATR study** (which collapsed to fixed-parity under honest conditions —
here the top cell beats on BOTH P/L and DD OOS with causal features and frozen magnitudes), but one split is not
proof.

## Recommended next step (the gate before adoption / wsh5)
**Multi-fold walk-forward validation of the top ~3 cells** (rolling-origin OOS folds, not one slice), with a
**selection-adjusted** read (does the cell win across MOST folds, or just this one?). Only if a cell wins
robustly across folds does it earn a `wsh5` joint search (Phase O, where the split long/short bounds also enter)
and, ultimately, a champion swap under the pre-registered "OOS-dominates" rule. The fixed champion stays
deployed until then.

## Artifacts / reproduce
`regime_features.py` (causal labels) → `regime_eval.py --pct 0.05` → `results/regime_eval_ranked.csv`.
Engine levers used: `tp_mult` (pinned-SL), `sl_tp_mult` (both-dynamic). Split long/short SL/TP (E1) is reserved
for the `wsh5` joint search (Phase O).
