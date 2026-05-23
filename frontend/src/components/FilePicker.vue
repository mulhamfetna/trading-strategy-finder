<template>
  <div class="flex flex-col gap-1">
    <!-- Hidden native file input -->
    <input
      ref="inputRef"
      type="file"
      accept=".csv"
      class="hidden"
      @change="onFileChange"
    />

    <!-- Trigger row -->
    <div
      class="flex cursor-pointer items-center gap-1.5 rounded px-2 py-1 ring-1 transition-colors"
      :class="[
        uploading ? 'pointer-events-none opacity-60' : 'hover:ring-tv-blue',
        error ? 'bg-tv-error-bg/60 ring-tv-error-ring' : 'bg-tv-tile ring-tv-border',
      ]"
      @click="inputRef?.click()"
    >
      <!-- Folder icon -->
      <svg class="h-3.5 w-3.5 shrink-0 text-tv-muted" viewBox="0 0 16 16" fill="currentColor">
        <path d="M1 3.5A1.5 1.5 0 0 1 2.5 2h3.586a1.5 1.5 0 0 1 1.06.44L8.207 3.5H13.5A1.5 1.5 0 0 1 15 5v7a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 1 12V3.5z"/>
      </svg>
      <span class="flex-1 truncate text-xs" :class="modelValue ? 'text-tv-text' : 'text-tv-muted'">
        {{ uploading ? 'Uploading…' : (modelValue || 'Choose file…') }}
      </span>
      <!-- Spinner -->
      <svg v-if="uploading" class="h-3.5 w-3.5 shrink-0 animate-spin text-tv-blue" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z"/>
      </svg>
      <!-- Browse hint -->
      <span v-else class="shrink-0 text-[10px] text-tv-muted">Browse</span>
    </div>

    <!-- Error message (full text, dismissable) -->
    <div
      v-if="error"
      class="flex items-start gap-1 rounded bg-tv-error-bg/80 px-2 py-1 text-[10px] text-tv-error-text"
    >
      <span class="flex-1">{{ error }}</span>
      <button class="shrink-0 hover:text-tv-error-text-hover" @click="error = ''">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import axios from 'axios';

const props = defineProps<{ modelValue: string }>();
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>();

const inputRef = ref<HTMLInputElement | null>(null);
const uploading = ref(false);
const error = ref('');

async function onFileChange(evt: Event) {
  const file = (evt.target as HTMLInputElement).files?.[0];
  if (!file) return;

  uploading.value = true;
  error.value = '';

  try {
    const form = new FormData();
    form.append('file', file);
    // Do NOT set Content-Type manually — axios must set it automatically
    // so the boundary string is included (multipart/form-data; boundary=…).
    const { data } = await axios.post<{ path: string }>('/api/upload-data-file', form);
    emit('update:modelValue', data.path);
  } catch (err: unknown) {
    const msg = axios.isAxiosError(err)
      ? (err.response?.data?.detail ?? err.message)
      : 'Upload failed.';
    error.value = String(msg);
  } finally {
    uploading.value = false;
    if (inputRef.value) inputRef.value.value = '';
  }
}
</script>
