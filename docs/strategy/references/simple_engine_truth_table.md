---
name: simple_engine_truth_table
description: Formal truth table for the simple engine — entry decision (Stage 1) and exit decision (dual-SL + TP).
type: reference
---

# Simple engine — entry & exit truth tables

Live reference for `src/strategy/simple_strategy.py`. The simple engine is **two coupled state machines**: an entry decision per closed 4h candle and an exit decision per 1-min bar of an open trade. This document is the formal decision-table specification.

---

## 1. Inputs

| Source | Meaning |
|---|---|
| `df_4h` | 4h OHLCV. `Date` column = bar **start** time (e.g., `18:00:00` means the bar covers 18:00–22:00). |
| `df_1min` | 1-min OHLCV. Same Date-is-start convention. |
| `box_df` | Per-day box geometry (`WTHU/WTHD`, `MRHU/MRHD`, etc.) indexed on the normalised box date. |

Per-candle inputs derived inline:
- `O, H, L, C` = candle's open, high, low, close
- `color = green if C > O else red if C < O else doji`
- `box_date = BoxLookup._candle_to_box_date(ts)` (NQ session rule: hour ≥ 18 rolls forward one calendar day)

---

## 2. Entry truth table (Stage 1 — `_stage1_candle_signal`)

**Entry uses Stage 1's logic exactly. No touch-style line-crossing logic — that is *exit-only*.** The decision is per-(candle, level-pair) and combines three things from the bar alone:

1. **Range-overlap** between the candle and the box: `range_overlap = (L ≤ BU) AND (H ≥ BL)`. This is a *precondition*, not a touch event. It uses `L` and `H` only to ask "did this candle's price band intersect the box at all?" — a single yes/no per pair.
2. **Color** of the candle: `green` (C > O), `red` (C < O), or `doji` (C == O).
3. **Close-vs-edge**: a strict `>` for green/upper or `<` for red/lower. Pure scalar comparison of the close to a single box edge; no high/low involved, no touch.

> Distinction worth nailing: an exit fires when a 1-min bar's `H` or `L` *crosses a line* (touch). The entry decision never asks that question. Entry asks "did the bar's range INTERSECT the box?" plus "did the close break a specific edge with the right color?" — neither of which is touch detection.

### 2.1 Per (candle, active level-pair) decision

For each active level pair on the candle's mapped box-date row, with edges `BU` (box upper), `BL` (box lower):

