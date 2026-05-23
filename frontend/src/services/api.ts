/**
 * Typed REST client. Uses relative URLs - the Vite dev server proxies
 * /api/* to localhost:8000 (see vite.config.ts), and a production
 * build serves the frontend from the same origin as the backend.
 */

import axios from 'axios';
import type { CandlesResponse } from '../types';

const client = axios.create({
  baseURL: '/api',
  timeout: 30_000,
});

export async function fetchCandles(
  start: string,
  end: string,
  dataset: 'train' | 'test',
  dataPath: string,
): Promise<CandlesResponse> {
  const resp = await client.get<CandlesResponse>('/candles', {
    params: { start, end, dataset, data_path: dataPath },
  });
  return resp.data;
}
