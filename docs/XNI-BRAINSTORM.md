# Phase 3 — Earnings × News × Indicators (XNI): the Opening Brainstorm and Use-Case Ledger

**Initiated 2026-08-20 by owner order ("we initiate the third phase of xnewsxindicators"),
under the WS-FUSION opening rule: a new phase opens with deep brainstorming + a numbered
follow-up ledger. The owner's thesis: the two event families share the same high-volatility
nature — "something hiding between the lines."**

## 1 · The raw materials (what three eras hand this phase)

- **Two forecastable calendars**: macro (P_hist ρ≈0.5, deployed) and earnings (ρ≈0.46,
  certified) — both size-only, both direction-dead.
- **The deployed income structure**: the box book (state-blind, flat, frozen — MEASURED
  choices) and the 4-leg CPI ride (state-blind by evidence).
- **E-D1**: the nightly blindness schedule — the system knows in advance which hours its
  live vol gate will mis-forecast, on both calendars' authority.
- **The laws (binding, not advisory)**: POWER ≠ PREMIUM · state-blind at full strength
  (direction, outcomes, conditioning, SIZE — both calendars) · instrument/ticker asymmetry
  first-class · placebo owns positives · a near-miss is a miss · tolerances must be powered
  · anti-premium ≠ harvestable drift · routing beats fitting.

## 2 · The hard constraint this phase is BORN with (read first)

The interesting XNI object is the **collision**: a macro release and a mega-cap earnings
within the same session. Collisions are RARE — CPI mornings × top-12 AMC nights intersect a
handful of times per year. Every A-family study below must open with a COUNT (how many
collisions exist ≥2016, per type) and a power analysis BEFORE any outcome is read; a
too-small n closes the study at the census stage, honestly and cheaply. And per E-C1/FU-5/6:
**no XNI study may condition on indicator stances without a NEW mechanism argued against
the standing nulls** — the library is telemetry here, not a predictor (X-R1 below makes
this a standing rule of the ledger).

## 3 · The use-case ledger (X-#) — the follow-up system

**Intake rule (the RQ/FU rule verbatim): every phase-3 idea gets an X number, a ledger row,
and an issue THE DAY IT APPEARS. Rows are never renumbered; statuses move QUEUED → ACTIVE →
CLOSED-<verdict>.**

### Family A — calendar × calendar (the collisions; census-gated)

| ID | use-case | mechanism | design sketch | status |
|---|---|---|---|---|
| **X-1** | **The collision census + compound-power measurement** — do same-session macro+earnings events SUPER-ADD in realized vol vs each alone? | Both calendars' power is real and independent-information (tape vs identity); if uncertainty resolutions compound, collision sessions are the tape's most violent knowable-in-advance hours — pure measurement, the phase's FU-1 | Census of collisions ≥2016 by type (macro-AM × earnings-PM-prior / same-24h); n and MDE FIRST; then realized RV of collision bars vs each family's solo bars, matched controls | **✅ CLOSED-INDEPENDENT (2026-08-20)**: census cleared (T1 63/64, T2 118); NQ primary CIs ∋ 0 both types; ES T1 single-witness texture recorded, not promoted. **Phase law #1: additive composition, no interaction term.** Claim `X1-CALENDARS-INDEPENDENT`, 60/60; record X-1 |
| **X-2** | **The deployed CPI ride × earnings adjacency** — does a top-12 earnings night adjacent to a CPI morning shift the ride's outcome distribution? | Positioning/liquidity carry-over between the two resolutions; the ride's tail-driven shape could fatten or thin | GATED on X-1's census (needs n); frozen ride outcomes (committed evidence only); per-leg; era split; pre-registered direction | QUEUED (gated on X-1) |
| **X-3** | **Compound-power night-before artifact** — extend E-D1's schedule with a collision flag + compound predicted power | Pure information composition of two certified layers (routing law); zero statistics needed beyond X-1's measurement | If X-1 finds super- or even plain additivity: one field added to the E-D1 JSONL, FU-14-pattern parity | **✅ SHIPPED-ON-BRANCH (2026-08-20)**: collision flag + additive compound lift; parity Δ0 post-change; census-consistent; 44 rows re-derive row-by-row; ⭐ the claim's V3 caught a negative-lift-flooring bug pass-one. Claim `X3-COMPOUND-ARTIFACT-SHIPPED`, 61/61 |

### Family B — deployed-layer protection (information consumers only)

| ID | use-case | mechanism | design sketch | status |
|---|---|---|---|---|
| **X-4** | **Blindness-hours observability** — annotate the dashboard/causal log with E-D1's schedule | FU-2 proved vetoes don't pay — so this is OBSERVABILITY, not gating: the operator sees which trades happened inside known-blind hours | Ops overlay, byte-identical books, dashboard-only; ship gate = visual parity | QUEUED |
| **X-5** | **Monitor × compound power** — do the news regime monitor's drawdown episodes cluster in high-compound-power regimes? | Protective analysis: if yes, the monitor's rolling window could carry a declared context field (information, not a new trigger) | Join the monitor's committed history with X-1's compound-power series; correlation + era split; NO trigger change without a full gate | **✅ INFORMATIVE (2026-08-20)**: ρ +0.906 CI-clear BUT the within-year shuffle bar is 0.879 — the ANNUAL regime carries the bulk (era-2's law re-measured); event-level margin 0.027. X-5b (report context field, own parity gate) ARMED; trigger untouched. Claim `X5-MONITOR-POWER-INFORMATIVE`, 62/62 |

### Family C — rules and substrate

| ID | use-case | mechanism | design sketch | status |
|---|---|---|---|---|
| **X-R1** | **The stance rule** (standing, not a study) | E-C1/FU-5/6 measured the library ≈0 on every conditioning axis | No XNI study conditions on stances without a NEW mechanism argued against the standing nulls in its pre-registration; the library serves as telemetry only | ACTIVE (rule) |
| **X-6** | **The collision dataset** — E-S1-schema rows for collision sessions (both calendars' context on one row) | Build-once substrate IF the census says collisions are numerous enough to study | GATED on X-1; FU-9/E-S1 machinery verbatim | QUEUED (gated) |

### Parking lot (noted, not numbered)
Cross-ticker earnings clustering (many AMC reports one night) as its own compound-power
type · the owner-supplied forward earnings calendar (unblocks E-D1's earnings side live) ·
FU-15's straddle revisited on collision sessions ONLY if X-1 finds super-additivity (its
power gate would then have its strongest input — still owner-parked).

## 4 · Execution order (proposed; awaits the owner's word to run)

**X-1 first** (the census + measurement — cheap, powers everything, closes fast if n is
tiny) → X-3/X-4 (information consumers, no statistics debt) → X-5 → X-2 (only if the
census funds it) → X-6 (only if warranted). The phase inherits WS-FUSION's §5 test for
"done": every row verdicted, ledger green, a closing report, hand-off notes.
