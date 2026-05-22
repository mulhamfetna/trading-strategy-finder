import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useBacktestStore } from './backtest';

const TICK_MS = 200;

export const useReplayStore = defineStore('replay', () => {
  const backtest = useBacktestStore();

  const isActive = ref(false);
  const currentIdx = ref(0);
  const isPlaying = ref(false);
  const speed = ref(1); // candles advanced per tick

  let timer: ReturnType<typeof setInterval> | null = null;

  const total = computed(() => backtest.candles.length);
  const percent = computed(() =>
    total.value > 1 ? (currentIdx.value / (total.value - 1)) * 100 : 0,
  );
  const currentCandle = computed(() => backtest.candles[currentIdx.value] ?? null);

  // Sum of P&L for trades that have fully completed (exit candle is in view).
  const runningPnl = computed(() =>
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
