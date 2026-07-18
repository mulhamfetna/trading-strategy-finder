# Workstream: TimesFM → L1 fusion (research-timesfm-fusion)

**Branch:** `research-timesfm-fusion` (off `dev`). **Opened:** 2026-07-15.
**Goal:** Investigate Google's **TimesFM** time-series foundation model and try to integrate it into our
**L1 test-integration paths and fusion** — starting from a teammate's prior work (`TFM.zip`).

## What TimesFM is (one line)
A pretrained, zero-shot *time-series foundation model* (this work uses **TimesFM 2.5, 200M, CPU**) that
forecasts a **distribution** over the future path — a median plus q10/q90 decile bands — for any series,
no per-series training.

## Fact-check of the teammate's `TFM.zip` (source: its own `vendor-baseline/FINDINGS.md`)

The result is a **reversal of the obvious use**:

1. **Direction predictor → FAILS.** Standalone directional walk-forward: **NQ −$12.7k OOS**, hit-rate
   ~51–53% (coin-flip). Verbatim: *"Do not use TimesFM to pick direction, at ANY timeframe."*
2. **Volatility / regime filter → the real edge.** The forecast band `(q90−q10)/price` is a calibrated
   (~73%) volatility proxy. Rule: **veto an entry when that band is in the top ~15% of its own causal
   history** (p85) — skip the highest-forecast-vol regimes.

Applied to **our own L1 1h+4h fusion book** (their "reference" = 481 trades / **$173,789** = our
MTF-fusion NQ default):

| NQ 1h | trades | PnL | maxDD | Return/DD |
|---|--:|--:|--:|--:|
| reference (all) | 481 | $173,789 | $18,572 | 9.36 |
| **+ vol gate p85** | 447 | **$194,536** | **$10,358** | **18.78** |

- **PnL +$20,747 (+12%), maxDD −$8,214 (−44%), Return/DD doubled.**
- **ES: gate HURTS** (Return/DD 13.62 → 12.18). "ES's edge is already vol-agnostic." → gate NQ, not ES.

### Correction to the brief we were given
The task brief quoted **+$50k PnL / DD $12k**. The directory does **not** support +$50k — the documented
uplift is **+$20.7k** (DD → $10.4k, in the right ballpark). **Decision (user, 2026-07-15): the report is
the truth** — baseline to reproduce and beat is **+$20.7k / DD $10.4k on NQ**.

## What is genuinely solid vs. what to distrust
- ✅ **Causality proven**: forecast at k−1 / k−2 used, k+1 future-peek control is *worse* (17.57 vs 18.78)
  → rides a slow vol regime, not leakage. Binary veto > continuous vol-target sizing. Cross-TF gating
  tested and rejected (match gate horizon to trade horizon).
- ⚠️ **n=1, one 16.5-month BULL sample** (2025-01 → 2026-05). By our standard (power analysis mandatory;
  dumb-control + noise check) a +12% uplift on a single bull regime is **not yet trustworthy** — needs
  regime-robustness before any deploy.

## Plan
1. **[#98] Deep research pass** (mandatory first): TimesFM 2.5 arch/licence; FMs as vol/regime filters vs
   direction; prior art on FM-uncertainty-gated execution; look-ahead pitfalls in quantile bands.
2. **[#99] Reproduce** the documented NQ +$20.7k baseline from the vendored `.npz` caches; re-prove
   causality + the ES no-benefit.
3. **[#100] Integrate** the causal `VolGate` into our real L1 fusion + test-integration paths (not just
   the offline book). Default OFF / golden-safe. Regime-robustness beyond the bull sample.

## Layout
- `vendor-baseline/` — the teammate's harness verbatim (reproduction target). `tfm/` package,
  `gate_service.VolGate` (the deployable causal rule), `deploy_gate.py`, `.cache/*.npz` (precomputed
  TimesFM forecasts → sweeps are instant), `nq_gated_book.csv` (audit trail), `FINDINGS.md`, `README.md`.
