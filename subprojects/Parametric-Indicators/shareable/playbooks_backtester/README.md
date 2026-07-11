# Playbooks Backtester — 55 box + indicator champions (9 markets × 6 timeframes + 1 variant)

A **self-contained, parity-locked backtester** for the box-strategy champions documented in the playbooks.
It bundles the **exact causal research engine** the live dashboard runs — so every champion reproduces its
playbook headline **to the dollar** (verified: 55/55 exact). This is not a re-implementation.

> **55 champions · 51/55 profitable out-of-sample (2026).** Each champion pairs a per-day price
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

## The 55 champions

Full write-up per champion = its **playbook PDF** (`<INST>_<TF>_playbook.pdf`). Headline numbers here match
those exactly. OOS = 2026 out-of-sample (held-out year the tuning never saw).

❌ = loses money in-sample — **do not trade**.  ⚠️ = profitable in-sample but flat/negative out-of-sample.

| Champion | Market · TF | Full P/L | Max DD | Win | 2026 OOS | #ind | cap(bars) |
|----------|-------------|---------:|-------:|----:|---------:|-----:|----------:|
| `NQ_4h` | Nasdaq-100 4h | $149,989 | $15,491 | 68% | +$58,029 | 3 | off |
| `NQ_2h` | Nasdaq-100 2h | $91,996 | $16,331 | 50% | +$19,569 | 8 | off |
| `NQ_1h` | Nasdaq-100 1h | $99,172 | $16,870 | 49% | +$19,012 | 8 | off |
| `NQ_15m` | Nasdaq-100 15m | $76,232 | $8,089 | 48% | +$29,114 | 8 | off |
| `NQ_5m` | Nasdaq-100 5m | $23,926 | $4,636 | 59% | +$5,860 | 7 | off |
| `NQ_2m` | Nasdaq-100 2m | $29,777 | $3,261 | 64% | +$7,816 | 7 | off |
| `ES_4h` | S&P 500 4h | $47,355 | $10,848 | 60% | +$19,815 | 7 | 1386 |
| `ES_2h` | S&P 500 2h | $75,692 | $6,993 | 40% | +$19,625 | 6 | 1362 |
| `ES_1h` | S&P 500 1h | $61,618 | $8,520 | 53% | +$29,035 | 8 | 696 |
| `ES_15m` | S&P 500 15m | $11,018 | $760 | 94% | +$1,218 | 9 | 1300 |
| `ES_5m` | S&P 500 5m | $7,838 | $770 | 64% | +$262 | 9 | 109 |
| `ES_2m` | S&P 500 2m | $12,587 | $1,648 | 54% | +$4,558 | 7 | 109 |
| `GC_4h` ⚠️ | Gold 4h | $57,570 | $12,800 | 66% | −$540 | 7 | 1132 |
| `GC_4h_ind4h` | Gold 4h · 4h-ind | $97,950 | $7,360 | 72% | +$22,310 | 7 | 1324 |
| `GC_2h` | Gold 2h | $23,340 | $3,200 | 57% | +$11,550 | 8 | 102 |
| `GC_1h` | Gold 1h | $39,140 | $3,130 | 30% | +$18,460 | 9 | 992 |
| `GC_15m` | Gold 15m | $10,340 | $1,880 | 70% | +$1,410 | 7 | 409 |
| `GC_5m` | Gold 5m | $15,130 | $3,790 | 71% | +$5,250 | 10 | 551 |
| `GC_2m` | Gold 2m | $30,420 | $4,400 | 61% | +$10,840 | 9 | 728 |
| `SI_4h` | Silver 4h | $21,928 | $7,452 | 30% | +$6,935 | 6 | 1377 |
| `SI_2h` | Silver 2h | $45,451 | $10,789 | 59% | +$394 | 6 | 921 |
| `SI_1h` | Silver 1h | $13,771 | $2,953 | 79% | +$364 | 5 | 448 |
| `SI_15m` | Silver 15m | $14,600 | $2,780 | 44% | +$2,349 | 8 | 1139 |
| `SI_5m` | Silver 5m | $28,735 | $3,534 | 43% | +$4,240 | 9 | 1203 |
| `SI_2m` | Silver 2m | $3,163 | $676 | 69% | +$154 | 7 | 193 |
| `HG_4h` | Copper 4h | $50,160 | $3,473 | 78% | +$19,200 | 8 | 1393 |
| `HG_2h` | Copper 2h | $25,535 | $3,880 | 59% | +$14,198 | 6 | 819 |
| `HG_1h` ⚠️ | Copper 1h | $4,970 | $1,190 | 86% | −$678 | 8 | 1300 |
| `HG_15m` | Copper 15m | $3,247 | $663 | 45% | +$925 | 6 | 752 |
| `HG_5m` ⚠️ | Copper 5m | $3,102 | $1,065 | 52% | −$240 | 7 | 544 |
| `HG_2m` | Copper 2m | $31,787 | $2,038 | 26% | +$13,688 | 7 | 45 |
| `CL_4h` | Crude Oil 4h | $21,760 | $3,990 | 48% | +$2,475 | 6 | 1051 |
| `CL_2h` | Crude Oil 2h | $10,448 | $1,098 | 60% | +$2,561 | 4 | 9 |
| `CL_1h` | Crude Oil 1h | $7,939 | $740 | 55% | +$1,436 | 9 | 9 |
| `CL_15m` | Crude Oil 15m | $15,852 | $1,021 | 29% | +$5,943 | 7 | 36 |
| `CL_5m` | Crude Oil 5m | $4,090 | $717 | 72% | +$42 | 6 | 175 |
| `CL_2m` | Crude Oil 2m | $17,775 | $911 | 46% | +$4,707 | 5 | 467 |
| `NG_4h` | Natural Gas 4h | $17,363 | $2,086 | 48% | +$5,910 | 7 | 458 |
| `NG_2h` | Natural Gas 2h | $18,112 | $2,053 | 52% | +$1,733 | 6 | 77 |
| `NG_1h` | Natural Gas 1h | $12,086 | $1,132 | 60% | +$6,183 | 10 | 1428 |
| `NG_15m` ❌ | Natural Gas 15m | $-1,635 | $3,060 | 47% | −$2,700 | 7 | 77 |
| `NG_5m` | Natural Gas 5m | $27,991 | $366 | 30% | +$8,502 | 7 | 939 |
| `NG_2m` | Natural Gas 2m | $30,294 | $230 | 40% | +$10,024 | 7 | 1128 |
| `RTY_4h` | Russell 2000 4h | $32,675 | $4,853 | 50% | +$19,677 | 8 | 992 |
| `RTY_2h` | Russell 2000 2h | $18,846 | $1,822 | 84% | +$7,580 | 8 | 458 |
| `RTY_1h` | Russell 2000 1h | $16,032 | $2,928 | 55% | +$6,539 | 6 | 897 |
| `RTY_15m` | Russell 2000 15m | $3,980 | $590 | 81% | +$1,090 | 11 | 45 |
| `RTY_5m` | Russell 2000 5m | $2,150 | $389 | 65% | +$1,390 | 10 | 168 |
| `RTY_2m` | Russell 2000 2m | $2,082 | $457 | 67% | +$1,546 | 6 | 597 |
| `YM_4h` | Dow 4h | $41,542 | $3,811 | 73% | +$15,146 | 10 | 819 |
| `YM_2h` | Dow 2h | $27,718 | $3,795 | 61% | +$9,389 | 7 | 948 |
| `YM_1h` | Dow 1h | $28,096 | $4,045 | 65% | +$6,978 | 8 | 973 |
| `YM_15m` | Dow 15m | $12,762 | $1,089 | 56% | +$310 | 7 | 109 |
| `YM_5m` | Dow 5m | $31,862 | $5,160 | 60% | +$8,732 | 7 | 1037 |
| `YM_2m` | Dow 2m | $19,406 | $1,946 | 44% | +$8,894 | 6 | 1272 |

### The 4 slots that did NOT clear the bar

- **GC_4h** — see its playbook; shipped for completeness, not for trading.
- **HG_1h** — see its playbook; shipped for completeness, not for trading.
- **HG_5m** — see its playbook; shipped for completeness, not for trading.
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
