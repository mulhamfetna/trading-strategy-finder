<template>
  <div ref="rootRef" class="relative">
    <!-- Trigger -->
    <div
      class="flex cursor-pointer items-center gap-1.5 rounded bg-tv-tile px-2 py-1 ring-1 ring-tv-border focus-within:ring-tv-blue"
      @click="toggle"
    >
      <svg class="h-3.5 w-3.5 shrink-0 text-tv-muted" viewBox="0 0 16 16" fill="currentColor">
        <path d="M5 1v1H3a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1h-2V1h-1v1H6V1H5zm-2 4h10v8H3V5z"/>
      </svg>
      <span class="flex-1 text-xs" :class="modelValue ? 'text-tv-text' : 'text-tv-muted'">
        {{ modelValue || placeholder }}
      </span>
      <button
        v-if="modelValue"
        class="text-tv-muted hover:text-tv-text"
        @click.stop="clear"
      >✕</button>
    </div>

    <!-- Calendar popup -->
    <Transition name="dp-fade">
      <div
        v-if="open"
        class="absolute left-0 top-full z-50 mt-1 w-60 rounded border border-tv-border bg-tv-surface p-3 shadow-xl"
      >
        <!-- Month navigation -->
        <div class="mb-3 flex items-center justify-between">
          <button class="dp-nav-btn" @click.stop="shiftMonth(-1)">
            <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="currentColor"><path d="M10 3L5 8l5 5V3z"/></svg>
          </button>
          <div class="flex items-center gap-1">
            <select
              :value="viewMonth"
              class="rounded bg-tv-tile px-1 py-0.5 text-xs text-tv-text outline-none"
              @change="viewMonth = Number(($event.target as HTMLSelectElement).value)"
              @click.stop
            >
              <option v-for="(m, i) in MONTHS" :key="i" :value="i">{{ m }}</option>
            </select>
            <select
              :value="viewYear"
              class="rounded bg-tv-tile px-1 py-0.5 text-xs text-tv-text outline-none"
              @change="viewYear = Number(($event.target as HTMLSelectElement).value)"
              @click.stop
            >
              <option v-for="y in yearRange" :key="y" :value="y">{{ y }}</option>
            </select>
          </div>
          <button class="dp-nav-btn" @click.stop="shiftMonth(1)">
            <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="currentColor"><path d="M6 3l5 5-5 5V3z"/></svg>
          </button>
        </div>

        <!-- Weekday labels -->
        <div class="mb-1 grid grid-cols-7 text-center">
          <span
            v-for="d in ['Su','Mo','Tu','We','Th','Fr','Sa']"
            :key="d"
            class="text-[10px] font-semibold text-tv-muted"
          >{{ d }}</span>
        </div>

        <!-- Day cells -->
        <div class="grid grid-cols-7 gap-y-0.5">
          <button
            v-for="cell in cells"
            :key="cell.key"
            class="dp-day"
            :class="dayClass(cell)"
            :disabled="!cell.current"
            @click.stop="select(cell)"
          >
            {{ cell.day }}
          </button>
        </div>

        <!-- Quick-jump: Today -->
        <div class="mt-2 border-t border-tv-border pt-2 text-center">
          <button
            class="text-[11px] text-tv-blue hover:underline"
            @click.stop="selectToday"
          >Today</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

const props = withDefaults(
  defineProps<{
    modelValue: string;   // "YYYY-MM-DD" or ""
    placeholder?: string;
  }>(),
  { placeholder: 'Pick a date' },
);

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void;
}>();

// ---- state ----
const open = ref(false);
const rootRef = ref<HTMLElement | null>(null);

const today = new Date();
const todayStr = fmt(today.getFullYear(), today.getMonth() + 1, today.getDate());

// The month/year currently shown in the calendar
const viewYear = ref(today.getFullYear());
const viewMonth = ref(today.getMonth()); // 0-based

// Sync viewYear/viewMonth to the currently selected value when opening
function toggle() {
  if (!open.value && props.modelValue) {
    const [y, m] = props.modelValue.split('-').map(Number);
    viewYear.value = y;
    viewMonth.value = m - 1;
  } else if (!open.value) {
    viewYear.value = today.getFullYear();
    viewMonth.value = today.getMonth();
  }
  open.value = !open.value;
}

function clear() {
  emit('update:modelValue', '');
}

// ---- calendar math ----

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

const yearRange = computed(() => {
  const base = today.getFullYear();
  return Array.from({ length: 12 }, (_, i) => base - 5 + i);
});

interface Cell { key: string; day: number; current: boolean; dateStr: string; }

const cells = computed<Cell[]>(() => {
  const year = viewYear.value;
  const month = viewMonth.value; // 0-based
  const firstDow = new Date(year, month, 1).getDay(); // 0=Sun
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const daysInPrev = new Date(year, month, 0).getDate();

  const grid: Cell[] = [];

  // Leading days from previous month
  for (let i = firstDow - 1; i >= 0; i--) {
    const d = daysInPrev - i;
    const pm = month === 0 ? 11 : month - 1;
    const py = month === 0 ? year - 1 : year;
    grid.push({ key: `p${d}`, day: d, current: false, dateStr: fmt(py, pm + 1, d) });
  }

  // Current month days
  for (let d = 1; d <= daysInMonth; d++) {
    grid.push({ key: `c${d}`, day: d, current: true, dateStr: fmt(year, month + 1, d) });
  }

  // Trailing days from next month
  const trailing = 42 - grid.length;
  for (let d = 1; d <= trailing; d++) {
    const nm = month === 11 ? 0 : month + 1;
    const ny = month === 11 ? year + 1 : year;
    grid.push({ key: `n${d}`, day: d, current: false, dateStr: fmt(ny, nm + 1, d) });
  }

  return grid;
});

function dayClass(cell: Cell) {
  const selected = cell.dateStr === props.modelValue;
  const isToday = cell.dateStr === todayStr;
  return [
    !cell.current && 'opacity-25 cursor-default',
    selected && 'bg-tv-blue text-white',
    !selected && isToday && 'ring-1 ring-tv-blue text-tv-blue',
    !selected && cell.current && 'hover:bg-tv-tile',
  ];
}

function select(cell: Cell) {
  if (!cell.current) return;
  emit('update:modelValue', cell.dateStr);
  open.value = false;
}

function selectToday() {
  viewYear.value = today.getFullYear();
  viewMonth.value = today.getMonth();
  emit('update:modelValue', todayStr);
  open.value = false;
}

function shiftMonth(delta: number) {
  let m = viewMonth.value + delta;
  let y = viewYear.value;
  if (m < 0) { m = 11; y--; }
  if (m > 11) { m = 0; y++; }
  viewMonth.value = m;
  viewYear.value = y;
}

function fmt(y: number, m: number, d: number): string {
  return `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

// ---- click-outside to close ----
function onDocClick(e: MouseEvent) {
  if (open.value && rootRef.value && !rootRef.value.contains(e.target as Node)) {
    open.value = false;
  }
}

onMounted(() => document.addEventListener('click', onDocClick));
onBeforeUnmount(() => document.removeEventListener('click', onDocClick));
</script>

<style scoped>
.dp-nav-btn {
  @apply rounded p-1 text-tv-muted hover:bg-tv-tile hover:text-tv-text;
}
.dp-day {
  @apply rounded py-1 text-center text-xs text-tv-text transition-colors;
}
.dp-fade-enter-active,
.dp-fade-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.dp-fade-enter-from,
.dp-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
