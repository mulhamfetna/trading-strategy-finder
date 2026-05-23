# Hardcoded Values Report — V2

**Generated:** 2026-05-23 (post master-strategy consolidation, post-conflict-policy ship)
**Supersedes:** `docs/revisions/swarm-2026-05-23/HARDCODED_VALUES_REPORT.md` (V1)

## What changed since V1

The system has gone through three major refactors since V1 was written:

| Round | What happened | Impact on hardcoded values |
|---|---|---|
| 1-1-2 engine restoration | Restored `scaling_strategy.py`; moved every playbook value into `ScalingParams` | `nq_point_value = 2.0` → `params.point_value`; all confirmation timeframes are now params |
| Box-rule decisions exposed | `box_tick_threshold`, `weekly_window_days`, `monthly_window_days` made constructor args | MN-B-3, MN-B-4 from V1 fixed |
| Master-strategy consolidation | Strategy toggle retired; `/api/backtest/scaling` endpoint deleted; Box is the only oracle | `_DEFAULT_SPLIT` likely orphaned; `StrategyConfig` Pydantic now dead |
| Big-Candle conflict policy shipped | `big_candle_resolution` param added | Implicit override removed |

This rescan inventories **what's still hardcoded today** with explicit FIXED / OUTSTANDING / NEW deltas vs V1.

Legend:
- **🟥 Action** — real hardcoded decision; recommend extracting.
- **🟨 Documented** — named constant + comment; acceptable.
- **🟩 Theme/UI** — colour token or label text; only matters for theming/i18n.
- **✅ Fixed since V1** — V1 finding that's now resolved.

---

## 1. Backend magic numbers

### 1.1 Fixed since V1

| Old ID | Location | Status |
|---|---|---|
| MN-B-3 | `box_lookup.py:89` `window_days=7` | ✅ Now `weekly_window_days` param (BoxStrategyParams) |
| MN-B-4 | `box_lookup.py:90` `window_days=30` | ✅ Now `monthly_window_days` param |
| MN-B-6 | `box_strategy.py:213` `pd.Timedelta(hours=4)` | ✅ The old box_strategy was rewritten to subclass `ScalingStrategy`. The 4h assumption no longer surfaces as a literal in the engine; it lives in the *bar grain* of the input CSV. |
| (V1 implicit) | `scaling_strategy.py:381` `nq_point_value = 2.0` | ✅ Now `params.point_value` |
| (V1 implicit) | `BoxLookup.tick_threshold = 0.75` defaulted from `DEFAULT_THRESHOLD` | ✅ Now `box_tick_threshold` param flows through `BoxStrategyParams` |

### 1.2 Still outstanding

| # | Location | Literal | Category | Notes |
|---|---|---|---|---|
| MN-B-2026A | `src/api/app.py:72` | `_DEFAULT_SPLIT = '2025-06-30'` | 🟥 Action | Hardcoded train/test split date. The endpoint that consumed this (`/api/backtest`) was deleted with the legacy purge; `split_train_test(..., split_date=_DEFAULT_SPLIT)` is still invoked from `_load_and_filter` (line 113). **Verify it's dead and remove**, or make it a request parameter. |
| MN-B-2026B | `src/api/app.py:174` | `data_path: str = Query('1min.csv', ...)` | 🟥 Action | `/api/candles` defaults to the legacy `1min.csv` filename that's been gone since the legacy purge. Should be `'NQ_4h.csv'`. This was MN-B-2026A in V1 (FP-5); the V1 fix list said "to be done" — still not done. |
| MN-B-2026C | `src/api/app.py:195-196` | `Query('NQ_week_data_shifted.csv')`, `Query('NQ_month_data_shifted.csv')` | 🟥 Action | `/api/boxes` query-string defaults — duplicate the canonical filenames a sixth and seventh time. (Counts as both FP and MN-B.) |
| MN-B-2026D | `src/api/app.py:424` | `queue.Queue(maxsize=512)` | 🟨 Documented | SSE producer→consumer queue depth. Acceptable but should be promoted to a module constant `SSE_QUEUE_SIZE = 512`. |
| MN-B-2026E | `src/api/app.py:442` | `progress_every = max(1, len(df) // 100)` | 🟨 Documented | Emit ~100 progress events. Reasonable; consider `MAX_PROGRESS_EVENTS = 100`. |
| MN-B-2026F | `src/api/app.py:336, scaling_strategy.py:231, :235, box_strategy.py:149,:154` | `* 100.0` percent conversions | 🟨 Documented | Arithmetic, fine. |
| MN-B-2026G | `src/api/app.py:67` | `MAX_UPLOAD_BYTES = 200 * 1024 * 1024` | 🟨 Documented | Named, env-overridable via `TRADING_DASH_MAX_UPLOAD` would be nicer; not a real action. |
| MN-B-2026H | `src/api/app.py:239` | `CHUNK = 1024 * 1024` | 🟨 Documented | Streaming chunk size; OK. |
| MN-B-2026I | `src/api/schemas.py:19-29` | `StrategyConfig.rsi_period=5, ema_fast=5, ema_slow=15, vol_threshold=2.0, stop_loss=0.6, take_profit=1.8, ...` | 🟥 Action | The whole model is **dead code**. `fetchStrategyConfig` is exported in `frontend/src/services/api.ts` but never called anywhere. The values don't even match the indicator defaults the frontend actually uses (`emaFast=20, emaSlow=50, rsiPeriod=14`). Delete `StrategyConfig` + the `/api/strategy/config` endpoint + the unused `fetchStrategyConfig`. |
| MN-B-2026J | `box_lookup.py:107` | `pd.Timedelta(days=window_days)` | 🟨 Documented | Derived from the configurable `weekly_window_days` / `monthly_window_days`; OK. |

