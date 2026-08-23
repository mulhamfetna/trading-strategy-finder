# WS-ORB (#183) — opening-range breakout on all 9 instruments: pre-registration

**Filed 2026-08-23 BEFORE any run.** Grounded in `docs/WS-ORB-PRIOR-ART.md` (verified prior art: one
negative futures test, no evidence for metals/energy/Globex-open, edge-inside-the-spread and year-concentration
as the documented failure modes). Two arms, chosen by the owner. Nothing below may be changed after a number
has been seen; additions go in a dated Amendment section.

## 0. Question
Does a simple, fully specified opening-range breakout make money **after realistic futures friction** on
NQ ES GC SI HG CL NG RTY YM, over 16 years (2010-06 → 2026-08-07), stably across years — and is any such edge
distinct from the volatility exposure our existing machinery already captures?

## 1. Data
- Server 16-year tape `~/Mulham/data_2010_1s/<TOK>_Continuous_Data/<TOK>_1m.csv` (ET-naive, bars labelled by
  start, continuous-contract splice; verified tick-for-tick against the vendor set in WS-FWD gate A).
- 1 contract always. Point values from `optimize/instruments.py` (NQ 20 · ES 50 · GC 100 · SI 5,000 · HG 25,000 ·
  CL 1,000 · NG 10,000 · RTY 50 · YM 5).
- Windows (fixed now): **exploration** 2010-06-06 → 2017-12-31 · **confirmation** 2018-01-01 → 2024-12-31 ·
  **fresh** 2025-01-01 → 2026-08-07. Verdicts are read on *confirmation*; exploration must agree in sign; fresh is
  reported (and is the only window untouched by any prior in-house work).

## 2. The two arms

### Arm A — cash-session ORB
Opening-range anchor = the instrument's cash/pit session open (ET): **09:30** NQ ES RTY YM · **08:20** GC SI HG ·
**09:00** CL NG. Session close for the flat rule: 16:00 indices · 13:30 GC SI · 13:00 HG · 14:30 CL NG.
*Data check before any P/L is computed:* the 1-minute volume profile must show its intraday step at the declared
anchor minute (±1 min) for each instrument; if it does not, the anchor is moved to the observed step and the
change is recorded here as a pre-run note. Anchors are never tuned on P/L.

### Arm B — Globex session-open ORB
Anchor = **18:00 ET** for all 9 (the engine's session boundary and 4h grid origin). Flat rule at **16:59 ET** next
day (session end). No cash-session notion; weekends/holidays follow the tape.

## 3. Opening-range windows
N ∈ **{5, 15, 30, 60} minutes** from the anchor, in both arms. OR high/low = max/min of the N one-minute bars.
A range is void if any of its bars is missing.

## 4. Rule families (per arm × window)
All entries: first 1-minute **close** beyond the OR high (long) / below the OR low (short) after the range completes;
fill at the **next 1-minute open**; one trade per session per direction-side; the first breakout wins (no re-entry
after a stop); no trade if both sides break on the same bar.
- **R1 classic** — stop at the opposite OR edge (1R), target 10R, flat at session close. (Zarattini & Aziz 2023.)
- **R2 ATR-stop** — stop = 10% of the 14-day ATR from entry, no target, flat at close. (Zarattini et al. 2024.)
- **R3 range-target** — stop at the opposite OR edge, target 50% of the range width. (practitioner ES rule.)
- **C1 vol-threshold comparator** — Holmberg 2013: no time window; enter when price crosses (1±ρ)·open with
  ρ = μ̂ + σ̂·q₀.₉₅ from the trailing 60 sessions' open-to-close returns; flat at close. Runs only in Arm A (the
  paper's setting) as a comparator row.
Fills on stops/targets follow the engine's gap rule: if the 1-minute bar gaps through the line, fill at that bar's
**open**, not the line (GAP-01/02). Stops and targets are evaluated on bar high/low; if both are touched in the same
bar, the **stop** is assumed first (worst case).

Grid size: 9 instruments × 2 arms × 4 windows × 3 rules = **216 cells** (+ 9 comparator cells).

## 5. Costs lead
Every table shows raw, **$10/round-trip**, and **$25/round-trip**. The headline per cell is the $25 figure. A
required output is **gross edge per trade in ticks** next to the instrument's tick value.

## 6. Verdict rules (fixed)
Per cell, on the confirmation window, at $25/rt:
- **POSITIVE** requires all of: mean net P/L per trade > 0 with **t ≥ 2.5** (Bonferroni across the 12 cells of that
  instrument-arm: α = 0.05/12); exploration-window sign agrees; **≥ 60% of calendar years positive** and no single year
  > 50% of the total (the year-concentration failure mode); **leave-one-year-out** minimum still > 0; dumb controls
  (§7) null; noise check (§7) passed.
- **NEGATIVE** requires the minimum detectable effect (80% power, two-sided 5%) to be ≤ the instrument's $25 friction
  per trade — i.e. the test could have seen a friction-sized edge. Otherwise **UNDERPOWERED**, no verdict.
- Anything else: **NULL**.
A cell's verdict is final; no rule or window may be added to rescue it.

## 7. Controls
- **Dumb control 1 — random-time range:** same N, same rules, anchor at a uniformly random minute of the same
  session (seeded, 20 draws); the real anchor must beat the control distribution's 95th percentile.
- **Dumb control 2 — direction shuffle:** breakout direction flipped on a random 50% of days (20 draws); real must beat p95.
- **Noise check:** per-cell block bootstrap by session (1,000 resamples) → 95% CI of the net mean; POSITIVE requires
  the CI to exclude zero.
- **Vol-subsumption check (pre-registered question):** regress daily cell P/L on the deployed FU-14 power forecast and on
  the trailing 20-day realised vol; report the share of variance explained and the net mean within the top/bottom vol
  tercile. An edge that lives only in the top tercile is recorded as "volatility exposure, not ORB".

## 8. Outputs
- `optimize/orb/orb_reference.py` — vectorised standalone reference (1m, numpy/pandas); `orb_run.py` (server,
  per instrument); `orb_controls.py`; `orb_power.py`.
- Evidence `optimize/orb/data/`: per-cell trade books, summary JSON, controls, bootstrap, year tables.
- Claims `optimize/verify/claims_orb.py` (V1 definitions/data gates, V2 stressed-cost + controls, V3 falsifier:
  randomised anchors must NOT reproduce the result).
- Report `docs/WS-ORB-REPORT.md` (plain language, Mermaid visuals, per-instrument deep dives, what went well/wrong).
- If an ORB view is added to the dashboard: server-side Playwright gate with committed screenshots.

## 9. Declared blind spots
1. Continuous-contract roll handling inside a session can fabricate or destroy a breakout on roll days; roll days
   are flagged and a with/without-roll-days table is reported.
2. The cash-session anchors for metals/energy are conventions (pit opens) — checked against the volume profile, but
   the "right" anchor for an electronic market is itself a hypothesis.
3. 1-minute data cannot see intra-bar sequencing; the stop-first assumption is conservative by construction.
4. Contract specifications (tick sizes, session hours) changed over 16 years; we use today's values throughout.
5. The exploration window overlaps nothing in-house, but the 2025→2026 fresh window overlaps the box champions'
   selection data — irrelevant for ORB parameters (none are fitted) but relevant if ORB is later combined with boxes.
