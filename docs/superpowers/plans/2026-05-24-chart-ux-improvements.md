# Chart UX Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four focused UX improvements — candle hover tooltip, collapsing RSI/Volume panes, default indicators off, and localStorage persistence for strategy params + indicators.

**Architecture:** All changes are in the Vue 3 frontend. Settings store gains localStorage read/write. ChartPane gains conditional pane creation (vol/RSI created only when enabled) and a crosshair tooltip overlay. No backend changes.

**Tech Stack:** Vue 3 (Composition API, `<script setup>`), Pinia, Lightweight Charts v5, Vitest, `@vue/test-utils`

---

## File Map

| File | What changes |
|------|-------------|
| `frontend/src/stores/settings.ts` | `DEFAULT_INDICATORS` defaults off; localStorage hydration + write-back; `reset()` clears keys |
| `frontend/src/components/ChartPane.vue` | Conditional pane creation in `initChart()`; `rebuildChart()` helper; `hoveredCandle` ref + crosshair sub + tooltip div |
| `frontend/src/components/SettingsPanel.vue` | Button text update (already exists) |
| `frontend/tests/settings_store.test.ts` | New tests: defaults off, localStorage persistence, hydration, reset clears |
| `frontend/tests/SettingsPanel.test.ts` | Verify existing reset button test still passes |

---

## Task 1: Default indicators to off + update tests

**Files:**
- Modify: `frontend/src/stores/settings.ts`
- Modify: `frontend/tests/settings_store.test.ts`

- [ ] **Step 1: Write failing test for new indicator defaults**

Open `frontend/tests/settings_store.test.ts`. Add inside the existing `describe` block:

```ts
it('default indicators: volume and RSI off', () => {
  const s = useSettingsStore();
  expect(s.indicators.showVolume).toBe(false);
  expect(s.indicators.showRSI).toBe(false);
  expect(s.indicators.emaFast).toBe(20);
  expect(s.indicators.emaSlow).toBe(50);
  expect(s.indicators.rsiPeriod).toBe(14);
});
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd frontend && npm test -- --reporter=verbose tests/settings_store.test.ts
```

Expected: FAIL — `expected true to be false` on `showVolume`.

- [ ] **Step 3: Change DEFAULT_INDICATORS in settings.ts**

In `frontend/src/stores/settings.ts`, change lines 18–24:

```ts
const DEFAULT_INDICATORS: IndicatorSettings = {
  emaFast: 20,
  emaSlow: 50,
  showVolume: false,   // was true
  showRSI: false,      // was true
  rsiPeriod: 14,
};
```

- [ ] **Step 4: Run tests — all pass**

```bash
cd frontend && npm test -- --reporter=verbose tests/settings_store.test.ts
```

Expected: all tests PASS (the existing `reset()` test already uses `DEFAULT_INDICATORS`, so it picks this up for free).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/settings.ts frontend/tests/settings_store.test.ts
git commit -m "feat(settings): default volume and RSI to off"
```

---

## Task 2: localStorage persistence for params + indicators

**Files:**
- Modify: `frontend/src/stores/settings.ts`
- Modify: `frontend/tests/settings_store.test.ts`

### Background
`params` and `indicators` are Pinia reactive objects (not refs). We save them on every deep change and hydrate them on store init. The `beforeEach` in the test file must clear localStorage between tests to avoid bleed.

- [ ] **Step 1: Add localStorage-clearing beforeEach to test file**

Replace the existing `beforeEach` in `frontend/tests/settings_store.test.ts`:

```ts
beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
});
```

- [ ] **Step 2: Write failing test — hydration from localStorage**

```ts
it('hydrates params from localStorage on init', () => {
  localStorage.setItem(
    'nq-dash:params',
    JSON.stringify({ total_contracts: 8 }),
  );
  setActivePinia(createPinia());
  const s = useSettingsStore();
  expect(s.params.total_contracts).toBe(8);
  // unrelated field from defaults is still intact
  expect(s.params.leg1_contracts).toBe(1);
});
```

- [ ] **Step 3: Write failing test — write-back on change**

```ts
import { nextTick } from 'vue';

it('saves params to localStorage when a param changes', async () => {
  const s = useSettingsStore();
  s.params.total_contracts = 9;
  await nextTick();
  const saved = JSON.parse(localStorage.getItem('nq-dash:params')!);
  expect(saved.total_contracts).toBe(9);
});

