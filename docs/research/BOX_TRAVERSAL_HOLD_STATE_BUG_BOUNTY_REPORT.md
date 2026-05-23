# Bug-Bounty Report — Box Traversal + HOLD State

**Date:** 2026-05-23
**Branch:** `v3-stable-dynamic-backtest-dashboard`
**Change under review:** edge-position box signal → traversal state-machine + explicit `'hold'` state
**Verification status:** all 46 backend tests + 77 frontend tests pass; frontend builds clean.

This report consolidates the findings from a 7-lens parallel review (financial, trading-strategy, UX/UI, logic/state-machine, QA/coverage, code-quality, technical/architecture).

---

## TL;DR

| Severity | Count | Notes |
|---|---|---|
| 🔴 Critical | **4** | Re-entry suppression, state starvation during open/cooldown, gap-skip semantics, closest-level stranding |
| 🟡 Concerns | 17 | Coverage gaps, minor frontend rendering, missing validations, doc-trail incomplete |
| 🟢 Acknowledged OK | 24 | PnL math intact, no-fallback compliance, per-request BoxLookup, doc-text consistency |

The critical findings are all **semantic** — they don't break the build or fail a test, but they make the strategy behave differently from what the user described. None of the critical issues require the test suite to be wrong; they require *more* tests and likely a refinement to the state machine.

---

## 🔴 Critical findings (must fix before declaring v3.1 stable)

### C1 — State starvation while a position is open or in cooldown
**Source:** Lens 4 (logic/state-machine)
**Location:** `src/strategy/scaling_strategy.py:220-227` + `src/strategy/box_lookup.py:187-190`

`_maybe_open_position` is the ONLY call site of `box_lookup.get_signal_detail`. The parent `ScalingStrategy.backtest` skips that call when a position is open OR when `cooldown_counter > 0`. Consequence: every bar a trade is active is **invisible** to the traversal state machine. A real traversal that occurs during a losing trade is silently swallowed; the next eligible bar then evaluates as if no traversal had occurred, and the stale `'above'`/`'below'` state from many bars ago can fire a spurious signal.

**Impact:** The strategy's signal stream is no longer continuous; it's gated by tradability. The user's spec implied a continuous classifier ("if it stayed inside the box… it's hold").

**Recommended fix:** Drive `get_signal_detail` from the `backtest` loop on EVERY bar — not from `_maybe_open_position`. Store the per-bar signal on the strategy and let `_maybe_open_position` *read* (not query) it. Reset is unchanged.

---

### C2 — Re-entry is structurally suppressed
**Source:** Lens 2 (trading strategy)
**Location:** `src/strategy/box_lookup.py:196-197` + `scaling_strategy.py:206-212`

After a `'long'` traversal fires, `_state[(row, label)] = 'above'` and remains there. To fire another `'long'`, the state must first go to `'below'` and back to `'above'` — a full round-trip. The documented `reentry_enabled=True` + `reentry_cooldown_candles=1` re-entry-after-profitable-exit flow can essentially never re-fire the same direction within the same box window.

**Impact:** Re-entry feature is structurally broken under traversal semantics.

**Recommended fix:** Decide intent. Two paths:
- **Re-entry by pullback (1-1-2 spirit):** after a profitable exit, allow re-fire on same-side close (without requiring an opposite-side traversal first). Treat re-entry as a separate signal path that doesn't consume traversal state.
- **Re-entry by full retrace:** keep current behaviour; document it; expose a toggle (`reentry_requires_full_retrace: bool`).

---

### C3 — Gap-skip fires without ever entering the box
**Source:** Lens 2 (trading strategy)
**Location:** `src/strategy/box_lookup.py:184-197`

`_classify` operates on close only. A bar that gaps from `200` (clearly above box at 80-90) straight to `50` (clearly below) fires `'short'` even though the close NEVER sat inside the box. The user's intent was "enters the box and exits from the other side."

