<template>
  <div class="space-y-4">
    <!-- Section: Data -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Data</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <label class="col-span-2 flex flex-col gap-1">
          <span class="text-tv-muted">4h data file <span class="text-tv-blue">(signals)</span></span>
          <FilePicker v-model="settings.dataPath" />
        </label>
        <label class="col-span-2 flex flex-col gap-1">
          <span class="text-tv-muted">Weekly box file</span>
          <FilePicker v-model="settings.weekDataPath" />
        </label>
        <label class="col-span-2 flex flex-col gap-1">
          <span class="text-tv-muted">Monthly box file</span>
          <FilePicker v-model="settings.monthDataPath" />
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

    <!-- §1 Entry distribution & sizing -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
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
    </section>

    <!-- §2 Big candle exception -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
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
    <section class="rounded border border-tv-border bg-tv-surface p-3">
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
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">§4 Stop loss (dual SL system)</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Soft SL (pts from avg)" v-model.number="settings.params.sl_soft_points" :min="0.25" :step="10" />
        <NumField label="Hard SL (pts from avg)" v-model.number="settings.params.sl_hard_points" :min="0.25" :step="10" />
        <NumField label="Soft SL confirmation (min)" v-model.number="settings.params.soft_sl_confirmation_timeframe_minutes" :min="1" />
        <NumField label="Hard SL confirmation (sec)" v-model.number="settings.params.hard_sl_confirmation_timeframe_seconds" :min="1" />
      </div>
      <p v-if="errors.slOrder" class="mt-1 text-[11px] text-tv-red" data-testid="sl-order-error">
        {{ errors.slOrder }}
      </p>
    </section>

    <!-- §5 Take profit -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">§5 Take profit</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Target (pts from avg)" v-model.number="settings.params.tp_target_points" :min="0.25" :step="5" />
        <NumField label="Watch threshold (pts)" v-model.number="settings.params.tp_watch_threshold_points" :min="0.25" :step="5" />
        <NumField label="TP confirmation timeframe (min)" v-model.number="settings.params.tp_confirmation_timeframe_minutes" :min="1" />
      </div>
    </section>

    <!-- §5b Re-entry -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
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
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Box-rule decisions</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Tick threshold (pts above edge)" v-model.number="settings.params.box_tick_threshold" :min="0" :step="0.25" />
        <div></div>
        <NumField label="Weekly window (days)" v-model.number="settings.params.weekly_window_days" :min="1" />
        <NumField label="Monthly window (days)" v-model.number="settings.params.monthly_window_days" :min="1" />
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
import { computed } from 'vue';
import { useSettingsStore } from '../stores/settings';
import DatePicker from './DatePicker.vue';
import FilePicker from './FilePicker.vue';
import NumField from './NumField.vue';

const settings = useSettingsStore();

const errors = computed(() => {
  const p = settings.params;
  return {
    slOrder:
      p.sl_hard_points < p.sl_soft_points
        ? 'Hard SL must be at least as far as Soft SL.'
        : '',
    legOrder:
      p.leg3_pullback_points <= p.leg2_pullback_points
        ? 'Leg 3 pullback must be deeper than Leg 2 pullback.'
        : '',
  };
});
</script>
