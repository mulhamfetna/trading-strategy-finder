---
name: truth_table
description: Full decision matrix for the Stage 1 rule — (candle color × touch × close-vs-edge) → signal
type: reference
---

# Stage 1 truth table

The complete decision matrix the rule encodes. See [[signals-master]] §2 for the prose version and [[generate_stage1]] for the implementation.

## Inputs per evaluation

For one (candle, box) pair:

| Symbol | Meaning |
|---|---|
| `O`, `H`, `L`, `C` | candle open / high / low / close |
| `BU`, `BL` | box upper / lower edge |
| `color` | `green` if `C > O`, `red` if `C < O`, `doji` if `C == O` |
| `touched` | `(L <= BU) AND (H >= BL)` — inclusive range overlap |

## Decision matrix

| # | `touched` | `color` | `C` vs `BU` | `C` vs `BL` | Result |
|---|---|---|---|---|---|
| 1 | false | any | any | any | **hold** (range miss) |
| 2 | true | `green` | `C > BU` | — | **long** |
| 3 | true | `green` | `C == BU` | — | **hold** (strict close) |
| 4 | true | `green` | `C < BU` | — | **hold** (close didn't break upper) |
| 5 | true | `red` | — | `C < BL` | **short** |
| 6 | true | `red` | — | `C == BL` | **hold** (strict close) |
| 7 | true | `red` | — | `C > BL` | **hold** (close didn't break lower) |
| 8 | true | `doji` | any | any | **hold** (color required) |
| 9 | true | `red` | `C > BU` | — | **hold** (color/direction mismatch) |
| 10 | true | `green` | — | `C < BL` | **hold** (color/direction mismatch) |

Rows 9 and 10 are practically rare — they require a candle that opened on one side of the box and closed all the way past the *opposite* side, which contradicts the color (e.g., green = `C > O`, but `C < BL ≤ BU ≤ O`).

## Special cases also covered

| Scenario | Resolved by row(s) | Result |
|---|---|---|
| Candle entirely above box (`L > BU`) | 1 | **hold** |
| Candle entirely below box (`H < BL`) | 1 | **hold** |
| Touch on edge (`H == BL` or `L == BU` exactly) | counts as touched (inclusive) | continue to color check |
| Close on edge (`C == BU` or `C == BL` exactly) | 3 / 6 | **hold** (strict close) |
| Doji touched and close beyond edge | 8 | **hold** |
| Dual touch (`L ≤ BU` and `H ≥ BU`, candle straddles box) | continue per color | normal evaluation |

## Multi-box per candle

The matrix above is evaluated independently for every active level pair on the candle's mapped box-date row. See [[signals-master]] §3 "Row fan-out per candle".
