# Chart UX Improvements — Design Spec
**Date:** 2026-05-24  
**Scope:** Four focused improvements to `ChartPane.vue` and `settings.ts` / `SettingsPanel.vue`

---

## 1. Candle Hover Tooltip

### What
When the user hovers over any candle on the chart, a floating info box appears in the **top-left corner** of the chart container showing the full bar detail.

### Content
```
2025-05-05  22:00
O 21 845.50   H 22 010.25
L 21 790.00   C 21 980.75
V 142 303
```
- Date and time on one line (`YYYY-MM-DD  HH:mm`), time always shown (not just date)
- O / H / L / C on two lines, H coloured green, L coloured red
- V on its own line
- Hidden when cursor leaves the chart

### Implementation
- Subscribe to `chart.subscribeCrosshairMove(handler)` inside `initChart()`; unsubscribe in `onBeforeUnmount`.
- The handler receives `{ time, seriesData }`. Resolve the candle by matching the UTC timestamp against `candles.value`.
- Store the resolved candle in a `ref<Candle | null>` (`hoveredCandle`).
- In the template, add a `<div v-if="hoveredCandle" class="chart-tooltip">` overlay (same `position:absolute` pattern as the existing `chart-warning` chip).
- Style: dark background (`#1e222d`), 1 px border (`#2a2e39`), monospace font, 11 px, matches existing theme tokens.
- The div is `pointer-events: none` so it never intercepts mouse events.

### Out of scope
- Tooltip does NOT follow the cursor (confirmed style A).
- No click-to-pin behaviour.

---

## 2. Pane Collapse When Indicator Is Unchecked

### What
When **Volume** or **RSI** is unchecked in the indicators panel, the corresponding chart pane is removed entirely — the main candlestick chart expands to fill the freed space. Re-checking re-adds the pane.

### Current behaviour (broken)
The existing watcher calls `applyData()` which calls `volSeries?.setData([])` / `rsiSeries?.setData([])`. The pane frame remains, wasting ~80 px each.

### New behaviour
The indicator visibility watcher in `ChartPane.vue` calls a new helper `syncPaneVisibility()` before `applyData()`:

```
syncPaneVisibility():
  if showVolume is false AND volSeries exists:
    chart.removeSeries(volSeries)
    volSeries = null
  if showVolume is true AND volSeries is null:
    re-add volSeries to pane 1 (same options as initChart)

  same pattern for rsiSeries / pane 2
```

`applyData()` already guards with `if (settings.indicators.showVolume) { volSeries?.setData(...) }` — no change needed there.

### Constraint
`initChart()` must still create both series unconditionally (to initialise the pane layout). The first `syncPaneVisibility()` call (triggered by the watcher firing on mount) will immediately remove any pane whose indicator is off by default.

Wait — simpler: call `syncPaneVisibility()` at the **end** of `initChart()` so the initial state is always correct, rather than relying on the watcher to fire.

---

## 3. Default State: Volume and RSI Off

### What
Change the factory defaults so both indicators are hidden on first load / after reset.

### Change
In `settings.ts`, `DEFAULT_INDICATORS`:
```ts
showVolume: false,   // was true
showRSI:    false,   // was true
```

`reset()` already uses `Object.assign(indicators, DEFAULT_INDICATORS)` — no further change needed.

---

## 4. Persist Strategy Params + Indicators; Reset to Defaults Button

### What
Strategy params and indicator settings survive page refresh. A **Reset to Defaults** button at the bottom of the Settings panel restores factory defaults and clears the saved values.

### Scope of persistence
- **Persisted:** `settings.params` (all `BoxParams` fields) + `settings.indicators` (EMA periods, show flags)
- **Not persisted:** `dataPath`, `boxDataPath`, `startDate`, `endDate` (file paths / dates are session-specific)

### localStorage keys
| Key | Value |
|-----|-------|
| `nq-dash:params` | `JSON.stringify(params)` |
| `nq-dash:indicators` | `JSON.stringify(indicators)` |

### Hydration on init
After `reactive<BoxParams>({ ...DEFAULT_BOX_PARAMS })` and `reactive<IndicatorSettings>({ ...DEFAULT_INDICATORS })`, attempt to parse each key from `localStorage`. On success, `Object.assign` the parsed value onto the reactive object. On any parse error, ignore and keep defaults (no throw).

### Write-back
A single `watch([params, indicators], save, { deep: true })` call writes both keys whenever any value changes. Debounce is not needed — the data is small.

### Reset behaviour
`reset()` (already exists) clears both localStorage keys and restores defaults:
```ts
function reset() {
  localStorage.removeItem('nq-dash:params');
  localStorage.removeItem('nq-dash:indicators');
  Object.assign(params, DEFAULT_BOX_PARAMS);
  Object.assign(indicators, DEFAULT_INDICATORS);
  dataPath.value = DEFAULT_DATA_PATH;
  boxDataPath.value = DEFAULT_BOX_DATA_PATH;
  startDate.value = '';
  endDate.value = '';
}
```

### Button placement
Bottom of `SettingsPanel.vue`, outside all `<section>` blocks, full-width. Muted/destructive style (grey border, red text on hover) to reduce accidental clicks.

```
[ Reset to Defaults ]
```

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/ChartPane.vue` | Add `hoveredCandle` ref + crosshair subscription + tooltip div; add `syncPaneVisibility()`; call both in `initChart()` |
| `frontend/src/stores/settings.ts` | Hydrate from localStorage on init; `watch` to write back; update `reset()` to clear keys; change `DEFAULT_INDICATORS` defaults |
| `frontend/src/components/SettingsPanel.vue` | Add Reset to Defaults button at bottom |

## Tests to update / add

- `frontend/tests/settings_store.test.ts`: test that `reset()` removes localStorage keys; test hydration from localStorage on store init
- `frontend/tests/ChartPane.test.ts`: existing tests should still pass; add a test that `syncPaneVisibility()` removes/re-adds series based on flags (may require mocking the chart API)
- No backend changes needed
