# Candle Taxonomy Boxes — Design Spec

**Date:** 2026-06-24 · **Status:** approved (brainstorm) · **Author:** pairing session

## Goal

Add a **complete classification of every candle** into a decision tree, with a **counter box (stat
card) on the dashboard for every node** — for L1, L2, and Combined. Each box shows a **count**, and
trading nodes also show a **summed dollar P/L**. Purely additive instrumentation derived from the
existing causal log; **no engine change, no behavioural change, no existing number moves.**

## Background — what already exists (source of truth)

The per-candle causal log (`logbook.run_causal` → one `LogRow` per decision bar) already carries every
field needed. The internal label strings below come verbatim from the code — nothing is invented.

- **L1 per-bar cause** — `attribute(sig, vol_gate, veto, confirm)` in `optimize/counterfactual_pause.py:32`
  emits, for `idx` in `1..n-1` (bar 0 → `None`):
  `box_silence` | `vol_gated` | `vetoed` | `confirm<K` | `would_enter` | (else the bar `entered`).
  `would_enter` = passed every gate but the breaker/cooldown skipped it (**no trade**); `entered` =
  an actual trade. The realized entry rows live in the L1 ledger; `would_be_pnl` (counterfactual $ for
  skipped/`would_enter` bars) is already on the log row.
- **L2 per-bar decision** — `_l2_reason(...)` in `optimize/l2/logbook.py:105` emits, only on bars L2
  evaluated: `entered` | `vol_gated` | `vetoed` | `confirm<K` | `passed` (gate passed, no open — e.g.
  already in an L2 position / breaker). L2 evaluates **only** L1's forwarded drops
  (`cause ∈ {vetoed, vol_gated}`, built in `l1_runner.py`) **while L1 is flat** (`optimize/l2/engine.py`).
  `confirm<K` and `would_enter` are **not** forwarded to L2.
- **Exit reasons** — `REASON_NAME` in `optimize/fast_engine.py:28` / `ExitReason` in `engine.py:54`:
  `TAKE_PROFIT_HARD` | `STOP_LOSS_SOFT` | `STOP_LOSS_HARD` | `TIME_CAP` (+ schema-only `TAKE_PROFIT_SOFT`,
  `OPEN`). L2-only `L1-entry` force-close in `optimize/l2/engine.py:force_close_on_l1_entry`.
- **Existing boxes** — `aggregate.boxes_for_layer` / `combined_boxes` (`optimize/l2/aggregate.py`)
  compute `pnl, max_dd, win, pf, payoff, n_taken`, streak/total boxes, `n_candidates/n_locks/exposure`,
  warmup. Rendered via `grp()` + `DB.card()` in `frontend/dashboard.html`. **These stay untouched.**

## Decisions (locked during brainstorm)

1. **L1 `passed` branch is split into TWO boxes:** `passed_skipped` (`would_enter`, no trade) and
   `entered` (actual trade). Exit-classification boxes hang off `entered` only.
2. **Every leaf carries count + dollars**, with this rule:
   - Non-trading leaves (`no_box_signal`, `gate_rejected`, `indicator_veto`, `indicator_no_confirm`,
     L2 `passed_no_open`, `forwarded_but_l1_in_position`) → **count only** (no `pnl` key).
   - `passed_skipped` (`would_enter`) → count + **counterfactual** $ (sum of `would_be_pnl`).
   - `entered` and all exit leaves → count + **realized** $ (sum of `pnl`).
3. **Win/loss sub-split applies ONLY to `time_cap_exit`** (TP is always a win, SL-hard always a loss;
   TIME_CAP closes at market so it can land either way). `win = pnl > 0`, `loss = pnl <= 0`.
4. **L2's smaller universe is explicit:** the L2 block is titled "of L1's forwarded drops"; a
   `forwarded_but_l1_in_position` box accounts for forwarded drops L2 never evaluated (L1 in-position).
5. **Combined** carries both layers' full sub-trees plus an additive `combined_exits` roll-up
   (L1 leaf + L2 leaf; trade sets are disjoint so counts and dollars sum exactly).
