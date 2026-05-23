# Bug Bounty Regression Audit

Generated: 2026-05-23
Auditor: Regression auditor against `docs/bug-checklist-revision-history.md` Master Bug Register (BUG-001..015) + legacy reports.

## Status Table

| Bug ID | Status | Evidence (file:line) | Notes |
|---|---|---|---|
| BUG-001 | PASS | src/strategy/scaling_strategy.py:459 | Active scaling SSE path multiplies `profit_points * contracts * point_value=2.0`. (Legacy `engine.py` path that previously held a regression of this bug has been erased.) |
| BUG-002 | PASS | src/strategy/scaling_strategy.py:172, 461-462 | `entry_idx = position.opened_at_idx` on prior bar; `exit_idx = idx` (current). |
| BUG-003 | PASS (active) / latent risk | src/api/app.py:120; frontend/src/components/TradeList.vue:105,109; ChartPane.vue:106 | Active CSVs ship single `datetime` column → no concat. Latent: `app.py:120` still does `f"{d}T{t}"` if a future CSV with separate Date+Time arrives. |
| BUG-004 | PASS | frontend/src/components/MetricsCards.vue:44-45; TradeList.vue:59,62 | Sign string is `'+' or ''`. |
| BUG-005 | PASS | MetricsCards.vue:11; TradeList.vue:50,58,61 | `>= 0 ? green : red` everywhere. (Edge cases at exactly 0 reported by UX/UI lens.) |
| BUG-006 | PASS | src/api/app.py:382-384, 405-419 | Scaling SSE separates gross_profit/gross_loss/total_profit cleanly. (Legacy `calculate_metrics` removed.) |
| BUG-007 | PASS | frontend/src/stores/backtest.ts:38-47 | `run()` zeroes all state before SSE stream. |
| BUG-008 | N/A | n/a | No insights/narrative panel exists in current Vue UI. |
| BUG-009 | PASS | src/api/app.py:399-414 | Scaling doesn't deduct fees anywhere; EV formula matches trade P&L. |
| BUG-010 | PASS | scaling_strategy.py:460-475 | No `capital_after` displayed; nothing to mis-reconcile. |
| BUG-011 | **FAIL** | frontend/src/components/MetricsCards.vue:14-15 | `profit_factor.toFixed(2)` / `sharpe_ratio.toFixed(2)` render `0.00` unconditionally — no `N/A` when wins=0 or trades<2. |
| BUG-012 | PASS | MetricsCards.vue (no R/R card) | R/R not displayed. |
| BUG-013 | PASS | scaling_strategy.py:411-429 | Exits clamp to stated SL/TP price. |
| BUG-014 | PASS | frontend/src/App.vue:5 | Header is "1-1-2 Scaling Strategy". No "scalping" label anywhere. (Legacy `ScalpingStrategy` class erased.) |
| BUG-015 | PASS | n/a | Both regression sites (`src/signals/ml_filter.py:89` and `src/main/ultimate_dashboard.py:310`) have been erased with the legacy purge. |

## Re-appeared Bugs (Regressions Detail)

### BUG-011 — Profit Factor / Sharpe shown as `0.00` when undefined
- **Location:** frontend/src/components/MetricsCards.vue:14-15
- **Pattern:** `profit_factor.toFixed(2)` and `sharpe_ratio.toFixed(2)` always render the raw number.
- **Reproduction:** Run a backtest range producing 0 wins or 1 trade → both cards display `0.00`.
- **Severity:** Medium.
- **Confirmed by:** Lens-Financial (FIN-M-3, FIN-M-4), Lens-Trading (TRD-M-2, TRD-M-3), Lens-UX/UI (UXUI-M-3), Lens-Logic (LOG-M-2), Lens-QC (QC-MC-1).

> **Cleanup note:** BUG-001 partial-FAIL (legacy engine.py:170-174) and BUG-015 FAIL (legacy ml_filter.py / ultimate_dashboard.py) are no longer applicable — both code locations were erased in the legacy purge on 2026-05-23. Marked PASS in the table above.

## Newly-Catalog-Worthy Patterns

