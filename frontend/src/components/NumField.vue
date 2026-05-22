<template>
  <label class="flex flex-col">
    <span class="text-tv-muted">{{ label }}</span>
    <input
      type="number"
      :value="modelValue"
      :min="min"
      :max="max"
      :step="step"
      class="rounded bg-tv-tile px-2 py-1 text-tv-text outline-none ring-1 ring-tv-border focus:ring-tv-blue"
      @input="onInput"
    />
  </label>
</template>

<script setup lang="ts">
const props = defineProps<{
  label: string;
  modelValue: number;
  min?: number;
  max?: number;
  step?: number;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void;
}>();

function onInput(ev: Event) {
  const t = ev.target as HTMLInputElement;
  const v = parseFloat(t.value);
  if (!Number.isNaN(v)) emit('update:modelValue', v);
}
</script>
