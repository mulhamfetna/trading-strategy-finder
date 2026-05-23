# Strategy Integration Analysis

**Question:** Should `BOXES_Strategy.md` and `Currunt_Strategy_Algo_for_Trading.md` be integrated, or is there a logical conflict?

**Short answer:** **They should be integrated, and they already are.** The two playbooks describe *different layers of the same trading system* — they were not designed as competing strategies. The integration is logically sound everywhere except **one well-defined conflict point** (the Big-Candle Exception) that needs an explicit policy.

The rest of this document does the deep study that supports that conclusion.

---

## 1. What each playbook actually decides

### 1.1 `Currunt_Strategy_Algo_for_Trading.md` — the 1-1-2 Scaling playbook

This document covers **the entire lifecycle of a trade after a direction is chosen**:

| § | Decision | Lives in code |
|---|---|---|
| §1 | Position sizing across 3 entry legs (1-1-2 contracts at 0 / −100 / −150 pt pullbacks) | `ScalingParams.total_contracts`, `legN_contracts`, `legN_pullback_points` |
| §2 | Big-candle exception (candle > 400 pts → enter full size, reverse direction) | `ScalingParams.big_candle_*` |
| §3 | Entry-trigger confirmation (3×15s for E1, 1×15s for E2/3) | `ScalingParams.entry*_confirmation_*` (documented, not enforced in 4h-only mode) |
| §4 | Dual stop loss (2-min soft, 5-sec hard, "close beyond line" rule) | `ScalingParams.sl_*` |
| §5 | Take profit (+150 pt target, +50 pt arm/watch trail, 2-min close exit) | `ScalingParams.tp_*` |
| §5b | Re-entry after profitable exit on pullback to base | `ScalingParams.reentry_*` |

It also defines **one** direction-selection rule, **implicitly**: trade in the direction of the trigger candle (close vs prev close). This is encoded in `ScalingStrategy._maybe_open_position`:

```python
if close > prev_close: direction = 'long'
elif close < prev_close: direction = 'short'
```

That rule is **not** explicitly documented in the playbook — the playbook assumes you have already decided which way to trade and is silent about *which* candle triggers it. The "close vs prev close" rule is the simplest reasonable default.

### 1.2 `BOXES_Strategy.md` — the TradingView Box playbook

This document covers **one thing and one thing only**: how to *choose the direction*. It is a **directional oracle**, not a complete trading system.

| Rule | Decision | Lives in code |
|---|---|---|
| Box edges define a horizontal range; weekly + monthly stacks | Direction = which edge the price crossed | `BoxLookup.get_signal` |
| Cross above an upper edge ⇒ LONG action | Directional read | same |
| Cross below a lower edge ⇒ SHORT action | Directional read | same |
| Price inside box ⇒ HOLD (no action) | Filter | same |
| Multiple stacked boxes ⇒ each cross is a fresh action | Re-fire policy | same |
| 3-tick margin (0.75 pt) above/below edge before firing | Noise filter | `BoxLookup.tick_threshold` (now a param) |
| Intersected boxes ignored (deferred) | Scope | n/a |
| -2 day calendar shift, one-time preprocessing | Data prep | `scripts/preprocess_boxes.py` |

The Box playbook is **silent** on:
- Position size
- Stop loss
- Take profit
- Re-entry
- Big-candle behaviour
- Confirmation timeframes

This silence is not an omission — it's a separation of concerns. The Box playbook is explicitly meant to **plug into an existing execution framework**. It says "I will tell you long/short; you decide how big and how to manage the trade."

### 1.3 What `docs/BOX_STRATEGY.md` adds

The structured version of the box spec confirms one extra fact:

> Entry execution → **Open of next 4h candle after signal closes**
> Same 1-1-2 scaling mechanics as current ScalingStrategy

That single sentence is the explicit declaration of intent: **box strategy delegates execution to 1-1-2 Scaling**. The integration is the whole point.

---

## 2. Side-by-side decision matrix

