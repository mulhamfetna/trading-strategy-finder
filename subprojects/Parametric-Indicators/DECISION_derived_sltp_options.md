# Decision Options — after the Stage-0 NO-GO (derived / adaptive SL/TP)

**Date:** 2026-06-14 · **Context:** `optimize/sub/STUDY_relative_feasibility.md` returned **NO-GO** — on
2024–2026 data, expressing SL/TP as a ratio to a live driver (ATR / HAR-RV `vf` / %price) makes the optimal
SL/TP **more** dispersed, not less; the absolute optima were already stable (sl_hard CV 0.15) and volatility
barely tracks them. This document describes **each forward option in full** so the choice is informed.
**No option below has been started.** The fixed champion remains the deployed default.

> Recap of the numbers that drive the decision: absolute CV — sl_soft **0.317**, sl_hard **0.151**, tp **0.527**;
> ratio CV (÷ATR) — 0.349 / 0.302 / 0.570 (worse on every target). Correlation best-SL vs ATR: sl_soft +0.44,
> sl_hard +0.05, tp +0.29. Span: 27 rolling 3-month windows, 2024-03 … 2026-05 (~one macro regime).

---

## Option 1 — STOP / keep fixed *(recommended)*

**What it is.** Close the derived-SL/TP workstream. Keep the fixed champion exactly as deployed. Treat
"values go stale" as a *future, occasional* event handled by a one-off re-optimization **only when evidence of
decay appears** — not by a structural rebuild now.

**Why it fits the evidence.** The premise that motivated the whole idea ("absolute SL/TP decay within a year")
is **not visible in 25 months of data** — the optimal absolute SL/TP barely drifted (sl_hard CV 0.15). If the
thing isn't decaying, there is nothing to fix, and a vol-relative rebuild would *add* instability (Stage 0).

**Concrete steps.**
1. Mark `ACTION_PLAN_derived_sltp.md` CLOSED-NOGO; keep the study + this doc as the record.
2. Keep the ATR-multiplier mode as an *exploratory* dashboard tool (already labelled), default-off.
3. (Optional, trivial) add a calendar reminder to re-check decay in ~6–12 months.

**Cost.** ~zero (docs only). No GPU, no engine change, no new tests.

**Expected result & odds.** Status quo performance retained with certainty; zero new risk. No upside beyond
what fixed already delivers.

**Risks.** If a genuine multi-year regime shift *does* eventually move the optimum, you find out reactively
(via live underperformance) rather than proactively. Mitigated cheaply by Option 4's monitor if desired.

**Success criteria.** N/A — it is the do-nothing baseline every other option is measured against.

**Interaction with champion / reversibility.** None; fully reversible (you can pick any other option later).

---

## Option 2 — Re-scope the robustness test, then re-gate

**What it is.** Don't build anything yet. First *fix the things that could have biased Stage 0 toward NO-GO*,
re-run the feasibility test, and only then decide. Stage 0 tested a specific, possibly-too-weak setup.

**Why it could change the verdict.** Three known limitations of the Stage-0 test could each be hiding a real
relationship:
- **Horizon:** 25 months ≈ one regime. Decay may be a multi-year phenomenon. More history → more drift to
  potentially explain.
- **Noisy labels:** "best SL/TP per window" are in-sample optima; noise inflates the ratio CV and biases the
  test *against* the ratio. De-noising (regularized / shrunk per-window optima, or wider averaging) gives the
  ratio a fairer test.
- **Driver granularity:** Stage 0 used per-window **mean** ATR/vf. A per-bar or per-trade driver, or a
  *different* feature (range expansion, regime/trend state, time-of-day) might track the optimum where mean
  volatility doesn't (note sl_soft already showed r=+0.44 to ATR — not nothing).

**Concrete steps.**
1. Acquire/locate longer history (pre-2024 NQ 4h + 1-min) if available → extend the rolling table.
2. Add de-noised labels to the sub_optimizer table (e.g. shrink each window's best toward the pooled mean,
   or score a small neighbourhood instead of the argmax).
3. Add candidate features beyond mean-vol (range, ADX/trend, realized-vol percentile, session).
4. Re-run `feasibility_relative_sltp.py` (extended) → re-gate with the *same* CV-improvement bar.

**Cost.** Low–moderate, **CPU/analysis only, no GPU.** Days, mostly data wrangling. Gated: stop if still NO-GO.

**Expected result & odds.** Moderate chance of flipping *one* target (sl_soft, which already correlates +0.44)
to GO; low chance for sl_hard/tp. Most likely outcome: a sharper, better-justified NO-GO, or a *narrow* GO
limited to sl_soft.

**Risks.** Researcher-degrees-of-freedom — testing many drivers/features until one "passes" is a
multiple-comparisons trap. Mitigate by pre-registering the driver list and the CV bar before running.

**Success criteria.** A driver whose ratio CV is **materially** below the absolute CV (e.g. ≥25% tighter) on a
**held-out** stretch of windows, with low half-split drift — *then* proceed to Stage 1/2.

**Interaction / reversibility.** No engine change; fully reversible. This is the disciplined "measure twice"
path before any build.

---

## Option 3 — Proceed as a pure PERFORMANCE bet (joint `wsh5` sweep)

**What it is.** Abandon the *robustness* justification (Stage 0 killed it) and pursue derived SL/TP purely as a
*performance* play: run the full joint NSGA-III walk-forward (`wsh5`) over `{driver, k_sl_soft, k_sl_hard,
k_tp_soft, k_tp_hard} ∪ {gate_pct, k-of-N}`, two-sided band, and see if any jointly-optimized sized config
**OOS-dominates** the fixed champion on return/DD.

