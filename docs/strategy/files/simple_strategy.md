---
name: simple_strategy
description: Simple backtest engine — Stage 1 entry + 1-min SL/TP exit. Sibling of BoxStrategy.
type: file
---

# `src/strategy/simple_strategy.py`

Sibling engine to [[box_strategy]] / [[scaling_strategy]]. Same project, same data, different ruleset. Built per `backtest_updates.md` after the truth-table reconciliation resolved that **Stage 1's rule wins** for entry direction.

The two engines coexist; the old one is unchanged. Pick by hitting the right endpoint (`/api/backtest/box` vs `/api/backtest/simple`) or by passing the right strategy class into the harness.

---

## 1. What it does, in one sentence

For each 4h candle, evaluate Stage 1's per-candle truth table; if it fires `long` or `short`, open a 1-contract trade at the candle's close; walk 1-min bars and close on the first 1-min `close` that crosses TP or SL; re-evaluate the next 4h candle whose start is strictly after the exit time.

---

## 2. What changed vs. `BoxStrategy`

| Concern | `BoxStrategy` (old) | `SimpleStrategy` (new) |
|---|---|---|
| Entry direction | stateful `above/inside/below` traversal state machine per (candle, level pair) | Stage 1 truth table — stateless, per-candle, per-(level pair) |
| Multi-level collapse on a single 4h | weekly priority then monthly | **any-long → long, any-short → short, else hold** |
| Big-candle override | yes (`big_candle_threshold_points`, `big_candle_resolution`) | **removed** |
| Position sizing | 1-1-2 ladder (up to 4 contracts) | **1 contract** |
| Anchor for SL/TP lines | toggle `anchor_mode ∈ {base, average}` | **fixed at entry price** (the 4h close) |
| Soft SL | 2 consecutive 1-min closes past the line | **single SL** — 1 close past |
| Hard SL | separate 1-min close past the hard line | **gone** — single SL only |
| TP fire condition | dual-timeframe sub-bar engine | **1-min close past the TP line** |
| Exit fill price | line price (idealised) | **the 1-min close that triggered** (slippage-realistic) |
| Direction-flip exit | yes (`DIRECTION_FLIP` reason) | **removed** — SL/TP are the only exits |
| Re-entry control | `reentry_cooldown_candles` counter | **time-based gate**: next 4h candle whose `Date > exit_time` |
| Trail mechanism | already removed in §9 prior work | n/a |

Net effect: ~150 lines of decision logic where the old engine has ~700.

---

## 3. The entry rule (delegated to Stage 1)

The simple engine **does not reimplement** Stage 1. It mirrors the rule inline (`_stage1_candle_signal`) but the canonical reference lives at `subprojects/signals/truth_table.md` and is also documented as [[truth_table]] in this tree.

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

## 4. The exit rule

Anchor at entry: `entry_price = candle.close`.

```
long  position:  tp_line = entry_price + tp_points
                 sl_line = entry_price - sl_points
short position:  tp_line = entry_price - tp_points
                 sl_line = entry_price + sl_points
```

Walk 1-min bars whose `Date >= entry_time`. For each `m`:

```
long:   if m.close >= tp_line: exit TAKE_PROFIT at m.close
        if m.close <= sl_line: exit STOP_LOSS  at m.close
short:  if m.close <= tp_line: exit TAKE_PROFIT at m.close
        if m.close >= sl_line: exit STOP_LOSS  at m.close
```

**A single close cannot fire both** under the close-past rule (`sl_line < entry_price < tp_line` for long; opposite for short). So the tie-break case from the plan (R3) is structurally impossible.

`pnl_points`:
- long  → `exit_price - entry_price`
- short → `entry_price - exit_price`

`pnl_dollars = pnl_points * NQ_POINT_VALUE` (20.0).

If EOF arrives with a trade open, emit it with `exit_reason='OPEN'`, `exit_time=None`, `pnl=None`.

---

## 5. The re-entry gate

On exit, store `blocked_until = exit_time`. The next 4h candle is signal-eligible iff `candle.Date > blocked_until`.

Worked example: trade opens at the close of 4h X (`Date = 2025-01-01 18:00`), SL fires at `19:10` inside X. `blocked_until = 19:10`. The next 4h candle (`Date = 22:00`) starts at 22:00, which is strictly after 19:10 → eligible. If Stage 1 says `hold` at the close of that candle, we wait one more; if `long`/`short`, we open immediately — regardless of the prior trade's direction or exit reason.

