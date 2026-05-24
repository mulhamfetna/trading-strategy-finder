---
name: toUTCTimestamp
file: frontend/src/services/chart_helpers.ts
signature: toUTCTimestamp(t: string) → Time
responsibility: Convert the backend's `"YYYY-MM-DD HH:MM:SS"` or `"YYYY-MM-DDTHH:MM:SS"` candle timestamp to a Lightweight Charts UTCTimestamp (seconds since epoch). Without this the chart silently renders nothing on an intraday dataset.
related: [[toLwcData]], [[candles_from_df]], [[chartpane_applyData]]
---

# `toUTCTimestamp`

## Why this exists

Lightweight Charts has two valid time formats:
- Daily bars: `"YYYY-MM-DD"` strings.
- Intraday bars: numeric `UTCTimestamp` (seconds since 1970-01-01 UTC).

Passing an intraday `"YYYY-MM-DD HH:MM:SS"` string is silently rejected — LWC renders an empty pane with no console error. Every chart this codebase draws is intraday (4h NQ), so every timestamp must be converted.

## Implementation

```ts
export function toUTCTimestamp(t: string): Time {
  const iso = t.replace(' ', 'T');
  const ms = new Date(iso + (iso.endsWith('Z') ? '' : 'Z')).getTime();
  if (isNaN(ms)) throw new Error(`Invalid candle timestamp: ${t}`);
  return (ms / 1000) as unknown as Time;
}
```

Three behaviours that matter:
1. **Space → `T`**: Backend emits either `"YYYY-MM-DD HH:MM:SS"` (legacy) or `"YYYY-MM-DDTHH:MM:SS"` (current). The `.replace(' ', 'T')` normalises both.
2. **Appended `Z`**: Without an explicit UTC suffix, `new Date(...)` interprets the string in the browser's LOCAL timezone — so a user in NY would see bars shifted by 5 hours from a user in London. Appending `Z` forces UTC interpretation. The `.endsWith('Z')` guard avoids `ZZ` if the backend ever starts emitting them.
3. **Throws on invalid input**: A bad timestamp is a load-bearing error — silently substituting NaN would corrupt every bar. The throw bubbles up to ChartPane and surfaces as a chart-render failure rather than a wrong-looking chart.

## Caller

Called once per candle inside [[toLwcData]] and once per crosshair-move event inside [[chartpane_initChart]]. Cheap (single Date construction); no caching layer is justified.

## Backend invariant this depends on

[[candles_from_df]] guarantees the output format is `"YYYY-MM-DDTHH:MM:SS"` (no timezone). If a future change makes the backend emit timezone-aware strings, the `.endsWith('Z')` guard will need to widen.
