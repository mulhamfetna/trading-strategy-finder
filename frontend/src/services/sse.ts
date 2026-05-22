/**
 * Server-Sent Events client for /api/backtest/scaling.
 *
 * Browser EventSource doesn't support POST, so we use fetch() + a
 * ReadableStream reader and parse SSE frames manually. The async
 * generator yields one event per frame.
 */

import type { ScalingCompletePayload, ScalingParams, ScalingProgress } from '../types';

export type ScalingStreamEvent =
  | { type: 'progress'; data: ScalingProgress }
  | { type: 'complete'; data: ScalingCompletePayload }
  | { type: 'error'; data: { detail: string } };

interface RunOptions {
  params: ScalingParams;
  data_path?: string;
  start?: string;
  end?: string;
}

/**
 * Stream a scaling backtest from the backend, yielding parsed SSE events.
 *
 * Usage:
 *   for await (const ev of streamScalingBacktest({ params })) {
 *     if (ev.type === 'progress') ...
 *     if (ev.type === 'complete') ...
 *   }
 */
export async function* streamScalingBacktest(
  opts: RunOptions,
): AsyncGenerator<ScalingStreamEvent, void, unknown> {
  const response = await fetch('/api/backtest/scaling', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      params: opts.params,
      data_path: opts.data_path ?? 'NQ_4h.csv',
      start: opts.start ?? null,
      end: opts.end ?? null,
    }),
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

    // SSE frames are separated by a blank line ("\n\n").
    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const rawFrame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const parsed = parseSseFrame(rawFrame);
      if (parsed) yield parsed;
      boundary = buffer.indexOf('\n\n');
    }
  }
  // Flush any trailing frame
  const tail = parseSseFrame(buffer);
  if (tail) yield tail;
}

function parseSseFrame(raw: string): ScalingStreamEvent | null {
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
    if (eventType === 'error') return { type: 'error', data };
  } catch {
    return null;
  }
  return null;
}
