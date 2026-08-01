# Box-strategy champions — DEPLOYED set, 2026-07-14

54 strategies (9 markets x 6 timeframes). These are the ones actually running on the dashboard.

## How each slot was chosen

Every slot holds the best of **three candidates**, decided on the held-out **2026** year — the only
window none of the searches ever saw. In-sample profit never picks a winner: each champion was
*selected* by a search that read the in-sample data, so its in-sample number flatters it by
construction. A challenger had to beat the incumbent's 2026 profit by **more than 10%** to take a
slot; anything that loses money in 2026 was disqualified outright.

| candidate | what it is | slots won |
|---|---|---:|
| **incumbent** | the champion already deployed (most hold overnight) | 29 |
| **forced end-of-day** | cold-start, re-optimized *with* the bell close forced on | 24 |
| **bolt-on** | the incumbent with the bell close simply switched on, not re-tuned | 1 |

Exit rules are therefore **mixed by design** — some close at the bell, some hold, some cap how many
bars they stay in. That mix is the finding, not an inconsistency.

## Does forcing the bell close help? Not as a blanket rule.

| if you ran ONE approach across all 54 slots | 2026 profit |
|---|---:|
| all incumbents | +$638,462 |
| all bolt-on (bell close, no re-tuning) | +$614,660 |
| all forced end-of-day (bell close, re-tuned) | +$631,999 |
| **best per slot (this set)** | **+$840,037** |

Forcing every slot to close at the bell **makes less money than leaving it alone** — whether you
bolt it on (+$614,660) or re-tune for it (+$631,999), both lose to simply keeping the
incumbents (+$638,462). There is no "end-of-day is good/bad" answer. The entire gain comes
from choosing **per slot**: +$840,037, which beats the incumbents by **+$201,575** (+31.6%).

## Every slot

