<template>
  <div
    v-if="replay.isActive"
    class="flex flex-col gap-2 rounded border border-tv-border bg-tv-surface px-4 py-3"
    data-testid="replay-bar"
  >
    <!-- top row: controls + speed + timestamp -->
    <div class="flex items-center gap-3 text-xs">
      <!-- playback buttons -->
      <button class="replay-btn" title="Step back" @click="replay.stepBack()">
        <svg class="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
          <path d="M3 3h1.5v10H3zm2.5 5 7-5v10z" />
        </svg>
      </button>

      <button class="replay-btn w-16" @click="toggle">
        {{ replay.isPlaying ? 'Pause' : 'Play' }}
      </button>

      <button class="replay-btn" title="Step forward" @click="replay.stepForward()">
        <svg class="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
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

      <!-- running P&L -->
      <span
        class="rounded px-2 py-0.5 font-semibold"
        :class="replay.runningPnl >= 0 ? 'text-tv-green' : 'text-tv-red'"
      >
        {{ replay.runningPnl >= 0 ? '+' : '' }}${{ replay.runningPnl.toFixed(2) }}
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
        class="ml-2 rounded px-2 py-0.5 text-tv-muted hover:bg-tv-tile hover:text-tv-text"
        @click="replay.deactivate()"
      >
        ✕ Exit replay
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
import { useReplayStore } from '../stores/replay';

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
</script>

<style scoped>
.replay-btn {
  @apply flex items-center justify-center rounded bg-tv-tile px-3 py-1 text-tv-text hover:bg-tv-border;
}
</style>
