# Hardcoded Values Report

Generated: 2026-05-23
Scope: every literal in `src/` (Python backend) and `frontend/src/` (Vue 3) that is NOT a UI-exposed default. Defaults that the user can change via the SettingsPanel are explicitly excluded.

Each finding is categorised:
- **🟥 Action** — hardcoded value that limits flexibility or hides an assumption; recommend extracting.
- **🟨 Documented** — hardcoded value that has a named constant + comment and is acceptable.
- **🟩 Theme/UI** — palette token or label text; only matters if i18n or theming is on the roadmap.

The report has four sections matching the categories you selected:
1. Magic numbers in source
2. Hardcoded file paths
3. Hardcoded colors and styles
4. Hardcoded UI strings

---

## 1) Magic numbers in source

### 1.1 Backend (Python)

| # | Location | Literal | Category | Notes |
|---|---|---|---|---|
| MN-B-1 | `src/strategy/box_lookup.py:66` | `NQ_TICK_POINTS = 0.25` | 🟨 Documented | NQ tick size. Named constant, fine. |
| MN-B-2 | `src/strategy/box_lookup.py:67` | `SIGNAL_TICKS = 3` | 🟨 Documented | "3 ticks above edge before firing". Named constant. |
| MN-B-3 | `src/strategy/box_lookup.py:89` | `window_days=7` (weekly load) | 🟥 Action | Box window length. Currently a call-site literal — a future "biweekly" box source would have to subclass. Move to module constant `WEEKLY_WINDOW_DAYS = 7`. |
| MN-B-4 | `src/strategy/box_lookup.py:90` | `window_days=30` (monthly load) | 🟥 Action | Same: extract `MONTHLY_WINDOW_DAYS = 30`. |
| MN-B-5 | `src/strategy/box_lookup.py:102` | `pd.Timedelta(days=window_days)` | 🟨 Documented | Derived from MN-B-3/4; OK once those are extracted. |
| MN-B-6 | `src/strategy/box_strategy.py:213` | `pd.Timedelta(hours=4)` | 🟥 Action | Hard assumption that the 4h frame is exactly 4h. Extract to `BoxParams.bar_hours: float = 4.0` or derive from the dataframe's actual delta to support 1h/15min sources. |
| MN-B-7 | `src/strategy/box_strategy.py:149` | `(idx + 1) / n * 100.0` | 🟨 Documented | Percent normaliser; ubiquitous, no action. |
| MN-B-8 | `src/strategy/box_strategy.py:154` | `100.0 * sum(...) / len(trades)` | 🟨 Documented | Win-rate percent normaliser. |
| MN-B-9 | `src/api/app.py:67` | `MAX_UPLOAD_BYTES = 200 * 1024 * 1024` | 🟨 Documented | Named constant. Could read from env (`TRADING_DASH_MAX_UPLOAD`); currently a code-level setting. |
| MN-B-10 | `src/api/app.py:62` | `_DEFAULT_SPLIT = '2025-06-30'` | 🟥 Action | Train/test split date hardcoded to mid-2025. Not used by any active endpoint (`split_train_test` is no longer wired from `_load_and_filter` since the legacy purge) — confirm it's dead; if so, delete. |
| MN-B-11 | `src/api/app.py:436` | `queue.Queue(maxsize=512)` | 🟨 Documented | SSE producer→consumer queue depth. 512 progress frames is generous; OK. Move to module constant `SSE_QUEUE_SIZE = 512` for clarity. |
| MN-B-12 | `src/api/app.py:445` | `progress_every = max(1, len(df) // 100)` | 🟨 Documented | Emit ~100 progress events over the run. Reasonable; consider `MAX_PROGRESS_EVENTS = 100`. |
| MN-B-13 | `src/api/app.py:336` | `len(wins) / n * 100.0` | 🟨 Documented | Win-rate percent. Fine. |
| MN-B-14 | `src/api/app.py:213` | `CHUNK = 1024 * 1024` (upload chunk) | 🟨 Documented | 1 MB streaming chunk; OK. Could be module-level. |
| MN-B-15 | `src/api/app.py:308-310` | `equity = 0.0`, `peak = 0.0`, `max_dd = 0.0` | 🟨 Documented | Loop-init zeros; not magic. |

