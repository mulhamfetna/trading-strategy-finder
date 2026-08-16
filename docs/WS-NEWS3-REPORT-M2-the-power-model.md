# WS-NEWS3 M2 — the power model: release |move| is predictable the night before, and power ≠ premium

**Date:** 2026-08-16 · **Issue:** #126 (M2), parent #124 · pre-registered on #126 before the first run
**Verification:** primary PASS 5/5 · V3 shuffle PASS 5/5 · control PASS 5/5 · V1 4/5 (NQ failed as
registered, cause diagnosed) · V2 3/5 (NQ/ES failed as registered — a category error in MY
registration, kept in the record) · ledger **24/24** (`P2-POWER-MODEL-CONFIRMED`,
`P2-FP-ADDS-NOTHING`, `P2-REGIME-LAG`) · selftest 5/5 · evidence committed (21a257f)

---

## Part 0 — The question and the model

Phase 2 (#116) proved the *surprise* explains the jump (ρ to −0.63) — but the surprise needs
`actual`, which arrives WITH the move. M2 asks: **how much of the release's power is knowable the
night before?** The model is deliberately the dumbest defensible one:

> **P_hist = the expanding median of the same (series × instrument)'s prior release-bar |open→close|%,
> shifted one release** (never sees the event it predicts; ≥8 priors required, exclusions counted).

If series identity + its own history can't rank releases by power, nothing pre-release can.
`|forecast − previous|` is tested as an *add-on*, not baked in.

## Part 1 — The pre-registered primary: PASS on all five instruments

Pooled out-of-sample Spearman(P_hist, realized release-bar |move|%), Fisher-z 95% CI:

| instrument | ρ (OOS) | 95% CI | n | shuffle p95 (V3) | control minutes |
|---|---|---|---|---|---|
| NQ | **+0.530** | [+0.466, +0.589] | 534 | +0.168 | +0.117 |
| ES | **+0.515** | [+0.450, +0.575] | 534 | +0.122 | +0.041 |
| GC | **+0.472** | [+0.403, +0.536] | 531 | +0.047 | −0.042 |
| CL | **+0.546** | [+0.508, +0.583] | 1,349 | +0.127 | +0.109 |
| RTY | **+0.582** | [+0.511, +0.645] | 378 | +0.240 | +0.097 |

- Every pre-registered CI lower bound > 0 — **the model is useful by the criterion fixed in advance.**
- **V3 (the falsifier that could have voided everything):** rebuilding P_hist under 200 random
  series-label shuffles collapses ρ to ≈ +0.1 (p95 well below observed on all five). The model's
  content is **series knowledge**, not volatility clustering.
- **Dumb control:** the same predictions scored against matched clean no-news minutes drop to
  ρ ≤ +0.15 everywhere.

**Secondary — the last consensus hope dies:** `|forecast − previous|` adds NOTHING to the residual
(NQ −0.003 p=0.95; max |ρ| across five instruments 0.084, and that one is *negative*), with the
null powered to ρ ≈ 0.16. Together with H1-B/C (direction) this closes every pre-release use of the
consensus numbers: **before the release, the consensus tells you neither direction nor size beyond
what the series' own history already said.**

## Part 2 — The two registered gates that FAILED, and what each was worth

**V2 failed on NQ/ES — a category error in my own pre-registration.** I required "CPI in the top-2
predicted power" because M1 put CPI on top — but M1 ranked **premium** (signed $) and M2 ranks
**power** (|move|). By power, the model put **NFP and FOMC** on top (NQ realized medians 0.178% /
0.135% vs CPI 0.188% *mean-tail-driven* but lower median) — which is the classic, correct prior.
The gate is not re-scored; it failed as registered, and the lesson is pinned:

> ⭐⭐ **POWER ≠ PREMIUM.** NFP and FOMC are the biggest movers with ~zero-to-negative long premium;
> CPI is the third-biggest mover with by far the largest premium. A straddle filter needs BOTH
> columns: |move| (does the prize clear the cost floor?) and premium (which leg to tilt, if any).

**V1 failed on NQ (+0.70 quintile monotonicity) — and the diagnosis became the third claim.**
CPI events sit in *mid* prediction buckets but realize *top-tier* moves:

| NQ, expanding model | predicted median | realized median | ratio |
|---|---|---|---|
| CPI (Inflation Rate MoM) | 0.0451% | 0.1875% | **4.16× — the lag** |
| NFP (stable power) | 0.1336% | 0.1782% | 1.33× — no lag |

⭐ **The expanding median lags regime shifts**: the window still remembers 2016–2020, when CPI moved
nothing. The lag is regime-specific, not model bias — NFP, whose power never shifted, is predicted
almost exactly (that contrast is `P2-REGIME-LAG`'s V3).

## Part 3 — The declared post-hoc variant: trailing-24

Reported **beside** the pre-registered primary, never instead of it; identical gates:

| instrument | primary ρ | trailing-24 ρ | V1 quintiles |
|---|---|---|---|
| NQ | +0.530 | **+0.591 [+0.533, +0.643]** | ⛔ +0.70 → **+1.00 PASS** (buckets 0.041 → 0.475, perfectly monotone) |
| ES | +0.515 | **+0.572** | +1.00 |
| GC | +0.472 | **+0.493** | +1.00 |
| CL | +0.546 | +0.546 | +1.00 |
| RTY | +0.582 | **+0.618** | +0.90 |

The variant shrinks the CPI lag (NQ 4.16× → 2.73×; **RTY 1.04× — closed**, its history carries no
stale pre-2021 weight) and its V3/control gates pass 5/5. Remaining honesty: trailing-24 on a
monthly series is a two-year window — it still lags fast regimes by up to that much (pinned in the
claim's blind spot).

## Part 4 — The deliverable: the M3 selection table (trailing-24, current-regime view)

Predicted release-bar |move|% (the straddle's prize estimate), with M1's premium column joined:

| release | NQ power | RTY power | GC power | CL power | premium (M1) |
|---|---|---|---|---|---|
| NFP | **0.148%** | 0.266% | **0.278%** | 0.124% | weak +, ns |
| FOMC | 0.135% | 0.117% | 0.158% | 0.098% | ~0 / negative |
| **CPI** | 0.069% (realized 0.188%) | **0.388%** (#1 on RTY) | 0.144% | 0.086% | **the engine: +$424/ev NQ** |
| EIA crude (CL) | — | — | — | **0.280%** ⚠️unverified | none (S4: 57.4% < 71%) |
| Retail Sales | 0.052% | 0.054% | 0.089% | 0.040% | negative |
| Durables | 0.022% | 0.033% | 0.052% | 0.042% | ~0 |

Reading it as M3 will: **NFP/FOMC/CPI clear the power bar on the indices; CPI alone carries a
premium worth tilting toward; Retail Sales and Durables are not worth a position at all.** For CL,
EIA has the power but Phase 2 already excluded the directional edge and the drift sits below
break-even — CL enters M3 only as the no-premium control instrument.

Worked example of what "power" buys: RTY CPI predicted 0.388% of ~2,300 ≈ 8.9 points ≈ **$446 of
expected absolute move per contract inside the release minute** — against a $12.50 realistic cost
floor. The prize exceeds the floor ~36×; whether a *structure* can capture it after stops and
whipsaw is exactly M3's question, and only M3's 1-second data can answer it.

## Part 5 — Claims, and one check that had to be rebuilt

`P2-POWER-MODEL-CONFIRMED` (+0.530, V1 re-derives from the per-event file, V2 = RTY/CL pass
independently, V3 = shuffle+control on all five) · `P2-FP-ADDS-NOTHING` (0 instruments where |f−p|
helps; powered) · `P2-REGIME-LAG` (4.155, V2 = trailing shrinks it, V3 = NFP shows none).

⚠️ Kept visible: `P2-FP-ADDS-NOTHING`'s first V1 failed because the CHECK compared raw row counts
across two different filters (533 vs 493) — a defect in the check, not the claim. It was rebuilt to
re-derive the actual statistic (now matches to 1e-6); the `expect` was never touched, and the
reason is recorded in the code.

## Part 6 — What went well / what went wrong

**Well:** pre-registration made the two gate failures *informative* instead of embarrassing — one
exposed a category error (power vs premium) that is now a design principle for M3; the other
localized a real model weakness (regime lag) that the declared variant then fixed under the same
gates. The dumbest-defensible-model choice paid off: ρ ≈ 0.5 with nothing to overfit.

**Wrong:** the V2 anchor was registered from the wrong quantity — the pre-registration discipline
caught my error, which is the system working, but the error was mine and avoidable: **when
registering an anchor, name the quantity it ranks, and check the anchor's source measured the same
quantity.** And one verification check was itself defective on first write (row-count proxy instead
of the statistic) — the same lesson at smaller scale.

## Part 7 — State of the milestones (#124)

M0 ✅ · M1 ✅ (#125 closed) · **M2 ✅ (this report — #126 closing)** · next **M3 (#117)**: the
long-tilted straddle on 1-second bars — selection filter from Part 4, long-tilt constraint from M1,
stressed costs leading, OOS-both-sides, both-legs-swept rate as a headline number. Then M4 closeout.
