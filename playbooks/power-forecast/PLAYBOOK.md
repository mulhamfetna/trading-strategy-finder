# PLAYBOOK — power-forecast v1.0.0 (the night-before event-size layer)

**Deployed v5.4.3 (FU-14, #166). An INFORMATION layer: it forecasts how BIG each scheduled
macro release's move will be, the night before — it takes no positions and drives no orders.
Consumers (sizing, geometry, the fused vol engine) are separate gated studies.**

## What it is
M2's verified power model (#126), productionized verbatim: for each upcoming scheduled event
of the modeled series ({CPI, NFP, FOMC, Retail Sales, Durable Goods} × instrument),
**P_hist = median of that series' own prior release-bar |open→close|%** — expanding (the
pre-registered primary) and trailing-24 (the regime-aware variant) — shifted one release,
≥8 priors. Verified skill: pooled OOS Spearman(P_hist, realized jump) **NQ 0.5907 · ES 0.5719
· RTY 0.6184 · GC 0.4932 · CL 0.5461** (t24; committed evidence + this module reproduce each
other to ≤1e-16).

## How to run it
```bash
# nightly ops artifact (JSONL: series, event time, n_priors, predicted power % and $/contract)
python3 -m src.deploy.power_forecast forecast --instrument NQ --now "<tonight>" --horizon-days 30
# verification (any time, any machine with the data tree)
python3 -m src.deploy.power_forecast verify   --instrument NQ     # parity vs committed evidence
python3 -m src.deploy.power_forecast scramble --instrument NQ     # the falsifier must collapse
```
Sample artifact: `sample_power_forecast_NQ.jsonl` (generated 2026-08-19; the 2026-08-26
Durables print predicted 0.020% t24 ≈ $117/contract).

## How to read it
- **POWER ≠ PREMIUM** (the programme's law): NFP/FOMC out-rank CPI on *predicted power* while
  only CPI pays the ride — this layer sizes expectations, it does not pick trades.
- The trailing-24 variant tracks regime shifts (the expanding median lags them); both are
  emitted; t24 is the operational default, the expanding value is the pre-registered primary.
- $/contract = predicted % × last close × point value — a scale aid, not a fill promise.

## Provenance
Model + gates confirmed in WS-NEWS3 M2 (#126, pre-registered; V1 quintiles, V3 label-shuffle,
clean-minute control). Productionization verified in FU-14 (#166): parity 5/5 exact, scramble
collapse (+0.591 → +0.212), golden gate 6/6 untouched, ledger claim
`FU14-POWER-FORECAST-DEPLOYED` (suite 43/43). Full record: `docs/WS-FUSION-FULL-RECORD.md` F-5.