### 1.2 Frontend (TypeScript / Vue)

| # | Location | Literal | Category | Notes |
|---|---|---|---|---|
| MN-F-1 | `frontend/src/stores/replay.ts:6` | `const TICK_MS = 200` | 🟨 Documented | Named constant — replay-timer interval. |
| MN-F-2 | `frontend/src/services/format.ts` | `'en-US'` locale, `minimumFractionDigits: 2` | 🟨 Documented | Number formatting; locale change would be the only reason to revisit. |
| MN-F-3 | `frontend/src/services/chart_helpers.ts:43` | `k = 2 / (period + 1)` (EMA constant) | 🟨 Documented | Standard EMA formula; OK. |
| MN-F-4 | `frontend/src/components/ChartPane.vue:361` | `.chart-container { min-height: 520px; }` | 🟥 Action | Fixed chart height; doesn't respect small viewports. Use `aspect-ratio` or relative units. (Lens UXUI-C-6.) |
| MN-F-5 | `frontend/src/components/TradeList.vue:24` | `max-h-96` (384px) | 🟥 Action | Inner-scroll cap. With unbounded trade lists this conflicts with the outer page scroll. (Lens UXUI-T-2.) |
| MN-F-6 | `frontend/src/components/TradeList.vue:65,66` | `max-w-[180px]`, `max-w-[200px]` | 🟨 Documented | Cell width caps for `truncate`. OK. |
| MN-F-7 | `frontend/src/components/TradeList.vue:72,76,80,84` | `text-[9px]`, `text-[10px]` | 🟨 Documented | Sub-row typography. OK. |
| MN-F-8 | `frontend/src/components/TradeList.vue:117` | `Math.abs(n) < 0.05` (zero-pts threshold) | 🟨 Documented | Render `-0.0` and `+0.0` as `0.0`. Single literal in one helper; OK. |

---

## 2) Hardcoded file paths

These four CSV filenames are **the entire data surface** of the app. They appear in five separate places and are not derived from any single source of truth — if a user wants to use `NQ_4h_v2.csv` they have to override at the SettingsPanel level every run.

### 2.1 The four canonical paths

| Path | Used as | Default at |
|---|---|---|
| `NQ_4h.csv` | 4h OHLCV signals | `schemas.py:94`, `sse.ts:35`, `settings.ts:23,34`, `app.py:174` (Query default) |
| `NQ_1m.csv` | 1-min monitoring | `schemas.py:95`, `sse.ts:36`, `settings.ts:24,35` |
| `NQ_week_data_shifted.csv` | Weekly box levels | `schemas.py:96`, `sse.ts:37`, `types.ts:133`, `box_lookup.py:84`, `settings.ts`, `app.py:195` |
| `NQ_month_data_shifted.csv` | Monthly box levels | `schemas.py:97`, `sse.ts:38`, `types.ts:134`, `box_lookup.py:85`, `settings.ts`, `app.py:196` |

### 2.2 Findings

| # | Location | Literal | Category | Notes |
|---|---|---|---|---|
| FP-1 | All five locations above | `'NQ_4h.csv'` | 🟥 Action | Five places to update if the canonical 4h filename changes. Centralise via a `DATA_DEFAULTS` constant in a shared module (`src/data/defaults.py` for Python, `frontend/src/services/defaults.ts` for TS) or, better, ship them via `/api/strategy/config` so the frontend always reads them from the backend. |
| FP-2 | Same | `'NQ_1m.csv'` | 🟥 Action | Same. |
| FP-3 | Same | `'NQ_week_data_shifted.csv'` | 🟥 Action | Same. The frontend has its own copy in `types.ts:DEFAULT_BOX_DATA_PATHS`; drift between TS and Pydantic was the root of BUG-021. |
| FP-4 | Same | `'NQ_month_data_shifted.csv'` | 🟥 Action | Same. |
| FP-5 | `src/api/app.py:174` | `data_path: str = Query('1min.csv', ...)` | 🟥 Action | `/api/candles` defaults to the legacy `1min.csv` filename — left over from the legacy purge. Should be `'NQ_4h.csv'` to match the active stack. |

