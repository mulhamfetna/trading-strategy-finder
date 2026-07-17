# Regime-detection — consolidated experiments log

**Workstream:** `research-regime-hmm` (off dev). **Opened 2026-07-15.** Origin: user X threads (`x.md`).
**Question:** can *market-regime detection* (HMM / Jump Model) improve our L1/L2 **policy** (size / sit-out,
NOT entry direction) — and does it survive the robustness bar that killed TimesFM?

Runs through the standard reporting system (template on the timesfm branch:
`subprojects/timesfm-fusion/docs/REPORTING_TEMPLATE.md`).

## Timeline

| # | Stage | What we did | Result | Doc |
|---|-------|-------------|--------|-----|
| 1 | **Prior-art** | Web sweep + the X-thread framework | **GO.** Regime-switching helps OOS (Nystrup 2402.05272, 1990–2023, costs+delays). **Jump Model beats HMM** (Sharpe 0.51→0.78). Filtered-not-smoothed causality. Regime = slow/daily state. | [PRIOR_ART.md](PRIOR_ART.md) |
| 2 | **Repro/baseline** | fit HMM + Jump Model on daily NQ (causal), label fusion trades by live regime | _in progress_ | REPRO.md (tbd) |
| 3 | Dumb control | vs realized-vol tercile / trend-vol quadrant; HMM vs JM | _pending_ | — |
| 4 | Robustness | per-year / CPCV / filtered-only / random-regime control | _pending_ | — |
| 5 | Verdict | regime → policy (size/sit-out) | _pending_ | — |

## Discoveries banked (running)
1. **Jump Model > HMM** for regime detection (persistence + Sharpe) — don't default to the X-thread's HMM.
2. **Regime-switching has genuine OOS precedent** — a materially more promising direction than the TimesFM
   vol-band (which had none). Still held to full robustness.
3. **Filtered-vs-smoothed** is the make-or-break causality control (smoothed labels in a backtest = lookahead).

## Method-workstream links
Trilogy cointegration → **Kalman** → HMM (couples to the Kalman study). Survivors feed the parked
**exogenous-signals-fusion** (regime state → policy head). Reuses the TimesFM extended fusion book
(`~/Mulham/tfm-repro/nq_2426_mtf_log.csv`) + NQ daily data (2010–2026) on the server.
