# E-X2 — the joint two-calendar forecast: pre-registration

**Filed 2026-08-20 BEFORE any run. Order rationale (recorded): the joint forecast before
the ×indicators phase — it is the declared follow-up of TWO green studies (FU-11 macro,
E-X1 earnings), consumes only committed evidence, and completes the forecast-layer repair
story; the conditioning phase starts from a ≈0 prior and can wait. One question: does ONE
model carrying BOTH calendars' terms deliver each calendar's repair simultaneously — the
single best forecast of the engine's own target?**

## Fixed design (every convention inherited verbatim)

- **Instruments**: NQ (primary), ES (witness). Frame: research 1h; target `rv_pts`;
  train < 2024-01-01, test 2024→; identical rows for every model.
- **Terms**: macro = the M2 scored events (expanding P_hist, the FU-11 assembly);
  earnings = the committed `ep1_events` scored events (per-ticker P_hist). Four calendar
  regressors: m_dummy, m_power, e_dummy, e_power.
- **Models**: A deployed HAR · B HAR-LS · **C_m** (B + macro terms — FU-11's C) ·
  **C_e** (B + earnings terms — E-X1's C) · **C_j** (B + all four terms, the joint).
  No new placebo arms — each calendar's power term already survived its own falsifier;
  E-X2 tests COMPOSITION, not existence.

## PASS lines (fixed now)

1. **No macro degradation**: on NQ test MACRO event bars, QLIKE(C_j) ≤ 1.001 × QLIKE(C_m).
2. **No earnings degradation**: on NQ test EARNINGS bars, QLIKE(C_j) ≤ 1.001 × QLIKE(C_e).
3. **The union decision**: on the UNION of test event bars (macro ∪ earnings), the paired
   QLIKE differential (B − C_j) > 0 with bootstrap 90% CI > 0 on NQ; ES differential
   positive in sign.
4. **Overall single-best**: overall test QLIKE(C_j) ≤ 1.001 × min(overall B, C_m, C_e) on
   NQ — one model, no regression anywhere.

**PASS** ⇒ the joint two-calendar model is the reference calendar-augmented forecast, and
**E-D1 is ARMED**: productionizing it as an information-layer upgrade in the FU-14 pattern
(parity + falsifier + nightly ops artifact, ZERO trading consumers — a proposal for the
owner, not an automatic ship). **FAIL on 1 or 2** ⇒ the calendars interfere — a real
finding (shared regression capacity), each single-calendar model stands alone. **FAIL on
3/4** ⇒ composition adds nothing; CLOSED with MDE.

## Blind spots (declared)

1. A macro event and an earnings event never share a bar in practice (08:30 vs 16:30
   clocks) but the design does not assume it — union bars are counted once.
2. All FU-11/E-X1 declarations carry over (research frames; acceptance smear; 2025+ gain
   shrinkage on macro).
3. Two instruments; the FM bands audition (declared possible in FU-11's draft) remains NOT
   run — one question per study.
