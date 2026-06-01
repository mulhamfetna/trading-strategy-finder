# Clone Dashboard — Vol-Aware Backtest Viewer

A **standalone** clone of the live trade dashboard, extended with model-driven panels. It is fully
self-contained (no server, no build, no node) — **just open `index.html` in a browser.**

## What it shows

- **Trades (legacy view):** candlesticks + entry/exit markers + per-trade SL (red) / TP (green)
  lines — the live dashboard's trade overlay.
- **Predicted volatility:** the per-bar HAR-RV forecast that drives the levers.
- **Adaptive SL/TP distances:** how far the stop/target sit each bar for the selected config.
- **Regime gate:** 1 = traded, 0 = skipped (turbulent bars filtered out).
- **Equity curve:** cumulative P/L ($, 1 contract) for the selected config.
- **Data dropdown:** switch the window the backtest runs on — **2025 / 2026 / full** (same picker as the original dashboard).
- **Config dropdown:** switch between baseline / S / G / S+G and watch every panel update.

Sanity check baked in: the **2025 baseline = +$41,740** (matches the approved manual anchor) and
**2026 baseline = −$55,160** (mirror of the flipped-mode claim). The vol levers help most where the
base strategy bleeds — in **2026**, S+G cuts the loss from −$55,160 to −$9,826.

## Engine provenance

Uses ONLY the **verified simple single-contract engine** (cloned, original untouched — see
`../notes/27_backtest_design_and_calibration.md`). The legacy 1-1-2 ladder engine is **not** used.
The proprietary box-grid graphics are intentionally NOT reproduced (project rule: never touch the
candle/box graphic mechanism); this clone focuses on trades + model values.

## How to view

Double-click `index.html`, or for a clean local server:

```bash
cd subprojects/meta-prophet/dashboard
python3 -m http.server 8077    # then open http://localhost:8077
```

## How to regenerate the data

```bash
cd subprojects/meta-prophet
.venv/bin/python scripts/18_dashboard_export.py   # rewrites dashboard/data.js
```

`data.js` embeds the backtest output as `window.DASHBOARD_DATA` (avoids file:// CORS). It is
produced by running the 4 configs through the cloned engine.

## Caveat

P/L numbers are **indicative only** — `../notes/28_phase_G_results.md` shows the calibration sweep
is non-monotonic (overfitting on n=1). Use the volatility model as a **drawdown-control overlay**
(the gate halves drawdown), not a profit figure.
