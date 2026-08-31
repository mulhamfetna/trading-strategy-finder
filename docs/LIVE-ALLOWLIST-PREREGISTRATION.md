# #195 — the live allowlist: pre-registration of the RULE

**Filed 2026-08-30 BEFORE deriving the list.** Part of #194 phase 1; consumed by the LIVE-PROTOCOL (#199).
Evidence base (already committed and published in `docs/WS-FWD-ROUND2-REPORT.md`): the round-2 forward books
`optimize/fwd/data_r2/fwd_book_*.csv` and slot diagnostics `fwd_slot_diag.json`.

## The rule (frozen)
A slot (instrument × timeframe) enters `optimize/live/live_allowlist.json` iff ALL of:
1. **fresh-window net P/L at $25/rt > 0** — positive on the only honest OOS window that exists;
2. **fresh-window entries ≥ 10** — the no-verdict floor from the WS-FWD prereg; a sliver cannot admit a slot;
3. **full-book gross per trade ≥ $50 = 2× friction** — the edge must be at least twice the toll (kills the
   $4–7/trade friction illusions even where a lucky fresh month was positive);
4. **full-book net at $25/rt > 0** — the slot's whole life, not only the fresh month, survives the toll;
5. **not gate-dark** — lifetime entry rate ≥ 5% AND last-60-days entry rate ≥ 1% (`fwd_slot_diag.json`);
   a slot whose vol gate admits nothing has no live existence regardless of its book.

## Dumb control (frozen)
20 seeded draws (seed 195) of random slot-sets of the SAME SIZE as the allowlist, drawn uniformly from the
54; compare fresh net@$25 totals. Declared honestly: criterion 1 selects on the same quantity, so beating
the control is a floor, not proof — the statement of record is the size of the margin.

## Blind spot (declared now)
The allowlist is selected ON the round-2 window; it is a **hypothesis the live run tests**, not a certified
edge. #197 (ES re-selection) and #198 (gate recalibration) may change members; any change is a dated
amendment to the JSON with the rule re-run, never a hand edit.
