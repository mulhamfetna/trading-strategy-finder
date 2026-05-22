<template>
  <div class="flex flex-col">
    <span class="text-tv-muted">{{ label }}</span>
    <span class="font-semibold" :class="color ?? 'text-tv-text'">{{ value }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  value: string;
  color?: string;
}>();
</script>