| Decision dimension | 1-1-2 Playbook says | Box Playbook says | Layer where it belongs |
|---|---|---|---|
| **Direction** | bar momentum (close vs prev close) | edge-cross signal | Box (when active), Scaling default otherwise |
| **Position size** | 1-1-2 across legs | not specified | 1-1-2 |
| **Leg-fill rule** | base ±100 / ±150 pullback | not specified | 1-1-2 |
| **Entry confirmation** | 3×15s for E1, 1×15s for E2/3 | 4h close beyond edge | Box for direction-detect, 1-1-2 for fill-confirm (in dual-timeframe mode) |
| **Big-candle override** | reverse direction on >400 pt bar | not specified | **CONFLICT — see §3** |
| **Stop loss** | dual SL with 2-min/5-sec close confirmations | not specified | 1-1-2 |
| **Take profit** | +150 hard / +50 watch trail with 2-min close | not specified | 1-1-2 |
| **Re-entry** | pullback to original base after profitable exit | not specified | 1-1-2 |
| **Data window** | 4h candles for backtest | 4h candles + box CSVs | both |

**Result:** Of the nine decision dimensions, **only one** is contested. The other eight are either uncontested (one playbook is silent) or harmonised through the natural layering.

---

## 3. The one real conflict — Big-Candle Exception vs Box signal

### 3.1 The conflict

Both playbooks define a **directional rule for the trigger candle**:

- **1-1-2 §2:** If the trigger candle is >400 pts, enter **the opposite direction** of the candle (green → short, red → long), with full size immediately, no scaling.
- **Box:** If the trigger candle's close is beyond an active edge, enter **in the cross direction**.

Both can be true on the same 4h bar:

| Bar | 1-1-2 says | Box says | Same direction? |
|---|---|---|---|
| Huge green +500 pt bar that closes above the weekly RHU edge | SHORT (reversal) | LONG (upper cross) | **NO — direct conflict** |
| Huge red −500 pt bar that closes below the weekly RLD edge | LONG (reversal) | SHORT (lower cross) | **NO — direct conflict** |
| Small +50 pt bar that closes above the weekly RHU edge | LONG (close > prev) | LONG (upper cross) | yes |
| Huge green +500 pt bar inside the box | SHORT (reversal) | HOLD (no cross) | only one fires |

### 3.2 What the current code does

```python
# src/strategy/box_strategy.py, _maybe_open_position
if candle_size > p.big_candle_threshold_points:
    # Big-candle takes over: enter reversed, ignore Box
    base_direction = 'long' if close > opn else 'short'
    if p.big_candle_reverses_dir:
        base_direction = 'short' if base_direction == 'long' else 'long'
    ...
    return pos  # <-- early return; box signal never consulted
```

**The Big-Candle Exception unconditionally overrides the Box signal.** A 500-point green bar that crossed the weekly upper edge will be entered SHORT (reversal), not LONG (breakout). This is a silent policy choice — neither playbook explicitly says which should win.

### 3.3 Three defensible policies

| Policy | Behaviour | Argument |
|---|---|---|
| **A — Big-Candle wins (current)** | Reverse on >400 pt bar even if box signal disagrees | A 500-pt bar is exhaustion-class momentum; the playbook's mean-reversion bias applies regardless of where the bar closed. |
| **B — Box wins** | When both fire, take the box direction with full big-candle size | The level cross is the *thesis*; bar size is just *sizing context*. The trader chose the box strategy because they trust level breaks over bar-color heuristics. |
| **C — Conflict ⇒ no trade** | If big-candle and box disagree, skip the bar | When two signals disagree, the safest action is to wait. |

**Recommendation:** Make this an explicit parameter — `big_candle_resolution: Literal['big_candle_wins', 'box_wins', 'skip']` defaulting to `big_candle_wins` to preserve current behaviour. Document the choice in the dashboard with a tooltip explaining the three options.

---

## 4. Softer concerns — documentation, not conflicts

These are places where the integration *works* but the semantics deserve to be written down so future maintainers don't trip:

### 4.1 Confirmation timeframe collapse (1-1-2 §3 vs Box)

The 1-1-2 playbook prescribes **15-second** confirmation for Entry 1. The Box playbook implicitly works on the **4h close**. In 4h-only backtest mode these collapse to the same event — the engine treats each 4h close as already-confirmed. In a future dual-timeframe build, the Box and the Entry-1 confirmation are different events on different timeframes — Box on 4h, Entry-1 on 15s. The current `ScalingParams.entry_confirmation_timeframe_seconds = 15` field is documented but not enforced. That's the right shape for now.

### 4.2 Leg-fill semantics under Box entry

The 1-1-2 sizing rule says "enter base + 100 + 150 on pullbacks". The pullbacks are *relative to the original entry direction*. With Box entry:

