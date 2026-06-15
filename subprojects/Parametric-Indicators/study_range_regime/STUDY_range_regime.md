# Study — Price-range REGIME → dynamic TP (S3 results)

**Date:** 2026-06-15 · Phase S3 of `ACTION_PLAN_range_regime_sltp.md`. Causal regime labels (`regime_features.py`,
no look-ahead) drive a widen/shrink-TP rule; each grid cell's (widen W, shrink S) magnitudes are **fit on TRAIN
(≤2025-06)** then scored on **TEST (2025-07…2026-05)** vs the fixed champion, via the exact engine + the
champion's drawdown breaker. Evaluator: `regime_eval.py` → `results/regime_eval_ranked.csv`.

> **TL;DR — the multi-fold gate flipped the answer.** On a single split, the apparent winner was *Quarterly ·
> mean-reversion · both-dynamic* (ret/DD 5.67 vs 4.17). But **multi-fold walk-forward (6 folds, 2024–2026)
> REJECTED it — it beats fixed in only 2/6 folds** (one-window luck, exactly the selection trap we feared).
> What **survived** is a *different, robust* rule: **trend-following · pinned-SL · widen-only (W1.25, S1.0) on
> the monthly/quarterly regime — beats fixed in 6/6 (M) and 5/6 (Q) folds** (median ret/DD 1.31 vs 1.17). i.e.
> *"when trading WITH the regime trend, let the winner run +25%; keep SL fixed; never shrink."* This is a
> credible, modest edge — but note 2024–26 was largely trending (which structurally favors widen-on-trend), so
> it needs other regimes/instruments + the `wsh5` joint test before deployment. **Fixed champion stays deployed.**
> *(See §Multi-fold validation; this supersedes the single-split ranking below.)*

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

## Multi-fold validation (the gate) — `regime_validate.py` → `results/regime_validate_folds.csv`
Each top-3 cell's FIXED config scored vs the fixed champion across **6 contiguous folds** spanning 2024-01…
2026-05 (causal labels; a fold = a realistic live sub-period). "Beats" = higher fold ret/DD than fixed.

| cell | folds beaten | median ret/DD (cell vs fixed) | verdict |
|------|:---:|:---:|---|
| Q · mean_rev · both · W2.0/S0.6 *(S3 single-split #1)* | **2 / 6** | 0.98 vs 1.17 | ❌ overfit — single-window luck |
| **M · trend_follow · pinned · W1.25/S1.0** | **6 / 6** | **1.31 vs 1.17** | ✅ robust |
| **Q · trend_follow · pinned · W1.25/S1.0** | **5 / 6** | 1.31 vs 1.17 | ✅ robust |

Per-fold: the trend-following widen-only cells beat fixed in every fold except (Q) the early 2024 down-leg;
they add P/L mostly while holding DD ≈ fixed (pinned SL). The mean-reversion/both-dynamic cell only wins in the
two folds that resemble the original test window — confirming its single-split dominance was selection bias.

**Revised answers:** **Q3a — for THIS data the robust direction is TREND-FOLLOWING, not mean-reversion**
(the opposite of the initial hypothesis). **Q3b — pinned-SL (widen-only) is the robust, DD-safe mode.**
**Q2b — month & quarter (not year).** **Caveat:** 2024–26 was largely trending; widen-TP-with-trend is
structurally favored in trends, so the edge may be partly era-driven — needs more regimes/instruments.

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
