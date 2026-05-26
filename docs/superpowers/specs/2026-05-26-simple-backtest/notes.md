# Simple Backtest — analysis & decisions

Companion to `backtest_updates.md`. The user's note resolves the truth-table reconciliation: **Stage 1's rule wins** for entries; the new backtest is a thin SL/TP exit layer on top.

Each section has a `>>>` / `<<<` block. I've **pre-filled a recommended default** in each — change it where you disagree, leave it alone where you agree. Tell me "ok done" when finished.

---

## Headline

| Layer | Before (current engine) | After (this proposal) |
|---|---|---|
| **Entry direction** | stateful per-(level-pair) `above/inside/below` traversal state machine + big-candle override + direction-flip | **Stage 1 truth table** — stateless per-candle rule |
| **Position sizing** | 1-1-2 ladder | **1 contract** (no ladder) |
| **Exit reasons** | TP, soft SL, hard SL, DIRECTION_FLIP, OPEN | **TP, SL** only |
| **Exit frame** | 1-min sub-bar engine (already correct) | unchanged — 1-min |
| **Re-entry** | `reentry_cooldown_candles` | next 4h candle whose start > exit_time |

The new engine is ~150 lines. Most of the existing complexity gets deleted.

### Your overall reaction

>>>
aproved
<<<

---

## Reconstructed engine pseudocode (sanity check this)

```
state: open_trade = None
       blocked_until_4h_after = None    # set on every exit, cleared on entry

for each 4h candle c, in datetime order:
    # ----- Entry layer (only if flat AND past gating) -----
    if open_trade is None and (blocked_until_4h_after is None or c.start > blocked_until_4h_after):
        signal = stage1_truth_table(c, active_boxes)   # → long / short / hold
        if signal in (long, short):
            open_trade = Trade(
                entry_time   = c.close_time,
                entry_price  = c.close,                # see Q1
                direction    = signal,
                tp_line      = c.close + (tp_points if long else -tp_points),
                sl_line      = c.close - (sl_points if long else -sl_points),
            )

    # ----- Exit layer (1-min walk) -----
    if open_trade is not None:
        for each 1-min bar m inside this 4h (or after entry_time within this 4h):
            if exit_condition(m, open_trade):
                open_trade.exit_time   = m.close_time
                open_trade.exit_price  = ...           # see Q4
                open_trade.exit_reason = TP or SL
                blocked_until_4h_after = open_trade.exit_time
                open_trade = None
                break
        # if no exit fired, trade carries into next 4h
```

### Does this match your intent?

>>>

<<<

---

## Q1. Entry-price / anchor for the SL & TP lines

Which price is the trade's anchor?

- **A. 4h close of the signal-firing candle** ← recommended (matches "signal fires at close")
- B. Open of the next 4h candle
- C. Open of the first 1-min candle inside the next 4h

>>>
A
<<<

---

## Q2. SL flavour — soft, hard, or both?

The note says "passed sl or tp" (singular). Pick one:

- **A. Single SL.** 1 single 1-min close past the line → exit. ← recommended for "that simple"
- B. Soft SL only. 2 consecutive 1-min closes past the line → exit at the 2nd close.
- C. Both (soft + hard) — keeps the current dual-line model.

>>>
A
<<<

---

## Q3. TP fire condition

- A. **Touch** — first 1-min `high` (long) / `low` (short) that crosses the TP line.
- **B. Close past** — first 1-min `close` past the TP line. ← recommended (mirrors SL semantics; avoids over-optimistic "wick fills")

>>>
B
<<<

---

## Q4. Fill price on exit

- A. Exit at the **line price** (idealised; assumes you got filled exactly at TP/SL).
- **B. Exit at the 1-min `close`** that triggered the exit. ← recommended (slippage-realistic; consistent with close-based fire condition)

>>>
B
<<<

---

## Q5. Position size

The note doesn't mention sizing. Confirm:

- **A. Always 1 contract.** ← recommended ("that simple")
- B. Configurable fixed size (`contracts` param, default 1).
- C. Keep the 1-1-2 ladder (legs 2/3 fire on adverse 1-min moves).

>>>
A
<<<

---

## Q6. Stage 1 input — which level pair drives the signal when a candle fires on multiple?