**Why one might still do it.** The councils noted the prior study *under-tested* sizing (froze the base, fit
one coefficient, shrink-only band). A true joint, two-sided search is the only fair test of "can adaptive
sizing beat fixed?" — a question Stage 0 did **not** answer (Stage 0 was about stability, not profit).

**Concrete steps (Stage 1 + Stage 2 of the action plan).**
1. Build `sltp_mode='relative'` + `ConstantPolicy` in the engine (parity-guarded; fixed stays byte-identical).
2. Wire the Manual/Auto UI (two sub-boxes, disable inactive).
3. Fresh `wsh5` prefix on Postgres; joint two-sided search space; objective = return AND drawdown; **multi-fold**
   walk-forward; parity anchor. **Pilot 4h first**, fan out to all TFs only if the pilot ≥ fixed OOS.
4. Pre-registered adopt rule: ship only if it OOS-dominates the champion across folds.

**Cost.** **High** — engine + UI build (Stage 1) + **GPU-hours** for the sweep (Stage 2), per-TF if it fans out.

**Expected result & odds.** **Low** probability of a clean OOS win: two councils + the existing study point to
"no profit edge" for vol sizing, and Stage 0 shows vol doesn't even track the optimum. Most likely outcome:
matches fixed at best, after significant spend.

**Risks.** Overfitting a larger search space on thin data; the n=1-regime caveat; sinking GPU/time into a
weak-prior bet. The pre-registered adopt rule is the safeguard (no adopt unless it earns it).

**Success criteria.** A `wsh5` point that ≥ champion return **and** ≤ champion DD across **all** folds, 4h pilot
first. Otherwise keep fixed — and the spend bought a definitive "no", which has value.

**Interaction / reversibility.** Build is additive (fixed untouched, golden-gated). Nothing deploys unless it
wins. Reversible, but the *time/GPU* is not refundable.

---

## Option 4 — Pivot: handle staleness OPERATIONALLY (re-opt cadence + drift monitor)

**What it is.** Accept that SL/TP stay fixed, and solve the *original worry* ("they'll be wrong next year")
**operationally** instead of structurally: build a lightweight **drift monitor** + a **scheduled
re-optimization** pipeline that re-runs `wsh5` on fresh data on a cadence (or when drift is detected) and
proposes an updated champion for sign-off.

**Why it fits.** Stage 0 says the absolute optimum is stable *now*; the real risk is *future* drift. The
cheapest correct insurance is to **detect** drift and **re-fit on demand**, not to rebuild the sizing model.
This is what the existing optimizer infra (`wsh5` on Postgres, walk-forward) already supports.

**Concrete steps.**
1. **Drift monitor:** a small job that, each month, scores the deployed champion on the newest window and
   tracks live-vs-expected return/DD and the box/vol stats; alerts when they leave a tolerance band.
2. **Re-opt trigger:** on alert (or every N months), launch the standard `wsh5` sweep on refreshed data
   (sequence already documented in `SYSTEM_UPDATES_MEGADOC.md` §4.3).
3. **Sign-off gate:** new champion must OOS-beat or match the incumbent before swap (human-approved).
4. **Record:** keep a champion-version log (date, data span, metrics) for auditability.

**Cost.** Moderate engineering (monitor + scheduler + report), **mostly CPU**; GPU only when a re-opt actually
fires (rare, per Stage 0). Far cheaper than maintaining an ML sizing model.

**Expected result & odds.** High value as *insurance*: directly addresses the staleness fear with a proven
mechanism (just re-optimize when needed), no new modelling risk. Doesn't add performance — it preserves it.

**Risks.** Monitor false-alarms (tune tolerances); re-opt introduces a *new* in-sample fit each time (the usual
overfit risk, controlled by the existing walk-forward + adopt rule). Operational complexity (a scheduled job).

**Success criteria.** Monitor catches a deliberately-injected drift in backtest; a scheduled re-opt reproduces
the champion on unchanged data (idempotence) and proposes a valid update on shifted data.

**Interaction / reversibility.** No change to trading logic; purely a maintenance wrapper around the existing
optimizer. Fully reversible.

---

## Comparison matrix
| | Cost | GPU | Addresses robustness? | Addresses performance? | Risk added | Odds of a "win" | Reversible |
|---|---|---|---|---|---|---|---|
| **1 Stop/keep fixed** | ~0 | none | n/a (premise unsupported now) | no | none | n/a (baseline) | yes |
| **2 Re-scope test** | low | none | re-tests it fairly | no | low (multiple-comparisons) | moderate→narrow GO | yes |
| **3 Performance bet (`wsh5`)** | high | yes | no (abandons it) | tests it directly | overfit/spend | low | yes (no auto-deploy) |
| **4 Operational cadence** | moderate | only on trigger | yes (via re-fit on demand) | preserves | monitor tuning | high (as insurance) | yes |

## Recommendation
- **Now:** **Option 1** (keep fixed) — the data does not justify a build, and fixed is provably best on every
  honest comparison.
- **If the staleness worry is the real driver:** add **Option 4** (cheap insurance that *actually* matches the
  problem: re-optimize when drift appears, don't rebuild sizing).
- **Before ever building derived sizing:** require **Option 2** to flip the gate to GO first. Reserve
  **Option 3** only for an explicit, funded "we want to try to beat fixed on profit" mandate, knowing the odds
  are low and the safeguard is the pre-registered OOS-dominance adopt rule.

These are not mutually exclusive over time: **1 now → 2 if/when you want to revisit → 4 as standing insurance →
3 only on a deliberate performance mandate.**