- We enter long at 20000 because price broke above the weekly RHU edge (say at 19950).
- Price falls back to 19900 (below the weekly upper edge again). Leg 2 fires.
- Price falls to 19850. Leg 3 fires. Average price is now 19925.
- We're now LONG 4 contracts at average 19925, but the box that triggered us is no longer being broken upward.

This is logically consistent — we're scaling into a losing position the same way 1-1-2 always does. It's also a known weakness of the 1-1-2 mechanic: it gets you maximum size at the worst average price if the breakout fails. The integration doesn't change this property; it just makes it possible to enter a 1-1-2 trade off a level-cross instead of a candle-color trigger.

### 4.3 Re-entry semantics under Box entry

The 1-1-2 re-entry rule says "after a profitable exit, if price pulls back to entry zone, re-enter same direction". With Box mode, the "entry zone" is the box edge. After exit, three interpretations are possible:

- **Literal:** pull back to original entry price (whatever `position.base_level` was). Current code does this.
- **Box-aware:** pull back to the *same box edge* that triggered. Requires storing the firing edge with the exit.
- **Box-fresh:** wait for a new box signal of the same direction. Simplest, no special re-entry logic needed.

Current behaviour (literal) is correct in the sense that it preserves 1-1-2 mechanics. Box-aware would be a future refinement.

### 4.4 Null edges in TH / TL boxes (`BOXES_Strategy.md` line 24)

> "we have to check for null values"

`BoxLookup._best_level` already does this with `pd.isna()`. No conflict; just an integration point that's already handled.

---

## 5. Architectural fit in the current codebase

```
       ┌──────────────────────────────────────┐
       │           ScalingStrategy            │
       │  ┌──────────────────────────────┐    │
       │  │  _maybe_open_position(idx,…) │← entry direction
       │  └──────────────────────────────┘    │
       │  ┌──────────────────────────────┐    │
       │  │  _maybe_fill_legs(...)       │    │  position management
       │  │  _check_exits(...)           │    │  (size, SL, TP, re-entry)
       │  │  _maybe_arm_watch(...)       │    │  — playbook §1, §4, §5
       │  └──────────────────────────────┘    │
       └──────────────────────────────────────┘
                        ▲
                        │ override _maybe_open_position only
                        │
       ┌──────────────────────────────────────┐
       │          BoxStrategy                 │
       │  (BoxLookup.get_signal_detail)       │
       └──────────────────────────────────────┘
```

The OOP layering matches the conceptual separation:
- `ScalingStrategy.backtest()` is the **lifecycle owner**.
- `_maybe_open_position` is the **direction-selection seam**.
- `BoxStrategy` overrides exactly that one method to swap the directional rule.
- Every other piece is inherited.

This is the **textbook Template Method pattern** applied to a strategy framework. It is **the right shape**, and the playbooks support it.

---

## 6. Conclusion

### 6.1 Should they be integrated?

**Yes — and they already are. The integration is conceptually sound.** The Box playbook is a *directional oracle* designed to plug into the 1-1-2 Scaling execution framework. The 1-1-2 playbook is the *execution framework* and is silent on which directional rule feeds it. They were written to layer.

### 6.2 Is there a logical conflict?

**One — the Big-Candle Exception.** When the trigger candle exceeds the configured threshold AND the box signal is firing AND the two disagree on direction, the current code silently lets the Big-Candle Exception win. This is a defensible default but should be made an explicit user policy with three options:
1. `big_candle_wins` (current behaviour — reverse, ignore box)
2. `box_wins` (take the box direction, with full big-candle size)
3. `skip` (disagreement ⇒ no trade)

### 6.3 Recommended follow-ups

| # | Action | Rationale |
|---|---|---|
| 1 | Add `big_candle_resolution` to `ScalingParams` + `BoxStrategyParams` | Make the §3.2 policy a deliberate user choice |
| 2 | Update `docs/BOX_STRATEGY.md` to spell out the integration contract: "Box decides direction, 1-1-2 owns everything else" | Lock in the architectural intent so future contributors don't try to add SL/TP rules to Box |
| 3 | Tighten the Big-Candle docstring in `ScalingParams` | Note that with Box mode the threshold may need to be tuned differently (Box already filters out small noise via the 3-tick margin) |
| 4 | (Optional, future) Add `reentry_mode: Literal['legacy', 'box_aware', 'box_fresh']` | Make §4.3 explicit instead of implicit |

These are the only loose ends. The strategies are correctly integrated; the question in the heading has a clean answer.
