# E-S1 — the earnings event-state dataset: frozen specification

**Filed 2026-08-20 BEFORE the build. The FU-9 schema (its spec's definitions inherited
verbatim wherever they apply) over the earnings calendar — the substrate for the return's
×indicators phase. Like FU-9: a dataset build, not a hypothesis test; committed only if its
integrity gates pass; its existence is NOT permission to scan it.**

## One row = (earnings event, instrument)

- **Events**: the committed `earnings_timestamps_FINAL_16y.csv` (783 events, 12 tickers,
  2010→2026, EDGAR acceptance ET) — every event whose stamp has a 1m bar (the coverage
  reality E-P1 counted: 462 per instrument).
- **Instruments**: **NQ and ES** (the legs with committed E-P1 evidence). RTY/YM declared a
  possible v2, not smuggled in.

## Columns (FU-9's, earnings edition)

1. **Identity**: `instrument, et (acceptance ET), title (= ticker), session` (AMC/BMO).
2. **Power context** (recomputed by the E-P1 machinery, then PARITY-ANCHORED — see C1):
   `jump_pct, pred` (per-ticker expanding P_hist, ≥8 priors; NaN in warmup).
3. **Reference bracket outcome**: the frozen macro geometry applied verbatim (LONG at
   stamp−300s, S 0.10% worse-of, TP 0.40% better-of, tie⇒STOP, exit +900s, qty=1, stressed
   costs) via the deployed `run_bracket` on server 1s data. RECORDED AS REFERENCE ONLY —
   H1 already rejected this ride on earnings (0/8); the dataset stores what it WOULD do,
   exactly as FU-9 stored Retail rides.
4. **The state vector**: the 165-registry `cdir_/vdir_` stances at the last 1m bar CLOSED
   at or before stamp−300s (the FU-9 convention verbatim: 2,000-bar context, default
   params, warmup-neutral; cross-series columns structurally neutral — declared).

## Integrity gates (all must pass or nothing is written)

- **C1 — power-context parity**: on every (ticker, et) present in the committed
  `ep1_events_{inst}.csv`, this build's `pred` and `jump_pct` must match EXACTLY — the
  dataset is pinned to the claim-bound E-P1 evidence.
- **C2 — the repaint falsifier** (FU-9's, verbatim): 25 seeded events × 165 indicators per
  instrument recomputed with +1h of future bars appended — stances must be unchanged.
- **C3 — uniqueness**: no duplicate (instrument, et, title).
- **C4 — coverage**: rows with a bracket outcome within ±10% of the events with 1s
  coverage; misses itemized.

## Versioning and discipline

Output `optimize/earnings/data/es1_event_state_{INST}.csv` + manifests; **v1 FROZEN**;
claim `ES1-EVENT-STATE-DATASET`; consumers cite the version. The fusion-era warning binds
double here: 330 state columns × ~460 events per instrument is a p-hacking machine, and the
fusion era measured state-conditioning at ≈zero on the macro calendar — any earnings
conditioning study must carry a mechanism, a locked holdout, and its own pre-registration.

## Blind spots (declared)

1. Acceptance-lag (INTC ~7min) shifts both the stance bar and the bracket entry — the C4
   human check (#110) remains the eventual cure; v1 is the frozen best-available.
2. AMC events sit in thin sessions — bracket fills there are model-grade at best.
3. Default indicator params; NQ/ES only; the FU-9 declarations carry over verbatim.
