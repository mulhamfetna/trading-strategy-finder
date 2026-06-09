---
name: golf-engulfing
description: WS-I review #2 — the golf indicator is now an N-candle ENGULFING reversal (opposite colour to all N prior + wick range-engulf + body ≥ 70% of prior span). Replaces the old "body bigger than prior N" test.
type: spec
status: implemented — awaiting your validation
created: 2026-06-08
workstream: WS-I
---

# Golf candle → N-candle engulfing (review #2)

The old "golf = body larger than the max body of the prior N candles" is **removed**. Golf is now a
multi-candle **engulfing reversal**, with `N` = the dashboard `golf_n`.

## Definition (per bar `t`, requires `t ≥ N`) → returns +1 bullish / −1 bearish / 0 none
Let the prior window be bars `t-N … t-1`, `prior_high = max(high)`, `prior_low = min(low)`,
`prior_span = prior_high − prior_low`, and `body = |close[t] − open[t]|`.

1. **Opposite colour to ALL N prior candles**
   - bullish: `close[t] > open[t]` (green) **and every** prior bar is red (`close < open`);
   - bearish: `close[t] < open[t]` (red) **and every** prior bar is green (`close > open`).
2. **Range engulf (wicks):** `high[t] ≥ prior_high` **and** `low[t] ≤ prior_low`
   (the current candle's high-to-low covers the prior window's high-to-low).
3. **Body filter:** `body ≥ 0.70 × prior_span` (the engulfing candle's real body is ≥ 70 % of the
   span it engulfs — rejects long-wick/doji engulfers).

A doji (`close == open`) is neither red nor green, so it fails the colour test (no golf).

## Worked example (N = 2, the one you reviewed)
prior t-2 high105/low100, prior t-1 high104/low99 **red** → prior_high 105, prior_low 99, span 6.
Current green open99.5/close105.5, high106/low99 → engulf (106≥105, 99≤99) ✓, body 6 ≥ 0.7×6 = 4.2 ✓,
prior all red + current green → **+1 bullish**. ✓

## Where it's used / blast radius
Golf is a **generated structure only** (Phase-1 generation report) — it is **not** a confirm/veto
vote and touches no parity path. The generation report now carries `n_golf` (total), `n_golf_bull`,
`n_golf_bear`. On real NQ 4h (N=3) it fires **8** times (2 bull / 6 bear) — appropriately rare given
the strict all-N-opposite + 70 %-body conditions.

## Validation
- `smc.golf_candle(open, high, low, close, golf_n)` rewritten; `generate.py` updated (new signature +
  directional counts); `tests/test_smc.py` updated (bullish engulf; rejects on small body / mixed
  prior colour). **78 tests pass.** Parity unchanged (golf is generation-only): PARITY OK ✓.

**Please validate this spec.** If the 70 % filter should compare against something other than the
prior combined span (e.g. current range), or the colour rule should be vs only `t-1`, say so and I'll
adjust.