| # | range overlap | color | C vs BU | C vs BL | per-pair result | impl line |
|---|---|---|---|---|---|---|
| 1 | false | any   | any    | any    | hold                          | `continue` (skip pair) |
| 2 | true  | green | C > BU | —      | **long**                      | `has_long = True` |
| 3 | true  | green | C == BU| —      | hold (edge equality)          | strict `>` ✓ |
| 4 | true  | green | C < BU | —      | hold (close didn't break)     | both branches skipped |
| 5 | true  | red   | —      | C < BL | **short**                     | `has_short = True` |
| 6 | true  | red   | —      | C == BL| hold (edge equality)          | strict `<` ✓ |
| 7 | true  | red   | —      | C > BL | hold (close didn't break)     | both branches skipped |
| 8 | true  | doji  | any    | any    | hold (doji never fires)       | early `return 'hold'` at top |
| 9 | true  | red   | C > BU | —      | hold (color/dir mismatch)     | red can only enter SHORT branch |
| 10| true  | green | —      | C < BL | hold (color/dir mismatch)     | green can only enter LONG branch |

### 2.2 Per-candle collapse

After scanning all active level pairs:

| has_long | has_short | candle_signal |
|---|---|---|
| true | false | `long`  |
| false| true  | `short` |
| false| false | `hold`  |
| true | true  | (cannot happen — Stage 1's color rule guarantees exclusivity) |

### 2.3 Verdict vs. documentation

- Matches `subprojects/signals/truth_table.md` row-for-row.
- Matches the candle-level collapse rule from `subprojects/signals/stage1_0_reverse_signals/` and `stage1_1_next_signal/`.
- Doji handled via early-return at the top of `_stage1_candle_signal` (one check, not duplicated per pair).

**No deviation.**

---

## 3. Exit truth table (per 1-min bar of an open trade)

**Two modes**, selected by `flip_entry_direction`. Touch detection lives only here (never in entry).

### 3.0 Flip layer (between entry signal and trade open)

After `_stage1_candle_signal()` produces a `long`/`short`/`hold` decision:

| flip_entry_direction | Stage 1 signal | actual position direction |
|---|---|---|
| false (normal) | long | long |
| false (normal) | short | short |
| false (normal) | hold | (no trade) |
| true (flipped) | long | **short** |
| true (flipped) | short | **long** |
| true (flipped) | hold | (no trade) |

`direction_scope` is applied **after** the flip (i.e., it filters the actual opened direction). Re-entry gate is independent of the flag.


### 3.1 The four lines

Every trade carries **four** line values regardless of mode. Only three are active per mode:

| Line | Long position | Short position | Active when |
|---|---|---|---|
| `sl_soft_line` | `entry − sl_soft` (below) | `entry + sl_soft` (above) | flip OFF |
| `sl_hard_line` | `entry − sl_hard` (below, deeper) | `entry + sl_hard` (above, deeper) | both modes |
| `tp_soft_line` | `entry + tp_soft` (above) | `entry − tp_soft` (below) | flip ON |
| `tp_hard_line` | `entry + tp_hard` (above, deeper) | `entry − tp_hard` (below, deeper) | both modes |

Constraints: `sl_hard ≥ sl_soft`, `tp_hard ≥ tp_soft`. All four > 0.

### 3.2 NORMAL mode (flip=OFF) — per-bar decision

Priority **hard SL > hard TP > soft SL**. Soft confirmation lives on the SL side.

LONG position:

| # | check | action | fill price | soft counter |
|---|---|---|---|---|
| 1 | `m.low ≤ sl_hard_line` | exit **STOP_LOSS_HARD** | `sl_hard_line` | reset |
| 2 | else `m.high ≥ tp_hard_line` | exit **TAKE_PROFIT_HARD** | `tp_hard_line` | reset |
| 3 | else `m.close ≤ sl_soft_line` AND counter+1 ≥ 2 | exit **STOP_LOSS_SOFT** | `m.close` | reset |
| 4 | else `m.close ≤ sl_soft_line` AND counter+1 < 2 | continue (arm soft) | — | `counter += 1` |
| 5 | else | continue | — | `counter := 0` |

SHORT position (mirrored — high↔low and `≤`↔`≥` swap on all rows).

### 3.3 FLIPPED mode (flip=ON) — per-bar decision

Priority **hard TP > hard SL > soft TP** (symmetric flip — Q-A locked). Soft confirmation lives on the TP side.

LONG position (this is the actual position direction; the original Stage 1 signal was short before the flip):

| # | check | action | fill price | soft counter |
|---|---|---|---|---|
| 1 | `m.high ≥ tp_hard_line` | exit **TAKE_PROFIT_HARD** | `tp_hard_line` | reset |
| 2 | else `m.low ≤ sl_hard_line` | exit **STOP_LOSS_HARD** | `sl_hard_line` | reset |
| 3 | else `m.close ≥ tp_soft_line` AND counter+1 ≥ 2 | exit **TAKE_PROFIT_SOFT** | `m.close` | reset |
| 4 | else `m.close ≥ tp_soft_line` AND counter+1 < 2 | continue (arm soft) | — | `counter += 1` |
| 5 | else | continue | — | `counter := 0` |

SHORT position (mirrored).

### 3.4 PnL formula (same in both modes)

- `long`:  `pnl_points = exit_price − entry_price`
- `short`: `pnl_points = entry_price − exit_price`
- `pnl_dollars = pnl_points × 20.0` (NQ point value)

`direction` is the **actual position direction** (post-flip), so the formula works without branching on the flip flag.

Soft-side fills land **past** the line in the soft direction:
- normal: `|pnl_points| ≥ sl_soft_points` (worse than the line — loss confirmed)
- flipped: `pnl_points ≥ tp_soft_points` (better than the line — profit confirmed; literal mirror per Q-B)

OPEN trades (still open at EOF): `exit_time = None`, `exit_price = None`, `pnl_* = None`.

### 3.5 Verdict vs. spec

| Aspect | Spec | Implementation | Match |
|---|---|---|---|
| Flip layer | swap long↔short, holds untouched | one-line conditional swap after `_stage1_candle_signal` | ✅ |
| Scope filter | applied to POST-flip direction (Q-2) | scope check runs after flip in main loop | ✅ |
| Normal SL/TP set | soft_sl + hard_sl + hard_tp | active when `flip=False` | ✅ |
| Flipped SL/TP set | soft_tp + hard_tp + hard_sl | active when `flip=True` | ✅ |
| Tie-break (normal) | hard SL > hard TP > soft SL | check order in code | ✅ |
| Tie-break (flipped) | hard TP > hard SL > soft TP (symmetric, Q-A) | check order in code | ✅ |
| Soft fill (normal) | 2nd close past line | `m_close` | ✅ |
| Soft fill (flipped) | 2nd close past line (literal mirror, Q-B) | `m_close` | ✅ |
| All four lines on trade | always populated regardless of mode | trade dict carries 4 lines + `flip` flag | ✅ |

**No deviation in exit logic.**

---

## 4. Re-entry gate

| Condition at iteration `idx` | Action |
|---|---|
| Open trade exists | skip entry decision; continue exit walk |
| Open trade is None AND `blocked_until is None` | evaluate Stage 1 signal |
| Open trade is None AND `ts_4h > blocked_until` | evaluate Stage 1 signal |
| Open trade is None AND `ts_4h ≤ blocked_until` | skip (re-entry blocked) |

After every exit: `blocked_until = exit_time`. Fresh Stage 1 evaluation per eligible 4h; no direction memory; no SL/TP differentiation in the gate.

---

## 5. Iteration timing — no look-ahead

The 4h CSV's `Date` column is the bar's **start** time (verified: 4h@18:00 Open = 1-min@18:00 Open).

**Locked interpretation (2026-05-26):** signal fires at the close of the *just-closed* bar; trade is executed at the *next* bar's start. At iteration `idx`:

- **Signal candle** = `df_4h.iloc[idx-1]` (the bar whose Close just landed).
- **Entry moment** = `df_4h.iloc[idx].Date` (the new 4h boundary; equals the previous bar's close in continuous data).
- **Entry price** = `signal_candle.Close` (the price at the boundary).
- **Exit walk** = 1-min bars in `[start_1m[idx], start_1m[idx+1])` — all chronologically *after* the signal, so no look-ahead.

Implementation detail in the trade dict: `entry_idx = idx` (the new bar that "owns" the position), `signal_idx = idx - 1` (the bar that fired the signal).

**Warm-up:** iteration `idx = 0` has no predecessor, so no signal can fire on the very first bar. This matches the spec's "first-candle warm-up" in `docs/strategy/MASTER.md §2.3`.

### Verdict

✅ No look-ahead. Verified by `test_real_data_no_lookahead_invariant`:

```python
for t in trades:
    assert t['entry_idx'] == t['signal_idx'] + 1
    if t['exit_time'] is not None:
        assert t['exit_time'] >= t['entry_time']
```

Removing the look-ahead bias on the simple engine swung total pnl from **−$1,163,360** to **+$65,555** on the same (sl_soft=100, sl_hard=200, tp=150) baseline — the look-ahead had been allowing the engine to "see" intraday volatility before the signal was actually computable, which biased exits toward hard SL hits that wouldn't have fired in live trading.

> USERNOTE: fix the system to use  ```Spec interpretation: signal fires at the close of the just-closed bar, executed at the next bar's start.** Then iteration `idx` should:
  - Use `df_4h.iloc[idx-1]`'s OHLC for the signal decision.
  - Set `entry_time = df_4h.iloc[idx].Date` (the just-arrived 4h boundary = previous bar's close).
  - Walk 1-min bars from `start_1m[idx]` onwards (the bars in the new 4h window, all of which post-date the signal).``` 
  
---

## 6. Test coverage matrix

| Branch / case | Synthetic test | Real-data lock |
|---|---|---|
| §2 row 1 (touched=false → hold) | `test_stage1_signal_hold_when_not_touched` | (implicit) |
| §2 row 2 (green LONG) | `test_stage1_signal_long_when_green_breaks_upper` | — |
| §2 row 3 (close==BU → hold) | `test_stage1_signal_hold_when_close_on_edge` | — |
| §2 row 5 (red SHORT) | `test_stage1_signal_short_when_red_breaks_lower` | — |
| §2 row 8 (doji) | `test_stage1_signal_hold_when_doji` | — |
| §2 row 9/10 mismatch | (not separately tested) | — |
| §3 LONG hard SL touch | `test_backtest_hard_sl_long_touch_fills_at_line` | `test_real_data_hard_sl_fills_at_line` |
| §3 LONG TP touch | `test_backtest_tp_long_touch_fills_at_line` | `test_real_data_tp_fills_at_line` |
| §3 SHORT hard SL | `test_backtest_short_hard_sl` | — |
| §3 soft SL fires after 2 closes | `test_backtest_soft_sl_needs_two_consecutive_closes` | `test_real_data_soft_sl_pnl_is_worse_than_line` |
| §3 soft counter reset | `test_backtest_soft_sl_counter_resets_on_recovery` | — |
| §3 tie-break hard > TP | `test_backtest_hard_sl_beats_tp_in_same_bar` | — |
| §4 re-entry gate | `test_backtest_reentry_gate_blocks_until_next_4h_start` | `test_real_data_reentry_gate_holds` |
| §3 EOF open trade | `test_backtest_open_at_eof_yields_open` | (1 of 590 trades is OPEN) |

15 real-data lock tests + 17 synthetic tests pass at sl_soft=100, sl_hard=200, tp=150.

---

## 7. Summary

- Entry logic: **exact match** with Stage 1 documentation.
- Exit logic: **exact match** with `notes.md v2` (the user-corrected version).
- Per-bar tie-break: **exact match** (hard SL > TP > soft SL).
- One open question: bar-close timing / look-ahead bias (§5). The current behaviour matches the legacy engine, but neither matches the strict "no look-ahead" reading of `MASTER.md §2`.

If §5 is the source of the "null values everywhere" symptom, this would manifest as: trades that exit on a 1-min bar **before** the 4h bar that triggered them has finished — which from the dashboard's chart perspective looks like exits are firing inside the entry-bar's window.
