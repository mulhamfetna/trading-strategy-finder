/**
 * Server-Sent Events client for /api/backtest/box — the master strategy.
 *
 * Browser EventSource doesn't support POST, so we use fetch() + a
 * ReadableStream reader and parse SSE frames manually.
 */

import {
  DEFAULT_BOX_DATA_PATH,
  DEFAULT_DATA_PATH,
  DEFAULT_DATA_PATH_1MIN,
} from '../types';
import type {
  BoxParams,
  ScalingCompletePayload,
  ScalingProgress,
} from '../types';

export type ScalingStreamEvent =
  | { type: 'progress'; data: ScalingProgress }
  | { type: 'complete'; data: ScalingCompletePayload }
  | { type: 'warning'; data: { stage: string; message: string } }
  | { type: 'error'; data: { detail: string } };

interface BoxRunOptions {
  params: BoxParams;
  data_path?: string;
  data_path_1min?: string;
  box_data_path?: string;
  start?: string;
  end?: string;
}

export function streamBoxBacktest(
  opts: BoxRunOptions,
): AsyncGenerator<ScalingStreamEvent, void, unknown> {
  return _streamSse('/api/backtest/box', {
    params: opts.params,
    data_path: opts.data_path ?? DEFAULT_DATA_PATH,
    data_path_1min: opts.data_path_1min ?? DEFAULT_DATA_PATH_1MIN,
    box_data_path: opts.box_data_path ?? DEFAULT_BOX_DATA_PATH,
    start: opts.start ?? null,
    end: opts.end ?? null,
  });
}

async function* _streamSse(
  endpoint: string,
  body: unknown,
): AsyncGenerator<ScalingStreamEvent, void, unknown> {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    throw new Error(`SSE request failed: ${response.status} ${response.statusText}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const rawFrame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const parsed = parseSseFrame(rawFrame);
      if (parsed) yield parsed;
      boundary = buffer.indexOf('\n\n');
    }
  }
  const tail = parseSseFrame(buffer);
  if (tail) yield tail;
}

// Exported so tests verify the SAME parser the production stream uses
// (BUG-025 — the test file used to inline a copy).
export function parseSseFrame(raw: string): ScalingStreamEvent | null {
  if (!raw.trim()) return null;
  let eventType: string | null = null;
  const dataLines: string[] = [];
  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) {
      eventType = line.slice('event:'.length).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice('data:'.length).trim());
    }
  }
  if (!eventType || dataLines.length === 0) return null;
  try {
    const data = JSON.parse(dataLines.join('\n'));
    if (eventType === 'progress') return { type: 'progress', data };
    if (eventType === 'complete') return { type: 'complete', data };
    if (eventType === 'warning') return { type: 'warning', data };
    if (eventType === 'error') return { type: 'error', data };
  } catch {
    return null;
  }
  return null;
}
