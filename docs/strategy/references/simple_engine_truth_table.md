---
name: simple_engine_truth_table
description: Formal truth table for the simple engine — entry decision (Stage 1) and exit decision (dual-SL + TP). Audit against backtest_updates.md and the v2 notes.md.
type: reference
---

# Simple engine — entry & exit truth tables

Audit document for `src/strategy/simple_strategy.py` against `backtest_updates.md` and the locked v2 decisions in `docs/superpowers/specs/2026-05-26-simple-backtest/notes.md`.

The simple engine is **two coupled state machines**: an entry decision per closed 4h candle and an exit decision per 1-min bar of an open trade. This document writes out both as formal decision tables and flags every place where the implementation might deviate from the spec.

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

**Touch detection lives here, and only here.** Hard SL and TP fire when the bar's *extreme* (`H` for shorts' SL / longs' TP, `L` for longs' SL / shorts' TP) crosses a single line. Soft SL is the one exit that is *not* touch-based — it fires on `close` past the line, twice in a row. The entry decision in §2 never uses any of this.


### 3.1 The three lines

For a position opened at `entry_price` with params `(sl_soft_points, sl_hard_points, tp_points)` where `sl_hard ≥ sl_soft`:

| Line | Long position | Short position |
|---|---|---|
| `sl_soft_line` | `entry − sl_soft_points` (below) | `entry + sl_soft_points` (above) |
| `sl_hard_line` | `entry − sl_hard_points` (below, deeper) | `entry + sl_hard_points` (above, deeper) |
| `tp_line` | `entry + tp_points` (above) | `entry − tp_points` (below) |

### 3.2 Per-bar decision for a LONG position

Given a 1-min bar with `m.high`, `m.low`, `m.close` and a running `soft_consec_count`:

| # | hard touched? | TP touched? | soft close past? | action | fill price | soft counter |
|---|---|---|---|---|---|---|
| 1 | `m.low ≤ sl_hard_line` | (irrelevant) | (irrelevant) | exit **STOP_LOSS_HARD** | `sl_hard_line` | reset to 0 |
| 2 | no | `m.high ≥ tp_line` | (irrelevant) | exit **TAKE_PROFIT** | `tp_line` | reset to 0 |
| 3 | no | no | `m.close ≤ sl_soft_line` AND counter+1 ≥ 2 | exit **STOP_LOSS_SOFT** | `m.close` | reset to 0 |
| 4 | no | no | `m.close ≤ sl_soft_line` AND counter+1 < 2 | continue (arm soft) | — | `counter += 1` |
| 5 | no | no | `m.close > sl_soft_line` | continue | — | `counter := 0` |

### 3.3 Per-bar decision for a SHORT position (mirror)

| # | hard touched? | TP touched? | soft close past? | action | fill price | soft counter |
|---|---|---|---|---|---|---|
| 1 | `m.high ≥ sl_hard_line` | — | — | exit **STOP_LOSS_HARD** | `sl_hard_line` | reset |
| 2 | no | `m.low ≤ tp_line` | — | exit **TAKE_PROFIT** | `tp_line` | reset |
| 3 | no | no | `m.close ≥ sl_soft_line` AND counter+1 ≥ 2 | exit **STOP_LOSS_SOFT** | `m.close` | reset |
| 4 | no | no | `m.close ≥ sl_soft_line` AND counter+1 < 2 | arm soft | — | `counter += 1` |
| 5 | no | no | `m.close < sl_soft_line` | continue | — | `counter := 0` |

### 3.4 Tie-break

Priority **hard SL > TP > soft SL** (rows 1 > 2 > 3 above) — the row order in the table IS the implementation's check order.

Rationale (from notes.md v2): hard SL and TP are intra-bar touch events with unknown intra-minute timing — under pessimism we resolve the loss-side touch first. Soft SL fires at bar close, which is the last temporal event in the bar, so it's the lowest priority.

### 3.5 PnL formula

- `long`:  `pnl_points = exit_price − entry_price`
- `short`: `pnl_points = entry_price − exit_price`
- `pnl_dollars = pnl_points × 20.0` (NQ point value)

OPEN trades (still open at EOF): `exit_time = None`, `exit_price = None`, `pnl_* = None`.

### 3.6 Verdict vs. documentation

| Aspect | Spec (notes.md v2) | Implementation | Match |
|---|---|---|---|
| Soft SL fire | 2 consecutive 1-min CLOSES past line | `soft_consec_count` increments on close past, fires at `>= 2` | ✅ |
| Soft SL fill | the 2nd close (worse than line) | `m_close` | ✅ |
| Soft SL counter | resets on a non-past close | `else: soft_consec_count = 0` | ✅ |
| Hard SL fire | bar EXTREME touches line | `m_low <= sh` (long) / `m_high >= sh` (short) | ✅ |
| Hard SL fill | line itself | `sh` | ✅ |
| TP fire | bar EXTREME touches line | `m_high >= tp` (long) / `m_low <= tp` (short) | ✅ |
| TP fill | line itself | `tp` | ✅ |
| Tie-break | hard SL > TP > soft SL | check order in code | ✅ |

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

## 5. ⚠️ Audit findings — possible timing/look-ahead question

The 4h CSV's `Date` column is the bar's **start** time (verified: 4h@18:00 Open = 1-min@18:00 Open).

The engine processes each 4h candle in the iteration loop and uses `candle.Close` to fire the entry signal. The trade's `entry_time` is set to `candle.Date` (the 4h start).

**That means:**

- Signal at iteration `idx` is computed from `candle.Close`, which in real time is only available at the bar's END (e.g., 22:00 for the 18:00 bar).
- But `entry_time` is recorded as the bar's START (18:00).
- The exit walk for the same iteration starts at `start_1m[idx]` (1-min bars from 18:00), so the engine immediately scans the 1-min bars **within the same 4h window that produced the signal**.

This means a trade can "exit" before the 4h candle that produced its signal would have actually closed in live trading. **It is a look-ahead bias** if `Date` is taken literally as the entry moment.

Two reconciliations are possible:

- **(a) Spec interpretation: signal fires at the close of the just-closed bar, executed at the next bar's start.** Then iteration `idx` should:
  - Use `df_4h.iloc[idx-1]`'s OHLC for the signal decision.
  - Set `entry_time = df_4h.iloc[idx].Date` (the just-arrived 4h boundary = previous bar's close).
  - Walk 1-min bars from `start_1m[idx]` onwards (the bars in the new 4h window, all of which post-date the signal).
- **(b) Treat `Date` as a label, not chronology.** The engine pretends "at iteration `idx` I have bar `idx`'s full OHLC and 1-min bars from its start onwards." This is the **current** implementation. The legacy `BoxStrategy` does the same thing.

Both engines (box and simple) use interpretation **(b)** today. If the user's intent is **(a)** (no look-ahead), both engines need the same one-iteration shift.

**This question is not resolved in the docs.** `backtest_updates.md` says "for entry we are watching 4 hours candle" — which is consistent with both interpretations. The MASTER.md spec says explicitly "no look-ahead" but doesn't translate that to code timing.

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
