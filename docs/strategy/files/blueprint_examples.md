---
name: blueprint_examples
description: tests/test_blueprint_examples.py — regression lock for the dual-timeframe master strategy on January 2025 NQ data
type: file
---

# test_blueprint_examples.py

Locked regression test for the strategy as implemented by [[box_strategy]] + [[scaling_strategy]] + [[box_lookup]].

## What it pins

Runs the engine on the real `NQ_4h.csv` + `NQ_full_data.csv` + `NQ_1m.csv` datasets over January 2025 with reference parameters and asserts:

- Every field of four representative trades (entry/exit indexes, prices, contracts, P/L, exit reasons, box signals).
- The total trade count for the month.

Any deviation from the inlined numbers = the engine or the dataset has drifted.

## Reference parameters

```
sl_soft = 10.0
sl_hard = 15.0
tp_target = 150.25
box_data_path = NQ_full_data.csv
```

## Regenerated post-trail-removal (current locked state)

After trail removal per [[strategy-master]] §4, the four representative trades are:

| Example | Entry idx | Direction | Exit reason | Exit price | Profit pts |
|---|---|---|---|---|---|
| 1 | 10 | long | `STOP LOSS (SOFT)` | 21497.25 | −12.00 |
| 2 | 62 | short | `STOP LOSS (HARD)` | 21305.50 | −15.00 |
| 3 | 101 | long (big-candle) | `TAKE PROFIT` | 21037.00 | +150.25 |
| 4 | 115 | short | `STOP LOSS (HARD)` | 21482.25 | −15.00 |

Total trade count for January 2025: **7** (unchanged).

The fixture is locked against the `anchor_mode='base'` engine. Re-locking against `anchor_mode='average'` would shift Examples 3's TP timing slightly (avg = base for single-leg trades and big-candle 4-contract trades, so no difference for the locked examples) but is not currently asserted.
