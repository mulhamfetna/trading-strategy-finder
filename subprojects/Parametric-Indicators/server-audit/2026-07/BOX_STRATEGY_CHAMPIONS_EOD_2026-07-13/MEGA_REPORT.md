# Forced end-of-day champions — 2026-07-13

## What this set is

Every one of these 54 strategies **closes its position at the end of the trading day**. None of them
hold overnight. They were re-optimized **from scratch** (cold start, 5,800 trials each, no warm start
from the existing champions) with the end-of-day close **forced on** — so their stops, targets,
indicator gate and bar cap are all tuned *for* a same-day horizon, rather than having the rule bolted
onto a strategy that was tuned to hold overnight.

Indicators run on the **1-minute frame** on every slot.

## Does forcing the bell close actually help?

That question has three answers per slot, and this report gives all three, decided on **2026** — the
held-out year none of these searches ever saw. In-sample profit is not used to pick a winner: every
champion here was chosen by a search that read the in-sample data, so its in-sample number flatters it
by construction.

| candidate | what it is |
|---|---|
| **deployed** | today's champion. Most hold overnight. |
| **bolt-on** | that same champion with the bell close switched on and *nothing re-tuned*. |
| **eod1** | this set: cold-start, re-tuned **with** the bell close forced. |

A challenger only takes a slot by beating the deployed champion's 2026 profit by **more than 10%**.
A tie does not churn a verified strategy.

## 2026 out-of-sample, all three, every slot

