# Action Plan — Box Traversal Semantics + Explicit HOLD State

**Branch:** `v3-stable-dynamic-backtest-dashboard`
**Date:** 2026-05-23
**Scope:** Behaviour change to the Box directional oracle. Adds a third decision state and changes when signals fire.

---

## 1. The change in one paragraph

Today the Box engine returns `'long'` or `'short'` whenever the 4h candle's close sits beyond a box edge (plus a 3-tick noise margin). That fires every bar the close stays past the edge — continuous repeated signalling. The new rule is **traversal-only**: a signal fires exactly at the moment the close **transitions from one side of the box to the opposite side**. Bars where the close stays put, oscillates inside the box, or exits back the same side return the new explicit `'hold'` state. The directional oracle now has three outputs: `'long'`, `'short'`, `'hold'`.

---

## 2. Why this matters (behaviour delta)

| Scenario | Old behaviour | New behaviour |
|---|---|---|
| Close was 100 (above box 80–90), now 75 (below) | `'short'` | `'short'` ✓ |
| Close was 100, then 88 (inside), then 75 (below) over 3 bars | `'short'` fires on bar 3 (close below) | `'short'` fires on bar 3 (state transition above→below) ✓ |
| Close above box for 10 consecutive bars | `'long'` fires on **every one of those 10 bars** | `'long'` fires once on the transition bar; bars 2–10 return `'hold'` |
| Close enters the box, oscillates inside, exits the same side | `'hold'` (no fire) | `'hold'` ✓ |
| Close above the box on bar 1 (first observation of the box) | `'long'` fires immediately | `'hold'` — first observation only records the state |

The key behaviour change is **edge-position → state-transition**. The strategy will open fewer positions and the trade log will show clearer entry points (each open is a real cross, not a stale "still beyond edge" sample).

---

## 3. State machine

Per `(box_row_id, level_name)` pair (e.g., (week of 2025-01-06, W-RH)):

```
states: { 'above', 'below', None }   // None = haven't observed this (row, level) yet
classify(close, upper, lower):
  if close > upper + threshold: 'above'
  elif close < lower - threshold: 'below'
  else: 'inside'

on each bar t with close c:
  c_side = classify(c, upper(row, level), lower(row, level))
  if c_side == 'inside':
    signal := 'hold'                 // do not change state
  elif state is None:
    state := c_side                  // first observation
    signal := 'hold'                 // no fire on first observation
  elif state == c_side:
    signal := 'hold'                 // same side; not a transition
  else:
    signal := 'short' if state == 'above' else 'long'
    state := c_side
```

Notes:
- `state` only updates on `'above'` or `'below'` classifications. `'inside'` does not reset state — it's a transient.
- When the active box row changes (new week / month), state for affected levels resets to `None` (no carry-over across rows; prices may have changed materially).

---

## 4. API / data-shape change

### 4.1 `BoxLookup.get_signal_detail(close, ts)` return shape

Before:
```python
{
  'signal':         'long' | 'short' | None,
  'weekly_signal':  'long' | 'short' | None,
  'monthly_signal': 'long' | 'short' | None,
  ...
}
```

After:
```python
{
  'signal':         'long' | 'short' | 'hold',         # ← never None when a row is active
  'weekly_signal':  'long' | 'short' | 'hold' | None,  # None only when no weekly row is active
  'monthly_signal': 'long' | 'short' | 'hold' | None,  # same
  'conflict':       bool,                              # unchanged
  ...
}
```

`'hold'` replaces what used to be `None` for the *aggregate* signal when at least one side has an active box but neither fired a traversal. `None` remains for the per-side signal only when that side has no active box row at all.

### 4.2 BoxLookup becomes stateful

A new internal dict tracks `(box_row_id, level_name) → state`. The state lives on the BoxLookup instance for the duration of a backtest run.

- `BoxLookup.__init__` initialises an empty state dict.
- `get_signal_detail` reads + writes the state on each call.
- New method `reset_state()` to clear the dict — called at the start of each backtest fold (future: walk-forward folds need fresh state per fold).

### 4.3 No-fallback rule still holds

The state machine itself uses explicit `None` as an initial sentinel (not a default fallback). `MissingParameterError` continues to fire on any constructor or method missing required args.