### 2.3 Recommendation

Add one source of truth:

```python
# src/data/defaults.py
NQ_4H_CSV    = 'NQ_4h.csv'
NQ_1MIN_CSV  = 'NQ_1m.csv'
NQ_WEEK_CSV  = 'NQ_week_data_shifted.csv'
NQ_MONTH_CSV = 'NQ_month_data_shifted.csv'
```

Then `schemas.py`, `box_lookup.py`, `app.py` all import from there. Expose the same constants in `/api/strategy/config` and have `frontend/src/types.ts` consume them at runtime instead of hardcoding.

---

## 3) Hardcoded colors and styles

### 3.1 ChartPane Lightweight Charts palette (`frontend/src/components/ChartPane.vue`)

| # | Line | Literal | Used by | Category |
|---|---|---|---|---|
| C-1 | 95, 107 | `#00c853` / `#ff5252` | Trade-marker bull/bear | 🟩 Theme/UI |
| C-2 | 154 | `#00c85344` / `#ff525244` | Volume bar tinted bull/bear | 🟩 Theme/UI |
| C-3 | 210 | `#131722` (chart bg) | LWC `layout.background` | 🟥 Action — duplicates `tv-bg` in Tailwind config |
| C-4 | 210 | `#d1d4dc` (chart text) | LWC `textColor` | 🟥 Action — duplicates `tv-text` |
| C-5 | 211-213 | `#363a45` (grid + borders) | LWC grid / scale borders | 🟥 Action — duplicates `tv-border` |
| C-6 | 219-224 | `#00c853` / `#ff5252` (candle palette) | Candle up/down/wick | 🟩 Theme/UI |
| C-7 | 235 | `#f7931a` (EMA fast) | EMA fast line | 🟩 Theme/UI |
| C-8 | 246 | `#2962ff` (EMA slow) | EMA slow line | 🟩 Theme/UI — same as `tv-blue` |
| C-9 | 269 | `#9c27b0` (RSI line) | RSI series | 🟩 Theme/UI |
| C-10 | 279, 287 | `#ff525288` / `#00c85388` (RSI 70/30 lines) | RSI threshold lines | 🟩 Theme/UI |
| C-11 | 353 | `.chart-empty { color: #787b86 }` (scoped CSS) | Empty-state text | 🟥 Action — duplicates `tv-muted` |
| C-12 | 365 | `.chart-warning { color: #f7931a; background: rgba(247, 147, 26, 0.15); }` | EMA insufficient-data overlay | 🟩 Theme/UI |

**Recommendation:** LWC accepts hex strings, not Tailwind classes, so the chart palette must be in JS. Centralise it in a `chart_theme.ts` module and import the strings everywhere:

```ts
// frontend/src/services/chart_theme.ts
export const CHART_THEME = {
  bg: '#131722',
  text: '#d1d4dc',
  border: '#363a45',
  bull: '#00c853',
  bear: '#ff5252',
  ema_fast: '#f7931a',
  ema_slow: '#2962ff',
  rsi: '#9c27b0',
  muted: '#787b86',
  // tinted variants
  bullTinted: '#00c85344',
  bearTinted: '#ff525244',
  bullThreshold: '#00c85388',
  bearThreshold: '#ff525288',
} as const;
```

That removes 17 separate hex literals from ChartPane and keeps the chart in lockstep with the `tv-*` Tailwind tokens.

### 3.2 Box level colors (`src/strategy/box_lookup.py:46-64`)

`_LEVEL_COLORS` maps each of 16 box labels (8 weekly + 8 monthly) to a `(fill, border)` rgba pair. **272 numeric literals total** (16 labels × 2 strings × ~8.5 numbers each). They're emitted to the frontend via `get_box_rects` and rendered by `BoxesPrimitive.ts`.

| Severity | Notes |
|---|---|
| 🟨 Documented | Bundled as a clearly-named dict with a comment ("Weekly bright, monthly softer so weekly levels are easy to distinguish"). |

**Recommendation:** Extract two helper functions — `_weekly_color(label)` and `_monthly_color(label)` — that derive the alpha from a multiplier (e.g. monthly = 0.5× weekly opacity). That turns 272 literals into 8 base colors + 2 multipliers.

