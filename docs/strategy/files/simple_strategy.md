---
name: simple_strategy
description: Simple backtest engine — Stage 1 entry + dual-SL/TP exit on 1-min bars. Sibling of BoxStrategy.
type: file
---

# `src/strategy/simple_strategy.py`

Sibling engine to [[box_strategy]] / [[scaling_strategy]]. Same project, same data, different ruleset. **Stage 1's per-candle rule is the canonical entry decision**; the simple engine is a thin SL/TP exit layer on top.

The two engines coexist; the old one is unchanged. Pick by hitting the right endpoint (`/api/backtest/box` vs `/api/backtest/simple`) or by passing the right strategy class into the harness.

---

## 1. What it does, in one sentence

At every 4h boundary, evaluate Stage 1's truth table on the **just-closed** 4h bar (no look-ahead — the bar's full OHLC is only available at its close); if it fires `long` or `short`, open a 1-contract trade at the *next* bar's start at the just-closed bar's close price; walk 1-min bars in the new window and close on **hard SL** (1-min extreme touches the hard line) / **TP** (extreme touches TP line) / **soft SL** (two consecutive 1-min closes past the soft line); re-evaluate the next 4h candle whose start is strictly after the exit time.

---

## 2. Exit lines — three lines, two semantics

The user's "mimic real live data stream" model:

| Line | Fire rule | Fill price | Pnl shape |
|---|---|---|---|
| **Soft SL** (closer to entry) | 2 consecutive 1-min **closes** past the soft line | the **2nd close** (worse than the line) | `\|pnl\| ≥ sl_soft_points` always |
| **Hard SL** (farther; `sl_hard ≥ sl_soft`) | 1-min bar **extreme** touches the hard line | **the hard line** | exactly `-sl_hard_points` |
| **TP** | 1-min bar **extreme** touches the TP line | **the TP line** | exactly `+tp_points` |

For a long: `sl_soft_line = entry − sl_soft_points`, `sl_hard_line = entry − sl_hard_points`, `tp_line = entry + tp_points`. The "extreme" is `low` for the hard SL check and `high` for the TP check. Short is mirrored: hard SL above entry watches the bar's `high`, TP below entry watches the `low`, soft SL above entry watches the `close`.

### Per-bar tie-break

Priority when multiple could fire in the same 1-min bar: **hard SL > TP > soft SL**. Reasoning:

- Hard SL and TP are intra-bar touch events; their exact intra-minute order is unknown from OHLC alone. Under pessimistic resolution, the loss-side touch fires first.
- Soft SL fires at bar close, which is the last temporal event in the bar.

In actual data (sl_soft=100, sl_hard=200, tp=150) hard-SL+TP same-bar collisions are essentially zero — see §8 R3 analysis.

---

## 3. What changed vs. `BoxStrategy`

| Concern | `BoxStrategy` (old) | `SimpleStrategy` (new) |
|---|---|---|
| Entry direction | stateful `above/inside/below` traversal state machine per (candle, level pair) | Stage 1 truth table — stateless, per-candle, per-(level pair) |
| Multi-level collapse on a single 4h | weekly priority then monthly | **any-long → long, any-short → short, else hold** |
| Big-candle override | yes | **removed** |
| Position sizing | 1-1-2 ladder (up to 4 contracts) | **1 contract** |
| Anchor for SL/TP lines | toggle `anchor_mode ∈ {base, average}` | **fixed at entry price** (the 4h close) |
| Soft SL | 2 consecutive 1-min closes past, fill at 2nd close | **kept** |
| Hard SL | 1-min close past, fill at line | **changed to touch detection** (1-min extreme), fill at line |
| TP | dual-timeframe sub-bar engine | **simple touch detection**, fill at line |
| Direction-flip exit | yes | **removed** |
| Re-entry control | `reentry_cooldown_candles` | **time-based gate** |

Net effect: ~280 lines of decision logic where the old engine has ~700.

---

## 4. The entry rule (Stage 1, candle-level)

Per-(level pair):

```
if NOT touched:                            signal = hold
elif color == green AND close > BU:        signal = long
elif color == red   AND close < BL:        signal = short
else:                                       signal = hold
```