### BUG-016 — Latent timestamp-concat corruption in `_candles_from_df`
- **Pattern name:** Stringified-Timestamp + Time concatenation
- **Category:** Data formatting / boundary
- **Severity:** High (latent — triggers on Date+Time CSVs)
- **Evidence:** src/api/app.py:120 — `f"{d}T{t}" for d, t in zip(df['Date'].astype(str), df['Time'].astype(str))`. After `load_data` parses Date to `Timestamp`, `astype(str)` yields `'2025-07-28 00:00:00'`. Concatenated with Time, produces `'2025-07-28 00:00:00T18:21:00'` — exact rev-3 corruption signature.
- **Why deserves slot:** Same root pattern as BUG-003 in a different code path still shipped. Currently dead because active CSVs are single-column, but restoring `1min.csv` immediately reproduces the corruption.
- **Recommended regression test:** Property test — `Date dtype is datetime64 AND Time exists ⇒ output matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$``.

### BUG-017 — Silent SSE degrade in /api/backtest/scaling
- **Pattern name:** Silent-degrade-to-fallback in API stream path
- **Category:** Technical reliability / observability
- **Severity:** Medium
- **Evidence:** src/api/app.py:307-308, :512-513, :541-542. 1-min data load failure silently degrades to 4h-only with no SSE warning frame; box-rect pre-compute swallows all exceptions.
- **Why deserves slot:** Same family as BUG-015 (silent error swallowing in load-bearing path), but in the NEW API layer.

### BUG-019 — Strategy-mode label drift (proposed)
- **Pattern name:** Header label hardcoded vs active strategy
- **Category:** UI/data freshness
- **Severity:** Medium
- **Evidence:** frontend/src/App.vue:5 — "NQ 1-1-2 Scaling Strategy Dashboard" hardcoded; Box mode runs under Scaling banner.
- **Why deserves slot:** Confirmed by 4 separate lenses (FIN-H-1, TRD-H-1, UXUI-H-1, QC-H-2). Direct echo of BUG-014's "strategy framing" risk.

### BUG-020 — Replay desync on Run Backtest mid-replay (proposed)
- **Pattern name:** Race: data-clear during active replay timer
- **Category:** State machine / data integrity
- **Severity:** High
- **Evidence:** frontend/src/stores/replay.ts:50-61, 79 + frontend/src/App.vue:21 — Clicking Run Backtest while replay active clears candles → `total=0` → `currentCandle=undefined` → `<input :max=-1>` invalid.
- **Why deserves slot:** Confirmed by 3 lenses (LOG-R-1, LOG-H-1, TECH-H-2).

### BUG-021 — Frontend `Metrics` TS shape diverges from Pydantic (proposed)
- **Pattern name:** TypeScript/Pydantic schema drift
- **Category:** Technical reliability / contract integrity
- **Severity:** High
- **Evidence:** frontend/src/types.ts:60-79 vs src/api/schemas.py:81-97 — `_scaling_metrics` emits raw dict bypassing Pydantic; TS declares fields (`total_fees`, `final_capital`) the scaling backend never sends.
- **Why deserves slot:** Same family as BUG-006 labeling mismatch but in the contract layer.

### BUG-022 — Unauthenticated arbitrary file upload (proposed)
- **Pattern name:** Open file-upload endpoint with no auth/size cap
- **Category:** Security
- **Severity:** High
- **Evidence:** src/api/app.py:55-63, 235-245 — `allow_origins=["*"]`; `await file.read()` with no size limit; CSV written to repo root.
- **Why deserves slot:** Distinct from anything currently in the register; security-class.

## Summary
- Catalogued bugs checked: 15
- PASS: 13 | FAIL: 1 (BUG-011) | N/A: 1 (BUG-008)
- New candidates proposed: 6 (BUG-016, BUG-017, BUG-019, BUG-020, BUG-021, BUG-022)

## Post-cleanup notes (2026-05-23)

The legacy Python pipeline was erased after this audit completed:
- `src/main/`, `src/dashboard/`, `src/indicators/`, `src/backtest/`, `src/signals/` directories deleted.
- `src/strategy/scalping_strategy.py`, `src/strategy/backtester.py` deleted.
- `/api/backtest` endpoint and its Pydantic models removed.
- 9 legacy tests deleted + the `/api/backtest` tests in `test_api.py`.

Consequently:
- BUG-001 partial-FAIL → resolved (engine.py no longer exists).
- BUG-015 FAIL → resolved (ml_filter.py / ultimate_dashboard.py no longer exist).
- BUG-018 (legacy sentinel divisor in `metrics.py:45`) → dropped (metrics.py deleted).