---

## 2. Frontend magic numbers

### 2.1 Fixed since V1

| Old ID | Location | Status |
|---|---|---|
| MN-F-3 | EMA constant `k = 2 / (period + 1)` | Still in `chart_helpers.ts:44`, now extracted from inline ChartPane.vue → centralised. 🟨 Documented. |

### 2.2 Still outstanding

| # | Location | Literal | Category | Notes |
|---|---|---|---|---|
| MN-F-2026A | `frontend/src/stores/replay.ts:6` | `const TICK_MS = 200` | 🟨 Documented | Named replay-timer interval; fine. |
| MN-F-2026B | `frontend/src/services/format.ts` | `'en-US'`, `minimumFractionDigits: 2`, `maximumFractionDigits: 2` | 🟨 Documented | Hardcoded number-formatting locale and precision. Acceptable; only matters if i18n becomes a goal. |
| MN-F-2026C | `frontend/src/components/ChartPane.vue:337, 344` | `min-height: 520px` (in both `.chart-container` and `.chart-shell`) | 🟥 Action | Fixed chart height. Doesn't respect small viewports. Replace with `aspect-ratio` or `clamp()`. Same finding as V1 MN-F-4. |
| MN-F-2026D | `frontend/src/components/TradeList.vue:24` | `class="max-h-96"` | 🟥 Action | Inner-scroll cap of 384px conflicts with outer page scroll for long trade lists. Same as V1 MN-F-5. |
| MN-F-2026E | `frontend/src/components/TradeList.vue:65,66` | `max-w-[180px]`, `max-w-[200px]` | 🟨 Documented | Truncation widths for the Reason / Box-signal cells. OK. |
| MN-F-2026F | `frontend/src/components/DatePicker.vue:156-170` | `0`, `11`, `42` (calendar arithmetic) | 🟨 Documented | Calendar facts: 0/11 are month indices, 42 = 6×7 calendar grid. Not "magic" — they are the domain. |
| MN-F-2026G | `frontend/src/components/TradeList.vue:117` | `Math.abs(n) < 0.05` (zero-pts threshold) | 🟨 Documented | Render small fractions as `0.0`. |

---

## 3. Hardcoded file paths

The four canonical CSV filenames are still **duplicated across 7 source files**. This was the largest 🟥 Action category in V1 and is unchanged.

| Filename | Locations |
|---|---|
| `NQ_4h.csv` | `schemas.py:160`, `sse.ts:34`, `settings.ts:27,37`, **`app.py:174` (still defaulting to legacy `'1min.csv'`)** |
| `NQ_1m.csv` | Removed from active code — the master strategy no longer reads 1-min CSVs in 4h-only mode. |
| `NQ_week_data_shifted.csv` | `schemas.py:161`, `sse.ts:35`, `types.ts:212`, `box_lookup.py:85`, `box_strategy.py:31`, `app.py:195` |
| `NQ_month_data_shifted.csv` | `schemas.py:162`, `sse.ts:36`, `types.ts:213`, `box_lookup.py:86`, `box_strategy.py:32`, `app.py:196` |

### Findings