it('saves indicators to localStorage when a flag changes', async () => {
  const s = useSettingsStore();
  s.indicators.showVolume = true;
  await nextTick();
  const saved = JSON.parse(localStorage.getItem('nq-dash:indicators')!);
  expect(saved.showVolume).toBe(true);
});
```

- [ ] **Step 4: Write failing test — reset() clears localStorage**

```ts
it('reset() clears localStorage keys and restores defaults', async () => {
  const s = useSettingsStore();
  s.params.total_contracts = 99;
  await nextTick();
  expect(localStorage.getItem('nq-dash:params')).not.toBeNull();

  s.reset();
  expect(localStorage.getItem('nq-dash:params')).toBeNull();
  expect(localStorage.getItem('nq-dash:indicators')).toBeNull();
  expect(s.params.total_contracts).toBe(4);
  expect(s.indicators.showVolume).toBe(false);
});
```

- [ ] **Step 5: Run tests — verify they fail**

```bash
cd frontend && npm test -- --reporter=verbose tests/settings_store.test.ts
```

Expected: 4 new tests FAIL (hydration/write-back/reset not implemented yet).

- [ ] **Step 6: Implement localStorage persistence in settings.ts**

Replace the entire content of `frontend/src/stores/settings.ts` with:

```ts
import { defineStore } from 'pinia';
import { reactive, ref, watch } from 'vue';
import {
  DEFAULT_BOX_DATA_PATH,
  DEFAULT_BOX_PARAMS,
  DEFAULT_DATA_PATH,
  type BoxParams,
} from '../types';

export interface IndicatorSettings {
  emaFast: number;
  emaSlow: number;
  showVolume: boolean;
  showRSI: boolean;
  rsiPeriod: number;
}

const DEFAULT_INDICATORS: IndicatorSettings = {
  emaFast: 20,
  emaSlow: 50,
  showVolume: false,
  showRSI: false,
  rsiPeriod: 14,
};

const LS_PARAMS = 'nq-dash:params';
const LS_INDICATORS = 'nq-dash:indicators';

function tryLoad<T extends object>(key: string, defaults: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return defaults;
    return { ...defaults, ...JSON.parse(raw) };
  } catch {
    return defaults;
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const params = reactive<BoxParams>(tryLoad(LS_PARAMS, { ...DEFAULT_BOX_PARAMS }));
  const dataPath = ref<string>(DEFAULT_DATA_PATH);
  const boxDataPath = ref<string>(DEFAULT_BOX_DATA_PATH);
  const startDate = ref<string>('');
  const endDate = ref<string>('');
  const indicators = reactive<IndicatorSettings>(
    tryLoad(LS_INDICATORS, { ...DEFAULT_INDICATORS }),
  );

  // Write-back on any deep change
  watch(
    () => [JSON.stringify(params), JSON.stringify(indicators)],
    ([p, i]) => {
      localStorage.setItem(LS_PARAMS, p);
      localStorage.setItem(LS_INDICATORS, i);
    },
  );

  function reset() {
    localStorage.removeItem(LS_PARAMS);
    localStorage.removeItem(LS_INDICATORS);
    Object.assign(params, DEFAULT_BOX_PARAMS);
    Object.assign(indicators, DEFAULT_INDICATORS);
    dataPath.value = DEFAULT_DATA_PATH;
    boxDataPath.value = DEFAULT_BOX_DATA_PATH;
    startDate.value = '';
    endDate.value = '';
  }

  return {
    params,
    dataPath,
    boxDataPath,
    startDate,
    endDate,
    indicators,
    reset,
  };
});
```

- [ ] **Step 7: Run all settings tests — all pass**

```bash
cd frontend && npm test -- --reporter=verbose tests/settings_store.test.ts
```

Expected: all PASS.

- [ ] **Step 8: Run full frontend suite — no regressions**

```bash
cd frontend && npm test
```

Expected: `Test Files 11 passed, Tests 77+ passed`.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/stores/settings.ts frontend/tests/settings_store.test.ts
git commit -m "feat(settings): persist params + indicators to localStorage; reset() clears keys"
```

---

## Task 3: Conditional pane creation — collapsing RSI / Volume panes

**Files:**
- Modify: `frontend/src/components/ChartPane.vue`