### 3.3 Tailwind palette escapes from `tv-*` tokens

Found in `frontend/src/components/FilePicker.vue` only:

| # | Line | Literal |
|---|---|---|
| TW-1 | 17 | `bg-red-950/30 ring-red-500` (error border) |
| TW-2 | 40 | `bg-red-950/40 text-red-400` (error chip) |
| TW-3 | 43 | `hover:text-red-200` (error dismiss button) |

**100 other usages stay inside the `tv-*` design system.** Only FilePicker leaks. Add `tv-error-bg`, `tv-error-ring`, `tv-error-text` Tailwind tokens or use `tv-red/30` instead.

### 3.4 CORS allowlist

`src/api/app.py:53` — `'http://localhost:5173,http://127.0.0.1:5173'` is the env default. Acceptable: env-overridable via `TRADING_DASH_ALLOW_ORIGINS`. Documented.

---

## 4) Hardcoded UI strings

Every user-facing string in the Vue app is an English literal in a `.vue` template. There is no i18n framework; if multi-language support is on the roadmap this is the biggest chunk of work in the codebase.

### 4.1 Top-level shell (`frontend/src/App.vue`)

| Location | String |
|---|---|
| L5 | `NQ TradingView Box Strategy Dashboard` (title) |
| L6 | `FastAPI + Vue 3 + Lightweight Charts` (subtitle) |
| L18 | `Settings changed — Run Backtest to apply` |
| L24 | `Replay` (button) |
| L32 | `Running...` / `Run Backtest` (button label) |

### 4.2 SettingsPanel (`frontend/src/components/SettingsPanel.vue`)

| Location | String |
|---|---|
| L5 | `Data` (section heading) |
| L8 | `4h data file` + `(signals)` |
| L12 | `1-min data file` + `(SL/TP monitoring)` |
| L16-20 | `Weekly box file` / `Monthly box file` (+ `(NQ_*_data_shifted.csv)` hints) |
| L24, L28 | `Start date (optional)`, `End date (optional)`, `(whole CSV)` placeholder |
| L36 | `Position` |
| L39 | `Contracts`, `Point value ($/pt)` |
| L45 | `Take profit / Stop loss` |
| L47, L48 | `TP (pts from entry)`, `SL (pts from entry)` |
| L54 | `Re-entry` |
| L58 | `Re-enter on the next box signal after exit` |
| L60 | `Cooldown (candles)` |
| L66 | `Indicators` |
| L69, L70 | `EMA fast period`, `EMA slow period` |
| L72 | `Show volume panel` |
| L76 | `Show RSI panel` |
| L79 | `RSI period` |
| L86 | `Reset to defaults` |

### 4.3 ProgressBar (`frontend/src/components/ProgressBar.vue`)

| Location | String |
|---|---|
| L8 | `Running backtest...` |
| L9 | `Error` |
| L10 | `Backtest complete` |
| L11 | `Idle` |
| L27 | `Candle` (status label) |
| L28 | `Trades` |
| L30 | `PnL` |
| L35 | `Win rate` |
| L38 | `Position` |

### 4.4 ReplayBar (`frontend/src/components/ReplayBar.vue`)

| Location | String |
|---|---|
| L13 | `Step back` (title), `Step back one candle` (aria-label) |
| L20-22 | `Pause` / `Play` (button text), `Pause replay` / `Play replay` (aria-label), `Pause (Space)` / `Play (Space)` (title) |
| L27 | `Step forward`, `Step forward one candle` (aria-label) |
| L33 | `Speed` |
| L48 | `candle X / Y` (counter) |
| L57 | `✕ Exit replay`, `Exit replay mode` (aria-label) |

### 4.5 MetricsCards (`frontend/src/components/MetricsCards.vue`)

| Location | String |
|---|---|
| L4 | `Report` |
| L5 | `No report yet`, `N trades` |
| L10-17 | `Net Profit`, `Total Trades`, `Win Rate`, `Profit Factor`, `Sharpe`, `Max DD`, `Avg Win`, `Avg Loss` |

