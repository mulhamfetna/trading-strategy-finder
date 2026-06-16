---
name: spec_entry_pause_visibility
description: "Entry-pause visibility side task — surface WHY the system isn't entering, everywhere: dashboard event log tags every prevented entry with its reason; 4 new dashboard metric cards (box-silence / position-hold / gate-non-entry / indicator-non-entry streaks); and the all-stocks signal delivery gains a holds_dropped column + a per-signal pause sidecar."
metadata:
  type: project
  workstream: entry-pause-visibility
  status: SPEC (approved design → writing-plans)
  date: 2026-06-16
---

# SPEC — Entry-pause visibility (dashboard + all-stocks signals)

## 0. Why
The α verdict + pause diagnosis showed the ~11.5-day no-entry stretch is **box-signal sparsity + the
confirmation layer**, not the vol gate. This task makes that **visible everywhere** so the (paused)
gate/entry redesign is data-driven: the dashboard shows *why* each non-entry happened, and the shipped
per-instrument signal files expose each instrument's longest box-only pause.

Three parts; build dashboard (1+3) first, then all-stocks (2).

## 1. Decisions (approved)
| # | Decision |
|---|---|
| D1 | Event log shows **all blocked candidates WITH reason** (`vol_gated` / `vetoed` / `confirm<K`) |
| D2 | Part-3a = **two** cards: longest **box-silence** AND longest **position-hold**, each labelled |
| D3 | Part-2 delivery = **per-signal sidecar report** (not filename encoding) |
| D4 | Dashboard backend changes are **additive** (new summary fields + new events) — trades/PnL unchanged → golden 6/6 |
| D5 | The `holds_dropped` column **re-anchors** the NQ byte-parity gate (#200) — a conscious, documented schema change |

## 2. Shared backend — `strategy.build_payload` (dashboard path)
`build_payload` already computes, per decision bar: the box signal (`sig`), `vol_gate` (`vf ≤ gthr`), the
indicator `veto_mask`, and the confirm resolver; and it captures `blocked` (gate-dropped directional signals).
Extend additively:

**Per-bar cause** (priority): `no_signal` (sig==0) → `vol_gated` (sig≠0, ¬vol_gate) → `vetoed` (veto) →
`confirm<K` (confirm fails) → `would_enter`. Reuse the masks already built; compute once.

**4 streak metrics → `summary`** (each `{bars, days}`; days via the decision-bar duration):
1. `longest_box_silence` — max consecutive `sig==0` bars.
2. `longest_position_hold` — max single trade duration (exit_idx − entry_idx) over the taken trades.
3. `longest_gate_noentry` — max consecutive bars with `sig≠0 ∧ ¬vol_gate` (vol-gate blocked candidates).
4. `longest_indicator_noentry` — max consecutive bars with `sig≠0 ∧ vol_gate ∧ (veto ∨ confirm<K)`
   (gate-approved but indicator-blocked).

**Blocked events → `events`**: each blocked candidate becomes an event `{time, type:"blocked", reason, dir}`
where `reason ∈ {vol_gated, vetoed, confirm<K}`. (Extend the existing `blocked` capture to carry the reason;
emit as events.)

**Invariants:** no change to `trades`, equity, DD, PnL, or the existing entry/exit events ⇒ **golden 6/6
unchanged** (verified after the change). Lock: a unit test on the 4 streak helpers (synthetic mask arrays).

## 3. Frontend — `frontend/index.html`
- **Event log**: render `blocked` events with a distinct style + the reason text, interleaved by time with
  entries/exits (filterable visually by the reason tag).
- **4 new cards** in the responsive `#cards` row (after the existing pause/no-entry card), each with a short
  description sublabel:
  - "longest box-silence" — `N candles · Hh Mm` ("no box signal at all")
  - "longest position hold" — `N candles · Hh Mm` ("single trade held")
  - "longest gate non-entry" — `N candles · Hh Mm` ("box signalled, vol-gate blocked")
  - "longest indicator non-entry" — `N candles · Hh Mm` ("gate-approved, indicators blocked")
- Values come from `D.meta.summary` (run-time, like the other cards). Time unit = the run's decision-bar
  duration (e.g. 4h → candles×4h).

## 4. all-stocks-signals — `subprojects/all-stocks-signals/`
- **`2_holds_dropped` CSVs**: add a **`holds_dropped`** integer column = the count of consecutive `hold` rows
  removed immediately before each `long`/`short` row (the box-silence run that preceded this signal).
- **Per-signal pause sidecar** `PAUSE_SUMMARY.json` (+ a readable `.md`) per `instrument×tf×preset`, also
  collated into the delivery bundle: `{holds_dropped_total, longest_box_pause:{bars,~time}, reverse:{longest_pause:{bars,~time}}}`.
  The "longest box pause" = max consecutive `hold` run in `1_all_signals`; the reverse value = max
  `holds_between` in `3_reverse_signals`.
- **Parity:** adding the column changes `2_holds_dropped` schema → **re-anchor** the NQ byte-parity baseline
  (#200) and note it in the all-stocks docs; structural validation re-run.

## 5. Testing
- `optimize/test_pause_streaks.py` — the 4 streak helpers on synthetic mask arrays (incl. edges: no signal,
  all-signal, single trade).
- Golden `perf/check_golden.py` 6/6 after the build_payload change.
- Dashboard smoke: run the champion, confirm the 4 cards populate + blocked events appear with reasons.
- all-stocks: regenerate one instrument bundle, confirm the `holds_dropped` column + `PAUSE_SUMMARY` sidecar;
  re-anchor the NQ parity baseline.

## 6. Files
```
strategy.py                                  # MODIFY: 4 streak metrics + reason-tagged blocked events (additive)
frontend/index.html                          # MODIFY: log blocked events w/ reason + 4 new cards
optimize/test_pause_streaks.py               # NEW: streak-helper unit lock
subprojects/all-stocks-signals/*.py          # MODIFY: holds_dropped column + PAUSE_SUMMARY sidecar + re-anchor parity
study_range_regime/UPDATE_entry_pause_visibility.md   # the verbose doc (Mermaid)
```

## 7. Non-goals
No change to the entry/exit engine, the gate logic, trades, or PnL (visibility only). No gate/entry REDESIGN
(that's the PAUSED brainstorm — this task feeds it data). No filename encoding for part 2 (sidecar only).
