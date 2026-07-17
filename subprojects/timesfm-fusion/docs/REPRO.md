# Reproduction log — NQ TimesFM vol-gate (workstream #99)

**2026-07-15, on the server** (`amd-trading:~/Mulham/tfm-repro`, `.venv` numpy 2.4.4 / pandas 3.0.3).
Script: `repro_gate.py` (self-contained; reads `vendor-baseline/nq_gated_book.csv`).

## Result: REPRODUCED to the dollar

| NQ 1h | trades | P/L | maxDD | Return/DD | win |
|---|--:|--:|--:|--:|--:|
| reference (all) | 481 | $173,789 | $18,572 | 9.36 | 54.7% |
| + vol gate p85 | 447 | $194,536 | $10,358 | 18.78 | 56.4% |

- All 6 headline metrics match `FINDINGS.md` within ±$50 / ±0.05. ✅
- **Causal gate re-verified independently**: a from-scratch `VolGate(pct=85)` replay reproduces the
  recorded keep/veto mask **481/481 EXACT**, and the gated stats to the dollar. The deployable rule
  in `gate_service.VolGate` does exactly what the report claims.
- The whole effect = **34 vetoed trades netting −$20,747** (32% win) — the −44% drawdown reduction is
  removing this small, losing, high-forecast-vol tail. (The report's "36% / 44 trades / −$15.6k" is its
  p80 *robustness* variant, not the p85 headline — no discrepancy.)

## What this layer PROVES vs. does NOT

**Proves:** the published numbers are internally consistent with the per-trade audit trail, and the
causal veto logic reproduces exactly. The result is real *given the recorded forecast bands*.

**Does NOT yet prove (blocked on missing input):** that the `rel_band` values themselves are correctly
derived from the raw TimesFM `.npz` forecasts. `deploy_gate.py` needs the **reference MTF fusion trade
log** (`nq_run_mtf_log.csv`) to map each entry to a bar and read `rel[k-1]` — that log is **not on the
server** and not in `TFM.zip`. So still outstanding:

1. **Regenerate the reference trade log** from our `mtf_layer_fusion_backtester` (NQ 1h+4h → 481 trades /
   $173,789), then run `deploy_gate.py NQ` end-to-end from the `.npz` → confirms band provenance +
   re-runs the k−1/k−2/k+1 causality control on live bands.
2. **Dumb control** (our SOP): once the reference log exists, gate the SAME book with a plain **ATR /
   realized-vol / rolling-range** percentile instead of TimesFM. If a cheap vol proxy captures most of
   the −44% DD, we don't need a 200M model. *This is the single most important next test.*
3. **ES**: reproduce the documented no-benefit (needs `es_run_mtf_log.csv`).
