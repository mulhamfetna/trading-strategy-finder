# FU-8 (#160) — the Retail short: pre-registration (absorbs RQ-2 / #142)

**Filed 2026-08-20 BEFORE any run. Design evolution recorded first: FU-8's ledger row waited
for FU-5/FU-6 to teach "which state variables carry signal" — they taught that NONE do (two
engineered states null, one inverted; the full library barely above noise; state-blind entry
measured correct). The state-filter rationale is therefore REMOVED, not assumed: FU-8
reduces to the plain question the anti-premium always begged — does the FROZEN ride
geometry, MIRRORED SHORT, pay on Retail Sales at stressed costs?**

## The consumed-history problem (the honest core)

The Retail anti-premium's existence is CONFIRMED on consumed data (M1 flagged it, N3
confirmed gross −$86.10 NQ / −$32.41 RTY with both halves negative, WS-GRID found it
gross-negative on 7 instruments). Every event through 2026 has been read repeatedly. So this
study CANNOT confirm anything on that era — it can only (a) price the frozen short spec
descriptively on the consumed era, and (b) arm a genuinely FORWARD test. Both grades are
labeled; neither is upgraded by enthusiasm.

## Fixed design

- **The spec (frozen a priori — the deployed geometry, mirrored)**: SHORT at rel−300s,
  S 0.10% worse-of, TP 0.40% better-of, tie⇒STOP, exit +900s, qty=1, stressed costs — via
  the deployed `run_bracket` primitive (which handles shorts natively).
- **Events/legs**: Retail Sales MoM ≥2016 from the frozen FU-9 files, on NQ/RTY/ES/YM
  (the legs with 1s archives). NQ+RTY are the anti-premium's confirmed instruments (the
  pre-registered primary pool); ES/YM are sign witnesses.
- **Parity anchor**: the LONG side re-run on the same events must reproduce FU-9's stored
  `ride_pnl_usd` to the cent (the proven-generator gate).
- **Descriptive-era statistics**: pooled NQ+RTY net-stressed per event, event-bootstrap 90%
  CI, era halves (true-span median); ES/YM sign. LABELED consumed-history throughout.
- **The forward protocol (the only confirmatory element)**: if the descriptive grade
  survives, FU-8 arms a PAPER forward arm — the short spec evaluated on FUTURE Retail
  events only (information-only, no execution), with the decision rule fixed NOW: after the
  next **12** Retail events, pooled NQ+RTY net > 0 AND ≥7/12 events with the sign of the
  descriptive mean ⇒ a full ship-gate study may be pre-registered; otherwise FU-8 closes.

## Pre-registered verdict rule (today's run)

- **ARMED-FORWARD** iff the consumed-era pooled NQ+RTY net-stressed mean > 0 with CI90 > 0
  AND both era halves positive AND ES+YM both sign-positive. (Armed = the forward paper
  protocol starts; NOTHING trades.)
- **CLOSED** otherwise — the anti-premium stays a confirmed-negative fact about LONGS whose
  short side does not clear costs/consistency, with MDE recorded; RQ-2 closes with it.

## Expectations recorded now (honesty anchors)

The gross anti-premium (−$86 NQ) minus the mirrored cost line ($22.50) suggests ≈+$60/event
IF the mirror were symmetric — but it is not: the bracket flips, the worse-of fills flip
against the short, and M3's tie⇒STOP pessimism now works on the other side. The mirrored
net may be far worse than the naive sign-flip; that gap is itself a finding. RTY's smaller
gross (−$32) sits near its cost line ($22.50) — RTY is expected marginal.

## Blind spots (declared)

1. The descriptive era is consumed — nothing on it confirms; only the forward arm can.
2. Retail events sometimes share the 8:30 minute with CPI (the M-era dedup) — shared-minute
   events ride the schedule's priority; the FU-9 event list is the frozen source.
3. qty=1 single-shot replay grade; no execution study exists for a Retail short (RQ-7's was
   YM CPI) — a ship gate would need its own.
4. The four legs share the release moment (semi-independent witnesses).
