# Swarm Audit Summary — 2026-05-23

Eight parallel auditors reviewed the NQ trading dashboard (FastAPI + Vue 3) from independent lenses, plus one regression-against-knowledge-base agent.

## Scope

Every panel of the current dashboard layout (status → report → charts → logs):
- Header (App.vue)
- SettingsPanel
- ProgressBar
- ReplayBar
- MetricsCards (the "report")
- ChartPane + BoxesPrimitive (the "charts")
- TradeList (the "logs")

## Lenses

| Lens | Findings | Critical | High | Medium | Low | Report |
|---|---:|---:|---:|---:|---:|---|
| Financial | 31 | 0 | 13 | 13 | 5 | [01-financial-lens.md](01-financial-lens.md) |
| Trading | 27 | 0 | 9 | 13 | 5 | [02-trading-lens.md](02-trading-lens.md) |
| UX/UI | 41 | 1 | 8 | 23 | 9 | [03-uxui-lens.md](03-uxui-lens.md) |
| Logic | 22 | 2 | 11 | 9 | 0 | [04-logic-lens.md](04-logic-lens.md) |
| QA | 18 | 2 | 10 | 6 | 0 | [05-qa-lens.md](05-qa-lens.md) |
| QC | 36 | 0 | 4 | 18 | 14 | [06-qc-lens.md](06-qc-lens.md) |
| Technical | 23 | 0 | 8 | 11 | 4 | [07-technical-lens.md](07-technical-lens.md) |
| **Regression** | **15+6** | **1 FAIL** | — | — | — | [08-regression-audit.md](08-regression-audit.md) |
| **Total** | **198** | **5** | **63** | **93** | **37** | |

## Bug Bounty Knowledge-Base Outcome

### Catalogued bugs (BUG-001..015) status (after legacy purge)
- **PASS:** 13 — fixes are still holding.
- **FAIL (regressions):** BUG-011 (Profit Factor / Sharpe shown as `0.00` instead of `N/A`).
- **N/A:** BUG-008 (no insights panel in current UI).
- **Resolved-by-purge:** BUG-001 partial-FAIL and BUG-015 FAIL — both lived in legacy files (`engine.py`, `ml_filter.py`, `ultimate_dashboard.py`) which were erased on 2026-05-23.

### Proposed new entries (active-stack only)
- **BUG-016** — Latent timestamp-concat corruption in `_candles_from_df` (src/api/app.py:120). Same BUG-003 pattern; dormant unless a Date+Time CSV is loaded.
- **BUG-017** — Silent SSE degrade in /api/backtest/scaling (app.py:307,512,541). BUG-015-family pattern in the new API layer.
- **BUG-019** — Strategy-mode label drift (App.vue:5). Echo of BUG-014. Confirmed by 4 lenses.
- **BUG-020** — Replay desync on Run Backtest mid-replay (replay.ts:50-61, App.vue:21). Confirmed by 3 lenses.
- **BUG-021** — TypeScript `Metrics` shape diverges from Pydantic; `_scaling_metrics` raw dict bypasses validation.
- **BUG-022** — Unauthenticated file upload, no size cap (app.py:55-63, 235-245). Security-class.

> **Dropped on 2026-05-23 legacy purge:** BUG-018 (sentinel-as-denominator in `src/backtest/metrics.py:45` — module deleted).

## Top 5 Critical (must-fix-before-release)

| # | Finding | Severity | File:line | Confirmed by |
|---|---|---|---|---|
| 1 | Max DD sign + color contradiction (`-$0.00` red when no DD) | **Critical** | frontend/src/components/MetricsCards.vue:12 | UXUI-M-1, LOG-M-1, QC-MC-3, TRD-M-1, FIN-M-1 |
| 2 | Replay desync on Run Backtest mid-replay → `:max=-1` HTML, `currentCandle=undefined` | **Critical** | frontend/src/stores/replay.ts:50-61, App.vue:21 | LOG-R-1, LOG-H-1, TECH-H-2 |
| 3 | EMA chart title stale after period change | **Critical** | frontend/src/components/ChartPane.vue:264-275, 326 | LOG-C-1 |
| 4 | BoxesPrimitive: zero test coverage on bar-time snapping (just rewrote, no tests) | **Critical** | frontend/src/components/BoxesPrimitive.ts (no peer test) | QA-CP-1 |
| 5 | sse_parser.test.ts re-implements production code; tests verify themselves | **Critical** | frontend/tests/sse_parser.test.ts:9-24 | QA-X-3 |
| 6 | BUG-011 regressed — PF/Sharpe `0.00` instead of `N/A` | **Critical¹** | frontend/src/components/MetricsCards.vue:14-15 | FIN-M-3/4, TRD-M-2/3, UXUI-M-3, LOG-M-2, QC-MC-1, Regression |

¹ Originally Medium severity; treated as Critical here because it's a regression of an explicitly-resolved checklist item.

> **Resolved-by-purge:** The earlier "Critical #1" (BUG-015 — bare `except: pass`) and the earlier "Critical #2" (Max DD unit collision dollars vs percent) were both legacy-stack issues. The legacy purge on 2026-05-23 erased the modules holding them.

## Strongest Cross-Lens Confirmations (most agents flagged the same defect)

1. **BUG-011 regression (PF/Sharpe = 0.00):** 7 lenses
2. **BUG-005 family at exactly-zero values:** 5 lenses
3. **Strategy-mode header hardcoded (BUG-019):** 4 lenses
4. **Max DD sign:** 4 lenses (unit-collision aspect resolved by legacy purge)
5. **Replay desync (BUG-020):** 3 lenses

## Notes for the Maintainer

- **Out-of-date documentation** flagged by Trading lens (TRD-T-6): `docs/BOX_STRATEGY.md:69-71` still describes the legacy "both weekly AND monthly must agree" rule. The user explicitly abandoned that rule in this session; the code (`box_lookup.py:154-157`) correctly fires on EITHER (weekly priority). **Doc must be updated to match code, not the reverse.**
- **UXUI-M-5** (no metrics empty state) was **fixed in this session** — see frontend/src/components/MetricsCards.vue placeholder cards.
- Out of the 5+1 Critical findings, 3 are test-suite failures (QA-CP-1, QA-X-3, BoxesPrimitive missing tests) — i.e., the regression risk is structurally invisible to CI today.
- **Legacy purge applied on 2026-05-23:** `src/main/`, `src/dashboard/`, `src/indicators/`, `src/backtest/`, `src/signals/`, `src/strategy/scalping_strategy.py`, `src/strategy/backtester.py`, the `/api/backtest` endpoint, and 9 legacy tests have all been deleted. Findings that referenced those modules have been dropped from the per-lens reports.