| # | Issue | Category |
|---|---|---|
| FP-2026A | 4 CSV names duplicated across 6+ locations | 🟥 Action |
| FP-2026B | `app.py:174` `data_path: str = Query('1min.csv', ...)` — legacy filename never updated | 🟥 Action |

### Recommendation (carried over from V1)

```python
# src/data/defaults.py  (new file)
NQ_4H_CSV    = 'NQ_4h.csv'
NQ_1MIN_CSV  = 'NQ_1m.csv'
NQ_WEEK_CSV  = 'NQ_week_data_shifted.csv'
NQ_MONTH_CSV = 'NQ_month_data_shifted.csv'
```

Then `schemas.py`, `box_lookup.py`, `box_strategy.py`, `app.py` all import from there. Ship them through `/api/strategy/config` (or a new `/api/data/defaults` endpoint) and have `frontend/src/types.ts` consume them at runtime instead of hardcoding.

---

## 4. Hardcoded colors and styles

### 4.1 ChartPane Lightweight Charts palette

V1 flagged 12 hex literals in `ChartPane.vue`. Today the count is **20 colour literals** in the same file, unchanged. Lightweight Charts requires hex strings (not Tailwind classes), so they have to live in JS — but they should live in **one** module, not be sprinkled across the component.

| # | Lines | Use |
|---|---|---|
| C-1 | 95, 107, 219, 221, 223 | `#00c853` — bull green |
| C-2 | 95, 107, 220, 222, 224 | `#ff5252` — bear red |
| C-3 | 154 | `#00c85344`, `#ff525244` — tinted volume bars |
| C-4 | 210 | `#131722` — chart bg (duplicates `tv-bg`) |
| C-5 | 210 | `#d1d4dc` — chart text (duplicates `tv-text`) |
| C-6 | 211-213 | `#363a45` — grid + scale borders (duplicates `tv-border`) |
| C-7 | 235 | `#f7931a` — EMA fast |
| C-8 | 246 | `#2962ff` — EMA slow (duplicates `tv-blue`) |
| C-9 | 269 | `#9c27b0` — RSI |
| C-10 | 279, 287 | `#ff525288`, `#00c85388` — RSI 70/30 lines |
| C-11 | 353 | `#787b86` — `.chart-empty` (duplicates `tv-muted`) |
| C-12 | 365 | `#f7931a` — `.chart-warning` |

**Action:** centralise in `frontend/src/services/chart_theme.ts` (described in V1, still not done).

### 4.2 Box level colours

`src/strategy/box_lookup.py:46-64` — `_LEVEL_COLORS` maps 16 box labels to `(fill, border)` rgba pairs. 17 rgba literals counted total in the file. Same finding as V1; no action taken.

### 4.3 Tailwind palette escapes

Only **3 lines** in `frontend/src/components/FilePicker.vue` use Tailwind palette colours outside the `tv-*` design tokens:

```
17 | bg-red-950/30 ring-red-500
40 | bg-red-950/40 text-red-400
43 | hover:text-red-200
```

Same as V1. Add `tv-error-*` tokens to the Tailwind config or use existing `tv-red/N` variants.

### 4.4 CORS allowlist

`src/api/app.py:60-63` — `'http://localhost:5173,http://127.0.0.1:5173'` is the env default, env-overridable via `TRADING_DASH_ALLOW_ORIGINS`. 🟨 Documented.

---

## 5. Hardcoded UI strings

Status **unchanged** from V1: approximately 120 English literals across 7 components. No i18n framework. Detailed inventory is in V1 §4 — every string still applies. Net of changes:

| Change since V1 | Impact |
|---|---|
| App.vue title is now the static string `"NQ Master Strategy Dashboard"` | No longer dynamic (no toggle) but still English. |
| Strategy mode radio strings (`'1-1-2 Scaling'`, `'TradingView Box'`) removed | ✅ −2 strings |
| Box-rule decisions sub-section now always visible with `big_candle_resolution` dropdown — three new English option labels added | +3 strings (`'Big-Candle wins (reverse, ignore box) — default'`, etc.) |

Net: roughly +1 string vs V1. Order of magnitude unchanged.

---

## 6. Diff vs V1 — summary

| Category | V1 🟥 Action | V2 🟥 Action | Delta |
|---|---:|---:|---:|
| Backend magic numbers | 4 | 3 | −1 |
| Frontend magic numbers | 2 | 2 | 0 |
| File paths | 5 | 2 (paths + 1-min default) | −3 |
| Colors / Tailwind | 4 (chart + FilePicker + ChartPane CSS) | 4 | 0 |
| UI strings | ~120 (one big bucket) | ~121 | +1 |