6. **Architecture:** computed server-side in a dedicated, separately-tested unit
   (`optimize/l2/taxonomy.py`), serialized into the existing view payload, rendered as a new collapsible
   card group. NOT computed in the browser (untestable; combined dollar math is subtle).

## Data model — the trees

### L1 tree (per decision bar)

```
all candles (n)
├ no_box_signal        (box_silence)        count
└ box_signal                                count
  ├ gate_rejected       (vol_gated)         count
  ├ indicator_veto      (vetoed)            count
  ├ indicator_no_confirm(confirm<K)         count
  ├ passed_skipped      (would_enter)       count + would-be $
  └ entered                                 count + realized $
    ├ tp_exit           (TAKE_PROFIT_HARD)  count + $
    ├ sl_soft_exit      (STOP_LOSS_SOFT)    count + $
    ├ sl_hard_exit      (STOP_LOSS_HARD)    count + $
    └ time_cap_exit     (TIME_CAP)          count + $
      ├ time_cap_win    (pnl > 0)           count + $
      └ time_cap_loss   (pnl <= 0)          count + $
```

### L2 tree (universe = L1's forwarded `vetoed ∪ vol_gated` drops, while L1 flat)

```
l2_evaluated                                count
├ gate_rejected         (l2 vol_gated)      count
├ indicator_veto        (l2 vetoed)         count
├ indicator_no_confirm  (l2 confirm<K)      count
├ passed_no_open        (l2 'passed')       count
└ entered                                   count + realized $
  ├ tp_exit                                 count + $
  ├ sl_soft_exit                            count + $
  ├ sl_hard_exit                            count + $
  ├ time_cap_exit                           count + $
  │ ├ time_cap_win                          count + $
  │ └ time_cap_loss                         count + $
  └ l1_entry_exit       (L1-entry)          count + $   ← L2-only
forwarded_but_l1_in_position = L1(vetoed+vol_gated) − l2_evaluated   count  (sibling reconciliation)
```

### Combined

`taxonomy = {"l1": <L1 dict>, "l2": <L2 dict>, "combined_exits": {...}}` where each `combined_exits`
leaf = the L1 leaf + the L2 leaf (count and $), since the trade sets are disjoint.

## Payload shape

Each view payload (L1 / L2 / combined) gains one `taxonomy` key — a **flat** dict (flat keys keep
serialization and tests trivial; the display reconstructs the tree). `pnl` omitted on count-only leaves.

```jsonc
"taxonomy": {
  "no_box_signal":        {"count": 1784},
  "box_signal":           {"count": 4572},
  "gate_rejected":        {"count": 1203},
  "indicator_veto":       {"count": 988},
  "indicator_no_confirm": {"count": 742},
  "passed_skipped":       {"count": 51,  "pnl": -4210.0},
  "entered":              {"count": 255, "pnl": 149989.0},
  "tp_exit":              {"count": 137, "pnl": 188400.0},
  "sl_soft_exit":         {"count": 12,  "pnl": -9100.0},
  "sl_hard_exit":         {"count": 26,  "pnl": -41300.0},
  "time_cap_exit":        {"count": 80,  "pnl": 11989.0},
  "time_cap_win":         {"count": 47,  "pnl": 34010.0},
  "time_cap_loss":        {"count": 33,  "pnl": -22021.0},
  "n_classified":         6340
}
```

- **L2** adds `l2_evaluated`, `passed_no_open`, `l1_entry_exit`, `forwarded_but_l1_in_position`; omits
  `no_box_signal`/`box_signal`.
- **Combined** nests `{"l1": {...}, "l2": {...}, "combined_exits": {...}}`.

## Invariants (each becomes a test)

