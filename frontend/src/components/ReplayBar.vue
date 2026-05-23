<template>
  <div
    v-if="replay.isActive"
    class="flex flex-col gap-2 rounded border border-tv-border bg-tv-surface px-4 py-3"
    data-testid="replay-bar"
  >
    <!-- top row: controls + speed + timestamp -->
    <div class="flex items-center gap-3 text-xs">
      <!-- playback buttons -->
      <button
        class="replay-btn"
        title="Step back"
        aria-label="Step back one candle"
        @click="replay.stepBack()"
      >
        <svg class="h-4 w-4" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M3 3h1.5v10H3zm2.5 5 7-5v10z" />
        </svg>
      </button>

      <button
        class="replay-btn w-16"
        :aria-label="replay.isPlaying ? 'Pause replay' : 'Play replay'"
        :title="replay.isPlaying ? 'Pause (Space)' : 'Play (Space)'"
        @click="toggle"
      >
        {{ replay.isPlaying ? 'Pause' : 'Play' }}
      </button>

      <button
        class="replay-btn"
        title="Step forward"
        aria-label="Step forward one candle"
        @click="replay.stepForward()"
      >
        <svg class="h-4 w-4" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
          <path d="M11.5 3H13v10h-1.5zm-8 0 7 5-7 5z" />
        </svg>
      </button>

      <!-- speed -->
      <label class="flex items-center gap-1 text-tv-muted">
        Speed
        <select
          v-model.number="replay.speed"
          class="rounded bg-tv-tile px-1 py-0.5 text-tv-text outline-none ring-1 ring-tv-border"
        >
          <option :value="1">1×</option>
          <option :value="2">2×</option>
          <option :value="5">5×</option>
          <option :value="10">10×</option>
          <option :value="25">25×</option>
        </select>
      </label>

      <!-- running P&L (realised + open-trade MTM, BUG-005-clean sign/color) -->
      <span
        class="rounded px-2 py-0.5 font-semibold"
        :class="signColor(replay.runningPnl) ?? 'text-tv-muted'"
        :title="pnlBreakdown"
        data-testid="running-pnl"
      >
        {{ formatDollar(replay.runningPnl) }}
      </span>

      <!-- candle counter -->
      <span class="ml-auto text-tv-muted">
        candle {{ replay.currentIdx + 1 }} / {{ replay.total }}
        <span v-if="replay.currentCandle" class="ml-2 text-tv-text">
          {{ formatTime(replay.currentCandle.t) }}
        </span>
      </span>

      <!-- close -->
      <button
        class="ml-2 rounded px-2 py-0.5 text-tv-muted hover:bg-tv-tile hover:text-tv-text focus:outline-none focus:ring-2 focus:ring-tv-blue"
        aria-label="Exit replay mode"
        @click="replay.deactivate()"
      >
        <span aria-hidden="true">✕</span> Exit replay
      </button>
    </div>

    <!-- scrubber -->
    <input
      type="range"
      :min="0"
      :max="replay.total - 1"
      :value="replay.currentIdx"
      class="w-full accent-tv-blue"
      @input="onScrub"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useReplayStore } from '../stores/replay';
import { formatDollar, signColor } from '../services/format';

const replay = useReplayStore();

function toggle() {
  if (replay.isPlaying) replay.pause();
  else replay.play();
}

function onScrub(e: Event) {
  replay.pause();
  replay.seekTo(Number((e.target as HTMLInputElement).value));
}

function formatTime(t: string) {
  // ISO string like "2025-01-03T08:00:00" → "2025-01-03 08:00"
  return t.replace('T', ' ').slice(0, 16);
}

// Hover tooltip exposes the realised vs unrealised split.
const pnlBreakdown = computed(
  () =>
    `Realised: ${formatDollar(replay.realisedPnl)}   ` +
    `Open: ${formatDollar(replay.unrealisedPnl)}`,
);
</script>

<style scoped>
.replay-btn {
  @apply flex items-center justify-center rounded bg-tv-tile px-3 py-1 text-tv-text hover:bg-tv-border;
}
</style>
