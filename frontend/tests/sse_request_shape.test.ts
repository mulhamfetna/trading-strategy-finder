/**
 * Locks the JSON body that streamBoxBacktest POSTs to /api/backtest/box.
 *
 * Regression guard: an earlier version of sse.ts enumerated body fields
 * by hand and silently dropped `data_path_1min`, even though the caller
 * (backtest.ts) was passing it. The backend now requires the field —
 * dropping it produces a 422 in the browser with no test coverage.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { streamBoxBacktest } from '../src/services/sse';
import { DEFAULT_BOX_PARAMS } from '../src/types';

describe('streamBoxBacktest wire shape', () => {
  let fetchSpy: ReturnType<typeof vi.fn>;
  let capturedBody: Record<string, unknown> | null = null;

  beforeEach(() => {
    capturedBody = null;
    fetchSpy = vi.fn(async (_url: string, init: RequestInit) => {
      capturedBody = JSON.parse(init.body as string);
      // Minimal response so the generator exits cleanly.
      return {
        ok: true,
        body: new ReadableStream({ start(c) { c.close(); } }),
      } as unknown as Response;
    });
    vi.stubGlobal('fetch', fetchSpy);
  });

  it('POSTs all five required body fields, including data_path_1min', async () => {
    const gen = streamBoxBacktest({
      params: { ...DEFAULT_BOX_PARAMS },
      data_path: 'NQ_4h.csv',
      data_path_1min: 'NQ_1m.csv',
      box_data_path: 'NQ_full_data.csv',
    });
    // Drain so fetch is actually invoked.
    for await (const _ of gen) { /* noop */ }

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy.mock.calls[0][0]).toBe('/api/backtest/box');
    expect(capturedBody).not.toBeNull();
    const body = capturedBody as Record<string, unknown>;

    // The exact key set the backend's BoxBacktestRequest requires.
    expect(Object.keys(body).sort()).toEqual(
      ['box_data_path', 'data_path', 'data_path_1min', 'end', 'params', 'start'].sort(),
    );
    expect(body.data_path_1min).toBe('NQ_1m.csv');
    expect(body.data_path).toBe('NQ_4h.csv');
    expect(body.box_data_path).toBe('NQ_full_data.csv');
    // start/end omitted from input → explicit null (backend requires the key).
    expect(body.start).toBeNull();
    expect(body.end).toBeNull();
  });

  it('falls back to DEFAULT_DATA_PATH_1MIN when caller omits data_path_1min', async () => {
    const gen = streamBoxBacktest({ params: { ...DEFAULT_BOX_PARAMS } });
    for await (const _ of gen) { /* noop */ }
    const body = capturedBody as Record<string, unknown>;
    expect(body.data_path_1min).toBe('NQ_1m.csv');
  });
});
