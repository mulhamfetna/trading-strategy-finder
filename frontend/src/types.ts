/**
 * TypeScript types matching the FastAPI backend Pydantic schemas.
 * Keep these in lock-step with src/api/schemas.py.
 */

export interface StrategyConfig {
  rsi_period: number;
  ema_fast: number;
  ema_slow: number;
  vol_threshold: number;
  stop_loss: number;
  take_profit: number;
  tp_sl_resolution: 'conservative' | 'optimistic' | 'direction-proxy';
  tp_sl_resolution_options: Array<'conservative' | 'optimistic' | 'direction-proxy'>;
  timeframe_options: string[];
  dataset_options: Array<'train' | 'test'>;
}

export interface Candle {
  t: string;
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
}

export interface CandlesResponse {
  candles: Candle[];
  count: number;
  range: { start: string; end: string };
}

export interface BacktestRequest {
  start: string;
  end: string;
  dataset: 'train' | 'test';
  timeframe: '15min';
  tp_sl_resolution: 'conservative' | 'optimistic' | 'direction-proxy';
  stop_loss?: number;
  take_profit?: number;
  initial_capital?: number;
  fee_per_trade?: number;
  data_path?: string;
}

export interface Trade {
  entry_idx: number;
  exit_idx: number;
  entry_price: number;
  exit_price: number;
  direction: string;
  profit_pct: number;
  profit_dollars: number;
  capital_after: number;
  exit_reason: string;
  fees_paid: number;
}

export interface Metrics {
  total_profit: number;
  total_fees?: number;
  profit_factor: number;
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_trades: number;
  avg_profit?: number;
  avg_loss?: number;
  expected_value?: number;
  max_consecutive_losses?: number;
  final_capital?: number;
  gross_profit?: number;
  net_profit?: number;
  wins?: number;
  losses?: number;
  gross_loss?: number;
  [key: string]: unknown;
}

export interface BacktestResponse {
  metrics: Metrics;
  trades: Trade[];
  candles: Candle[];
}

// ---- scaling strategy (phase C) ----

export interface ScalingParams {
  total_contracts: number;
  leg1_contracts: number;
  leg2_contracts: number;
  leg3_contracts: number;
  leg2_pullback_points: number;
  leg3_pullback_points: number;
  big_candle_threshold_points: number;
  big_candle_full_contracts: number;
  big_candle_reverses_dir: boolean;
  tp_target_points: number;
  tp_watch_threshold_points: number;
  sl_soft_points: number;
  sl_hard_points: number;
  reentry_enabled: boolean;
  reentry_cooldown_candles: number;
}

export interface ScalingTrade {
  entry_idx: number;
  exit_idx: number;
  direction: string;
  avg_entry_price: number;
  exit_price: number;
  contracts: number;
  profit_points: number;
  profit_dollars: number;
  exit_reason: string;
  legs: Array<{ contracts: number; price: number; candle_idx: number }>;
}

export interface ScalingProgress {
  current_idx: number;
  total: number;
  percent: number;
  phase: string;
  trades_so_far: number;
  pnl_so_far: number;
  win_rate_so_far: number;
  current_position: 'long' | 'short' | 'flat';
  current_legs_filled: number;
}

export interface ScalingCompletePayload {
  metrics: Metrics;
  trades: ScalingTrade[];
  candles: Candle[];
  elapsed_ms: number;
}

export const DEFAULT_SCALING_PARAMS: ScalingParams = {
  total_contracts: 4,
  leg1_contracts: 1,
  leg2_contracts: 1,
  leg3_contracts: 2,
  leg2_pullback_points: 100,
  leg3_pullback_points: 150,
  big_candle_threshold_points: 400,
  big_candle_full_contracts: 4,
  big_candle_reverses_dir: true,
  tp_target_points: 150,
  tp_watch_threshold_points: 50,
  sl_soft_points: 200,
  sl_hard_points: 300,
  reentry_enabled: true,
  reentry_cooldown_candles: 1,
};