---

## 5. BoxStrategy integration

The change is entirely contained inside `BoxLookup`. `BoxStrategy._maybe_open_position` doesn't need to change its `box_signal` reading — it already handles `signal in ('long', 'short')` to open positions and treats any other value (including `None` today, `'hold'` tomorrow) as no-op.

One small refinement: `BoxStrategy.backtest` should call `self._box.reset_state()` at the start to ensure clean state across multiple `backtest()` calls on the same BoxLookup instance.

The Big-Candle vs Box conflict resolution (`big_candle_resolution`) continues to work — it operates on the resolved direction, which is either `'long'`, `'short'`, or `'hold'`. The conflict policy now treats `'hold'` as "no box signal" (i.e., box doesn't disagree with big-candle's read), so big-candle wins by default. This is consistent with the prior semantics.

---

## 6. Test plan

| Test file | Coverage |
|---|---|
| `tests/test_box_lookup_signal.py` | NEW cases for traversal semantics: (a) above→below = short; (b) below→above = long; (c) above→inside→above = hold; (d) above→inside→below = short on the exit bar; (e) first observation never fires; (f) state resets when active box row changes |
| `tests/test_box_strategy_big_candle.py` | Update fixtures: existing test that asserts "box says LONG" must now use a multi-bar fixture that creates a traversal, not a single-bar above-edge close |
| `tests/test_api_box_sse.py` | Update synthetic CSV to produce a traversal (price climbs through the box) so the existing "complete event has trades" assertion still passes |
| `frontend/tests/...` | No changes — TS types accept `'hold'` as a string already; UI cell already renders unknown signals as `'—'` |

---

## 7. Documentation updates

| File | Change |
|---|---|
| `docs/MASTER_STRATEGY_GUIDE.md` §2 | Rewrite the directional oracle section. New rule, three states, state-machine pseudocode. |
| `docs/BOX_STRATEGY.md` | Update §Signal Logic. Move the old edge-position rule under a "Legacy (pre-v3.1)" header. |
| `docs/revisions/REVISION_LOG.md` | Round 14 entry documenting the behaviour change + verification. |
| `docs/CODING_RULES.md` | No change — the no-fallback rule still applies; `'hold'` is an explicit return value not a default. |
| `frontend/src/types.ts` | `BoxSignal.signal` already typed as `string | null`; no narrowing needed. Comment update to call out the new `'hold'` value. |

---

## 8. Execution checklist

1. ✅ Write this action plan
2. ⏳ Update `docs/MASTER_STRATEGY_GUIDE.md` §2 to describe the new rule
3. ⏳ Update `docs/BOX_STRATEGY.md` Signal Logic section
4. ⏳ Implement state machine in `src/strategy/box_lookup.py`
5. ⏳ Add `reset_state()` call in `BoxStrategy.backtest()`
6. ⏳ Rewrite `tests/test_box_lookup_signal.py` to cover traversal
7. ⏳ Update `tests/test_box_strategy_big_candle.py` fixtures
8. ⏳ Update `tests/test_api_box_sse.py` synthetic data
9. ⏳ Run pytest + npm test + build until green
10. ⏳ Launch bug bounty multi-lens swarm (7 perspectives) against the change
11. ⏳ Synthesise swarm findings into a report
12. ⏳ Update REVISION_LOG with Round 14
13. ⏳ Return to user with the swarm report + next-step question

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Existing tests broken by the behaviour change | They WILL break — the tests assume edge-position signals. Plan to rewrite the affected fixtures (single-bar above-edge → multi-bar traversal). |
| Test coverage hides multi-fold state pollution | New `reset_state()` is called per `backtest()`. Add a test that runs `backtest()` twice on the same BoxLookup and asserts trade list determinism. |
| Existing trade results change materially | Yes — fewer trades, different entries. This IS the point of the change. The bug bounty swarm's job is to validate the new behaviour is correct. |
| User intent ambiguity: "traversal" could mean "any close beyond edge once" (a relaxed reading) vs "state transition" (the strict reading) | Strict reading chosen — see §3. If the user clarifies they wanted relaxed semantics, the state machine relaxes to: fire on every transition out of `'inside'`. Easy to revisit. |
