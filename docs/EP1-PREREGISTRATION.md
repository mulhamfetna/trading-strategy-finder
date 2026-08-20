# E-P1 (#169) — the earnings power model: pre-registration

**Filed 2026-08-20 BEFORE any run. The WS-EARN return's phase 1, per `WS-EARN-HANDOFF.md`.
One question: is the SIZE of the index move at a ticker's earnings forecastable the night
before from that ticker's own history — the exact M2 question, earnings edition?**

## Fixed design (M2's methodology transplanted, nothing re-invented)

- **Events**: the committed `optimize/earnings/data/earnings_timestamps_FINAL_16y.csv`
  (783 events, 12 tickers, 2010→2026, EDGAR acceptance ET). Events whose stamp has no 1m
  bar are dropped and counted (the table's own `nq_coverage` predicts this).
- **Realized move**: M2's `realized_moves` on the 16-year 1m frames — the event-minute
  |open→close|% (`jump_pct`). Instruments: **NQ primary; ES the confirmation witness**.
- **Predictor**: `build_predictions` grouped by **ticker** — P_hist = expanding median of
  the same ticker's prior events' jump_pct, shifted one event, **≥8 priors** (the M2
  constant). Scored events = those with a prediction.
- **Gates (all fixed now; the M2 battery verbatim)**:
  1. **Primary**: pooled OOS Spearman(P_hist, jump_pct) on NQ, Fisher-z 95% CI —
     useful iff **CI-lo > 0**.
  2. **V1 (different scorer)**: quintile buckets by P_hist — Spearman of bucket realized
     MEANS ≥ 0.8.
  3. **V2 (independent instrument)**: the same predictions scored against ES realized
     moves — CI-lo > 0.
  4. **V3 (falsifier)**: 200 ticker-label shuffles with P_hist REBUILT each time — the
     observed Spearman must beat the shuffled 95th percentile, else the "model" is vol
     clustering: VOID.
  5. **Control**: the same predictions scored against matched clean-minute |moves| (same
     clock minute, ±3–6 calendar days, excluding any table event day) must be materially
     weaker — control ρ ≤ half the real ρ.
- **Verdict**: **PASS** (all five) ⇒ earnings size is forecastable; E-S1 (the event-state
  dataset) and E-X1 (earnings × the fused forecast) are ARMED, each with its own pre-reg.
  **FAIL** ⇒ CLOSED-NEGATIVE with the mandatory power analysis (n scored, Fisher CI width,
  minimum detectable ρ); the return re-plans from the E-X1 side (the vol-engine blindness
  question survives even without a per-ticker ranking).

## Expectations recorded now (honesty anchors)

Stage 2 (#111) measured announcement minutes at **4.98×** matched minutes — power exists;
whether it is RANKABLE per ticker is the open question. 12 tickers × ~65 events give ~540
scorable events after warmup — comparable to M2's per-instrument n. AMC events cluster at
16:30 ET where NQ volume is thin — jump_pct may be noisier than macro 08:30 prints;
recorded, not adjusted for.

## Blind spots (declared)

1. Acceptance ≠ announcement (INTC ~7 min) — inherited verbatim from the timestamp table;
   a stale stamp SMEARS the event minute and biases jump_pct DOWN (conservative for the
   primary, but a pass does not certify per-minute tradability — that is E-S1's ground).
2. 12 mega-cap tickers, one index — ticker asymmetry is first-class (the fusion law); a
   pooled pass does not certify any single ticker.
3. The 2010→2016 slice predates the news programme's ≥2016 calendar rule — irrelevant here
   (no TV calendar involved), but control minutes avoid only THIS table's events, not macro
   releases; a control landing on a CPI minute inflates control moves (conservative
   direction for gate 5).
4. C4 (#110, the human timestamp spot-check) remains owner-side pending; E-P1 does not
   depend on it but E-S1's per-second work will.
