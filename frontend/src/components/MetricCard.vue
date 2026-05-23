<template>
  <div class="rounded border border-tv-border bg-tv-surface p-3 text-center">
    <div class="text-lg font-semibold tabular-nums" :class="color ?? 'text-tv-text'">{{ value }}</div>
    <div class="mt-1 text-xs text-tv-muted">{{ label }}</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  value: string;
  color?: string;
}>();
</script>
