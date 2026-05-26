/**
 * Synchronous JSON client for `POST /api/backtest/simple`.
 *
 * Unlike the box endpoint (SSE), the simple engine runs in ~1-2s and
 * returns a single JSON payload. Response shape is intentionally
 * shaped to match the box engine's `complete` event so the same
 * Pinia store + components consume both.
 */

import {
  DEFAULT_BOX_DATA_PATH,
  DEFAULT_DATA_PATH,
  DEFAULT_DATA_PATH_1MIN,
} from '../types';
import type { Candle, Metrics, ScalingTrade } from '../types';

export interface SimpleRequest {
  sl_soft_points: number;
  sl_hard_points: number;
  tp_soft_points: number;
  tp_hard_points: number;
  direction_scope: 'both' | 'long_only' | 'short_only';
  flip_entry_direction: boolean;
  data_path?: string;
  data_path_1min?: string;
  box_data_path?: string;
  start?: string | null;
  end?: string | null;
}

export interface SimpleResponse {
  summary: {
    n_trades: number;
    n_take_profit: number;
    n_stop_loss: number;
    n_stop_loss_hard: number;
    n_stop_loss_soft: number;
    n_open_at_eof: number;
    total_pnl_dollars: number;
    total_pnl_points: number;
    win_rate: number | null;
  };
  metrics: Metrics;
  trades: ScalingTrade[];
  candles: Candle[];
  elapsed_ms: number;
}

export async function runSimpleBacktest(req: SimpleRequest): Promise<SimpleResponse> {
  const body: SimpleRequest = {
    sl_soft_points:       req.sl_soft_points,
    sl_hard_points:       req.sl_hard_points,
    tp_soft_points:       req.tp_soft_points,
    tp_hard_points:       req.tp_hard_points,
    direction_scope:      req.direction_scope,
    flip_entry_direction: req.flip_entry_direction,
    data_path:            req.data_path       ?? DEFAULT_DATA_PATH,
    data_path_1min:       req.data_path_1min  ?? DEFAULT_DATA_PATH_1MIN,
    box_data_path:        req.box_data_path   ?? DEFAULT_BOX_DATA_PATH,
    start:                req.start ?? null,
    end:                  req.end   ?? null,
  };
  const r = await fetch('/api/backtest/simple', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let detail: unknown = null;
    try { detail = await r.json(); } catch { /* keep null */ }
    const msg = typeof detail === 'object' && detail !== null && 'detail' in detail
      ? JSON.stringify((detail as { detail: unknown }).detail)
      : `${r.status} ${r.statusText}`;
    throw new Error(`Simple backtest failed: ${msg}`);
  }
  return r.json() as Promise<SimpleResponse>;
}
