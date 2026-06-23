# Verbose causal logs + output-calculation audit — design

**Date:** 2026-06-23 · **Status:** approved (brainstorm) → ready for implementation plan
**Scope:** this spec covers (A) making the per-candle causal log fully verbose — every field
populated, every field shown on the dashboard, every field exported to CSV — and (B) an
output-calculation audit that makes **every displayed box derive from the log** (single source of
truth), correcting any miscalculated box. The `max-1min-open-trade-streak-cap` time-based exit is a
**separate later spec** (this work is its prerequisite).

## Why

A log audit found the per-candle causal log carries far more information than the dashboard or the
CSV surface. The `LogRow` schema has **23 fields**; today:
- the dashboard per-candle log table shows **7** (`layer, time, decision, reason, box_cause,
  direction, pnl`);
- `_serialize_log_row` sends **17** to the frontend (omits `entry_price, exit_price` + the 4 deferred
  fields);
- the CSV exports **~20**;
- **4 fields are never populated** by `run_causal` (`text, indicators, veto_flip, would_be_pnl`) —
  they exist in the schema as a frozen superset but were deferred.

Separately, not every displayed box is log-derived. The unified 3-tab dashboard (`/api/causal_backtest`
→ `build_view_payload`) is already log-first via `aggregate.boxes_for_layer` / `combined_boxes`. But the
legacy `/api/combined_backtest` (`build_combined_payload`) computes its summaries from the **engine
objects** (`_l1_full_summary(l1)`, `metrics.score(l2)`, `metrics.combined(l1,l2)` reading
`l1.ledger`/`l2.ledger` directly) — a second path that can diverge from the log.

## Decisions (locked during brainstorm)

1. **Log = single source of truth.** Every displayed box, on every endpoint, derives from the
   per-candle log. (Approach 1.)
2. **Corrected numbers win + re-lock.** If a box is genuinely miscalculated, the corrected log-derived
   value replaces the old one even if it differs from today's locked anchors/golden — we update the
   parity anchors + golden baseline to the corrected numbers. Truth over the old lock.
3. **Dashboard log = wide, all-columns** (every field a column; `indicators` as vote chips; horizontal
   scroll).
4. **Populate all 4 deferred fields** (`text, indicators, veto_flip, would_be_pnl`).
5. **Lost-info diff report** vs the last tag `approved-4h-indicators-backtester` (2026-06-09).
6. **Time-cap exit = separate later spec.**

## Data model — `LogRow` (the 23 fields)

Source: `optimize/l2/logbook.py`. One row **per decision bar** (~2,119 for 4h — so per-bar detail,
incl. `indicators`, is cheap to carry).

| field | populated today | meaning |
|---|---|---|
| `i` | ✅ | decision-bar index |
| `time` | ✅ | epoch (s) |
| `layer` | ✅ | L1 \| L2 \| None |
| `decision` | ✅ | entry \| nonentry |
| `reason` | ✅ | entered \| box_silence \| vol_gated \| vetoed \| confirm<K \| open_trade \| force_closed \| breaker_locked/unlocked \| warmup/warmed |
| `box_cause` | ✅ | underlying L1 box/gate/veto/confirm cause (kept during open/force-close) |
| `event_type` | ✅ | ENTRY \| WIN \| LOSS \| LOCK \| UNLOCK \| SKIP \| NOENTRY \| WARMUP \| WARMED |
| `direction` | ✅ | long \| short (entered direction) |
| `box_dir` | ✅ | the box signal direction from the prior bar |
| `entry_price` | ✅ (row) — ❌ serialized | fill entry price |
| `exit_time` | ✅ | epoch (s) of exit |
| `exit_price` | ✅ (row) — ❌ serialized | fill exit price |
| `exit_reason` | ✅ | why the trade exited |
| `pnl` | ✅ | realized P/L (on entry rows) |
| `equity` | ✅ | per-layer cumulative equity |
| `dd` | ✅ | per-layer underwater drawdown |
| `in_position` | ✅ | layer holding on this bar |
| `position_owner` | ✅ | L1 \| L2 \| None (who owns the position) |
| `l2_reason` | ✅ | L2's own decision on bars it evaluated |
| `text` | ❌ **deferred** | human-readable line |
| `indicators` | ❌ **deferred** | per-bar vote detail `[{key, vote, active}]` |
| `veto_flip` | ❌ **deferred** | entry reversed vs box signal |
| `would_be_pnl` | ❌ **deferred** | would-be P/L for breaker-SKIP candidate rows |

## Section 1 — Log enrichment (backend)

In `logbook.run_causal`, populate the 4 deferred fields per row:
- **`indicators`** — the per-decision-bar vote list `[{key, vote, active}]`, sourced from the votes
  **already computed for the entry gate** (`runner.compute_votes`); thread them into the row. Near-zero
  extra compute (votes already exist). Rows where no votes were computed carry `[]`.
- **`would_be_pnl`** — on breaker-SKIP candidate rows (`event_type=SKIP`), the candidate trade's
  would-be realized P/L (the engine already evaluates the candidate to know it was skipped).