| invariant | meaning |
|---|---|
| `no_box_signal + gate_rejected + indicator_veto + indicator_no_confirm + passed_skipped + entered == n−1` | every L1 candle classified (bar 0 has no cause) |
| `n_classified == n−1` | anchor exposed in payload |
| L1 `entered.count == n_taken == len(L1 ledger)`; `entered.pnl == Σ pnl` | entered reconciles with the ledger |
| L1 `tp + sl_soft + sl_hard + time_cap == entered` (count and $) | exits partition entries |
| `time_cap_win + time_cap_loss == time_cap` (count and $) | win/loss partition |
| L2 `gate_rejected + indicator_veto + indicator_no_confirm + passed_no_open + entered == l2_evaluated` | L2 partition |
| `l2_evaluated + forwarded_but_l1_in_position == L1(vetoed+vol_gated)` | L2 universe reconciles to L1's forwarded drops |
| L2 `tp + sl_soft + sl_hard + time_cap + l1_entry_exit == entered` | L2 exits partition entries |
| Combined `combined_exits[leaf] == l1[leaf] + l2[leaf]` | additive roll-up |
| `perf/check_golden.py` ✅ ALL MATCH | no existing number moved |

## Dashboard layout

A new collapsible card group **"📊 Candle taxonomy"** per tab, using existing `grp()` + `DB.card()`.
Card value = count; trading cards add the dollar as a second line (e.g. `137` / `+$188,400`).
Indented sub-group headers mirror the tree (`box-signal ▸`, `entered ▸ exits`, `time-cap ▸ win/loss`).
Sign coloring reuses existing `pos`/`neg`. The CSV download note is updated to mention the taxonomy is
a log-derived projection (no new CSV columns — the per-candle CSV already carries cause/reason).

## Components / files

- **Create** `optimize/l2/taxonomy.py` — pure functions `taxonomy_l1(result)`, `taxonomy_l2(result)`,
  `taxonomy_combined(result)` returning the flat dicts above. Reads `result.log` rows + ledgers; reuses
  the existing cause/`l2_reason`/`exit_reason` fields. No engine or ledger mutation.
- **Create** `optimize/l2/test_taxonomy.py` — invariant + value tests against the frozen lean L1 default
  (and L2/combined), anchored on the known parity numbers.
- **Modify** `optimize/l2/payload.py` — `build_view_payload` attaches `taxonomy`.
- **Modify** `optimize/l2/test_payload.py` — assert the `taxonomy` key + a sentinel leaf.
- **Modify** `frontend/dashboard.html` — new card group + fill JS for all three tabs; collapse toggle.
- **Modify** `docs/LOG_FIELDS.md`, `docs/PNL_EXPLAINED.md` — document the taxonomy + its log derivation.

## Testing strategy (the one-by-one walk)

Each task ends with a Python test (count + dollars + invariant) **and**, for the UI task, a Playwright
check (card present, number == payload, no console errors). TDD throughout; golden gate after the
compute/payload tasks to prove no existing number moved.

| # | task | gate |
|---|---|---|
| B0 | `taxonomy.py` scaffold + `n_classified` invariant | `== n−1` |
| B1 | L1 no-entry leaves | counts + partition invariant |
| B2 | L1 `passed_skipped` (+ would-be $) & `entered` (+realized $) | `entered == n_taken` |
| B3 | L1 exit leaves + `time_cap_win/loss` | `Σ exits == entered`; `win+loss == time_cap` |
| B4 | L2 tree + `l2_evaluated` + `forwarded_but_l1_in_position` | L2 partition + universe reconcile |
| B5 | Combined sub-keys + additive `combined_exits` | additive invariant |
| B6 | payload wiring | `test_payload` |
| B7 | dashboard card group (3 tabs) + collapse | server test + Playwright |
| B8 | docs + CSV note + golden re-confirm | golden ✅, full L2 suite green |

## Out of scope (YAGNI)

- No new engine state, no new exit reason, no optimizer search-space change.
- No win/loss split on TP/SL-soft/SL-hard exits (only TIME_CAP).
- No new CSV columns (the per-candle CSV already carries cause/reason/exit_reason).
- No port to the shareable bundles in this change (separate follow-up, as with prior work).
