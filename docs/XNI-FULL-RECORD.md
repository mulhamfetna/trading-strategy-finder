# XNI Phase 3 — the Full Record (earnings × news × indicators)

**Opened 2026-08-20 (tracking #172; brainstorm + X-ledger `XNI-BRAINSTORM.md`; claims
`claims_xni.py`).**

## X-0 · The opening state

Three eras hand this phase: two certified size forecasts (macro ρ≈0.5 deployed; earnings
ρ≈0.46), the released two-calendar blindness schedule (E-D1, v5.5.0), the state-blind law
at full strength (X-R1: stances = telemetry only), and the born constraint — collisions are
rare, census before outcomes, mechanically gated.

## X-1 · The collision census + compound-power measurement: CLOSED-INDEPENDENT ✅ (2026-08-20)

**The census (the gate cleared — no underpowered closure was needed):** of ~560 macro
events ≥2016, **63/64** (NQ/ES) had a top-12 earnings print in the prior 18 hours (T1) and
**118** had one within ±24h (T2); 190 earnings events sit within 24h of a macro release.
Collisions are not rare after all at the top-12 scale — the born constraint was satisfied
by measurement, not assumption.

**The outcomes (NQ primary; matched same-series controls; within-series shuffles):**

| type | n | NQ Δlog(jump) | CI90 | shuffle p95 | verdict |
|---|---|---|---|---|---|
| T1 earnings-night→macro-morning | 63 | +0.1723 | [−0.0631, +0.3985] | +0.2630 | **CLOSED-INDEPENDENT** |
| T2 same-24h | 118 | +0.0494 | [−0.1443, +0.2409] | +0.2049 | **CLOSED-INDEPENDENT** |

**Recorded, NOT promoted**: ES's T1 clears every registered line alone — **+0.3580, CI
[+0.1225, +0.5845], above its shuffle p95 (+0.2543)** — but the registered primary is NQ
and no pooled rule existed; none was invented post hoc (ledger V2 verifies the
non-promotion). It stands as a single-witness, fresh-registration-eligible hypothesis
("T1 super-additivity, ES-led") on future data.

**The consequence — the phase's first law**: the two calendars resolve INDEPENDENTLY at
the measurable level. Compound power therefore composes ADDITIVELY from the two certified
forecasts — X-3's collision flag needs no interaction statistics, and FU-15's parked gate
input gains nothing beyond the two forecasts it already has. Ledger:
`X1-CALENDARS-INDEPENDENT`, **60/60 both machines**.

## X-3 · The compound-power artifact: SHIPPED-ON-BRANCH ✅ (2026-08-20)

**A composition, not a study (law #1: the calendars resolve independently ⇒ ADDITIVE
composition, no interaction statistics). The E-D1 artifact now carries, per event: the
`collision` flag (T1/T2, X-1's frozen windows) and `compound_lift_rv_pts` (own lift + the
max counterpart lift within ±24h).**

Three lines, all green: **P** — verify Δ0.0e+00 both instruments AFTER the change ·
**C** — census consistency: the 2025 artifact's T1 rate 22.6% vs X-1's own machinery on
the same window 22.4% (ratio 1.009, inside the registered ±10%) · **A/V3** — every one of
the 44 compound rows re-derives additively from a ±24h counterpart, checked ROW BY ROW in
the ledger claim itself (e.g. FOMC 2025-01-29: own 58.0 + earnings 15.5 = 73.5 rv pts).

**The incident worth the record**: the claim's own V3 caught a real composition bug on the
first pass — a `max(best or 0.0, …)` seed silently FLOORED negative counterpart lifts to
zero. The earnings model's dummy beta is negative, so a tiny-power print carries a negative
lift — the certified model's honest statement, which the composition must respect. Fixed,
re-run, all green. A machine check catching its own author within the hour is the protocol
working exactly as designed.

Bundle re-zips at the next release (noted). Ledger: `X3-COMPOUND-ARTIFACT-SHIPPED`,
**61/61 both machines**.
