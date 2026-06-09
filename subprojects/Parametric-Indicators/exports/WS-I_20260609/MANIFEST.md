# WS-I export bundle — 2026-06-09

All WS-I (Parametric-Indicators) deliverables, packaged in groups. Self-contained zips —
unzip each independently.

| Bundle | Contents | What it is |
|---|---|---|
| `WS-I_docs.zip` | 17 markdown docs + `INDICATOR_DECISIONS.pdf` + 4 interactive Plotly charts (`docs/charts/*.html`) + 2 chart-builder scripts | The reference set: indicator logic, vectorization, NSGA-III, playbook, HAR-lag / engulfing / entry-timing reviews, engine + dashboard reports, and the combined `WS-I_MEGADOC.md`. |
| `WS-I_results.zip` | 7× `<tf>_wsi_pareto.csv` + 7× `<tf>_wsi_pareto.png` + `wsi_leaderboard.csv` | The sweep output: per-TF **feasible Pareto fronts** (median P/L ↔ worst DD ↔ win%) and the cross-TF champion leaderboard. |
| `WS-I_report.zip` | `WS-I_RESULTS.md` | The summary report — per-TF champion combos + caveats. |
| `WS-I_server_logs.zip` | 7× `<tf>.log` | Raw AMD-server run logs (3000 trials/TF, NSGA-III). |

## Sweep provenance
- Engine: NSGA-III, 3 objectives (median fold P/L ↑, worst-fold maxDD ↓, median win-rate ↑).
- Feasibility constraint: full-period maxDD ≤ 25% of full-period P/L.
- Search space: box params + all 15 indicators on/off + their params + confirm-K.
- Budget: 3000 trials/TF × 7 TFs (1m, 2m, 5m, 15m, 1h, 2h, 4h), AMD server, weighted parallel workers.

## Caveat
n=1 history (2025→2026): candidate generation, not proof. Re-validate any chosen combo on the
exact dashboard engine (retrace/wait + carry apply there). Fine TFs (1m/2m) attract cost-blind
flip-scalpers — sanity-check exposure + trade counts.
