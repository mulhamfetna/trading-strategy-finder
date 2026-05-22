<template>
  <div class="space-y-4">
    <!-- Section: Data range -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Data</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <label class="flex flex-col">
          <span class="text-tv-muted">CSV path</span>
          <input
            v-model="settings.dataPath"
            class="rounded bg-tv-tile px-2 py-1 text-tv-text outline-none ring-1 ring-tv-border focus:ring-tv-blue"
          />
        </label>
        <div></div>
        <label class="flex flex-col">
          <span class="text-tv-muted">Start (YYYY-MM-DD, optional)</span>
          <input
            v-model="settings.startDate"
            placeholder="(whole CSV)"
            class="rounded bg-tv-tile px-2 py-1 text-tv-text outline-none ring-1 ring-tv-border focus:ring-tv-blue"
          />
        </label>
        <label class="flex flex-col">
          <span class="text-tv-muted">End (YYYY-MM-DD, optional)</span>
          <input
            v-model="settings.endDate"
            placeholder="(whole CSV)"
            class="rounded bg-tv-tile px-2 py-1 text-tv-text outline-none ring-1 ring-tv-border focus:ring-tv-blue"
          />
        </label>
      </div>
    </section>

    <!-- Section: Entry distribution -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Entry distribution &amp; sizing (1-1-2)</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Total contracts" v-model.number="settings.params.total_contracts" :min="1" />
        <NumField label="Leg 1 contracts" v-model.number="settings.params.leg1_contracts" :min="0" />
        <NumField label="Leg 2 contracts" v-model.number="settings.params.leg2_contracts" :min="0" />
        <NumField label="Leg 3 contracts" v-model.number="settings.params.leg3_contracts" :min="0" />
        <NumField label="Leg 2 pullback (pts)" v-model.number="settings.params.leg2_pullback_points" :step="5" />
        <NumField label="Leg 3 pullback (pts)" v-model.number="settings.params.leg3_pullback_points" :step="5" />
      </div>
    </section>

    <!-- Section: Big candle -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Big candle exception</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Threshold (pts)" v-model.number="settings.params.big_candle_threshold_points" :step="10" />
        <NumField label="Full size contracts" v-model.number="settings.params.big_candle_full_contracts" :min="0" />
        <label class="col-span-2 flex items-center gap-2">
          <input type="checkbox" v-model="settings.params.big_candle_reverses_dir" />
          <span class="text-tv-text">Reverse direction on big candle</span>
        </label>
      </div>
    </section>

    <!-- Section: Take profit -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Take profit</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Target (pts from avg)" v-model.number="settings.params.tp_target_points" :step="5" />
        <NumField label="Watch threshold (pts)" v-model.number="settings.params.tp_watch_threshold_points" :step="5" />
      </div>
    </section>

    <!-- Section: Stop loss -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Stop loss</h3>
      <div class="grid grid-cols-2 gap-2 text-xs">
        <NumField label="Soft SL (pts from avg)" v-model.number="settings.params.sl_soft_points" :step="10" />
        <NumField label="Hard SL (pts from avg)" v-model.number="settings.params.sl_hard_points" :step="10" />
      </div>
    </section>

    <!-- Section: Re-entry -->
    <section class="rounded border border-tv-border bg-tv-surface p-3">
      <h3 class="mb-2 text-sm font-semibold text-tv-blue">Re-entry</h3>
      <div class="space-y-2 text-xs">
        <label class="flex items-center gap-2">
          <input type="checkbox" v-model="settings.params.reentry_enabled" />
          <span>Enabled (re-enter after profitable exit if price pulls back)</span>
        </label>
        <NumField label="Cooldown (candles)" v-model.number="settings.params.reentry_cooldown_candles" :min="0" />
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
import { useSettingsStore } from '../stores/settings';
import NumField from './NumField.vue';

const settings = useSettingsStore();
</script>