| slot | market | deployed | bolt-on | eod1 (this set) | winner |
|---|---|---:|---:|---:|---|
| NQ_4h | Nasdaq-100 4h | +$64,877 | +$56,090 | +$19,133 | deployed |
| NQ_2h | Nasdaq-100 2h | +$19,569 | +$12,194 | +$40,745 | **eod1** |
| NQ_1h | Nasdaq-100 1h | +$21,944 | +$23,319 | +$27,203 | **eod1** |
| NQ_15m | Nasdaq-100 15m | +$29,114 | +$30,398 | +$21,286 | deployed |
| NQ_5m | Nasdaq-100 5m | +$5,860 | +$4,966 | +$2,600 | deployed |
| NQ_2m | Nasdaq-100 2m | +$7,816 | +$7,488 | +$4,561 | deployed |
| ES_4h | S&P 500 4h | +$28,188 | +$24,201 | +$22,953 | deployed |
| ES_2h | S&P 500 2h | +$18,240 | +$12,317 | +$24,943 | **eod1** |
| ES_1h | S&P 500 1h | +$28,193 | +$31,073 | +$24,161 | **bolt-on** |
| ES_15m | S&P 500 15m | +$1,218 | +$890 | +$9,836 | **eod1** |
| ES_5m | S&P 500 5m | +$2,701 | +$2,701 | +$839 | deployed |
| ES_2m | S&P 500 2m | +$6,913 | +$6,753 | +$1,263 | deployed |
| GC_4h | Gold 4h | +$11,816 | +$12,481 | +$31,041 | **eod1** |
| GC_2h | Gold 2h | +$22,657 | +$20,048 | +$20,597 | deployed |
| GC_1h | Gold 1h | +$28,741 | +$28,741 | +$30,505 | deployed |
| GC_15m | Gold 15m | +$37,286 | +$36,109 | +$3,971 | deployed |
| GC_5m | Gold 5m | +$7,150 | +$7,150 | +$10,346 | **eod1** |
| GC_2m | Gold 2m | +$13,639 | +$13,639 | +$2,445 | deployed |
| SI_4h | Silver 4h | +$5,111 | +$5,111 | +$13,927 | **eod1** |
| SI_2h | Silver 2h | +$5,957 | +$5,957 | +$29,840 | **eod1** |
| SI_1h | Silver 1h | +$15,511 | +$15,511 | +$19,020 | **eod1** |
| SI_15m | Silver 15m | +$18,139 | +$17,894 | +$18,757 | deployed |
| SI_5m | Silver 5m | +$18,663 | +$18,716 | +$21,806 | **eod1** |
| SI_2m | Silver 2m | +$10,452 | +$10,303 | +$21,484 | **eod1** |
| HG_4h | Copper 4h | +$22,095 | +$20,225 | +$4,395 | deployed |
| HG_2h | Copper 2h | +$16,030 | +$16,030 | +$19,745 | **eod1** |
| HG_1h | Copper 1h | +$3,270 | +$3,198 | +$8,720 | **eod1** |
| HG_15m | Copper 15m | +$11,268 | +$11,268 | +$552 | deployed |
| HG_5m | Copper 5m | +$3,072 | +$3,640 | +$3,435 | **bolt-on** |
| HG_2m | Copper 2m | +$13,687 | +$13,537 | +$17,890 | **eod1** |
| CL_4h | Crude Oil 4h | +$5,854 | +$6,504 | +$6,293 | **bolt-on** |
| CL_2h | Crude Oil 2h | +$3,835 | +$3,835 | +$1,913 | deployed |
| CL_1h | Crude Oil 1h | +$4,809 | +$4,809 | +$3,785 | deployed |
| CL_15m | Crude Oil 15m | +$5,764 | +$5,496 | +$896 | deployed |
| CL_5m | Crude Oil 5m | +$3,139 | +$3,060 | +$3,553 | **eod1** |
| CL_2m | Crude Oil 2m | +$8,008 | +$8,008 | +$3,480 | deployed |
| NG_4h | Natural Gas 4h | +$6,910 | +$6,910 | +$5,650 | deployed |
| NG_2h | Natural Gas 2h | +$6,113 | +$5,966 | +$3,933 | deployed |
| NG_1h | Natural Gas 1h | +$6,183 | +$5,711 | +$1,572 | deployed |
| NG_15m | Natural Gas 15m | −$2,775 | −$2,765 | +$282 | **eod1** |
| NG_5m | Natural Gas 5m | +$7,938 | +$7,940 | −$1,915 | deployed |
| NG_2m | Natural Gas 2m | +$9,758 | +$9,758 | +$8,410 | deployed |
| RTY_4h | Russell 2000 4h | +$23,872 | +$23,872 | +$18,831 | deployed |
| RTY_2h | Russell 2000 2h | +$7,417 | +$6,562 | +$5,282 | deployed |
| RTY_1h | Russell 2000 1h | +$6,539 | −$1,729 | +$5,444 | deployed |
| RTY_15m | Russell 2000 15m | +$3,900 | +$3,621 | +$2,080 | deployed |
| RTY_5m | Russell 2000 5m | +$6,484 | +$5,754 | +$2,635 | deployed |
| RTY_2m | Russell 2000 2m | +$1,627 | +$1,791 | +$3,668 | **eod1** |
| YM_4h | Dow 4h | +$34,921 | +$34,921 | +$12,331 | deployed |
| YM_2h | Dow 2h | +$11,111 | +$11,111 | +$7,163 | deployed |
| YM_1h | Dow 1h | +$12,527 | +$12,527 | +$26,368 | **eod1** |
| YM_15m | Dow 15m | +$3,511 | +$3,563 | +$18,192 | **eod1** |
| YM_5m | Dow 5m | +$8,732 | +$6,866 | +$2,465 | deployed |
| YM_2m | Dow 2m | +$10,533 | +$9,421 | +$966 | deployed |

## The bottom line

| if you ran ONE approach across all 54 slots | 2026 profit |
|---|---:|
| all **deployed** (what you have today) | +$695,886 |
| all **bolt-on** (bell close, no re-tuning) | +$655,457 |
| all **eod1** (bell close, re-tuned) | +$621,272 |
| **best per slot** | **+$861,943** |

Best-per-slot beats today's deployed set by **+$166,056** (+23.9%) on 2026.

Slots won: deployed **32** · bolt-on **3** · eod1 **19**

## How the numbers were produced

Every number here comes from the **causal engine** — the same one the dashboard draws, which never
sees a bar before it closes. The optimizer's own fast engine is an approximation and has claimed
profits on strategies the causal engine says LOSE money (Copper 2m; Natural Gas 15m, twice), so
nothing it reported is trusted here. The bundled backtester reproduces every headline and every 2026
figure in this report to the dollar; that check is run before the bundle ships.

Weak and negative slots are included and **flagged**, not hidden. The backtester reproduces their bad
numbers too — a champion set you can only trust when it flatters you is not a champion set.

---

Mulham Fetna · contact@mulhamfetna.com · ORCID 0009-0006-4432-798X · github.com/mulhamfetna
