# Dumb control — does a cheap vol proxy replace TimesFM? (workstream #99, layer 2a)

**2026-07-15, server** (`~/Mulham/tfm-repro`, `dumb_control.py`, NQ 1h = `bundle_data_all/NQ_1h.csv`,
8121 bars, all 481 entries mapped). Our SOP: never accept a positive result without the **dumb control**.

## Question
TimesFM's causal p85 vol-gate lifts NQ Return/DD 9.36 → 18.78 (DD −44%). Can a plain volatility
estimator do the same job on the **same 481-trade book**, using the identical causal p85 `VolGate`?

## Method
Same audit-trail book (entry_time + pnl). Replace the TimesFM band with cheap proxies computed on NQ 1h
price at the bar BEFORE entry (causal): **ATR(n)/close**, **realized-vol(n)** (std of log-returns),
**rolling-range(n)/close**, each swept over n ∈ {14, 24, 50, 100}. **Keep the proxy's BEST lookback** —
an in-sample advantage deliberately handed to the dumb control (steelman).

## Result — TimesFM wins clearly

| gate | trades | P/L | maxDD | Return/DD | ∩ TimesFM vetoes | corr(band) |
|---|--:|--:|--:|--:|--:|--:|
| reference (all) | 481 | $173,789 | $18,572 | 9.36 | — | — |
| **TimesFM p85** | 447 | **$194,536** | **$10,358** | **18.78** | (self) | 1.00 |
| range50 (best cheap) | 431 | $179,387 | $13,528 | 13.26 | 21/34 | 0.68 |
| ATR100 | 429 | $177,417 | $14,059 | 12.62 | 15/34 | 0.80 |
| realvol24 | 427 | $156,856 | $12,479 | 12.57 | 12/34 | 0.59 |
| range24 | 430 | $176,395 | $14,600 | 12.08 | 14/34 | 0.63 |
| range14 | 435 | $183,753 | $15,649 | 11.74 | 13/34 | 0.54 |
| range100 | 434 | $169,815 | $15,545 | 10.92 | 22/34 | 0.75 |
| realvol50 | 428 | $176,902 | $16,587 | 10.67 | 16/34 | 0.66 |
| realvol100 | 424 | $169,721 | $17,593 | 9.65 | 14/34 | 0.73 |
| ATR24 | 433 | $172,447 | $18,997 | 9.08 | 14/34 | 0.69 |
| realvol14 | 428 | $145,318 | $17,415 | 8.34 | 12/34 | 0.49 |
| ATR14 | 434 | $164,809 | $20,308 | 8.12 | 12/34 | 0.56 |
| ATR50 | 429 | $171,488 | $22,003 | 7.79 | 20/34 | 0.75 |

**Best cheap proxy (range50) = 13.26 vs TimesFM 18.78.**

## Interpretation
- **TimesFM survives the dumb control.** Even best-of-12 (in-sample-picked) cheap proxies reach only
  ~13.3 Return/DD; the best recovers ≈40% of the 9.36→18.78 uplift. TimesFM ≈ doubles that.
- **Not a lagged ATR.** Band↔proxy correlations are 0.49–0.80 (related, not identical), and cheap gates
  veto a *different* set — only 12–22 of TimesFM's 34 vetoes overlap. TimesFM drops a *better-chosen*
  losing tail. Plausible mechanism: the band is a **forward** forecast, the proxies are **backward**.
- So the 200M model is **earning its keep on this sample** — a cheap substitute does NOT capture the edge.

## Still NOT proven (do not deploy yet)
- **n=1, single bull sample.** The whole effect is 34 tail trades; TimesFM picks a better 34 than ATR,
  but "better tail selection on one 16.5-month window" can still be luck. Needs **multi-regime / purged
  cross-validation / randomized-OOS** (per PRIOR_ART.md §5) before trust.
- **Band provenance** (bands re-derived from the raw `.npz` via `deploy_gate.py` + reference log) still
  outstanding — the shareable `mtf_layer_fusion_backtester` needs its champion paths wired first.
- This uses the p85 the teammate chose; threshold not re-tuned OOS here.

## Verdict
**GO deeper.** TimesFM beats the dumb control → integrate the causal gate into L1 (default OFF,
golden-safe) and run the regime-robustness battery. The edge is real *and* not trivially replicable —
exactly the profile that justifies the integration work (#100).
