# Plan — turning the structure detectors into ENTRY rules (Q6, plan only — no build yet)

The detectors from task B (`swing_labels`, `ifvg`, `breaker_blocks`, `cisd`, plus existing `fvg`,
`order_blocks`, `golf_candle`, `structure_trend`) currently only **label/flag**. This plan describes how they'd
become real **entry decisions** — *where* to enter on a zone and *what confirms* it — so it can be reviewed and
sized before any implementation. Nothing here is built.

## A. Entry placement on an order-block / breaker zone (your "immediate / middle / top / wait")
A live OB or breaker is a price *zone* `[lo, hi]`. When price trades into it, four placement modes:
1. **immediate** — enter at first touch of the zone edge (current behaviour of the reaction signal).
2. **middle** — enter at the zone midpoint `(lo+hi)/2` (limit order; fills only if price reaches mid).
3. **far edge ("top")** — enter at the deep edge (`hi` for a short zone / `lo` for a long zone) — best price,
   lowest fill rate.
4. **wait-for-confirmation** — do not enter on touch; arm, and enter only when a confirmation fires (below).

These map cleanly onto the existing **entry-resolver** mechanism (`runner.build_layer` retrace/wait already
supports "enter at a level" and "wait N bars") — so placement = a resolver parameter, not new engine surgery.

## B. Confirmation (your "FVG or CISD", and the breaker's "all three")
Arm on the zone; require one (or a configurable AND/OR) of:
- **FVG** in the trade direction within K bars of the touch (`fvg` / `fvg_active_direction`);
- **CISD** in the trade direction (`cisd` — standard close-through-prior-leg-open);
- **golf/engulfing** (`golf_candle`) as the displacement confirmation.
Your "all three for the breaker" = require golf **and** FVG **and** CISD agree before taking a breaker — the
strictest setting. This is a boolean policy over the three per-bar signals (cheap to evaluate).

## C. IFVG / breaker as standalone signals
Beyond confirming OB entries, IFVG and breaker can each be a **vote** in the existing confirm/veto layer
(like the current 8 indicators) — i.e. wired as `indicators/` vote sources. That makes them optimizer-searchable
(see `NEXT_OPTIMIZER_NOTES.md`).

## D. Retrace tuning (your "how much price / how much time / both")
Already in the engine (global retrace amount + wait bars, WS-I rev#3/#4). The follow-up is to **sweep** these
per entry-type (price-distance vs time-bars vs both) and pick by OOS return/DD — a study, not new code.

## Proposed build order (when you greenlight)
1. **Wire IFVG + breaker + CISD as vote sources** in `indicators/` (parity-gated, golden-safe) → they become
   optimizer inputs.
2. **Entry-placement policy** (immediate/mid/far/wait) as a resolver param + confirmation policy (A∧/∨B).
3. **A focused study**: does any (zone × placement × confirmation) combo OOS-beat the champion on return/DD?
4. Only then, a `wsh5` joint search including these knobs + the split SL/TP (Q3).

## Guardrails
Causal detectors only · reuse the existing resolver/vote machinery (no hot-path surgery) · golden + fast-parity
after any engine touch · judge on return/DD OOS · fixed champion stays deployed until something OOS-dominates.
**Status: PLAN — awaiting your go-ahead before any of A–D is built.**
