# Playbooks Backtester — 54 box + indicator champions (9 markets × 6 timeframes + 0 variant)

A **self-contained, parity-locked backtester** for the box-strategy champions documented in the playbooks.
It bundles the **exact causal research engine** the live dashboard runs — so every champion reproduces its
playbook headline **to the dollar** (verified: 54/54 exact). This is not a re-implementation.

> **54 champions · 53/54 profitable out-of-sample (2026).** Each champion pairs a per-day price
> "box" with a K-of-N indicator confirm/veto gate, a max-hold time cap, and a drawdown circuit-breaker,
> on one instrument + decision timeframe. 1 contract; point value per instrument baked into each champion.

## Run it

```bash
pip install -r requirements.txt          # numpy, pandas

# put your CSVs for the instrument in a folder (default ./data), named as below, then:
python3 backtest.py --champion champions/GC_4h.json --data ./data --out trades_GC_4h.csv
python3 backtest.py --champion champions/GC_4h_ind4h.json --data ./data   # the 4h-indicator variant
```

Prints the summary (matching the playbook headline) and writes a per-trade CSV.

### Data you provide (one folder, CSV, one header row)

| File | What | Columns |
|------|------|---------|
| `<INST>_<tf>.csv` | decision-frame candles (e.g. `GC_4h.csv`) | `Date,Open,High,Low,Close` |
| `<INST>_1m.csv` | 1-minute candles (shared exit + indicator frame) | `Date,Open,High,Low,Close` |
| `<INST>_box.csv` | per-day box levels | `Date,<weekly/monthly level columns>` |

`INST ∈ {NQ, ES, GC, SI, HG, CL, NG, RTY, YM}`. Non-NQ box files are the **−1-workday-shifted** boxes (as onboarded).
Dates are tz-naive `YYYY-MM-DD HH:MM:SS`. Point the loader elsewhere with `--data <dir>`.

## The 54 champions

Full write-up per champion = its **playbook PDF** (`<INST>_<TF>_playbook.pdf`). Headline numbers here match
those exactly. OOS = 2026 out-of-sample (held-out year the tuning never saw).

❌ = loses money in-sample — **do not trade**.  ⚠️ = profitable in-sample but flat/negative out-of-sample.