### 4.6 ChartPane (`frontend/src/components/ChartPane.vue`)

| Location | String |
|---|---|
| L5 | `No candles loaded yet.` |
| L70 | `EMA20 / EMA50 hidden — only N candles loaded.` (template literal) |
| L98 | Marker text: `B` / `S` |
| L264 | Title format: `EMA{period}` |
| L270 | `RSI` (pane title) |

### 4.7 TradeList (`frontend/src/components/TradeList.vue`)

| Location | String |
|---|---|
| L7 | `Trades (N)` |
| L11-13 | `Save CSV`, `Export trades to CSV` (title + aria-label) |
| L22 | `No trades yet. Run a backtest to see the trade list.` |
| L28-37 | Column headers: `#`, `Dir`, `Entry time`, `Exit time`, `Entry px`, `Exit px`, `Pts`, `$`, `Reason`, `Box signal` |
| L77 | `conflict` (badge) |
| L78 | `Weekly fired despite monthly disagreement` (title) |
| L138-145 | Tooltip lines: `Box signal:`, `Weekly :`, `Monthly:`, `edges:`, `Weekly box start :`, `Monthly box start:`, `NOTE: weekly and monthly disagreed...` |
| L152 | `${level} (W)` / `(M)` (firing-side label) |
| L158-160 | `since ${date}` |
| L178 | CSV header row (14 columns) |

### 4.8 ProgressBar warnings + errors

Backend warning frames (`stage`, `message`) come through SSE in English (`1min CSV failed to load (...)`; `box-rect overlay disabled (...)`). They concatenate dynamic values, so an i18n boundary would have to lift the message format strings out of `src/api/app.py:411-420, 552-558, 584-588`.

### 4.9 Recommendation

If i18n becomes a goal:
1. Adopt `vue-i18n` (or similar). Replace every templated string with `$t('settings.section.data')` etc.
2. Centralise an `en.json` translation file under `frontend/src/i18n/`.
3. Move backend warning/error messages to a small `messages.py` module that returns keys + a `format()` helper; let the frontend translate by key.

If i18n is NOT on the roadmap, the strings can stay where they are — the inventory above is the cost-of-conversion estimate.

---

## Summary

| Category | 🟥 Action | 🟨 Documented | 🟩 Theme/UI |
|---|---:|---:|---:|
| Magic numbers (backend) | 4 | 11 | 0 |
| Magic numbers (frontend) | 2 | 6 | 0 |
| File paths | 5 | 0 | 0 |
| Chart colors | 4 | 0 | 8 |
| Tailwind palette escapes | 3 | 0 | 0 |
| UI strings | ~120 strings across 7 components | — | — |

### Recommended action items (in order)

1. **Centralise the 4 canonical CSV paths** into one Python module + ship them through `/api/strategy/config`. Removes FP-1..FP-5 (5 hardcoded sites).
2. **Fix `app.py:174` legacy `'1min.csv'` default** on `/api/candles` (one-line change; surfaced by the legacy purge).
3. **Extract `WEEKLY_WINDOW_DAYS`, `MONTHLY_WINDOW_DAYS`, `SSE_QUEUE_SIZE`, `MAX_PROGRESS_EVENTS`** as named module constants (cosmetic but locks the convention).
4. **Replace `pd.Timedelta(hours=4)` in `box_strategy.py:213`** with either a `BoxParams.bar_hours` field or a value derived from the dataframe itself, so a 1h or 15min source could be backtested without code edits.
5. **Confirm `_DEFAULT_SPLIT = '2025-06-30'`** in `app.py:62` is dead code from the legacy purge; if so, delete; if not, expose as a request param.
6. **Centralise chart colors** in `services/chart_theme.ts` (removes 17 hex literals from ChartPane.vue).
7. **Refactor `_LEVEL_COLORS`** in `box_lookup.py` to derive monthly alpha from weekly via a multiplier (272 literals → 8 base + 2 multipliers).
8. **Replace FilePicker's `bg-red-950` / `text-red-400`** with `tv-*` error tokens or with the existing `tv-red/N` variants.
9. **i18n decision:** only worth the ~120-string refactor if multi-language is on the roadmap.