**Five V1 findings actually fixed:**
- MN-B-3, MN-B-4 (`window_days` literals → params)
- MN-B-6 (`pd.Timedelta(hours=4)` removed in BoxStrategy rewrite)
- NQ point value (was buried in scaling_strategy:381 → now `params.point_value`)
- Box tick threshold (was `DEFAULT_THRESHOLD = 0.75` constant → now `box_tick_threshold` param)

**Five V1 findings still pending:**
- FP-1..4 (4 CSV paths duplicated across 6+ files) — unchanged
- FP-5 (`'1min.csv'` legacy default on `/api/candles`) — STILL THERE despite being flagged in V1's "recommended action items"
- MN-B-10 (`_DEFAULT_SPLIT = '2025-06-30'`) — STILL THERE (might be dead code now after the legacy purge; verify)
- MN-F-4 / MN-F-5 (chart `min-height: 520px`, TradeList `max-h-96`) — unchanged
- Tailwind escapes in FilePicker.vue — unchanged

**Three NEW findings (not in V1):**
- MN-B-2026I — `StrategyConfig` Pydantic model + `/api/strategy/config` endpoint + `fetchStrategyConfig` TS function are all **dead code** since the master-strategy consolidation. The defaults inside StrategyConfig (`ema_fast=5, ema_slow=15`) don't even match the frontend's actual indicator defaults (`emaFast=20, emaSlow=50`).
- MN-B-2026C — `/api/boxes` Query defaults duplicate `'NQ_week_data_shifted.csv'` and `'NQ_month_data_shifted.csv'` (5th and 6th sites for these filenames).
- `big_candle_resolution` dropdown adds 3 new English UI strings. (Minor.)

---

## 7. Recommended action plan (ordered by ROI)

| # | Action | Files touched | Effort | Removes |
|---|---|---|---|---|
| 1 | **Centralise the 4 CSV defaults** in `src/data/defaults.py` + mirror in a TS module. Import from one source. | `defaults.py` (new), `schemas.py`, `box_lookup.py`, `box_strategy.py`, `app.py`, `sse.ts`, `types.ts`, `settings.ts` | 1 hr | 6+ hardcoded strings |
| 2 | **Delete `StrategyConfig` + `/api/strategy/config` + `fetchStrategyConfig`** — they are dead code. | `schemas.py`, `app.py`, `api.ts`, `types.ts` | 10 min | 10+ stale defaults |
| 3 | **Fix `app.py:174` `data_path: str = Query('1min.csv', ...)`** to use the centralised default. | `app.py` | 2 min | 1 dead literal |
| 4 | **Audit `_DEFAULT_SPLIT = '2025-06-30'`**. If still called by the active code, expose it as a request param; if dead, delete it. | `app.py` (verify), maybe `schemas.py` | 15 min | 1 hardcoded date |
| 5 | **Centralise chart colours** in `frontend/src/services/chart_theme.ts` and import. | `chart_theme.ts` (new), `ChartPane.vue` | 30 min | 20 inline hex literals |
| 6 | **Refactor `_LEVEL_COLORS`** in `box_lookup.py` to derive monthly alpha from weekly via a multiplier. | `box_lookup.py` | 30 min | ~270 → ~10 constants |
| 7 | **Replace FilePicker Tailwind escapes** with `tv-*` tokens. | `tailwind.config.*`, `FilePicker.vue` | 15 min | 3 escape lines |
| 8 | **Replace `min-height: 520px`** with responsive units. | `ChartPane.vue` | 15 min | 2 magic numbers |
| 9 | **Promote `MAX_PROGRESS_EVENTS = 100` and `SSE_QUEUE_SIZE = 512`** to named module constants. | `app.py` | 5 min | Cosmetic; locks the convention |
| 10 | **i18n decision** — defer unless multi-language is on the roadmap. | All `.vue` templates | days | ~121 strings |

---

## Final note

The master strategy itself is now **fully parameterised** — every behavioural decision from `Currunt_Strategy_Algo_for_Trading.md` and `BOXES_Strategy.md` is reachable from `BoxStrategyParams` and exposed in the dashboard. The remaining 🟥 Action items are **plumbing** (CSV paths, dead config, chart palette duplication), not strategy decisions.

If actions #1 and #2 above are taken, the system goes from 7 hardcoded CSV-filename sites + 10 dead Pydantic defaults to **zero** hardcoded strategy-related literals.
