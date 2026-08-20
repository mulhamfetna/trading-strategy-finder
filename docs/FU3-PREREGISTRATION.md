# FU-3 (#155) — power-aware box sizing: pre-registration

**Filed 2026-08-20 BEFORE any run. The first consumer implementation of the FU-11 result:
the night-before power forecast carries real information exactly where the book's vol
engine is blind. FU-3 asks whether the BOX BOOK should size WITH that forecast — the
regime-edge programme proved this book rewards sizing WITH volatility (and FU-13 proved
that lesson does NOT generalize across instruments, which scopes this study).**

## Fixed design

- **Scope**: NQ, the six champion frames — the FU-1/FU-2 books (each baseline must again
  reproduce the committed FU-1 book exactly; abort on mismatch). Other instruments are a
  declared Phase 2 REQUIRED before any adoption (the FU-13 lesson as law).
- **The power input** (frozen provenance): the committed FU-9 v1 dataset's `pred_exp`
  (M2's expanding night-before P_hist, NQ rows) — P(d) = the max predicted power over day
  d's scored events; days without a scored event carry no ramp.
- **The ramp** (the Exp2 shape, unchanged): multiplier = 0.5 + percentile, where percentile
  is the CAUSAL expanding rank of P(d) among all PRIOR event days' P values (first 20 event
  days warm up at multiplier 1.0). Non-event days: 1.0. Applied to trades by ENTRY day.
- **Equal-exposure normalization**: after assigning multipliers, all are scaled so their sum
  over trades equals the trade count (Σm = n) — the flat book and the ramped book deploy the
  same gross exposure; the comparison is allocation, not leverage.
- **Decision statistic**: pooled (6 TFs) equal-exposure Δnet vs flat; day-bootstrap 90% CI
  (10,000); **dumb control**: 1,000 seeded permutations of the event-day multipliers among
  event days (same distribution, destroyed alignment) — the real Δ's percentile against
  them; era halves (2016–2020 vs 2021→) for sign.

## Pre-registered verdict rule

- **ADOPT-CANDIDATE** iff pooled Δnet > 0 with CI90 > 0 **AND** the real map beats ≥95% of
  the 1,000 permutations **AND** both era halves positive. Adoption still deploys NOTHING —
  it arms a Phase-2 cross-instrument battery (FU-13's X/M stages) which alone can promote.
- **CLOSED-NEGATIVE** iff CI90 < 0.
- **CLOSED-NULL** otherwise, with the mandatory power analysis (MDE).

## Expectations recorded now (honesty anchors)

Event days are ~18% of trading days, so the ramp touches a minority of trades; the effect
will be small in absolute $ and the MDE matters. FU-2 taught that in-window activity PAYS on
the 4h frame — sizing UP on high-power days is the aligned direction; but FU-13 taught that
even a true NQ sizing signal can be an NQ idiosyncrasy. A positive here is an ARM, never a
deploy.

## Blind spots (declared)

1. NQ-only; the FU-13 asymmetry makes cross-instrument confirmation MANDATORY before
   anything ships.
2. Post-book P&L scaling assumes qty-linearity (proven to the cent in era 3) and no market
   impact at study size.
3. P(d) covers the four modeled series only; other volatile days ride at 1.0 — the ramp is
   sparse by construction.
4. The ramp shape (0.5→1.5 linear) is inherited from Exp2, not optimized here — deliberately,
   to avoid a shape search on top of a small event sample.
