# FU-6 (#158) — per-event outcome prediction: pre-registration

**Filed 2026-08-20 BEFORE any run. The last B-family study: can the 165-registry's stance
vector at rel−300s classify winning vs losing ride events? This is the overfit trap the
brainstorm named (330 columns × small n), so the design is EXPLORATION-GRADE with a locked
holdout: fixed models, fixed hyperparameters, one look at each holdout, promotion only via a
fresh pre-registration. Expectation recorded now: NULL is the likely outcome — direction
died three ways, and FU-5's engineered states just failed; this study measures whether the
LIBRARY as a whole sees what single features do not.**

## Fixed design

- **Data**: the frozen FU-9 v1 dataset, deployed-leg series only (NQ/RTY {CPI,NFP,FOMC},
  ES/YM {CPI}); target = ride WIN (`ride_net_stressed_usd > 0`); features = the 330 stance
  columns, minus columns with zero variance on the TRAINING SLICE only (no other selection).
- **Split (locked)**: TRAIN = NQ events before 2022-01-01. HOLDOUT-1 = NQ ≥2022 (one look).
  HOLDOUT-2 = ES, RTY, YM (fully untouched by training; one look).
- **Models (fixed, no tuning, no CV)**: ① logistic regression, L2, C=1.0, saga,
  max_iter=2000, features as-is (int8 stances); ② decision tree, max_depth=3,
  min_samples_leaf=20. Nothing else will be fit.
- **Metrics**: AUC per holdout; the money statistic = mean net difference between
  predicted-top-half and bottom-half events on HOLDOUT-1 (threshold = the TRAIN median
  predicted probability), event-bootstrap 90% CI.
- **Dumb control**: 20 label-shuffled retrains — the real HOLDOUT-1 AUC must exceed the
  shuffled 95th percentile.

## Pre-registered verdict rule (per model)

- **ARMED** iff HOLDOUT-1 AUC ≥ 0.58 AND above the shuffle p95 AND the top-minus-bottom net
  difference CI90 > 0 AND the AUC direction holds (>0.5) on ≥2 of the 3 HOLDOUT-2 legs.
  Armed = a fresh confirmatory pre-registration may be filed; nothing changes anywhere.
- **CLOSED-NULL** otherwise, with MDE. If BOTH models close null, FU-6 closes null and the
  B-family is complete: the ride enters state-blind with the full library measured.

## Blind spots (declared)

1. Default-parameter stances only (the library's information, not any tuned champion's).
2. Cross-series stance columns are structurally zero in FU-9 v1 (declared there).
3. n_train is small (~NQ pre-2022 events); the logistic may saturate in-sample — only the
   holdouts speak.
4. The four legs share CPI moments; HOLDOUT-2 is semi-independent as always declared.
5. Win/lose binarization discards magnitude — deliberate (the +4R tail question belongs to
   the money statistic, not the classifier).
