<template>
  <div class="space-y-4">
    <!-- Engine toggle (Simple = new Stage-1-driven engine; Box = legacy 1-1-2) -->
    <section class="rounded border border-tv-border bg-tv-surface p-3" data-testid="engine-toggle">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Engine</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <label class="flex items-center gap-2">
          <input
            type="radio"
            value="simple"
            v-model="settings.engineMode"
            data-testid="engine-simple"
          />
          <span><strong>Simple</strong> — Stage 1 entry + dual-SL/TP exit. <em>(recommended)</em></span>
        </label>
        <label class="flex items-center gap-2">
          <input
            type="radio"
            value="box"
            v-model="settings.engineMode"
            data-testid="engine-box"
          />
          <span><strong>Box</strong> — legacy 1-1-2 ladder + box state machine.</span>
        </label>
      </div>
      <p class="mt-1 text-[10px] text-tv-muted">
        Simple = `POST /api/backtest/simple` (JSON, ~1-2s). Box = `POST /api/backtest/box` (SSE, slower).
      </p>
    </section>

    <!-- Section: Data -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Data</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <!-- Dataset preset — flips the three paths in one click. -->
        <label class="col-span-2 flex flex-col gap-1">
          <span class="text-tv-muted">Dataset preset</span>
          <select
            v-model="datasetPreset"
            class="rounded bg-tv-tile px-2 py-1 text-tv-text outline-none ring-1 ring-tv-border focus:ring-tv-blue"
            data-testid="dataset-preset"
          >
            <option value="2026">2026 data (default)</option>
            <option value="2025">2025 data</option>
            <option value="full">Full data</option>
          </select>
          <span class="text-[10px] text-tv-muted">
            Switching the preset overwrites the three paths below. Edit a path manually to override.
          </span>
        </label>

        <label class="col-span-2 flex flex-col gap-1">
          <span class="text-tv-muted">4h data file <span class="text-tv-blue">(signals)</span></span>
          <FilePicker v-model="settings.dataPath" />
        </label>
        <label class="col-span-2 flex flex-col gap-1">
          <span class="text-tv-muted">1-min data file <span class="text-tv-blue">(SL/TP timing)</span></span>
          <FilePicker v-model="settings.dataPath1min" />
        </label>
        <label class="col-span-2 flex flex-col gap-1">
          <span class="text-tv-muted">Box data file <span class="text-tv-blue">(unified W+M levels)</span></span>
          <FilePicker v-model="settings.boxDataPath" />
        </label>
        <label class="flex flex-col gap-1">
          <span class="text-tv-muted">Start date (optional)</span>
          <DatePicker v-model="settings.startDate" placeholder="(whole CSV)" />
        </label>
        <label class="flex flex-col gap-1">
          <span class="text-tv-muted">End date (optional)</span>
          <DatePicker v-model="settings.endDate" placeholder="(whole CSV)" />
        </label>
      </div>
    </section>

    <!-- Simple-engine params (visible only when engineMode='simple') -->
    <section
      v-if="settings.engineMode === 'simple'"
      class="rounded border border-tv-border bg-tv-surface p-3"
      data-testid="simple-params"
    >
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Simple-engine params</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Soft SL (pts from entry)" v-model.number="settings.simpleParams.sl_soft_points" :min="0.25" :step="10" />
        <NumField label="Hard SL (pts from entry)" v-model.number="settings.simpleParams.sl_hard_points" :min="0.25" :step="10" />
        <NumField label="TP (pts from entry)"      v-model.number="settings.simpleParams.tp_points"      :min="0.25" :step="10" />
        <label class="flex flex-col gap-1">
          <span class="text-tv-muted">Direction scope</span>
          <select
            v-model="settings.simpleParams.direction_scope"
            class="rounded bg-tv-tile px-2 py-1 text-tv-text outline-none ring-1 ring-tv-border focus:ring-tv-blue"
            data-testid="direction-scope"
          >
            <option value="both">both (long + short)</option>
            <option value="long_only">long only</option>
            <option value="short_only">short only</option>
          </select>
        </label>
      </div>
      <p
        v-if="simpleErrors.slOrder"
        class="mt-1 text-[11px] text-tv-red"
        data-testid="simple-sl-order-error"
      >{{ simpleErrors.slOrder }}</p>
      <p class="mt-2 text-[10px] text-tv-muted">
        Soft SL fires on <strong>2 consecutive 1-min closes</strong> past the line (fill at the 2nd close).
        Hard SL fires on <strong>1 touch</strong> of the bar's extreme (fill at the line).
        TP fires on a touch of the bar's extreme (fill at the line).
        Per-bar priority: <strong>hard SL &gt; TP &gt; soft SL</strong>.
      </p>
    </section>

    <!-- §1 Entry distribution & sizing -->
    <section v-if="settings.engineMode === 'box'" class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">§1 Entry distribution &amp; sizing (1-1-2)</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Total contracts" v-model.number="settings.params.total_contracts" :min="1" />
        <NumField label="Point value ($/pt)" v-model.number="settings.params.point_value" :min="0.01" :step="0.5" />
        <NumField label="Leg 1 contracts" v-model.number="settings.params.leg1_contracts" :min="0" />
        <NumField label="Leg 2 contracts" v-model.number="settings.params.leg2_contracts" :min="0" />
        <NumField label="Leg 3 contracts" v-model.number="settings.params.leg3_contracts" :min="0" />
        <div></div>
        <NumField label="Leg 2 pullback (pts)" v-model.number="settings.params.leg2_pullback_points" :min="0.25" :step="5" />
        <NumField label="Leg 3 pullback (pts)" v-model.number="settings.params.leg3_pullback_points" :min="0.25" :step="5" />
      </div>
      <p v-if="errors.legOrder" class="mt-1 text-[11px] text-tv-red" data-testid="leg-order-error">
        {{ errors.legOrder }}
      </p>
      <!-- Ladder vs SL tier warning (master strategy §3.2) -->
      <div
        v-if="ladderTier.tier !== 'full'"
        class="mt-2 rounded border px-2 py-1 text-[11px]"
        :class="ladderTier.tier === 'deactivated'
          ? 'border-tv-red/40 bg-tv-red/10 text-tv-red'
          : 'border-yellow-500/40 bg-yellow-500/10 text-yellow-300'"
        data-testid="ladder-tier-warning"
      >
        <strong class="font-semibold uppercase">{{ ladderTier.tier }}:</strong>
        {{ ladderTier.message }}
      </div>
    </section>

    <!-- §2 Big candle exception -->
    <section v-if="settings.engineMode === 'box'" class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">§2 Big candle exception (&gt;400 pts)</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Threshold (pts)" v-model.number="settings.params.big_candle_threshold_points" :min="0.25" :step="10" />
        <NumField label="Full size contracts" v-model.number="settings.params.big_candle_full_contracts" :min="0" />
        <label class="col-span-2 flex items-center gap-2">
          <input type="checkbox" v-model="settings.params.big_candle_reverses_dir" />
          <span class="text-tv-text">Reverse direction on big candle (green→short, red→long)</span>
        </label>
      </div>
    </section>

    <!-- §3 Entry trigger confirmation -->
    <section v-if="settings.engineMode === 'box'" class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">§3 Entry trigger (15-sec confirmation)</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Confirmation timeframe (sec)" v-model.number="settings.params.entry_confirmation_timeframe_seconds" :min="1" />
        <div></div>
        <NumField label="Entry-1 confirmation candles" v-model.number="settings.params.entry1_confirmation_candles" :min="1" />
        <NumField label="Entry-2 / 3 confirmation candles" v-model.number="settings.params.entry23_confirmation_candles" :min="1" />
      </div>
      <p class="mt-1 text-[10px] text-tv-muted">
        Documented but not enforced in 4h-only backtest mode.
      </p>
    </section>

    <!-- §4 Stop loss -->
    <section v-if="settings.engineMode === 'box'" class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">§4 Stop loss (dual SL system)</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Soft SL (pts from avg)" v-model.number="settings.params.sl_soft_points" :min="0.25" :step="10" />
        <NumField label="Hard SL (pts from avg)" v-model.number="settings.params.sl_hard_points" :min="0.25" :step="10" />
        <NumField label="Soft SL confirmation (min)" v-model.number="settings.params.soft_sl_confirmation_timeframe_minutes" :min="1" />
        <NumField label="Hard SL confirmation (min)" v-model.number="settings.params.hard_sl_confirmation_timeframe_minutes" :min="1" />
      </div>
      <p v-if="errors.slOrder" class="mt-1 text-[11px] text-tv-red" data-testid="sl-order-error">
        {{ errors.slOrder }}
      </p>
    </section>

    <!-- §5 Take profit (fixed; no trail per master strategy spec) -->
    <section v-if="settings.engineMode === 'box'" class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">§5 Take profit</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Target (pts from anchor)" v-model.number="settings.params.tp_target_points" :min="0.25" :step="5" />
        <div></div>
      </div>
      <p class="mt-1 text-[10px] text-tv-muted">
        TP is a fixed line at <code class="text-tv-text">anchor ± target</code>. No dynamic trail.
      </p>
    </section>

    <!-- §5c SL/TP anchoring (master strategy §5) -->
    <section v-if="settings.engineMode === 'box'" class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">SL / TP anchor mode</h3>
      <div class="space-y-1 text-xs">
        <label class="flex items-center gap-2">
          <input
            type="radio"
            value="base"
            v-model="settings.params.anchor_mode"
            data-testid="anchor-mode-base"
          />
          <span><strong>Base</strong> — lines fixed at <code>base ± thresholds</code> for trade lifetime.</span>
        </label>
        <label class="flex items-center gap-2">
          <input
            type="radio"
            value="average"
            v-model="settings.params.anchor_mode"
            data-testid="anchor-mode-average"
          />
          <span><strong>Average</strong> — lines re-anchor on every leg fill to the running avg entry.</span>
        </label>
      </div>
    </section>

    <!-- §5b Re-entry -->
    <section v-if="settings.engineMode === 'box'" class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">§5b Re-entry</h3>
      <div class="space-y-2 text-xs">
        <label class="flex items-center gap-2">
          <input type="checkbox" v-model="settings.params.reentry_enabled" />
          <span>Enabled (re-enter after profitable exit if price pulls back)</span>
        </label>
        <NumField label="Cooldown (candles)" v-model.number="settings.params.reentry_cooldown_candles" :min="0" />
      </div>
    </section>

    <!-- Box-rule decisions (always shown; Box is the only directional oracle) -->
    <section v-if="settings.engineMode === 'box'" class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Box-rule decisions</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Tick threshold (pts above edge)" v-model.number="settings.params.box_tick_threshold" :min="0" :step="0.25" />
        <div></div>
      </div>
      <!-- MASTER_STRATEGY_GUIDE §5 — explicit policy for Big-Candle vs Box conflicts -->
      <label class="mt-2 flex flex-col gap-1 text-xs">
        <span class="text-tv-muted">Big-Candle vs Box conflict policy</span>
        <select
          v-model="settings.params.big_candle_resolution"
          class="rounded bg-tv-tile px-2 py-1 text-tv-text outline-none ring-1 ring-tv-border focus:ring-tv-blue"
          data-testid="big-candle-resolution"
        >
          <option value="big_candle_wins">Big-Candle wins (reverse, ignore box) — default</option>
          <option value="box_wins">Box wins (take box direction with full size)</option>
          <option value="skip">Skip — no trade when they disagree</option>
        </select>
        <span class="text-[10px] text-tv-muted">
          Applies only when both rules fire on the same bar with opposite directions.
        </span>
      </label>
    </section>

    <!-- Indicators -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Indicators</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="EMA fast period" v-model.number="settings.indicators.emaFast" :min="2" />
        <NumField label="EMA slow period" v-model.number="settings.indicators.emaSlow" :min="2" />
        <label class="col-span-2 flex items-center gap-2">
          <input type="checkbox" v-model="settings.indicators.showVolume" />
          <span class="text-tv-text">Show volume panel</span>
        </label>
        <label class="col-span-2 flex items-center gap-2">
          <input type="checkbox" v-model="settings.indicators.showRSI" />
          <span class="text-tv-text">Show RSI panel</span>
        </label>
        <NumField label="RSI period" v-model.number="settings.indicators.rsiPeriod" :min="2" :disabled="!settings.indicators.showRSI" />
      </div>
    </section>

    <div class="flex justify-between">
      <button
        class="rounded bg-tv-tile px-3 py-1 text-xs text-tv-muted hover:text-tv-text"
        @click="settings.reset"
      >
        Reset to playbook defaults
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useSettingsStore } from '../stores/settings';
import { DATASET_PRESETS, DEFAULT_DATASET_PRESET, type DatasetPreset } from '../types';
import DatePicker from './DatePicker.vue';
import FilePicker from './FilePicker.vue';
import NumField from './NumField.vue';

