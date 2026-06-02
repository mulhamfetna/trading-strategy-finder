# Winning-Strategy Dashboard (`dashboard_winner/`)

A dedicated, standalone clone dashboard wired to the **WS-G winning strategy** (tag
`v4.2-wsg-drawdown-capped-winner`). It is a *separate* dashboard — the main dashboard
(`../dashboard/`) and the live system are **never touched**.

**Open:** double-click `index.html` (data is embedded in `data.js`; no server needed).

## The strategy it visualises
`SL_soft/hard = 30/40 · TP = 60 · vol-gate @ 60th pct · drawdown circuit-breaker $2,500 / 30 trades`
→ **+$24,720 P/L, max drawdown $4,845 (< $5,000 cap), both years positive, PF 1.55, win 48.3%**
(single contract, 2025–2026 NQ 4h, **n=1 in-sample** — see `../notes/44_winning_system_full_report.md`).

## What it exposes (so the viewer knows what happened, when & why)
- **Header chips:** the exact SL/TP, gate, breaker, and **max-drawdown cap** values.
- **Price panel:** candles + entry/exit markers + **all exit lines — soft SL (amber), hard SL
  (red), TP (green)** drawn per trade; dashed grey = 2025→2026 boundary.
- **Volatility panel:** the HAR-RV forecast with the **gate threshold** line (bars above it are skipped).
- **Engine-state panel:** `1 = TRADING`, `0 = LOCKED` — shows exactly when the drawdown
  circuit-breaker halted trading.
- **Equity** + **underwater drawdown** (with the −$2,500 breaker-trigger and −$5,000 cap lines).
- **Event log (verbose):** every ENTRY (with gate context + the SL/TP placed), EXIT (price,
  exit reason, P/L, running equity & drawdown), and breaker **LOCK / UNLOCK / SKIP** with the why.
- **Trade ledger:** all 120 taken trades with soft/hard SL, TP, exit reason, P/L, equity, drawdown.

## Regenerate
```bash
python3 subprojects/meta-prophet/scripts/49_winning_dashboard_export.py
```
Edit the `# WINNING CONFIG` constants at the top of that script to point the dashboard at a
different config (e.g. the robust alt SL35/40,TP40). Engine = verified single-contract clone
(`../engine_clone/`); the drawdown breaker is a causal post-processing overlay (for live use it
must become an execution-layer equity-stop).
