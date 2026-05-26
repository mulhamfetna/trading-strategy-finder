# Stage 1 — signal truth table

The complete decision matrix that produces the `signal` column in `signals_{preset}.csv`.

## Symbols

| Symbol | Meaning |
|---|---|
| `O` | candle open |
| `H` | candle high |
| `L` | candle low |
| `C` | candle close |
| `BU` | `box_upper` (upper edge of the level pair) |
| `BL` | `box_lower` (lower edge of the level pair) |

## Derived inputs

| Name | Definition |
|---|---|
| `color` | `green` if `C > O`, `red` if `C < O`, `doji` if `C == O` |
| `touched` | `(L <= BU)` AND `(H >= BL)` — inclusive range overlap |

## Decision matrix

| # | `touched` | `color` | `C` vs `BU` | `C` vs `BL` | Result | Note |
|---|---|---|---|---|---|---|
| 1 | false | any | any | any | **hold** | range miss — candle and box don't overlap |
| 2 | true | green | `C > BU` | — | **long** | canonical LONG branch |
| 3 | true | green | `C == BU` | — | **hold** | strict close — equality on upper edge is hold |
| 4 | true | green | `C < BU` | — | **hold** | close didn't break upper edge |
| 5 | true | red | — | `C < BL` | **short** | canonical SHORT branch |
| 6 | true | red | — | `C == BL` | **hold** | strict close — equality on lower edge is hold |
| 7 | true | red | — | `C > BL` | **hold** | close didn't break lower edge |
| 8 | true | doji | any | any | **hold** | color is required — `C == O` is always hold |
| 9 | true | red | `C > BU` | — | **hold** | color/direction mismatch (rare) |
| 10 | true | green | — | `C < BL` | **hold** | color/direction mismatch (rare) |

## Only two branches produce a non-hold signal

- **LONG** ← row 2: `touched AND green AND C > BU`
- **SHORT** ← row 5: `touched AND red AND C < BL`

Every other combination — including no-box-row, range miss, close-on-edge, doji, and color/direction mismatch — collapses to `hold`.

## Per-candle row fan-out

The matrix is evaluated **independently** for every active level pair on the candle's mapped box-date row. A candle with K active level pairs produces K rows in the output (or 1 hold row with NaN box columns if K = 0).

## Equivalent pseudocode

```
if NOT touched:
    signal = hold
elif color == green AND C > BU:
    signal = long
elif color == red AND C < BL:
    signal = short
else:
    signal = hold
```

This is the exact rule implemented in `_emit_rows` in `generate_stage1.py`.