| Champion | Market · TF | Full P/L | Max DD | Win | 2026 OOS | #ind | cap(bars) |
|----------|-------------|---------:|-------:|----:|---------:|-----:|----------:|
| `NQ_4h` | Nasdaq-100 4h | $148,670 | $12,284 | 63% | +$64,877 | 8 | 451 |
| `NQ_2h` | Nasdaq-100 2h | $91,996 | $16,331 | 50% | +$19,569 | 8 | off |
| `NQ_1h` | Nasdaq-100 1h | $77,439 | $9,144 | 52% | +$21,944 | 7 | off |
| `NQ_15m` | Nasdaq-100 15m | $76,232 | $8,089 | 48% | +$29,114 | 8 | off |
| `NQ_5m` | Nasdaq-100 5m | $23,926 | $4,636 | 59% | +$5,860 | 7 | off |
| `NQ_2m` | Nasdaq-100 2m | $29,777 | $3,261 | 64% | +$7,816 | 7 | off |
| `ES_4h` | S&P 500 4h | $68,168 | $13,552 | 61% | +$28,188 | 6 | 825 |
| `ES_2h` | S&P 500 2h | $75,692 | $6,993 | 40% | +$18,240 | 6 | 1362 |
| `ES_1h` | S&P 500 1h | $61,618 | $8,520 | 53% | +$28,193 | 8 | 696 |
| `ES_15m` | S&P 500 15m | $11,018 | $760 | 94% | +$1,218 | 9 | 1300 |
| `ES_5m` | S&P 500 5m | $5,598 | $1,108 | 80% | +$2,701 | 11 | 902 |
| `ES_2m` | S&P 500 2m | $12,632 | $1,567 | 80% | +$6,913 | 6 | 734 |
| `GC_4h` | Gold 4h | $77,875 | $17,164 | 77% | +$11,816 | 7 | off |
| `GC_2h` | Gold 2h | $81,157 | $15,649 | 51% | +$22,657 | 9 | off |
| `GC_1h` | Gold 1h | $86,969 | $21,007 | 45% | +$28,741 | 8 | off |
| `GC_15m` | Gold 15m | $80,909 | $10,097 | 67% | +$37,286 | 7 | off |
| `GC_5m` | Gold 5m | $18,126 | $4,115 | 65% | +$7,150 | 12 | 556 |
| `GC_2m` | Gold 2m | $38,639 | $4,577 | 55% | +$13,639 | 7 | 589 |
| `SI_4h` | Silver 4h | $21,928 | $7,452 | 30% | +$5,111 | 6 | 1377 |
| `SI_2h` | Silver 2h | $31,540 | $4,452 | 26% | +$5,957 | 7 | 660 |
| `SI_1h` | Silver 1h | $43,984 | $6,379 | 29% | +$15,511 | 9 | off |
| `SI_15m` | Silver 15m | $76,579 | $10,363 | 60% | +$18,139 | 6 | 702 |
| `SI_5m` | Silver 5m | $88,296 | $2,901 | 38% | +$18,663 | 8 | 820 |
| `SI_2m` | Silver 2m | $59,880 | $2,307 | 36% | +$10,452 | 5 | off |
| `HG_4h` | Copper 4h | $60,390 | $3,465 | 56% | +$22,095 | 8 | off |
| `HG_2h` | Copper 2h | $44,977 | $4,053 | 64% | +$16,030 | 10 | off |
| `HG_1h` | Copper 1h | $27,157 | $3,347 | 69% | +$3,270 | 7 | off |
| `HG_15m` | Copper 15m | $41,588 | $2,465 | 17% | +$11,268 | 6 | 110 |
| `HG_5m` | Copper 5m | $8,977 | $1,395 | 27% | +$3,072 | 7 | off |
| `HG_2m` | Copper 2m | $31,787 | $2,038 | 26% | +$13,687 | 7 | 45 |
| `CL_4h` | Crude Oil 4h | $21,925 | $3,487 | 63% | +$5,854 | 6 | off |
| `CL_2h` | Crude Oil 2h | $10,448 | $1,098 | 60% | +$3,835 | 4 | 9 |
| `CL_1h` | Crude Oil 1h | $10,546 | $1,645 | 46% | +$4,809 | 8 | 995 |
| `CL_15m` | Crude Oil 15m | $15,852 | $1,021 | 29% | +$5,764 | 7 | 36 |
| `CL_5m` | Crude Oil 5m | $13,692 | $885 | 67% | +$3,139 | 5 | off |
| `CL_2m` | Crude Oil 2m | $23,990 | $730 | 40% | +$8,008 | 0 | 412 |
| `NG_4h` | Natural Gas 4h | $21,224 | $2,576 | 56% | +$6,910 | 7 | 1031 |
| `NG_2h` | Natural Gas 2h | $17,314 | $1,739 | 42% | +$6,113 | 7 | 940 |
| `NG_1h` | Natural Gas 1h | $12,086 | $1,132 | 60% | +$6,183 | 10 | 1428 |
| `NG_15m` ❌ | Natural Gas 15m | $-1,635 | $3,060 | 47% | −$2,775 | 7 | 77 |
| `NG_5m` | Natural Gas 5m | $27,991 | $366 | 30% | +$7,938 | 7 | 939 |
| `NG_2m` | Natural Gas 2m | $30,294 | $230 | 40% | +$9,758 | 7 | 1128 |
| `RTY_4h` | Russell 2000 4h | $36,688 | $9,092 | 49% | +$23,872 | 5 | 941 |
| `RTY_2h` | Russell 2000 2h | $18,846 | $1,822 | 84% | +$7,417 | 8 | 458 |
| `RTY_1h` | Russell 2000 1h | $16,032 | $2,928 | 55% | +$6,539 | 6 | 897 |
| `RTY_15m` | Russell 2000 15m | $10,697 | $1,351 | 54% | +$3,900 | 7 | off |
| `RTY_5m` | Russell 2000 5m | $21,201 | $2,145 | 60% | +$6,484 | 6 | 255 |
| `RTY_2m` | Russell 2000 2m | $3,649 | $831 | 61% | +$1,627 | 10 | 472 |
| `YM_4h` | Dow 4h | $51,917 | $9,126 | 56% | +$34,921 | 5 | 719 |
| `YM_2h` | Dow 2h | $20,573 | $1,434 | 78% | +$11,111 | 12 | off |
| `YM_1h` | Dow 1h | $47,341 | $4,490 | 50% | +$12,527 | 4 | off |
| `YM_15m` | Dow 15m | $16,407 | $1,509 | 68% | +$3,511 | 9 | off |
| `YM_5m` | Dow 5m | $31,862 | $5,160 | 60% | +$8,732 | 7 | 1037 |
| `YM_2m` | Dow 2m | $28,716 | $2,383 | 59% | +$10,533 | 10 | off |

### The 1 slots that did NOT clear the bar

- **NG_15m** — see its playbook; shipped for completeness, not for trading.

They are included so the record is honest and reproducible, **not** because they are tradeable. The engine
reproduces their (bad) numbers exactly, which is the point.

**GC_4h_ind4h** is the 4-hour-indicator variant (indicators on the 4-hour frame, `ind_1min=false`) — the
high-timeframe winner from the 1-min-vs-4h comparison: **+$97,950 / +$22,310 OOS** vs the deployed 1-minute
GC 4h (+$57,570 / −$540). The dashboard hard-codes the 1-minute frame, so it is not served by default.

## What each champion carries

`champions/<name>.json` → `{id, instrument, timeframe, label, preset}`. The `preset` is the exact object the
dashboard sends: box risk knobs (`sl_soft/sl_hard/tp/gate_pct/dd_limit/cooldown/flip/k`), the max-hold time
cap (`cap_1min` + `cap_mode`), the indicator frame (`ind_1min`), the full indicator spec list (each with its
enabled flag, fixed mode, and tuned internals), and the instrument point value (`pv`).

## Notes

- Numbers match the dashboard's **causal L1 view** (the playbook headline). NQ champions run capless; every
  non-NQ champion uses an active max-hold time cap, which the causal engine applies.
- `--insample-year` is fixed to 2025 (the volatility-gate percentile is frozen on 2025 bars, causally).
- Bundle ships the engine only — you provide your own market data.

---
_Author: **Mulham Fetna** · contact@mulhamfetna.com · ORCID [0009-0006-4432-798X](https://orcid.org/0009-0006-4432-798X)
· github.com/mulhamfetna_