- **`veto_flip`** — `True` when the entered `direction` is the reverse of `box_dir` (flip/veto-flip).
- **`text`** — the human-readable line (same phrasing conventions as `strategy.py` events).

End state: all 23 fields carry real data. Existing populated fields are untouched (no numeric change).

## Section 2 — Serialization + CSV (all 23 fields)

- `_serialize_log_row` (`optimize/l2/payload.py`): add `entry_price, exit_price, text, veto_flip,
  would_be_pnl, indicators` → emit the full 23-field row. (Backwards-compatible: only adds keys.)
- CSV export (`aggregate._CSV_COLS` + `log_to_csv`): extend to all 23 columns — add `would_be_pnl,
  veto_flip, text`, and `indicators` (JSON-encoded cell, e.g. `[{"key":"macd","vote":"long","active":true}]`).
  Keep the provenance `#`-comment header (view, params, tf, timestamp). The CSV becomes a complete dump
  of the log — nothing in the row is omitted.

## Section 3 — Dashboard (wide, all-columns)

`frontend/dashboard.html`, `renderView`:
- Per-candle log table: render **every** field as a column in a fixed order; the `indicators` field
  renders as vote chips (reuse the existing `.ind-chips`/`.chip` styling already used in the event log).
  Wrap the table for **horizontal scroll** so the wide layout stays usable. Empty/None cells render
  blank. `would_be_pnl` shown on SKIP rows.
- Trade ledger: add `entry_price` / `exit_price` columns (now serialized).
- Both views (L1 / L2 / Combined) and the ledger-CSV / log-CSV download buttons reflect the same full
  column set, so screen and CSV agree.

## Section 4 — Output-calculation audit (log = single source of truth)

1. **Endpoint reachability check (first implementation step).** Determine whether
   `/api/combined_backtest` (`build_combined_payload`) + `frontend/combined.html` are still reached by
   any current frontend. The live unified dashboard uses `/api/causal_backtest`.
   - If **dead** → retire `build_combined_payload` + the route + `frontend/combined.html`.
   - If **live** → convert `build_combined_payload` to derive its summaries from the log via
     `aggregate.boxes_for_layer` / `combined_boxes` (the same path the unified views use), demoting
     `_l1_full_summary` / `metrics.score` / `metrics.combined` to **test-oracle-only** (kept for parity
     tests, not for display).
2. **Per-box correctness pass.** For every displayed box — `pnl, pnl_2025/2026, max_dd, win, pf,
   payoff, exposure, n_taken, n_candidates, n_locks, the no-entry streak/total boxes` — confirm it
   recomputes correctly from the log; fix any whose derivation is wrong (e.g. an engine-object shortcut
   that can disagree with the log). The combined `max_dd` must remain the merged-equity underwater
   (not a sum).
3. **Re-lock.** Any box whose corrected value differs from today's locked number → update the parity
   anchors (`test_parity_anchor`, `test_aggregate`) **and** the golden baseline (`perf/golden/*.json`
   via `perf/capture_golden.py`) to the corrected values, and note the before→after in the report.
4. **Lost-info diff report** (`docs/`): the log/CSV/dashboard surface at tag
   `approved-4h-indicators-backtester` vs now — confirming the expansion restores anything dropped and
   lists everything added.

## Testing & acceptance

- `perf/check_golden.py` — green (re-locked if any number legitimately changed; the diff documented).
- `optimize/test_fast_parity.py`, `optimize/l2/test_parity_anchor.py`, `optimize/l2/test_aggregate.py`
  — green (anchors updated if corrected).
- New/updated: a CSV test asserting **all 23 columns present** + the 4 newly-populated fields are
  non-empty on representative rows (an entry row has `indicators`; a SKIP row has `would_be_pnl`; a
  flipped entry has `veto_flip=true`); update the existing `test_l2_server` CSV-shape assertion.
- A serialization test asserting `_serialize_log_row` emits all 23 keys.
- Manual/Playwright: load the dashboard, Run, confirm the wide log table renders every column + vote
  chips and the ledger shows entry/exit price.

## Out of scope

- The `max-1min-open-trade-streak-cap` time-based exit (separate spec; this is its prerequisite).
- Any change to entry/exit **logic** or indicator math — Section 1 only *records* what the engine
  already decides; the audit only *re-sources* boxes to the log (numbers change only where the old box
  was provably miscalculated).
- The shareable bundles: update in a follow-up once the main repo lands (note it; don't block).

## Risks

- **Numbers shifting on re-lock.** Mitigation: every changed anchor is documented before→after in the
  report with the log-derived justification; golden re-captured deliberately, not silently.
- **CSV `indicators` JSON cell** could complicate naive CSV parsers. Mitigation: it's the last column,
  JSON-quoted; the provenance header already marks the file as a rich export.
- **Wide table UX.** Mitigation: horizontal scroll + sticky header; the CSV remains the full-fidelity
  artifact for analysis.