A 4h candle can have multiple non-hold Stage 1 rows (e.g. long on weekly *and* long on monthly).

- **A. Candle-level collapse** (any-long → long; any-short → short; else hold). ← recommended (matches Stage 1.0 / 1.1)
- B. Weekly priority then monthly (matches the current engine's tie-break).
- C. Per-(candle, box) — one trade per firing level-pair; multiple concurrent trades allowed.

>>>
A
<<<

---

## Q7. Re-entry gating — three sub-questions

### Q7a. After exit at 19:43 inside 4h candle X (18:00–22:00), which is the first signal-eligible 4h close?

Concrete example:
- X starts 18:00, ends 22:00. Exit at 19:43.
- X+1 starts 22:00, ends 02:00.
- X+2 starts 02:00, ends 06:00.

- A. Evaluate at X+1's close (02:00). X+1 started at 22:00 — after the exit, so eligible.
- **B. Evaluate at X+1's close (22:00 start was strictly after 19:43 exit, so it qualifies).** ← same as A; recommended reading
- C. Skip X+1 because the *entry decision* would be made at the close of a candle that started before exit_time. Evaluate at X+2's close.

(A and B are the same option — pick the right one.)

>>>
B
<<<

### Q7b. Does the re-entry candle need a *fresh* signal?

After an exit, the very next eligible 4h close is checked against Stage 1's rule. If it says `hold`, we wait. If it says `long` or `short`, we open immediately — even if it's the same direction as the trade we just exited.

- **A. Yes — fresh Stage 1 evaluation per eligible 4h candle, no memory.** ← recommended
- B. No — block same-direction re-entry for N candles after a STOP_LOSS.

>>>
A
<<<

### Q7c. Different behaviour after STOP_LOSS vs TAKE_PROFIT?

- **A. No difference.** Same re-entry gating regardless of exit reason. ← recommended
- B. Yes — longer wait after STOP_LOSS.

>>>
A
<<<

---

## Q8. In-progress 4h candle at the exit moment

When the trade exits at 19:43 inside the 4h candle that opened the trade, what happens to the rest of that candle?

- **A. Just wait for the next 4h close. No signal evaluation inside a partial 4h.** ← recommended (Stage 1's rule is per-closed-candle)
- B. Evaluate a partial-bar signal at the exit moment.

>>>
A
<<<

---

## Q9. Implementation approach

- A. **In-place edit** of `src/strategy/box_strategy.py` + `scaling_strategy.py`. Risk: huge diff, hard to review.
- B. **New module** `src/strategy/simple_strategy.py`. Old engine stays in place behind a config flag. Both engines co-exist until the new one is verified. ← recommended
- C. Build in `subprojects/backtest_simple/` first, promote later.

>>>
B
<<<

---

## Q10. NSGA-II re-targeting

After this change, what does the optimizer search over?

- **A. `(sl_points, tp_points)` — 2 vars.** Single objective: total profit. Per-direction with option to tie. ← recommended given Q5=A
- B. Keep the current `(sl_soft, sl_hard_delta, tp)` if Q2 picks "both SL flavours".
- C. Expand: include the entry-direction choice (long-only / short-only / both) as a third var.

>>>
A
<<<

---

## Q11. Test-locking strategy

The current `tests/test_blueprint_examples.py` locks January-2025 trades from the OLD engine. They will all fail under the new engine.

- A. Throw out old locks, generate new ones from the simple engine, lock those.
- **B. Keep both engines alive until the simple engine has its own locks (matches Q9=B).** ← recommended
- C. Skip blueprint locks for the simple engine; rely on smaller golden set + integration tests.

>>>
B
<<<

---

## Q12. Anything else to add or veto

The viewer at `docs/superpowers/specs/2026-05-26-nsga2-truth-table-prep/viewer/index.html` is the truth-table comparison. Once the simple engine is built, that viewer is obsolete — should I delete or keep it as a historical record?

>>>

<<<

---

## After approval — proposed work order

1. Write the implementation plan (`docs/superpowers/plans/2026-05-26-simple-backtest.md`) reflecting your answers.
2. Build `src/strategy/simple_strategy.py` with a Stage-1-style entry rule + SL/TP exit + the re-entry gate. Add Pydantic schema in `src/api/schemas.py` (`SimpleBacktestRequest`).
3. Add an API endpoint `POST /api/backtest/simple` (alongside the existing `POST /api/backtest/box`).
4. Write synthetic + real-data tests for the simple engine.
5. Re-target NSGA-II to call the simple engine. Update `src/optimization/objective.py`.
6. Decide what to do with the old engine (keep behind flag / deprecate / delete).

Nothing happens until you fill the `>>>` blocks above and ping me.

---

## Update 2026-05-26 v2 — exit model overruled

The Q2/Q3/Q4 answers above are superseded by a clarification from the user:

> *"the soft stop loss waits till two sequence candles to close under specific value so it exit and registers the price as the actual exit price ... for the hard stop loss it watches the up (max) (touch) value ... at the close of the end of the 1 min candle we are comparing the value of the max (UP) price of the candle with our hard stop loss ... if passed it we exit and store the hard sl value not the close value to mimic real live data stream ... the tp system is always tied to the one minute candle for touch ... it compares the value we introduced to the UP value the max value and stores it not the close value"*

Locked behaviour:

- **Soft SL** — 2 consecutive 1-min **closes** past the soft line → exit at the **2nd close** (worse than the line in absolute value). Single-close past, then a recovery, resets the counter.
- **Hard SL** — 1-min bar's **extreme** (`low` for long, `high` for short) touches the hard line → exit at the **hard line price** (idealised stop fill).
- **TP** — 1-min bar's **extreme** (`high` for long, `low` for short) touches the TP line → exit at the **TP line price** (idealised limit fill).
- Per-bar tie-break: **hard SL > TP > soft SL** (pessimistic intra-bar ordering).
- New params: `sl_soft_points`, `sl_hard_points`, `tp_points`. Validator: `sl_hard_points >= sl_soft_points`.
- New exit reasons: `TAKE_PROFIT`, `STOP_LOSS_HARD`, `STOP_LOSS_SOFT`, `OPEN`.

Real-data lock at `(sl_soft=100, sl_hard=200, tp=150)` on the full preset:

| | count |
|---|---|
| Total trades | 590 |
| STOP_LOSS_HARD | 152 |
| STOP_LOSS_SOFT | 343 |
| TAKE_PROFIT | 94 |
| OPEN | 1 |
| Total pnl $ | −1,163,360 |

Engine + tests + API + docs were updated to match. The earlier single-SL close-past locks (604 trades) are obsolete.

---

## Update 2026-05-26 v3 — no look-ahead

User: the engine had a timing bug. The 4h CSV's `Date` is the bar's **start**, but the engine fired entries at `Date` using the bar's close (which is only known at the bar's END). That meant the engine "saw" intraday volatility before the signal was actually computable, and the resulting exits — especially hard SL touches — were biased.

Locked interpretation:

- **Signal candle** = `df_4h.iloc[idx - 1]` (the just-closed bar).
- **Entry time** = `df_4h.iloc[idx].Date` (the new 4h boundary).
- **Entry price** = signal candle's close.
- **Exit walk** = 1-min bars in window `idx` (chronologically after the boundary).
- **Warm-up:** iteration `idx=0` has no predecessor → no signal can fire on the first bar (matches `MASTER.md §2.3`).

The trade dict gains `signal_idx` so the chart/UI can mark both the bar that fired the signal and the bar where the trade lives.

New real-data locks at `(sl_soft=100, sl_hard=200, tp=150)`:

| | count |
|---|---|
| Total trades | 594 |
| STOP_LOSS_HARD | 8    (was 152 with look-ahead) |
| STOP_LOSS_SOFT | 315  (was 343) |
| TAKE_PROFIT    | 271  (was 94) |
| OPEN           | 0    (was 1) |
| Total pnl $    | **+65,555** (was −1,163,360) |

Hard SL count collapsed because the bulk of those came from the engine seeing the intraday low of the entry bar before the bar had actually closed. With no look-ahead, only legitimate hard SL touches fire — and there are very few at sl_hard=200 because the soft SL (at 100) confirms first in most cases.

Engine, tests, API, and docs updated to match. Invariant test:

```python
assert t['entry_idx'] == t['signal_idx'] + 1
```
