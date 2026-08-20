# E-X2 v2 — the joint two-calendar forecast under POWERED tolerances: pre-registration

**Filed 2026-08-20 BEFORE the v2 run, by owner order ("powered tolerance ex2 v2"). A
declaration first, because it decides whether this study is honest: v2 is registered AFTER
v1's numbers are known. Its legitimacy therefore rests on three things, none of which is a
tuned constant: (1) the tolerance form is the HOUSE STANDARD applied consistently — the
same paired-bootstrap CI machinery every other line in the programme uses, replacing v1's
arbitrary fixed ratio (the design law v1's miss produced: tolerances must be powered);
(2) v2 is STRICTER than v1 on the axis we could still tighten — BOTH instruments must pass
every line (v1 required only NQ + an ES sign); (3) v1's verdict STANDS untouched in the
ledger — v2 is a new registered test, not a revision of the old one.**

## Fixed design (data/models identical to v1 — only the verdict lines are re-registered)

Same frames, split, terms, and five models (A, B, C_m, C_e, C_j); same seeds. New
computation: per-bar PAIRED QLIKE differentials with event-bootstrap 90% CIs (10,000).

## The v2 lines (each evaluated on BOTH NQ and ES; all must pass on both)

1. **No macro degradation (powered)**: on that instrument's test MACRO bars, the paired
   differential (C_m − C_j) must NOT be clear-negative — degradation is declared only if
   the CI90 upper bound < 0 (C_j significantly worse than C_m). The MDE of this
   differential is reported with the verdict either way.
2. **No earnings degradation (powered)**: same form with (C_e − C_j) on EARNINGS bars.
3. **The union decision (unchanged from v1)**: paired (B − C_j) on the union of event bars
   > 0 with CI90 > 0.
4. **Overall no-rival (powered)**: for each rival R ∈ {B, C_m, C_e}, the paired overall
   differential (R − C_j) must NOT be clear-negative (no rival significantly beats the
   joint model overall).

**PASS (all four lines, both instruments)** ⇒ the joint two-calendar model is the reference
calendar-augmented forecast and **E-D1 is ARMED**: a proposal to productionize it in the
FU-14 pattern (parity + falsifier + nightly artifact, information-only, zero trading
consumers) — built only on the owner's word. **FAIL** ⇒ v1's outcome is confirmed at
proper power; the single-calendar models stand permanently.

## Blind spots (declared)

1. The post-v1 registration issue above — mitigated by principle-not-constant, added
   strictness, and v1's standing verdict; noted forever in the claim.
2. n≈92 earnings bars: the powered line can only detect degradations larger than its MDE
   (reported) — small true degradations pass; that is what "powered tolerance" means and
   its honest cost.
3. All v1/FU-11/E-X1 declarations inherit.