Stage 1's rule is **per closed candle**, so the engine never evaluates a partial 4h.

---

## 6. Public API

```python
@dataclass
class SimpleStrategyParams:
    sl_points: float                                    # > 0
    tp_points: float                                    # > 0
    data_path_4h: str
    data_path_1min: str
    box_data_path: str
    direction_scope: Literal['both', 'long_only', 'short_only'] = 'both'


class SimpleStrategy:
    NQ_POINT_VALUE = 20.0
    def __init__(self, params: SimpleStrategyParams): ...
    def backtest(
        self,
        df_4h:           pd.DataFrame,
        df_1min:         pd.DataFrame,
        box_df_indexed:  pd.DataFrame,   # indexed on normalised Date
    ) -> Tuple[List[Dict], Dict]:
        """Returns (trades, final_state)."""
```

**Trade dict schema:**

```python
{
    'entry_idx':   int,                  # df_4h row index
    'entry_time':  pd.Timestamp,         # 4h close that fired the signal
    'entry_price': float,                # = candle.close
    'direction':   'long' | 'short',
    'tp_line':     float,
    'sl_line':     float,
    'exit_time':   pd.Timestamp | None,  # None for OPEN
    'exit_price':  float | None,         # 1-min close that triggered
    'exit_reason': 'TAKE_PROFIT' | 'STOP_LOSS' | 'OPEN',
    'pnl_points':  float | None,
    'pnl_dollars': float | None,
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
    "n_trades":          604,
    "n_take_profit":      87,
    "n_stop_loss":       516,
    "n_open_at_eof":       1,
    "total_pnl_dollars": -1455105.0,
    "total_pnl_points":  -72755.25,
    "win_rate":          0.144
  },
  "trades": [ /* trade dicts with Timestamps serialised as ISO strings */ ]
}
```

---

## 8. Locked counts (`full` preset, sl=100, tp=150)

Regression-pinned in `tests/test_simple_strategy.py`:

| Metric | Value |
|---|---|
| Total trades | 604 |
| `STOP_LOSS` | 516 |
| `TAKE_PROFIT` | 87 |
| `OPEN` (open at EOF) | 1 |
| long anchors | 312 |
| short anchors | 292 |
| First trade | `2025-01-01 18:00:00` long @ 21322.25 → SL `2025-01-01 19:10:00` (pnl_points = −104.5) |
| Total pnl $ | −1,455,105 |

These are the values for the **arbitrary** `(sl=100, tp=150)` baseline. The pnl is negative because the params weren't tuned — finding the params that don't lose money is the whole point of the planned NSGA-II re-target.

---

## 9. Implementation status

| Item | Status |
|---|---|
| `simple_strategy.py` engine | ✅ done — `dev` commit `f44a635` |
| Synthetic + real-data tests (26 total) | ✅ done — all green |
| Pydantic schema `SimpleBacktestRequest` | ✅ done |
| `POST /api/backtest/simple` endpoint | ✅ done |
| Re-target NSGA-II / single-objective search | ⏳ follow-up — see plan §4 P4 |
| Frontend wiring (toggle simple vs box) | ⏳ follow-up |
| Deprecation of old engine | ⏳ TBD — both engines coexist for now |

---

## 10. Wired to

- [[truth_table]] supplies the entry rule.
- [[box_lookup]] supplies box geometry (`_LEVEL_PAIRS`, `_candle_to_box_date`). The simple engine reuses these constants but does not invoke `BoxLookup.get_signal()` — the stateful state machine is intentionally bypassed.
- Plan: `docs/superpowers/plans/2026-05-26-simple-backtest.md`.
- Decisions wizard: `docs/superpowers/specs/2026-05-26-simple-backtest/notes.md`.
- Original requirement: `backtest_updates.md`.

---

## 11. What it does NOT do

- Multiple concurrent positions (one open trade at a time).
- Position sizing > 1 contract.
- Ladder / scaling / averaging.
- Big-candle override.
- Direction-flip exits.
- Soft-SL / hard-SL split.
- Trail mechanism.
- Touch-based fills (close-based only).
- Modify the box CSV, Stage 1 outputs, or the old engine.