**Impact:** Possible spurious signals on real price gaps (weekends, holidays, news).

**Recommended fix:** Either (a) require an intervening `'inside'` observation before a transition can fire, or (b) explicitly document gap-skip as intentional and add a `require_box_traverse: bool` toggle. Action plan §9 flagged this as the "strict reading" choice; the user should make the call.

---

### C4 — Closest-level jitter strands per-level state
**Source:** Lens 1, Lens 2, Lens 4
**Location:** `src/strategy/box_lookup.py:163-177`

`_best_level` deterministically picks ONE level (closest by mid-distance) per bar. State is keyed `(row, label)` per level. If price drifts so that bar N is "closest to W-RH" and bar N+1 is "closest to W-IH", the W-RH state recorded on bar N is **stranded** — no future call will re-visit W-RH unless the price returns toward its mid. Master guide §2.5 explicitly says stacked boxes should "produce multiple LONG signals as price walks up through nested boxes"; the current implementation cannot, because only ONE level is ever consulted per bar.

**Impact:** Stacked-box behaviour is silently lost; weekly box reduces to a single-level oracle.

**Recommended fix:** Update **every** level's state on every bar — not just the closest one. Then pick the closest level whose state transitioned this bar as the "active firing level" for the trade log.

---

## 🟡 Notable concerns (yellow)

Grouped by theme.

### Coverage gaps (Lens 5)
- **Y1** No test runs `BoxStrategy.backtest()` twice on the same BoxLookup (verifies `reset_state` works end-to-end). Action plan §9 risk explicitly unverified.
- **Y2** No test exercises `_maybe_open_position` on a big-candle bar when `box_signal == 'hold'`.
- **Y3** No integration test confirms a re-entry after a profitable exit re-opens via a 2nd traversal (intersects with C2).
- **Y4** First-observation independence untested per-side (weekly='above' + monthly='inside' simultaneously).
- **Y5** SSE test (`test_box_backtest_streams_progress_and_complete_events`) doesn't assert `len(trades) > 0` — a future regression to zero-trades would silently pass.
- **Y6** `weekly_side` / `monthly_side` end-to-end propagation through `/api/backtest/box` SSE payload untested.
- **Y7** No test verifies two BoxLookups from the same file have isolated state (guards against future class-level state refactor).
- **Y8** No frontend test verifies a trade with `box_signal.signal === 'hold'` renders cleanly.

