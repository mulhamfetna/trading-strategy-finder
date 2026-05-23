import { defineStore } from 'pinia';
import { ref, computed, watch } from 'vue';
import { useBacktestStore } from './backtest';
import { useSettingsStore } from './settings';

const TICK_MS = 200;

export const useReplayStore = defineStore('replay', () => {
  const backtest = useBacktestStore();

  const isActive = ref(false);
  const currentIdx = ref(0);
  const isPlaying = ref(false);
  const speed = ref(1); // candles advanced per tick

  let timer: ReturnType<typeof setInterval> | null = null;

  const total = computed(() => backtest.candles.length);

  // BUG-020: when the backtest store clears candles (`run()` resets the
  // arrays before the new SSE stream starts) we must drop replay state
  // — otherwise the scrubber's `:max` becomes -1 and currentCandle goes
  // undefined while the timer keeps ticking.
  // flush:sync so the cleanup runs in the same tick as the candles
  // reassignment, before any setInterval callback can observe total=0.
  watch(
    total,
    (newTotal) => {
      if (newTotal === 0) {
        deactivate();
        currentIdx.value = 0;
      } else if (currentIdx.value >= newTotal) {
        currentIdx.value = newTotal - 1;
      }
    },
    { flush: 'sync' },
  );
  const percent = computed(() =>
    total.value > 1 ? (currentIdx.value / (total.value - 1)) * 100 : 0,
  );
  const currentCandle = computed(() => backtest.candles[currentIdx.value] ?? null);

  // FIX-16: realised PnL (trades that closed at or before the current
  // bar) + mark-to-market of any trade still open at this bar.
  // Without the MTM component the running PnL line snaps from 0 to the
  // final close value the moment the exit bar is reached, hiding all
  // drawdown / max-favourable-excursion behaviour during the hold.
  const realisedPnl = computed(() =>
    backtest.trades
      .filter((t) => t.exit_idx <= currentIdx.value)
      .reduce((s, t) => s + t.profit_dollars, 0),
  );

  // Index of the trade whose entry≤currentIdx<exit (open trade in replay).
  const activeTrade = computed(() =>
    backtest.trades.findIndex(
      (t) => t.entry_idx <= currentIdx.value && t.exit_idx > currentIdx.value,
    ),
  );

  const unrealisedPnl = computed(() => {
    const idx = activeTrade.value;
    if (idx < 0) return 0;
    const t = backtest.trades[idx];
    const candle = backtest.candles[currentIdx.value];
    if (!t || !candle) return 0;
    const settings = useSettingsStore();
    const pointValue = settings.params.point_value;
    const dirSign = t.direction === 'long' ? 1 : -1;
    return (candle.c - t.avg_entry_price) * t.contracts * pointValue * dirSign;
  });

  const runningPnl = computed(() => realisedPnl.value + unrealisedPnl.value);

  function activate() {
    _stopTimer();
    isActive.value = true;
    currentIdx.value = 0;
    isPlaying.value = false;
  }

  function deactivate() {
    _stopTimer();
    isActive.value = false;
    isPlaying.value = false;
  }

  function play() {
    if (currentIdx.value >= total.value - 1) currentIdx.value = 0;
    isPlaying.value = true;
    _stopTimer();
    timer = setInterval(() => {
      if (currentIdx.value >= total.value - 1) {
        pause();
        return;
      }
      currentIdx.value = Math.min(currentIdx.value + speed.value, total.value - 1);
    }, TICK_MS);
  }

  function pause() {
    _stopTimer();
    isPlaying.value = false;
  }

  function stepForward() {
    pause();
    currentIdx.value = Math.min(currentIdx.value + 1, total.value - 1);
  }

  function stepBack() {
    pause();
    currentIdx.value = Math.max(currentIdx.value - 1, 0);
  }

  function seekTo(idx: number) {
    currentIdx.value = Math.max(0, Math.min(Math.round(idx), total.value - 1));
  }

  function _stopTimer() {
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
  }

  function jumpToTrade(entryIdx: number) {
    if (!isActive.value) {
      isActive.value = true;
      isPlaying.value = false;
    }
    seekTo(entryIdx);
  }

  return {
    isActive,
    currentIdx,
    isPlaying,
    speed,
    total,
    percent,
    currentCandle,
    runningPnl,
    realisedPnl,
    unrealisedPnl,
    activeTrade,
    activate,
    deactivate,
    play,
    pause,
    stepForward,
    stepBack,
    seekTo,
    jumpToTrade,
  };
});