| slot | market | incumbent 2026 | bolt-on 2026 | forced-EOD 2026 | ships | full P/L | max DD |
|---|---|---:|---:|---:|---|---:|---:|
| NQ_4h | Nasdaq-100 4h | +$64,877 | +$56,090 | +$19,133 | incumbent | +$148,670 | $12,284 |
| NQ_2h | Nasdaq-100 2h | +$15,764 | +$15,764 | +$40,745 | **forced-EOD** | +$82,752 | $9,419 |
| NQ_1h | Nasdaq-100 1h | +$21,944 | +$23,319 | +$27,203 | **forced-EOD** | +$78,823 | $8,815 |
| NQ_15m | Nasdaq-100 15m | +$16,156 | +$16,156 | +$21,286 | **forced-EOD** | +$35,176 | $7,326 |
| NQ_5m | Nasdaq-100 5m | +$1,459 | +$923 | +$2,600 | **forced-EOD** | +$15,216 | $1,723 |
| NQ_2m | Nasdaq-100 2m | +$1,015 | +$546 | +$4,561 | **forced-EOD** | +$31,741 | $3,833 |
| ES_4h | S&P 500 4h | +$28,188 | +$24,201 | +$22,953 | incumbent | +$68,168 | $13,552 |
| ES_2h | S&P 500 2h | +$12,714 | +$9,930 | +$24,943 | **forced-EOD** | +$68,109 | $9,070 |
| ES_1h | S&P 500 1h | +$12,015 | +$12,691 | +$24,161 | **forced-EOD** | +$61,507 | $9,385 |
| ES_15m | S&P 500 15m | +$278 | +$83 | +$9,836 | **forced-EOD** | +$25,337 | $5,095 |
| ES_5m | S&P 500 5m | +$2,701 | +$2,701 | +$839 | incumbent | +$5,598 | $1,108 |
| ES_2m | S&P 500 2m | +$6,913 | +$6,754 | +$1,263 | incumbent | +$12,632 | $1,567 |
| GC_4h | Gold 4h | +$11,816 | +$12,481 | +$31,041 | **forced-EOD** | +$85,823 | $9,142 |
| GC_2h | Gold 2h | +$22,658 | +$20,048 | +$20,597 | incumbent | +$81,157 | $15,649 |
| GC_1h | Gold 1h | +$28,740 | +$28,740 | +$30,505 | incumbent | +$86,969 | $21,007 |
| GC_15m | Gold 15m | +$37,283 | +$36,107 | +$3,971 | incumbent | +$80,903 | $10,098 |
| GC_5m | Gold 5m | +$7,150 | +$7,150 | +$10,346 | **forced-EOD** | +$19,965 | $4,305 |
| GC_2m | Gold 2m | +$13,640 | +$13,640 | +$2,445 | incumbent | +$38,640 | $4,577 |
| SI_4h | Silver 4h | +$2,878 | +$2,878 | +$13,929 | **forced-EOD** | +$61,524 | $8,716 |
| SI_2h | Silver 2h | +$6,258 | +$6,258 | +$29,854 | **forced-EOD** | +$75,357 | $7,477 |
| SI_1h | Silver 1h | +$15,521 | +$15,521 | +$19,018 | **forced-EOD** | +$33,112 | $4,612 |
| SI_15m | Silver 15m | +$18,090 | +$17,844 | +$18,675 | incumbent | +$76,453 | $10,368 |
| SI_5m | Silver 5m | +$19,127 | +$19,180 | +$22,537 | **forced-EOD** | +$51,814 | $3,681 |
| SI_2m | Silver 2m | +$10,773 | +$10,625 | +$21,756 | **forced-EOD** | +$71,799 | $2,605 |
| HG_4h | Copper 4h | +$22,101 | +$20,231 | +$4,249 | incumbent | +$60,413 | $3,461 |
| HG_2h | Copper 2h | +$16,045 | +$16,045 | +$19,869 | **forced-EOD** | +$34,405 | $5,100 |
| HG_1h | Copper 1h | +$3,218 | +$3,145 | +$8,687 | **forced-EOD** | +$28,475 | $2,146 |
| HG_15m | Copper 15m | +$8,440 | +$8,440 | +$588 | incumbent | +$33,351 | $2,563 |
| HG_5m | Copper 5m | +$5,727 | +$5,692 | +$3,542 | incumbent | +$24,085 | $737 |
| HG_2m | Copper 2m | +$21,279 | +$21,279 | +$11,527 | incumbent | +$62,210 | $1,315 |
| CL_4h | Crude Oil 4h | +$5,855 | +$6,505 | +$6,292 | **bolt-on** | +$17,524 | $3,205 |
| CL_2h | Crude Oil 2h | +$2,913 | +$2,913 | +$1,913 | incumbent | +$6,455 | $1,240 |
| CL_1h | Crude Oil 1h | +$4,643 | +$4,643 | +$3,787 | incumbent | +$10,388 | $1,644 |
| CL_15m | Crude Oil 15m | +$3,345 | +$3,345 | +$2,685 | incumbent | +$14,138 | $1,195 |
| CL_5m | Crude Oil 5m | +$3,148 | +$3,069 | +$3,566 | **forced-EOD** | +$15,238 | $961 |
| CL_2m | Crude Oil 2m | +$7,983 | +$7,983 | +$3,494 | incumbent | +$23,901 | $732 |
| NG_4h | Natural Gas 4h | +$7,816 | +$7,816 | +$5,658 | incumbent | +$25,128 | $2,564 |
| NG_2h | Natural Gas 2h | +$6,120 | +$5,972 | +$3,914 | incumbent | +$17,338 | $1,735 |
| NG_1h | Natural Gas 1h | +$4,436 | +$4,394 | +$1,624 | incumbent | +$16,176 | $2,798 |
| NG_15m | Natural Gas 15m | +$5,545 | +$5,370 | +$291 | incumbent | +$22,805 | $840 |
| NG_5m | Natural Gas 5m | +$4,368 | +$4,368 | +$11,155 | **forced-EOD** | +$38,079 | $261 |
| NG_2m | Natural Gas 2m | +$6,680 | +$6,680 | +$9,541 | **forced-EOD** | +$30,179 | $575 |
| RTY_4h | Russell 2000 4h | +$23,872 | +$23,872 | +$18,831 | incumbent | +$36,688 | $9,092 |
| RTY_2h | Russell 2000 2h | +$6,688 | +$5,635 | +$5,282 | incumbent | +$18,016 | $2,001 |
| RTY_1h | Russell 2000 1h | +$3,385 | +$3,385 | +$5,444 | **forced-EOD** | +$15,954 | $2,220 |
| RTY_15m | Russell 2000 15m | +$3,900 | +$3,621 | +$2,080 | incumbent | +$10,697 | $1,351 |
| RTY_5m | Russell 2000 5m | +$6,483 | +$5,753 | +$2,635 | incumbent | +$21,199 | $2,145 |
| RTY_2m | Russell 2000 2m | +$1,627 | +$1,791 | +$3,667 | **forced-EOD** | +$18,128 | $1,058 |
| YM_4h | Dow 4h | +$34,921 | +$34,921 | +$12,331 | incumbent | +$51,917 | $9,126 |
| YM_2h | Dow 2h | +$11,111 | +$11,111 | +$7,163 | incumbent | +$20,573 | $1,434 |
| YM_1h | Dow 1h | +$12,527 | +$12,527 | +$26,368 | **forced-EOD** | +$55,530 | $4,710 |
| YM_15m | Dow 15m | +$3,511 | +$3,563 | +$18,192 | **forced-EOD** | +$26,709 | $4,348 |
| YM_5m | Dow 5m | +$2,281 | +$1,544 | +$2,465 | incumbent | +$16,245 | $1,902 |
| YM_2m | Dow 2m | +$10,533 | +$9,421 | +$966 | incumbent | +$28,716 | $2,383 |

## How the numbers were produced

Every figure comes from the **causal engine** — the same one the dashboard draws, which never sees a
bar before it closes. The bundled backtester reproduces every headline and every 2026 figure here to
the dollar; that check runs before the bundle ships.

Weak and negative slots are **included and flagged**, not hidden. The backtester reproduces their bad
numbers too — a champion set you can only trust when it flatters you is not a champion set.

> **A note on precision.** An earlier build of this bundle persisted stop and target parameters
> rounded to four decimal places. Prices here span four orders of magnitude (the Dow trades near
> $44,000, natural gas near $3.57), so four decimals leaves a natural-gas stop of 0.0008 with a single
> significant digit. On NG 5m that 1.1% distortion moved the result by $39,793 and flipped its sign.
> Parameters are now stored to 12 significant digits, and every number in this bundle was re-measured
> from the corrected champions.

---

Mulham Fetna · contact@mulhamfetna.com · ORCID 0009-0006-4432-798X · github.com/mulhamfetna