### Background
Currently `initChart()` always creates vol (pane 1) and RSI (pane 2) even when the indicators are off. Turning them off only clears their data; the pane frames remain. Fix: only add a series when its indicator is enabled. When the user toggles visibility, call `rebuildChart()` which saves the time range, calls `initChart()`, and restores the range.

The RSI pane index depends on whether volume is present: if vol is hidden, RSI goes to pane 1 (no gap); if vol is shown, RSI goes to pane 2.

- [ ] **Step 1: Modify the `initChart()` function in ChartPane.vue**

Inside `initChart()`, replace the **volume** and **RSI** series creation blocks (currently lines ~265–303) with conditional versions:

```ts
// pane 1: volume histogram — only when enabled
if (settings.indicators.showVolume) {
  volSeries = chart.addSeries(
    HistogramSeries,
    {
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    },
    1,
  );
}

// RSI pane — only when enabled; pane index = 1 if no vol, 2 if vol exists
if (settings.indicators.showRSI) {
  const rsiPane = settings.indicators.showVolume ? 2 : 1;
  rsiSeries = chart.addSeries(
    LineSeries,
    {
      color: CHART_THEME.rsi,
      lineWidth: 1,
      title: 'RSI',
      priceLineVisible: false,
      lastValueVisible: true,
    },
    rsiPane,
  );
  rsiSeries.createPriceLine({
    price: 70,
    color: CHART_THEME.bearThreshold,
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: '70',
  });
  rsiSeries.createPriceLine({
    price: 30,
    color: CHART_THEME.bullThreshold,
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: '30',
  });
}
```

- [ ] **Step 2: Add `rebuildChart()` helper after `applyData()`**

Add this function after the closing brace of `applyData()` (around line 200):

```ts
async function rebuildChart() {
  const range = chart?.timeScale().getVisibleLogicalRange() ?? null;
  initChart();
  if (range) {
    await nextTick();
    chart?.timeScale().setVisibleLogicalRange(range);
  }
}
```

Add `nextTick` to the existing Vue import at the top of `<script setup>`:
```ts
import { computed, onMounted, onBeforeUnmount, watch, ref, toRefs, nextTick } from 'vue';
```

- [ ] **Step 3: Split the indicator watcher into two**

Find the single `watch(...)` that currently watches all indicator settings together (around line 311–325). Replace it with two separate watchers:

```ts
// Visibility toggles → rebuild panes (preserves time range)
watch(
  () => [settings.indicators.showVolume, settings.indicators.showRSI],
  rebuildChart,
);

// Period changes → recompute data only (no pane rebuild)
watch(
  () => [
    settings.indicators.emaFast,
    settings.indicators.emaSlow,
    settings.indicators.rsiPeriod,
  ],
  () => {
    emaFastSeries?.applyOptions({ title: `EMA${settings.indicators.emaFast}` });
    emaSlowSeries?.applyOptions({ title: `EMA${settings.indicators.emaSlow}` });
    applyData();
  },
);
```

- [ ] **Step 4: Run frontend tests — all pass**

```bash
cd frontend && npm test
```