const settings = useSettingsStore();

// Dataset preset dropdown. Changing the preset overwrites the three paths
// in one shot; a user who then edits any path manually has diverged from
// the preset — that's fine, the preset value here is just the last-picked
// quick-fill source, not a stored constraint.
const datasetPreset = ref<DatasetPreset>(DEFAULT_DATASET_PRESET);

watch(datasetPreset, (next) => {
  const triplet = DATASET_PRESETS[next];
  settings.dataPath     = triplet.candles4h;
  settings.dataPath1min = triplet.candles1m;
  settings.boxDataPath  = triplet.boxes;
});

const simpleErrors = computed(() => {
  const p = settings.simpleParams;
  return {
    slOrder:
      p.sl_hard_points < p.sl_soft_points
        ? `Hard SL points (${p.sl_hard_points}) must be ≥ Soft SL points (${p.sl_soft_points}).`
        : '',
  };
});

const errors = computed(() => {
  // Dashboard invariants — match the backend's BoxParamsModel._sl_ordering
  // Pydantic validator. If either rule fails here, the backend would also
  // 422 the request — surface the issue inline before submit.
  const p = settings.params;
  const slPtsBad   = p.sl_hard_points <= p.sl_soft_points;
  const slTfBad    = p.soft_sl_confirmation_timeframe_minutes
                   <= p.hard_sl_confirmation_timeframe_minutes;
  const slMessages = [
    slPtsBad ? 'Hard SL points must be strictly greater than Soft SL points.' : '',
    slTfBad  ? 'Soft SL timeframe (min) must be strictly greater than Hard SL timeframe (min).' : '',
  ].filter(Boolean);
  return {
    slOrder: slMessages.join(' '),
    legOrder:
      p.leg3_pullback_points <= p.leg2_pullback_points
        ? 'Leg 3 pullback must be deeper than Leg 2 pullback.'
        : '',
  };
});

// Ladder vs soft-SL validation tier (master strategy §3.2 / R5).
// The ladder needs two adverse moves to fully fill (leg-2 at -leg2_pullback,
// leg-3 at -leg3_pullback). If the soft SL is tighter than those distances,
// the SL fires before the ladder gets a chance — surface the active tier so
// the user sees what behaviour their config produces.
const ladderTier = computed(() => {
  const p = settings.params;
  const sl = p.sl_soft_points;
  const step1 = p.leg2_pullback_points;
  const step2 = p.leg3_pullback_points;
  if (sl < step1) {
    return {
      tier: 'deactivated' as const,
      message:
        `Soft SL (${sl} pts) is tighter than the leg-2 trigger (${step1} pts). ` +
        `The trade will close on SL before any follow-up leg fires — ladder deactivated, single-contract trade.`,
    };
  }
  if (sl < step2) {
    return {
      tier: 'partial' as const,
      message:
        `Soft SL (${sl} pts) is between the leg-2 (${step1}) and leg-3 (${step2}) triggers. ` +
        `Leg-2 can fire, but leg-3 cannot — partial ladder (max 2 contracts).`,
    };
  }
  return { tier: 'full' as const, message: '' };
});
</script>
