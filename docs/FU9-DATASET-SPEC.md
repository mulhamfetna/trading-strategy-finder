# FU-9 (#161) — the event-state dataset: frozen specification

**Filed 2026-08-20 BEFORE the build. FU-9 is a substrate, not a hypothesis test — its
pre-registration is this SPEC (definitions frozen) plus integrity gates that must pass for
the dataset to be committed. Every B-family study (FU-5/FU-6/FU-8), FU-15's design, and the
WS-EARN return (same schema on earnings timestamps) consume THIS file's definitions.**

## One row = (event, instrument)

- **Events**: the three confirmed series from the DEPLOYED schedule
  (`src/deploy/data/release_schedule.csv`, status=confirmed, ≥2016: CPI, NFP, FOMC) **plus
  Retail Sales MoM** from the TV calendar (the confirmed anti-premium, needed by FU-8).
- **Instruments (legs)**: NQ, ES, RTY, YM — the four deployed legs. Every leg gets rows for
  ALL four series (a research superset: the deployed layer rides subsets, but the dataset
  records what the frozen ride WOULD have done everywhere — that is exactly what the
  conditioning studies need).

## Columns (definitions frozen)

1. **Identity**: `instrument, et, title, source` (schedule | tv).
2. **Power context** (from M2's own functions, causal by construction): realized `jump_pct`,
   `pred_exp` (expanding P_hist — FU-14's primary), `pred_t24`, `n_priors`.
3. **Ride outcome** (the frozen deployed spec, qty=1, via the parity-proven
   `release_executor.run_bracket` on server 1-second data): `ride_outcome, ride_exit_s,
   ride_pnl_usd, ride_net_stressed_usd` (stressed = the deployed per-leg cost). Missing 1s
   coverage ⇒ outcome columns NaN, row kept.
4. **The state vector**: for each of the **165 registry indicators** at DEFAULT parameters,
   `cdir_<key>` and `vdir_<key>` (int8 ∈ {+1,−1,0,2=BOTH}) — the indicator's raw directional
   stance on the **last 1-minute bar CLOSED at or before the rel−300s entry** (= the bar
   stamped rel−360s for on-the-minute releases; the deployed `--ind-1min` convention).
   Context = the trailing **2,000 1m bars** ending at that bar (max default warmup is 255 —
   always satisfied; warmup-neutral enforced anyway). Cross-series indicators carry no
   reference here (`ref_close=None` ⇒ neutral) — DECLARED: their 8 columns are structurally 0
   in v1; a v2 with ES→NQ refs is a follow-up, not smuggled in.
5. **Box-book state (NQ rows only, from the committed FU-1 audits)**: `box_<tf>` ∈ {+1,−1,0}
   for tf ∈ {4h,2h,1h,15m,5m,2m} — the direction of the champion trade OPEN at rel−300s
   (entry_time ≤ t < exit_time), else 0. Other instruments: FU-1 Phase 2 never ran — columns
   absent, not faked.

## Integrity gates (all must pass or the dataset is not committed)

- **C1 — replay parity**: on every (instrument, et) overlapping the committed
  `wsescpi_replay_{INST}.csv` evidence, `ride_pnl_usd` must match to the cent. The outcome
  generator is thereby pinned to the deployed executor's proven behaviour.
- **C2 — causality falsifier**: for a seeded sample of 25 (instrument, event) pairs, the
  stance recomputed with the context window EXTENDED THROUGH THE RELEASE (+1h of future bars)
  must equal the stored stance at the same bar — proving the registry's per-bar values do not
  change when future bars are appended (no centered/future-leaking indicator survives this).
- **C3 — uniqueness**: no duplicate (instrument, et, title) rows.
- **C4 — coverage**: per series, the row count within ±10% of the calendar's ≥2016 count for
  that instrument's data span (missing coverage itemized, not silently dropped).

## Versioning and use rules

- Output: `optimize/fundamentals/fu9_event_state_{INST}.csv` (+ `fu9_result.json` manifest
  with counts, gate results, per-indicator timing) — committed, ledger-bound
  (claim `FU9-EVENT-STATE-DATASET`).
- **v1 freeze**: consumers must cite the dataset version; any regeneration is a new version
  with its own manifest — never an in-place overwrite.
- **Statistical discipline reminder (from the brainstorm ledger)**: this table makes
  p-hacking CHEAP — 330 state columns × ~130 CPI events. FU-5/FU-6 remain bound to their own
  pre-registrations (1–2 mechanism-first conditions, locked holdouts, cross-instrument
  confirmation). The dataset existing is not permission to scan it.

## Blind spots (declared)

1. The state vector uses default indicator parameters — champions run tuned subsets; FU-9
   measures the LIBRARY's information, not any champion's.
2. Cross-series columns structurally neutral in v1 (above).
3. Box state is NQ-only (FU-1 Phase 1 scope).
4. 1m frames are the extended research frames (`load_1m_extended`), not the engine loader —
   same declaration as FU-11 Stage 1.