Expected: all `Test Files` pass. (Chart internals are mocked in ChartPane tests so no structural changes needed in tests.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ChartPane.vue
git commit -m "feat(chart): collapse RSI/volume panes when indicators are disabled"
```

---

## Task 4: Candle hover tooltip

**Files:**
- Modify: `frontend/src/components/ChartPane.vue`

### Background
Subscribe to `chart.subscribeCrosshairMove()`. On every crosshair move, find the matching candle and store it in a reactive ref. A `v-if` div in the template renders the OHLCV block in the top-left corner of the chart. The div is `pointer-events: none` so it never blocks interaction.

- [ ] **Step 1: Add `MouseEventParams` to the lightweight-charts import**

In the `import { ... } from 'lightweight-charts'` block (around line 29), add `MouseEventParams`:

```ts
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
  type LineData,
  type HistogramData,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
} from 'lightweight-charts';
```

- [ ] **Step 2: Add `hoveredCandle` ref**

After the existing `const containerRef = ref<HTMLDivElement | null>(null);` line, add:

```ts
const hoveredCandle = ref<Candle | null>(null);
```

- [ ] **Step 3: Add crosshair subscription to `initChart()`**

At the end of `initChart()`, just before `applyData()`, add:

```ts
chart.subscribeCrosshairMove((param: MouseEventParams<Time>) => {
  if (!param.time || !candles.value.length) {
    hoveredCandle.value = null;
    return;
  }
  const ts = param.time as number;
  hoveredCandle.value =
    candles.value.find((c) => (toUTCTimestamp(c.t) as number) === ts) ?? null;
});
```

- [ ] **Step 4: Clear hoveredCandle in `onBeforeUnmount`**

In the `onBeforeUnmount` callback, add:

```ts
hoveredCandle.value = null;
```

- [ ] **Step 5: Add the tooltip div to the template**

In the `<template>` block, add the tooltip div after the `<div ref="containerRef" ...>` line:

```html
<div v-if="hoveredCandle" class="chart-tooltip" data-testid="candle-tooltip">
  <div class="ct-time">
    <span class="ct-date">{{ hoveredCandle.t.split('T')[0] }}</span>
    {{ ' ' }}
    <span class="ct-hr">{{ hoveredCandle.t.split('T')[1]?.substring(0, 5) }}</span>
  </div>
  <div class="ct-row">
    <span class="ct-lbl">O</span>{{ hoveredCandle.o.toLocaleString() }}
    <span class="ct-lbl">H</span><span class="ct-bull">{{ hoveredCandle.h.toLocaleString() }}</span>
  </div>
  <div class="ct-row">
    <span class="ct-lbl">L</span><span class="ct-bear">{{ hoveredCandle.l.toLocaleString() }}</span>
    <span class="ct-lbl">C</span>{{ hoveredCandle.c.toLocaleString() }}
  </div>
  <div class="ct-row">
    <span class="ct-lbl">V</span>{{ hoveredCandle.v.toLocaleString() }}
  </div>
</div>
```

- [ ] **Step 6: Add tooltip CSS to the `<style scoped>` block**

Append inside the existing `<style scoped>` section:

```css
.chart-tooltip {
  position: absolute;
  top: 8px;
  left: 8px;
  background: rgba(30, 34, 45, 0.92);
  border: 1px solid #2a2e39;
  border-radius: 4px;
  padding: 6px 10px;
  font-family: monospace;
  font-size: 11px;
  line-height: 1.6;
  pointer-events: none;
  z-index: 10;
  color: #d1d4dc;
  min-width: 140px;
}
.ct-time {
  margin-bottom: 2px;
}
.ct-date { color: #787b86; }
.ct-hr   { color: #c3c3c3; }
.ct-lbl  { color: #787b86; margin-right: 4px; }
.ct-bull { color: #26a69a; }
.ct-bear { color: #ef5350; }
.ct-row  { display: flex; gap: 10px; }
```

- [ ] **Step 7: Run full test suite — all pass**

```bash
cd frontend && npm test
```

Expected: all `Test Files` pass. The tooltip div is hidden by `v-if` when `hoveredCandle` is null, so existing snapshot/render tests are unaffected.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ChartPane.vue
git commit -m "feat(chart): candle hover tooltip — date/time + OHLCV in top-left overlay"
```

---

## Self-Review

**Spec coverage:**
- ✅ §1 Tooltip: Task 4 — crosshair sub, top-left overlay, date+time+OHLCV
- ✅ §2 Pane collapse: Task 3 — conditional series creation, `rebuildChart()`
- ✅ §3 Default off: Task 1 — `DEFAULT_INDICATORS` changed
- ✅ §4 Persist params+indicators: Task 2 — `tryLoad`, watch write-back, `reset()` clears
- ✅ Reset button: already exists in `SettingsPanel.vue` (`@click="settings.reset"`) — `reset()` now also clears localStorage keys, so no button change needed

**Placeholder scan:** No TBDs, no vague steps — all steps contain actual code.

**Type consistency:**
- `hoveredCandle: ref<Candle | null>` — `Candle` imported from `'../types'` ✅
- `MouseEventParams<Time>` — imported from `'lightweight-charts'` ✅
- `tryLoad<T extends object>` — generic, used with `BoxParams` and `IndicatorSettings` ✅
- `LS_PARAMS`, `LS_INDICATORS` constants defined once, used in `tryLoad`, `watch`, and `reset()` ✅
- `rebuildChart()` uses `nextTick` — added to Vue import in Task 3 Step 2 ✅
