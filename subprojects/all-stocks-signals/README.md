# all-stocks-signals (WS-AS)

Generalize the frozen NQ signal-export pipeline (`subprojects/signals/`) to **all 6 instruments** in
`ALL_STOCKS/` and produce a delivery bundle per instrument that mirrors `NQ_SIGNALS_DELIVERY/`.

Instruments: `NQ`, `ES`, `QQQ-RTH`, `QQQ-ETH`, `SQQQ-RTH`, `SQQQ-ETH`.
Each: 4-stage product (all-signals → holds-dropped → reverse-signals → reverse-by-direction) ×
7 timeframes (1m…4h) × 3 presets (full/2025/2026). **Candles matched to their own boxes — no mixing.**

## Docs (read in order)
- `docs/ANALYSIS.md` — deep study + the divergences from NQ + the gating decisions (D1/D2/D3).
- `docs/DATA_MAP.md` — exhaustive input→output map, schemas, coverage, the no-mix pairing table.
- `docs/PLAN.md` — phased, test-driven action plan; NQ byte-parity is the correctness anchor.

## Status
Steps 1–4 (scaffold + analysis + data map + plan) complete. **Awaiting verification** of D1/D2/D3
before implementation (PLAN Phase AS.1+). The frozen Stage 1/Stage 2 math is reused, not modified.
