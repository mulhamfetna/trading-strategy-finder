# FU-11 Stage 1 (#162) — the Fused Size Engine: forecast-quality pre-registration

**Filed 2026-08-20, BEFORE any run. Derived from the saved design of record
(`docs/FU11-FUSED-SIZE-DESIGN-DRAFT.md`) after the owner's "proceed". Stage 1 is the
DECIDING stage: if the fused forecast does not beat the deployed engine's family as a
FORECAST, the study ends here and no consumer study runs.**

## The question

The live volatility engine (`volatility.py`, every champion's entry gate) forecasts next-bar
realized vol from tape memory alone (HAR terms 1/6/30 bars). It cannot know that tomorrow
08:30 is a CPI print. The M2 power layer (FU-14, live) knows each scheduled release's expected
move size the night before (Spearman ≈0.5). **Does adding the calendar terms the live engine
is blind to produce a measurably better volatility forecast?**

## Prior art (deep-research-first, recorded before the run)

HAR models augmented with scheduled macroeconomic-announcement dummies are an established
published specification (the "HAR-M" family — a standard HAR plus dummies marking bars that
coincide with named macro releases), and macro-uncertainty-augmented HAR-type models report
significant forecast improvements. Two consequences pre-registered here: (a) the mechanism has
independent literature support — this is not a novel bet; (b) the literature's gain may come
from the DUMMY (knowing an event happens) rather than the POWER MAGNITUDE — so a dummy-only
decomposition arm is mandatory, and "fusion wins" must be attributed to the right term.

## Fixed design (nothing below changes after the first run)

- **Instruments**: NQ (primary) + ES, RTY, GC, CL — the five with committed M2 evidence.
- **Frame**: research-built 1h decision bars from the 16-year 1m frames
  (`load_1m_extended`, floor-to-hour binning, engine RV convention via `compute_rv_pts`);
  NQ additionally at 4h (the parity-lineage frame). ⚠️ Declared blind spot: these are
  research frames, not the engine's session frames — consumer ① would redo on engine frames.
- **Target**: `rv_pts[i]` per decision bar (the engine's own quantity), forecast causally
  from bars < i. Same target, same rows, for every model.
- **Models** (all causal; fits on TRAIN only):
  - **A — deployed HAR**: the live fixed-weight forecast `0.5·rv[i−1] + 0.3·mean₆ + 0.2·mean₃₀`.
  - **B — HAR-LS**: OLS on [1, rv₁, mean₆, mean₃₀] (the honest fitted baseline: any fusion win
    must beat FITTING alone, not just the fixed weights).
  - **C — FUSED**: B's regressors + `evt_dummy[i]` (a scored M2 event falls inside bar i's
    window) + `evt_power[i]` (that event's night-before expanding P_hist %, M2's pre-registered
    primary; max if several; 0 off-event).
  - **D — dummy-only**: B + `evt_dummy` (the decomposition: does power MAGNITUDE add anything
    beyond calendar awareness?).
  - **C\* — placebo falsifier**: C with the per-event power values SHUFFLED across events
    (20 seeds, median) — must collapse C's gain toward D.
- **Split**: train < 2024-01-01, test 2024-01-01→end (the operative window; matches FU-13's
  TRAIN_END). Era halves of test (2024 vs 2025+) for sign stability. M2 predictions are
  shifted/expanding — causal by construction, no leakage.
- **Metrics**: QLIKE primary (meta-prophet definition, `mean(v_t/v_p − log − 1)`), RMSE
  secondary; each computed overall, on EVENT bars, and on quiet bars. The decision statistic:
  the paired per-bar QLIKE differential (B − C) on TEST EVENT BARS, bootstrap 90% CI
  (2,000 resamples).

## PASS lines (fixed now)

Stage 1 **PASSES** iff ALL of:

1. **NQ primary**: mean event-bar QLIKE differential (B − C) > 0 with bootstrap 90% CI > 0
   (C also beats A on the same bars).
2. **Cross-instrument sign**: the event-bar differential (B − C) is positive on ≥3 of the
   other 4 instruments.
3. **No harm off-event**: overall test QLIKE(C) ≤ 1.001 × QLIKE(B) on NQ.
4. **Falsifier**: the shuffled-power placebo C\* loses ≥ half of C's event-bar gain over D
   (median of 20 seeds) — else the "power term" is decoration and the result is VOID.

**Attribution rule**: if C ≈ D (the dummy captures the gain), Stage 1 may still pass, but the
verdict is recorded as **calendar-aware, not power-aware** — consumers would then use the
dummy form and the power term is dropped. No re-framing after results.

**If Stage 1 fails**: consumers ①–④ do NOT run; a power analysis (n event bars, sd of the
differential, minimum detectable effect) is mandatory in the negative verdict; the study
closes as CLOSED-NEGATIVE with the live engine unchanged.

**If Stage 1 passes**: each consumer (① champions' re-gate, ② sizing ramp per FU-13's
per-instrument lesson, ③ FU-7 news-leg geometry, ④ box stop distances) gets its OWN
pre-registration before its first run. Nothing ships from Stage 1 itself — it changes no
deployed component.

## Blind spots (declared)

1. Research frames ≠ engine session frames (above).
2. ~1% of bars are event bars — the overall-QLIKE gain will be tiny by construction; that is
   why the decision statistic is event-bar-local. Consumers ②③④ act on event days, so the
   local statistic is the operative one; consumer ① (all-bar gate) is already predicted
   neutral by the Chronos program rule.
3. Event coverage starts ≥2016 (calendar) while frames start 2010 — pre-2016 bars carry
   dummy=0 even if events occurred; they sit in TRAIN only and bias the event coefficients
   toward zero (conservative, not inflationary).
4. The five instruments share macro moments — cross-instrument agreement is semi-independent
   (different price files, same calendar), as declared in every prior fusion study.
