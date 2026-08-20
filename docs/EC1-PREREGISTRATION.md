# E-C1 — earnings × indicators: pre-registration (the conditioning phase opens)

**Filed 2026-08-20 BEFORE any run. The owner's roadmap phase "earnings × indicators", run
under the fusion era's full discipline and carrying its hardest prior: on the macro
calendar, tape-state conditioning measured ≈ZERO everywhere it was tried (FU-5 null ×2,
FU-6 bar-held, FU-2 seasonality). The question is chosen to be the one a null or a pass
would both inform: not "can state gate a dead trade" (H1's ride is rejected — conditioning
it answers nothing anyone will use) but the programme's one live quantity — SIZE. Does the
165-indicator state vector carry size information BEYOND the ticker's own history
(P_hist)?**

## Fixed design

- **Data**: the frozen E-S1 v1 dataset, scored rows only (pred non-NaN). Features: P_hist
  (`pred`) + the 330 stance columns (train-slice variance filter only). Target:
  `jump_pct` (the realized event-minute |move|%).
- **Split (locked, the FU-6 pattern)**: TRAIN = NQ events before 2023-01-01; HOLDOUT-1 =
  NQ ≥2023 (one look); HOLDOUT-2 = ES, fully untouched (one look).
- **Models (fixed, no tuning)**: ① ridge regression (alpha=1.0) on [P_hist, stances];
  ② depth-3 tree regressor (min_samples_leaf=20) on the same. Baseline: P_hist alone
  (rank scorer — no fit needed).
- **Decision statistic**: ΔSpearman on HOLDOUT-1 = ρ(model prediction, jump) −
  ρ(P_hist, jump); event-bootstrap 90% CI (10,000).
- **Control**: 20 retrains with the STANCE BLOCK row-permuted (P_hist kept aligned) — the
  real Δ must exceed the permuted 95th percentile (else the "state information" is the
  extra degrees of freedom).

## Pre-registered verdict rule (per model; two models = two tests, no third)

- **ARMED** iff HOLDOUT-1 ΔSpearman > 0 with CI90 > 0 AND above the permuted p95 AND the
  ES HOLDOUT-2 Δ positive in sign. Armed = a state-augmented power forecast becomes a
  registered follow-up (an FU-14-pattern information-layer candidate); nothing trades.
- **CLOSED-NULL** otherwise, with MDE. If both models close null, the conditioning phase
  CLOSES with the law extended: state carries no incremental information on either
  calendar, for direction, outcome, or size — the strongest form of the state-blind result.

## Expectations recorded now (honesty anchors)

The prior says NULL: the fusion era found the library barely above noise on outcomes, and
P_hist is a strong own-history baseline (ρ≈0.46). The one mechanism that could beat the
prior: stances summarize the CURRENT tape regime while P_hist is regime-lagging (expanding)
— if pre-event tape state proxies the power regime, ridge may add a little. FU-5's macro
finding (pre-release tape vol mildly ANTI-predictive for outcomes) cuts the other way.
A NEGATIVE Δ that clears the permuted band would be a real finding too (state actively
misleads) — recorded as CLOSED-CONTRARIAN, not traded, per the FU-5 precedent.

## Blind spots (declared)

1. All E-S1 declarations inherit (acceptance smear, AMC thin bars, default params, NQ/ES).
2. n_train ≈ 200 with 331 features — the ridge leans on regularization; only the holdouts
   speak (the FU-6 lesson).
3. Two models × one look each; the 2023 split (not 2022) balances H1 size on the earnings
   calendar's density — chosen a priori, recorded here.