Per-candle (collapse across all active level pairs on the candle's mapped box-date):

```
candle_signal =
    'long'  if any pair fired long
    'short' if any pair fired short
    'hold'  otherwise
```

Stage 1's color rule guarantees a single candle cannot fire both long and short simultaneously.

---

## 5. The re-entry gate

On exit, store `blocked_until = exit_time`. The next 4h candle is signal-eligible iff `candle.Date > blocked_until`.

Worked example: trade opens at the close of 4h X (`Date = 2025-01-01 18:00`), hard SL fires at `19:10` inside X. `blocked_until = 19:10`. The next 4h candle (`Date = 22:00`) starts at 22:00, strictly after 19:10 → eligible. Stage 1 evaluates the close of that candle fresh; if `hold` we wait, if `long`/`short` we open immediately — regardless of the prior trade's direction or exit reason.

Stage 1's rule is **per closed candle**, so the engine never evaluates a partial 4h.

---

## 6. Public API

```python
@dataclass
class SimpleStrategyParams:
    sl_soft_points: float                                # > 0
    sl_hard_points: float                                # >= sl_soft_points
    tp_points:      float                                # > 0
    data_path_4h:   str
    data_path_1min: str
    box_data_path:  str
    direction_scope: Literal['both', 'long_only', 'short_only'] = 'both'


class SimpleStrategy:
    NQ_POINT_VALUE = 20.0
    def __init__(self, params: SimpleStrategyParams): ...
    def backtest(
        self,
        df_4h:           pd.DataFrame,
        df_1min:         pd.DataFrame,
        box_df_indexed:  pd.DataFrame,
    ) -> Tuple[List[Dict], Dict]:
        """Returns (trades, final_state)."""
```

**Trade dict schema:**

```python
{
    'entry_idx':    int,                  # the 4h bar the trade is OPEN in (signal_idx + 1)
    'signal_idx':   int,                  # the just-closed 4h bar that fired the signal
    'entry_time':   pd.Timestamp,         # entry_idx's Date (= signal bar's close)
    'entry_price':  float,                # = signal bar's close
    'direction':    'long' | 'short',
    'sl_soft_line': float,
    'sl_hard_line': float,
    'tp_line':      float,
    'exit_time':    pd.Timestamp | None,
    'exit_price':   float | None,
    'exit_reason':  'TAKE_PROFIT' | 'STOP_LOSS_HARD' | 'STOP_LOSS_SOFT' | 'OPEN',
    'pnl_points':   float | None,
    'pnl_dollars':  float | None,
}
```

---

## 7. HTTP endpoint

`POST /api/backtest/simple`. Synchronous JSON (no SSE — engine runs in ~1–2 seconds on the full preset).

Request body: `SimpleBacktestRequest` (Pydantic, `src/api/schemas.py`).

Response shape:

```json
{
  "summary": {
    "n_trades":           590,
    "n_take_profit":       94,
    "n_stop_loss":        495,
    "n_stop_loss_hard":   152,
    "n_stop_loss_soft":   343,
    "n_open_at_eof":        1,
    "total_pnl_dollars": -1163360.0,
    "total_pnl_points":  -58168.0,
    "win_rate":          ...
  },
  "trades": [ /* trade dicts with Timestamps serialised as ISO strings */ ]
}
```

---

## 8. Locked counts (`full` preset, sl_soft=100, sl_hard=200, tp=150)

Regression-pinned in `tests/test_simple_strategy.py`:

| Metric | Value |
|---|---|
| Total trades | 594 |
| `STOP_LOSS_HARD` | 8 |
| `STOP_LOSS_SOFT` | 315 |
| `TAKE_PROFIT` | 271 |
| `OPEN` (open at EOF) | 0 |
| Total pnl $ | **+65,555** |

Pnl is positive even without parameter tuning — the no-look-ahead timing (signal from the just-closed bar; entry at the next bar's start) keeps the exit walk on bars chronologically after the signal. The optimizer will find better params; this baseline is just to lock the rule semantics.

### R3 analysis (hard SL + TP touch in same bar)

Theoretical concern: a single 1-min bar can span both the TP line above and the hard SL line below an entry. Empirical sweep across (sl_soft, sl_hard, tp) combos shows R3 events at 0 or 1 per backtest at realistic params; at absurdly tight `sl=tp=10` it peaks at 4 events in 829 trades (0.48%). The hard-SL > TP tie-break handles them consistently.

---

## 9. Implementation status

| Item | Status |
|---|---|
| `simple_strategy.py` engine | ✅ done |
| Dual-SL/TP exit semantics (soft close-past + hard touch + TP touch) | ✅ done |
| Synthetic + real-data tests (31 total) | ✅ done — all green |
| Pydantic schema `SimpleBacktestRequest` (with `sl_hard >= sl_soft` validator) | ✅ done |
| `POST /api/backtest/simple` endpoint | ✅ done |
| Optimizer re-target (TBD: single-objective vs two-objective Pareto) | ⏳ follow-up |
| Frontend wiring (toggle simple vs box, dual-SL inputs) | ⏳ follow-up |

---

## 10. Wired to

- [[truth_table]] supplies the entry rule.
- [[simple_engine_truth_table]] is the formal entry + exit decision-table reference.
- [[box_lookup]] supplies box geometry (`_LEVEL_PAIRS`, `_candle_to_box_date`). The simple engine reuses these constants but does not invoke `BoxLookup.get_signal()` — the stateful state machine is intentionally bypassed.

---

## 11. What it does NOT do

- Multiple concurrent positions (one open trade at a time).
- Position sizing > 1 contract.
- Ladder / scaling / averaging.
- Big-candle override.
- Direction-flip exits.
- Trail mechanism.
- Modify the box CSV, Stage 1 outputs, or the old engine.
