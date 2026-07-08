# Playbooks Backtester — 37 box + indicator champions (6 markets × 6 timeframes + 1 variant)

A **self-contained, parity-locked backtester** for the box-strategy champions documented in the playbooks.
It bundles the **exact causal research engine** the live dashboard runs — so every champion reproduces its
playbook headline **to the dollar** (verified: 37/37 exact). This is not a re-implementation.

> **37 champions · 36/37 profitable out-of-sample (2026).** Each champion pairs a per-day price
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

`INST ∈ {NQ, ES, GC, SI, RTY, YM}`. Non-NQ box files are the **−1-workday-shifted** boxes (as onboarded).
Dates are tz-naive `YYYY-MM-DD HH:MM:SS`. Point the loader elsewhere with `--data <dir>`.

## The 37 champions

Full write-up per champion = its **playbook PDF** (`<INST>_<TF>_playbook.pdf`). Headline numbers here match
those exactly. OOS = 2026 out-of-sample (held-out year the tuning never saw).

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
| `GC_4h` | Gold 4h | $57,570 | $12,800 | 66% | −$540 | 7 | 1132 |
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
