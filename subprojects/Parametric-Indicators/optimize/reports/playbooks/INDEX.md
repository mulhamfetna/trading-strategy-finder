# Shareable Playbooks — 9 markets × 6 timeframes (54 + 1 variant = 55)

_Numbers captured live from the dashboard UI (on-screen `meta.boxes` = truth); 2026 out-of-sample from the
held-out 2026 backtest. Every champion is reproduced to the dollar by the shareable backtester bundle._

**44 Deployable ✓ · 9 Caution ⚠ · 2 Non-feasible ✗ · 51/55 profitable out-of-sample (2026).**

Each `<INST>_<TF>_playbook.pdf` is a self-contained pageless PDF: verdict, what-it-is, copy-paste champion
settings, how-it-trades (Mermaid), full tearsheet + embedded dashboard snapshot, 2026 out-of-sample, and
honest when-NOT-to-trade guidance.

| Playbook | Market | Verdict | Full P/L | Max DD | Win | 2026 OOS | Flags |
|---|---|---|--:|--:|--:|--:|---|
| `NQ_4h` | Nasdaq-100 | ✓ Deployable | $149,989 | $15,491 | 67.8% | +$58,029 | — |
| `NQ_2h` | Nasdaq-100 | ✓ Deployable | $91,996 | $16,331 | 49.6% | +$19,569 | — |
| `NQ_1h` | Nasdaq-100 | ✓ Deployable | $99,172 | $16,870 | 48.9% | +$19,012 | — |
| `NQ_15m` | Nasdaq-100 | ✓ Deployable | $76,232 | $8,089 | 48.5% | +$29,114 | — |
| `NQ_5m` | Nasdaq-100 | ✓ Deployable | $23,926 | $4,636 | 59.3% | +$5,860 | — |
| `NQ_2m` | Nasdaq-100 | ✓ Deployable | $29,777 | $3,261 | 64.1% | +$7,816 | — |
| `ES_4h` | S&P 500 | ✓ Deployable | $47,355 | $10,848 | 59.6% | +$19,815 | — |
| `ES_2h` | S&P 500 | ✓ Deployable | $75,692 | $6,993 | 40.1% | +$19,625 | — |
| `ES_1h` | S&P 500 | ✓ Deployable | $61,618 | $8,520 | 52.6% | +$29,035 | — |
| `ES_15m` | S&P 500 | ✓ Deployable | $11,018 | $760 | 93.8% | +$1,218 | — |
| `ES_5m` | S&P 500 | ✓ Deployable | $7,838 | $770 | 63.8% | +$262 | — |
| `ES_2m` | S&P 500 | ✓ Deployable | $12,587 | $1,648 | 53.6% | +$4,558 | — |
| `GC_4h` | Gold | ⚠ Caution | $57,570 | $12,800 | 65.7% | −$540 | loses −$540 out-of-sample |
| `GC_4h_ind4h` | Gold | ✓ Deployable | $97,950 | $7,360 | 72.2% | +$22,310 | — |
| `GC_2h` | Gold | ✓ Deployable | $23,340 | $3,200 | 57.1% | +$11,550 | — |
| `GC_1h` | Gold | ⚠ Caution | $39,140 | $3,130 | 30.3% | +$18,460 | low win rate (30%) |
| `GC_15m` | Gold | ✓ Deployable | $10,340 | $1,880 | 69.6% | +$1,410 | — |
| `GC_5m` | Gold | ✓ Deployable | $15,130 | $3,790 | 71.3% | +$5,250 | — |
| `GC_2m` | Gold | ✓ Deployable | $30,420 | $4,400 | 61.1% | +$10,840 | — |
| `SI_4h` | Silver | ⚠ Caution | $21,928 | $7,452 | 29.5% | +$6,935 | low win rate (30%) |
| `SI_2h` | Silver | ⚠ Caution | $45,451 | $10,789 | 58.8% | +$394 | essentially flat out-of-sample (+$394 vs $10,789 DD) |
| `SI_1h` | Silver | ✓ Deployable | $13,771 | $2,953 | 79.3% | +$364 | — |
| `SI_15m` | Silver | ✓ Deployable | $14,600 | $2,780 | 44.5% | +$2,349 | — |
| `SI_5m` | Silver | ✓ Deployable | $28,735 | $3,534 | 42.9% | +$4,240 | — |
| `SI_2m` | Silver | ✓ Deployable | $3,163 | $676 | 69.1% | +$154 | — |
| `HG_4h` | Copper | ✓ Deployable | $50,160 | $3,473 | 77.7% | +$19,200 | — |
| `HG_2h` | Copper | ✓ Deployable | $25,535 | $3,880 | 59.4% | +$14,198 | — |
| `HG_1h` | Copper | ✗ Non-feasible | $4,970 | $1,190 | 85.8% | −$678 | loses −$678 out-of-sample |
| `HG_15m` | Copper | ✓ Deployable | $3,247 | $663 | 45.0% | +$925 | — |
| `HG_5m` | Copper | ⚠ Caution | $3,102 | $1,065 | 51.8% | −$240 | loses −$240 out-of-sample |
| `HG_2m` | Copper | ⚠ Caution | $31,787 | $2,038 | 26.1% | +$13,688 | low win rate (26%) |
| `CL_4h` | Crude Oil | ✓ Deployable | $21,760 | $3,990 | 47.7% | +$2,475 | — |
| `CL_2h` | Crude Oil | ✓ Deployable | $10,448 | $1,098 | 60.1% | +$2,561 | — |
| `CL_1h` | Crude Oil | ✓ Deployable | $7,939 | $740 | 55.0% | +$1,436 | — |
| `CL_15m` | Crude Oil | ⚠ Caution | $15,852 | $1,021 | 29.4% | +$5,943 | low win rate (29%) |
| `CL_5m` | Crude Oil | ⚠ Caution | $4,090 | $717 | 71.8% | +$42 | essentially flat out-of-sample (+$42 vs $717 DD) |
| `CL_2m` | Crude Oil | ✓ Deployable | $17,775 | $911 | 45.6% | +$4,707 | — |
| `NG_4h` | Natural Gas | ✓ Deployable | $17,363 | $2,086 | 48.4% | +$5,910 | — |
| `NG_2h` | Natural Gas | ✓ Deployable | $18,112 | $2,053 | 51.6% | +$1,733 | — |
| `NG_1h` | Natural Gas | ✓ Deployable | $12,086 | $1,132 | 59.8% | +$6,183 | — |
| `NG_15m` | Natural Gas | ✗ Non-feasible | $-1,635 | $3,060 | 46.7% | −$2,700 | loses money in-sample |
| `NG_5m` | Natural Gas | ⚠ Caution | $27,991 | $366 | 30.4% | +$8,502 | low win rate (30%) |
| `NG_2m` | Natural Gas | ✓ Deployable | $30,294 | $230 | 40.2% | +$10,024 | — |
| `RTY_4h` | Russell 2000 | ✓ Deployable | $32,675 | $4,853 | 49.7% | +$19,677 | — |
| `RTY_2h` | Russell 2000 | ✓ Deployable | $18,846 | $1,822 | 83.8% | +$7,580 | — |
| `RTY_1h` | Russell 2000 | ✓ Deployable | $16,032 | $2,928 | 55.0% | +$6,539 | — |
| `RTY_15m` | Russell 2000 | ✓ Deployable | $3,980 | $590 | 80.6% | +$1,090 | — |
| `RTY_5m` | Russell 2000 | ✓ Deployable | $2,150 | $389 | 65.2% | +$1,390 | — |
| `RTY_2m` | Russell 2000 | ✓ Deployable | $2,082 | $457 | 66.7% | +$1,546 | — |
| `YM_4h` | Dow | ✓ Deployable | $41,542 | $3,811 | 73.1% | +$15,146 | — |
| `YM_2h` | Dow | ✓ Deployable | $27,718 | $3,795 | 61.3% | +$9,389 | — |
| `YM_1h` | Dow | ✓ Deployable | $28,096 | $4,045 | 64.9% | +$6,978 | — |
| `YM_15m` | Dow | ✓ Deployable | $12,762 | $1,089 | 56.4% | +$310 | — |
| `YM_5m` | Dow | ✓ Deployable | $31,862 | $5,160 | 60.5% | +$8,732 | — |
| `YM_2m` | Dow | ✓ Deployable | $19,406 | $1,946 | 44.5% | +$8,894 | — |

---
_Author: **Mulham Fetna** · contact@mulhamfetna.com · ORCID [0009-0006-4432-798X](https://orcid.org/0009-0006-4432-798X)_
