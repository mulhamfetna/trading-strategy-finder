# E-X1 — earnings × the fused forecast: pre-registration

**Filed 2026-08-20 BEFORE any run. Order rationale (recorded): E-X1 runs before E-S1
because it consumes only committed evidence (E-P1's per-event files) and FU-11's proven
Stage-1 machinery — the cheapest path to the return's highest-value question. One question:
FU-11 proved the live vol engine is catastrophically blind on MACRO release bars and that
the calendar repairs it. Does the same hold on EARNINGS bars — the ~65 scheduled nights/yr
the gate is equally blind to?**

## Fixed design (FU-11 Stage 1 verbatim, earnings calendar swapped in)

- **Instruments**: NQ (primary), ES (the one witness — the two instruments with committed
  E-P1 evidence).
- **Frame/target**: research 1h bars from the 16-year 1m frames; target = the engine's own
  `rv_pts`; identical rows for every model.
- **Events**: the committed `ep1_events_{inst}.csv` SCORED events (pred non-NaN) — the
  event's decision bar = the 1h bar containing its acceptance stamp; power term = the
  night-before P_hist (%); dummy = an earnings bar. Macro terms deliberately ABSENT (the
  joint macro+earnings model is a declared follow-up, not this question).
- **Models** (train < 2024-01-01, test 2024→; fits on TRAIN only): A deployed fixed-weight
  HAR · B HAR-LS · C fused (B + earn_dummy + earn_power) · D dummy-only · C* shuffled-power
  placebo ×20 (within-ticker... the powers are per-event; shuffle among earnings events).
- **Decision statistic**: paired per-bar QLIKE differential (B − C) on TEST EARNINGS bars,
  bootstrap 90% CI (2,000).

## PASS lines (fixed now — FU-11's four, one witness)

1. **NQ primary**: mean earnings-bar QLIKE differential (B − C) > 0 with CI90 > 0 (and C
   beats A on the same bars).
2. **Witness**: the ES differential positive in sign.
3. **No harm off-event**: overall test QLIKE(C) ≤ 1.001 × QLIKE(B) on NQ.
4. **Falsifier**: the shuffled-power placebo loses ≥ half of C's gain over D — else the
   result is calendar-aware only (recorded as such, per FU-11's attribution rule).

**PASS** ⇒ the blindness+repair law covers BOTH calendars; the (macro + earnings) joint
forecast becomes the declared follow-up, and any consumer remains behind the fusion-era
consumer laws (predicted neutral for the all-bar gate; nothing ships from a quality stage).
**FAIL** ⇒ a real asymmetry between macro and earnings bars — a finding either way, with
the mandatory power analysis.

## Blind spots (declared)

1. AMC events land in the 16:00–17:00 session tail — thin bars; the acceptance-lag smear
   biases the event-bar RV placement (declared conservative in E-P1, same here).
2. ~100–110 scored earnings bars in the test window — fewer than FU-11's 140; the CI will
   be wider (recorded, not adjusted for).
3. Research frames, not engine session frames (the FU-11 declaration verbatim).
4. Two instruments only (the two with committed evidence) — GC/CL/RTY earnings sensitivity
   is out of scope.
