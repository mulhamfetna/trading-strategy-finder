/**
 * TypeScript types matching the FastAPI backend Pydantic schemas.
 *
 * Two strategies (1-1-2 Scaling + Box variant) share execution and
 * trade shape. Every numeric strategy decision lives on `ScalingParams`
 * (Box extends it). Keep this file in lockstep with src/api/schemas.py.
 */

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

export interface Metrics {
  total_profit: number;
  profit_factor: number | null;
  win_rate: number;
  sharpe_ratio: number | null;
  max_drawdown: number;
  total_trades: number;
  avg_profit?: number;
  avg_loss?: number;
  expected_value?: number;
  gross_profit?: number;
  gross_loss?: number;
  wins?: number;
  losses?: number;
  [key: string]: unknown;
}

// ---- 1-1-2 Scaling strategy params ----

export interface ScalingParams {
  // §1 Entry distribution & sizing
  total_contracts: number;
  leg1_contracts: number;
  leg2_contracts: number;
  leg3_contracts: number;
  leg2_pullback_points: number;
  leg3_pullback_points: number;

  // §2 Big candle exception
  big_candle_threshold_points: number;
  big_candle_full_contracts: number;
  big_candle_reverses_dir: boolean;

  // §3 Entry trigger (15-second confirmation)
  entry_confirmation_timeframe_seconds: number;
  entry1_confirmation_candles: number;
  entry23_confirmation_candles: number;

  // §4 Stop loss
  sl_soft_points: number;
  sl_hard_points: number;
  soft_sl_confirmation_timeframe_minutes: number;
  hard_sl_confirmation_timeframe_seconds: number;

  // §5 Take profit
  tp_target_points: number;
  tp_watch_threshold_points: number;
  tp_confirmation_timeframe_minutes: number;

  // Re-entry
  reentry_enabled: boolean;
  reentry_cooldown_candles: number;

  // Instrument
  point_value: number;
}

// ---- Box strategy params (extends ScalingParams with box-rule decisions) ----

export type BigCandleResolution = 'big_candle_wins' | 'box_wins' | 'skip';

export interface BoxParams extends ScalingParams {
  box_tick_threshold: number;
  /** Conflict policy when a big bar AND a box edge-cross disagree — see MASTER_STRATEGY_GUIDE §5. */
  big_candle_resolution: BigCandleResolution;
}

// ---- Trades / progress / SSE payload ----

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
  exit_time?: string;
  box_signal?: BoxSignal;
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
  boxes?: BoxRect[];
}

export interface BoxSignal {
  signal: string | null;
  weekly_signal: string | null;
  monthly_signal: string | null;
  conflict?: boolean;
  weekly_level: string | null;
  monthly_level: string | null;
  weekly_upper: number | null;
  weekly_lower: number | null;
  monthly_upper: number | null;
  monthly_lower: number | null;
  weekly_box_start: string | null;
  monthly_box_start: string | null;
}

export interface BoxRect {
  start_time: number;
  end_time: number;
  upper: number;
  lower: number;
  level: string;
  timeframe: 'weekly' | 'monthly';
  fill_color: string;
  border_color: string;
}

// ---- Defaults ----

export const DEFAULT_SCALING_PARAMS: ScalingParams = {
  // §1
  total_contracts: 4,
  leg1_contracts: 1,
  leg2_contracts: 1,
  leg3_contracts: 2,
  leg2_pullback_points: 100,
  leg3_pullback_points: 150,
  // §2
  big_candle_threshold_points: 400,
  big_candle_full_contracts: 4,
  big_candle_reverses_dir: true,
  // §3
  entry_confirmation_timeframe_seconds: 15,
  entry1_confirmation_candles: 3,
  entry23_confirmation_candles: 1,
  // §4
  sl_soft_points: 200,
  sl_hard_points: 300,
  soft_sl_confirmation_timeframe_minutes: 2,
  hard_sl_confirmation_timeframe_seconds: 5,
  // §5
  tp_target_points: 150,
  tp_watch_threshold_points: 50,
  tp_confirmation_timeframe_minutes: 2,
  // Re-entry
  reentry_enabled: true,
  reentry_cooldown_candles: 1,
  // Instrument
  point_value: 2,
};

export const DEFAULT_BOX_PARAMS: BoxParams = {
  ...DEFAULT_SCALING_PARAMS,
  box_tick_threshold: 0.75,
  big_candle_resolution: 'big_candle_wins',
};

export const DEFAULT_BOX_DATA_PATH = 'NQ_full_data.csv';