### Frontend rendering (Lens 3)
- **Y9** `frontend/src/components/TradeList.vue:152-153` — `boxFiringLabel` uses `if (b.weekly_signal && b.weekly_level)`; the truthy check treats `'hold'` as truthy, so a HOLD-on-weekly + SHORT-on-monthly trade would mislabel the firing side. Tighten to `if (b.weekly_signal === 'long' || b.weekly_signal === 'short')`.
- **Y10** `boxTooltip` at `TradeList.vue:138` now renders `Box signal: HOLD` literally for any trade whose entry bar resolved to `'hold'` (shouldn't happen on a normal entry, but defensive).
- **Y11** `weekly_side`/`monthly_side` new fields not declared in `frontend/src/types.ts:130-143` `BoxSignal`; no break (TS allows extra keys) but no UI surface either.

### State-machine hardening (Lenses 4, 7)
- **Y12** `get_signal` and `get_signal_detail` BOTH mutate `_state` per call. A caller invoking both on the same bar double-advances. Only a docstring warning today — no guard.
- **Y13** `_classify` performs no `upper >= lower` validation; a swapped/garbage CSV row silently maps all bars to `'above'`.
- **Y14** Duplicate `Date` rows in the box CSV collide on the state key; `_active_row` returns `iloc[-1]` and state shares across distinct row instances with no warning.
- **Y15** `_best_level` tie-breaking on equal `dist` relies on Python's stable sort + `_WEEKLY_LEVELS` declaration order — implicit determinism, untested.

### Financial / trading-economics (Lens 1)
- **Y16** First-observation rule drops the backtest's FIRST active week's standing setup (close already 500pts above the box on day 1 → no fire). Acceptable for long backtests, problematic for short walk-forward folds.
- **Y17** Big-candle conflict resolution silently shifts toward `big_candle_wins` because `'hold'` is mapped to "no box signal". Net effect: slight bias change worth quantifying with a baseline backtest comparison.

### Doc trail (Lens 6)
- **Y18** Action plan checklist §8 items 2-13 are still ⏳ (should be ✅ for items completed in this session).
- **Y19** `docs/revisions/REVISION_LOG.md` has no Round 14 entry for the traversal change.
- **Y20** `reset_state()` docstring at `box_lookup.py:103-106` is missing the "behaviour on subsequent calls" / idempotency contract.

---

## 🟢 Acknowledged OK (green) — selected highlights

- **PnL math untouched** (`scaling_strategy.py:412`) — `point_value=2.0` accounting preserved.
- **No-fallback rule preserved** — `'hold'` is an explicit enum value, `None` strictly means "no active row". `_state.get(key)` returning `None` is an explicit sentinel documented at `box_lookup.py:100-101`, not a default-fallback.
- **Per-request BoxLookup** (`src/api/app.py:449-455`) — no shared mutable state between concurrent backtest requests.
- **Reset order correct** — `BoxStrategy.backtest:98` calls `reset_state()` BEFORE `super().backtest()`.
- **Memory bound trivial** — ~1k state entries/year, well under 1 MB for a decade.
- **TS BoxSignal.signal: string | null** already accepts `'hold'` without narrowing.
- **Box overlay rendering** (`ChartPane.vue:189-194`) unaffected by per-bar state.
- **Determinism** — Python 3.7+ dict order + stable sort + same inputs → same trades.
- **Doc text consistent** in `MASTER_STRATEGY_GUIDE.md §2` and `BOX_STRATEGY.md` — no leftover edge-position language in current sections; legacy is FROZEN-headered.

---

## Recommended action plan (next steps)

### Tier 1 — must fix to ship v3.1
1. **C1 (state starvation):** move `get_signal_detail` call into the backtest loop, observed every bar. Add a regression test that runs a fixture where a traversal occurs while a position is open and asserts the post-exit signal is correct.
2. **C2 (re-entry suppression):** decide intent with the user (pullback vs. full-retrace). Implement the chosen path. Add a re-entry integration test.
3. **C4 (closest-level stranding):** update every level's state on every bar, then select the firing level by transition-this-bar + closest-by-mid. Add a stacked-boxes test that walks price through nested levels and asserts multiple fires.

### Tier 2 — discuss with user, defer if not blocking
4. **C3 (gap-skip):** explicit policy decision needed.
5. **Y9/Y10/Y11:** small frontend cleanup pass.
6. **Y12-Y15:** state-machine hardening (validation, double-call guard, dedup-row detection).
7. **Y16-Y17:** quantify with a head-to-head backtest comparison (old edge-position vs new traversal on the same data).

### Tier 3 — hygiene
8. Y18/Y19/Y20: update action plan checklist + REVISION_LOG Round 14 + reset_state docstring.

---

## Notes on test status

The verification gate (Task #71) showed all 46 backend tests + 77 frontend tests passing, with a clean Vite/TS build. The critical findings above are **not** test failures — they are correctness concerns that the current tests don't cover. The 14 traversal tests I added exercise the state machine in isolation; they do NOT integrate with the open-position-then-exit-then-reopen flow where C1, C2, and C4 actually live.

A reasonable next step is to add an INTEGRATION test fixture (in `tests/test_box_strategy_integration.py`) that runs `BoxStrategy.backtest` on a multi-bar synthetic that includes: setup → traversal long → in-position bars with traversal back below (silently swallowed today) → SL hit → cooldown → next eligible bar. Assert what *should* happen, then fix the code until it does.
