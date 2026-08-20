# X-1 (#173) — the collision census + compound-power measurement: pre-registration

**Filed 2026-08-20 BEFORE any run. XNI's opening measurement (its FU-1): when the two
forecastable calendars share a session, does realized violence SUPER-ADD — or are the two
uncertainty resolutions independent? Pure measurement; nothing trades; every downstream
X-case consumes this.**

## The census-first rule (mechanical, not aspirational)

The script computes the census and the MDE FIRST and applies the pre-registered gate
automatically: a collision type proceeds to outcomes **iff n ≥ 30 collision events** on the
primary instrument; below 30 it closes **CLOSED-UNDERPOWERED at the census stage** with the
count and MDE recorded — no outcome for that type is ever computed or read.

## Fixed definitions

- **Macro events**: the M2 scored set per instrument (5 series, ≥2016, realized `jump_pct`,
  night-before `pred` — the E-P1/FU-11 assembly verbatim).
- **Earnings events**: the committed `ep1_events_{inst}.csv` scored set (12 tickers).
- **Collision types** (a macro event is "in collision" iff):
  - **T1 — earnings-night → macro-morning**: ≥1 earnings event in [macro_et − 18h,
    macro_et), i.e. the prior evening's AMC print feeding into the morning release.
  - **T2 — same-24h**: ≥1 earnings event within ±24h of the macro event. (T1 ⊂ T2;
    both reported; T2 is the broad flag.)
  The symmetric earnings-side flags (macro within the prior 24h of an earnings event) are
  computed for the census table but carry no registered outcome test in X-1 v1 (declared —
  one primary direction per study).
- **The outcome statistic** (per type that clears the gate): the mean difference of
  **log(jump_pct)** between collision macro events and their MATCHED controls — the
  nearest-in-time non-collision event of the SAME series (series identity is the dominant
  power regime; matching removes it). Event-bootstrap 90% CI (10,000).
- **Noise check**: 200 shuffles of the collision flag within series — the observed
  difference must exceed the shuffled 95th percentile for a positive.
- **Cross-instrument**: NQ primary; ES witness (sign agreement required for a positive).

## Pre-registered verdict rule (per type)

- **SUPER-ADDITIVE** iff mean log-jump difference > 0 with CI90 > 0 AND above the shuffle
  p95 AND the ES sign agrees. (Consequence: X-3's compound flag is armed, and FU-15's
  parked design gains its strongest gate input — still owner-parked.)
- **CLOSED-INDEPENDENT** iff the CI90 contains 0 with |mean| below the shuffle p95 — the
  calendars resolve independently (itself a valuable fact: compound power = simple max/sum
  of the two forecasts, no interaction term needed).
- **CLOSED-CONTRARIAN** iff CI90 < 0 (collision sessions QUIETER — recorded, not traded).
- **CLOSED-UNDERPOWERED** at the census stage (n < 30), MDE recorded.

## Expectations recorded now (honesty anchors)

T1 is the mechanistically interesting type (overnight positioning carry-over into the
morning release) and likely the rarer; T2 will be more numerous but dilute. AMC earnings
cluster in Jan/Apr/Jul/Oct weeks — CPI/NFP mornings fall in those weeks routinely, so T2
n≥30 is plausible; T1 may not clear. Both calendars' own powers are already in `pred` —
matching by series controls the macro side; the earnings side's power is NOT controlled in
v1 (declared: X-1 asks IF there is an interaction, not its dose-response — that would be a
follow-up with its own registration).

## Blind spots (declared)

1. 12 mega-cap tickers only — "earnings night" here means a top-12 print, not the broad
   earnings season.
2. log(jump_pct) requires jump>0 — zero-jump events are dropped and counted.
3. Matching is nearest-in-time within series (one control per collision, no replacement);
   residual regime drift between an event and its match is the price of small n.
4. All inherited declarations (acceptance smear on the earnings side, ≥2016 rule, research
   frames irrelevant here — this is minute-level jump data).
