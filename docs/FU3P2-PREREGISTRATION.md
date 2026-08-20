# FU-3 Phase 2 (#155) — cross-instrument power sizing: the fresh pre-registration

**Filed 2026-08-20 BEFORE any run, as FU-3's own verdict required ("the legitimate re-test
is the declared Phase 2... under a fresh pre-registration"). One question: does the SAME
frozen ramp that showed the promising NQ texture (+$30,338, 6/6 frames, perm 98%, CI
touching zero) hold on OTHER instruments' books — or is it an NQ idiosyncrasy, as FU-13's
ES reversal warns?**

## Fixed design (everything inherited frozen from FU-3 except the instruments)

- **Instruments**: ES, RTY, YM — the legs with committed FU-9 power files. GC/CL excluded
  (no frozen power file; declared, not smuggled).
- **Books**: 6 frames × 3 instruments = 18 books, built by the FU-1/FU-2/FU-3 convention —
  L1 box signals + the champion volatility gate + champion stops via the STRICT extractor
  (`champion_stops`) from the deployed `best_champions_full_{inst}.json` `box` params
  (sl_soft/sl_hard/tp/flip/gate_pct). Declared: this is the L1-with-vol-gate book (no
  indicator votes, no caps/cooldown), the same convention Phase 1 used on NQ; baselines
  have no committed anchor — their totals are recorded as evidence.
- **The ramp (frozen, identical to FU-3)**: day power = max committed `pred_exp` over the
  day's scored events FROM THAT INSTRUMENT'S OWN FU-9 file; multiplier = 0.5 + causal
  expanding percentile among prior event days (warmup 20 at 1.0); non-event days 1.0;
  equal-exposure normalization (Σm = n) per book.
- **Decision statistic**: pooled (18 books) Δnet; day-bootstrap 90% CI (10,000); 1,000
  event-day permutations of each instrument's multipliers (same normalization); era halves
  on the pooled ACTIVE span's median day (the FU-3 span lesson, applied); per-instrument
  pooled Δ reported.
- **Anchored expectation (recorded now)**: FU-13 found ES rewards no vol-mapped size
  dispersion on its MTF book — ES is expected the weakest leg here; RTY (highest FU-7 width
  response) the strongest. If ES is negative while RTY/YM are positive, that CONFIRMS the
  asymmetry law rather than contradicting Phase 1.

## Pre-registered verdict rule

- **CONFIRMED** iff pooled Δnet > 0 with CI90 > 0 AND the real maps beat ≥95% of the 1,000
  permutations AND ≥2 of 3 instruments individually positive. Confirmed = Phase 1's texture
  generalizes; a deployment-track study (full champion books, caps, indicator votes, ship
  gate) may then be pre-registered. Nothing ships from P2 itself.
- **REFUTED** iff pooled CI90 < 0 — the NQ texture was idiosyncratic; FU-3 closes for good.
- **CLOSED-NULL** otherwise, with MDE — and with the COMBINED P1+P2 pooled figure reported
  as a labeled secondary (the two phases' pooled CI is the honest running total).

## Blind spots (declared)

1. The L1-with-vol-gate convention is not the full deployed champion (no indicator gate) —
   a CONFIRMED here still requires the deployment-track study on full books.
2. Engine-loader books are recent-era (~2025→) as established; the era-half line splits the
   ACTIVE span.
3. The three instruments share macro moments with NQ and each other (semi-independent).
4. Equal-exposure post-book scaling as in Phase 1 (qty-linear, no market impact).
