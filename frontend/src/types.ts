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
  [key: string]: unknown;
}

export interface BacktestResponse {
  metrics: Metrics;
  trades: Trade[];
  candles: Candle[];
}
