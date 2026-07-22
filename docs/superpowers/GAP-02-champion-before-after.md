# GAP-AWARE FILLS — every champion, before vs after (54 slots, no time cap)

**The engine used to fill every hard stop and take-profit exactly at its line, even when the bar had
already OPENED beyond it — a price that never traded (GAP-01). Since 2026-07-20 it fills at the OPEN in
that case. This is the effect on EVERY champion we have: 9 markets x 6 timeframes = 54 slots, time cap
forced off, run twice with only the fill model changed.**

---

## 1 — THE HEADLINE, AND IT IS NOT WHAT I EXPECTED

| Window | P&L before | P&L after | Δ | **Max drawdown before** | **after** | **Δ** |
|---|---|---|---|---|---|---|
| **Full** | 2,053,207 | 2,049,713 | **−3,494 (−0.2%)** | 292,408 | 320,996 | **+28,588 (+9.8%)** |
| **2026 OOS** | 683,251 | 672,420 | **−10,831 (−1.6%)** | 221,341 | 237,903 | **+16,562 (+7.5%)** |

**Profit is essentially unchanged. Risk is materially worse.**

That is the finding. The old fill model was **not** meaningfully inflating our profits — across 54
champions the gains and losses cancel to −0.2%. What it *was* doing is **understating drawdown by ~10%**,
and on individual slots by far more.

29 champions improved, 24 worsened, 1 unchanged. **Zero flipped from profitable to losing.**

> ### Why this corrects my own earlier numbers
> Earlier today I reported this change as costing **−16.7%** of P&L, and before that **−44% of the edge**.
> Both were measured on a narrow slice — NQ champions only, through the raw engine, on one window. On the
> full 54-champion book the aggregate P&L effect is **−0.2%**. The two earlier figures were not wrong
> arithmetic; they were **wrong scope**, and I should have said "NQ only, one config" rather than letting
> them read as the system-wide cost. The system-wide cost is in the **drawdown column**, which neither
> earlier measurement looked at.

---

## 2 — WHERE THE RISK MOVED

14 of 54 champions saw max drawdown grow by more than 25%:

| market | tf | DD before | DD after | multiple |
|---|---|---|---|---|
| **NG** | 5m | 366 | 1,860 | **5.08×** |
| **NG** | 2m | 230 | 1,106 | **4.81×** |
| **NG** | 4h | 2,576 | 8,446 | **3.28×** |
| **NG** | 1h | 1,132 | 3,160 | **2.79×** |
| RTY | 15m | 1,351 | 3,451 | 2.55× |
| NG | 2h | 1,739 | 4,208 | 2.42× |
| CL | 1h | 1,645 | 3,737 | 2.27× |
| NQ | 5m | 4,636 | 8,160 | 1.76× |
| NQ | 1h | 9,144 | 13,870 | 1.52× |
| HG | 1h | 3,347 | 4,600 | 1.37× |

**Natural gas is the outlier by a wide margin — its book drawdown rose +148%.** NG is the gappiest
contract we trade (inventory reports, thin overnight liquidity), and the old model was hiding almost all
of that. An NG risk budget built on the old numbers understates the real hole by up to **5×**.

**This matters more than the P&L result**, because Z2 and Z4 both concluded that **drawdown — not ruin —
is what binds position sizing**. The sizing recommendation was derived against drawdown figures that were
systematically ~10% optimistic, and far worse than that on the fast energy slots.

---

## 3 — PER MARKET (full window)

| market | P&L before | P&L after | Δ% | DD before | DD after | **Δ DD%** |
|---|---|---|---|---|---|---|
| NQ | 442,662 | 444,867 | +0.5% | 55,504 | 63,670 | +14.7% |
| ES | 213,498 | 217,463 | +1.9% | 32,517 | 33,035 | +1.6% |
| **GC** | 384,519 | **393,244** | **+2.3%** | 76,751 | **74,445** | **−3.0%** |
| SI | 321,455 | 315,236 | −1.9% | 34,536 | 36,261 | +5.0% |
| CL | 91,531 | 95,154 | +4.0% | 13,708 | 15,899 | +16.0% |
| **NG** | 104,102 | 95,582 | −8.2% | 9,223 | **22,870** | **+148.0%** |
| HG | 211,247 | 204,597 | −3.1% | 18,502 | 19,987 | +8.0% |
| RTY | 106,435 | 102,346 | −3.8% | 15,737 | 18,904 | +20.1% |
| YM | 177,756 | 181,223 | +2.0% | 35,930 | 35,924 | −0.0% |

**Gold is the only market that improves on both axes** — more profit *and* less drawdown. That fits what
we found this morning: gold gaps hard around macro releases, and because it moves inverse to macro
surprises with a consistent directional bias, those gaps land on the take-profit side more often than the
stop side. The old model was truncating gold's winners at the TP line.

---

## 4 — THE LARGEST INDIVIDUAL MOVES

| market | tf | before | after | Δ |
|---|---|---|---|---|
| NG | 5m | 27,991 | 20,738 | **−7,253 (−25.9%)** |
| HG | 15m | 39,703 | 32,628 | **−7,075 (−17.8%)** |
| SI | 5m | 88,296 | 82,857 | −5,439 (−6.2%) |
| NQ | 15m | 76,232 | 81,290 | **+5,058 (+6.6%)** |
| NQ | 4h | 143,292 | 147,191 | +3,899 (+2.7%) |
| NG | 4h | 18,082 | 21,930 | **+3,848 (+21.3%)** |

Individual champions swing up to **±28%**. So while the *aggregate* is neutral, **per-slot rankings change
a great deal** — which is exactly why a re-optimization matters for *choosing* champions even though it
barely moves the headline total.

---

## 5 — METHOD (so this is auditable)

- Champion parameters from `optimize/results/wsh4_champions_full<_INST>.json` — the stored, reported set.
  Its NQ 4h `full_pnl` of **148,670.2** is exactly the pre-change golden, confirming these are the
  champions the existing reports were built on.
- **Time cap forced OFF** on every slot (`cap_mode="none"`, `cap_1min=0`) so all 54 compare like-for-like.
- **BEFORE** = `gap_fills=False` (bit-for-bit the old fill-at-the-line behaviour — verified to reproduce
  the old golden ledger byte-for-byte on 4 of 5 timeframes).
- **AFTER** = `gap_fills=True`.
- Same signals, same gate, same data, same parameters. **Only the fill price model differs.**
- Run through `build_view_payload` — the same causal path the dashboard and playbooks use, so every
  number here is reproducible on screen.
- The L1 disk cache was cleared first; it keys on params rather than engine behaviour, and stale entries
  would have made BEFORE and AFTER silently identical.

> ⚠️ **Scope caveat, stated plainly.** A champion set *optimized* without the time-cap model exists only
> for **NQ** (commit `de23947`); the other 8 markets were onboarded after caps existed. So this is not
> "the pre-cap champions" for those markets — it is **the last reported champions run with the cap off**,
> which is the only definition under which all 54 slots are comparable.

---

## 6 — WHAT TO DO WITH THIS

1. **Do not re-cut the profit expectations.** The book's P&L was roughly right; −0.2% is noise.
2. **Do re-cut the risk budget.** Drawdown was understated ~10% overall, +148% on NG, up to 5× on
   individual slots. Every sizing number derived from drawdown needs revisiting — and per Z2/Z4, drawdown
   is precisely the binding constraint on sizing.
3. **NG deserves separate treatment.** It is a different risk animal from the rest of the book once gaps
   are priced honestly.
4. **Re-optimization is still warranted** — not to rescue the total, but because per-slot rankings moved
   by up to ±28%, so the *selection* of champion parameters was made against a distorted scoreboard.

---

## 7 — FULL TABLE (all 54, full window)

Generated from `optimize/reports/gap_fills/champion_gap_compare.json` — not transcribed by hand.

| # | mkt | tf | BEFORE P&L | AFTER P&L | Δ P&L | Δ% | BEFORE DD | AFTER DD | Δ DD | BEFORE trades | AFTER trades |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | NQ | 4h | 143,292 | 147,191 | +3,899 | +2.7% | 14,043 | 14,043 | +0 | 248 | 248 |
| 2 | NQ | 2h | 91,996 | 88,478 | -3,518 | -3.8% | 16,331 | 16,274 | -57 | 152 | 152 |
| 3 | NQ | 1h | 77,439 | 75,919 | -1,521 | -2.0% | 9,144 | 13,870 | +4,726 | 181 | 179 |
| 4 | NQ | 15m | 76,232 | 81,290 | +5,058 | +6.6% | 8,089 | 8,089 | +0 | 492 | 492 |
| 5 | NQ | 5m | 23,926 | 20,092 | **-3,834** | **-16.0%** | 4,636 | 8,160 | +3,524 | 203 | 203 |
| 6 | NQ | 2m | 29,777 | 31,898 | +2,121 | +7.1% | 3,261 | 3,234 | -27 | 379 | 70 |
| 7 | ES | 4h | 46,234 | 48,128 | +1,894 | +4.1% | 14,369 | 14,369 | +0 | 114 | 114 |
| 8 | ES | 2h | 79,537 | 82,755 | +3,218 | +4.0% | 6,993 | 6,993 | +0 | 191 | 191 |
| 9 | ES | 1h | 58,480 | 58,950 | +470 | +0.8% | 7,720 | 7,720 | +0 | 141 | 141 |
| 10 | ES | 15m | 11,018 | 11,025 | +7 | +0.1% | 760 | 760 | +0 | 44 | 44 |
| 11 | ES | 5m | 5,598 | 5,080 | -518 | -9.3% | 1,108 | 1,108 | +0 | 41 | 41 |
| 12 | ES | 2m | 12,632 | 11,525 | -1,107 | -8.8% | 1,567 | 2,085 | +518 | 479 | 479 |
| 13 | GC | 4h | 77,875 | 79,015 | +1,141 | +1.5% | 17,164 | 17,164 | +0 | 251 | 251 |
| 14 | GC | 2h | 81,157 | 84,927 | +3,771 | +4.6% | 15,649 | 15,649 | +0 | 208 | 208 |
| 15 | GC | 1h | 91,701 | 94,236 | +2,535 | +2.8% | 25,659 | 23,356 | -2,303 | 298 | 298 |
| 16 | GC | 15m | 80,909 | 82,616 | +1,707 | +2.1% | 10,097 | 10,094 | -4 | 1469 | 1469 |
| 17 | GC | 5m | 15,771 | 15,861 | +90 | +0.6% | 3,296 | 3,296 | +0 | 152 | 155 |
| 18 | GC | 2m | 37,106 | 36,587 | -519 | -1.4% | 4,887 | 4,887 | +0 | 731 | 731 |
| 19 | SI | 4h | 21,928 | 22,755 | +827 | +3.8% | 7,452 | 7,452 | +0 | 140 | 140 |
| 20 | SI | 2h | 27,505 | 26,040 | -1,465 | -5.3% | 5,134 | 5,152 | +18 | 253 | 253 |
| 21 | SI | 1h | 47,267 | 44,729 | -2,538 | -5.4% | 6,379 | 6,633 | +254 | 219 | 219 |
| 22 | SI | 15m | 76,579 | 79,487 | +2,908 | +3.8% | 10,363 | 10,304 | -59 | 1639 | 1639 |
| 23 | SI | 5m | 88,296 | 82,857 | -5,439 | -6.2% | 2,901 | 3,777 | +876 | 2405 | 2405 |
| 24 | SI | 2m | 59,880 | 59,369 | -511 | -0.9% | 2,307 | 2,943 | +637 | 3516 | 3516 |
| 25 | CL | 4h | 21,925 | 23,740 | +1,815 | +8.3% | 3,487 | 3,487 | +0 | 384 | 384 |
| 26 | CL | 2h | 4,201 | 4,019 | -183 | -4.3% | 5,928 | 5,989 | +61 | 165 | 165 |
| 27 | CL | 1h | 11,214 | 10,233 | -982 | -8.8% | 1,645 | 3,737 | +2,092 | 539 | 539 |
| 28 | CL | 15m | 16,208 | 16,787 | +579 | +3.6% | 1,022 | 1,022 | +0 | 1390 | 1390 |
| 29 | CL | 5m | 13,692 | 15,088 | +1,397 | +10.2% | 885 | 894 | +9 | 1620 | 1620 |
| 30 | CL | 2m | 24,290 | 25,287 | +996 | +4.1% | 741 | 769 | +28 | 4648 | 4648 |
| 31 | NG | 4h | 18,082 | 21,930 | **+3,848** | **+21.3%** | 2,576 | 8,446 | +5,870 | 599 | 599 |
| 32 | NG | 2h | 17,314 | 14,279 | **-3,035** | **-17.5%** | 1,739 | 4,208 | +2,469 | 362 | 362 |
| 33 | NG | 1h | 12,086 | 15,485 | **+3,399** | **+28.1%** | 1,132 | 3,160 | +2,028 | 312 | 312 |
| 34 | NG | 15m | -1,665 | -3,885 | **-2,220** | **-133.3%** | 3,180 | 4,090 | +910 | 998 | 998 |
| 35 | NG | 5m | 27,991 | 20,738 | **-7,253** | **-25.9%** | 366 | 1,860 | +1,494 | 2618 | 2618 |
| 36 | NG | 2m | 30,294 | 27,035 | -3,259 | -10.8% | 230 | 1,106 | +876 | 4711 | 4711 |
| 37 | HG | 4h | 60,390 | 63,502 | +3,112 | +5.2% | 3,465 | 3,492 | +28 | 244 | 244 |
| 38 | HG | 2h | 43,195 | 44,870 | +1,675 | +3.9% | 5,678 | 5,678 | +0 | 264 | 264 |
| 39 | HG | 1h | 27,157 | 24,508 | -2,650 | -9.8% | 3,347 | 4,600 | +1,253 | 445 | 445 |
| 40 | HG | 15m | 39,703 | 32,628 | **-7,075** | **-17.8%** | 2,580 | 2,670 | +90 | 1893 | 1893 |
| 41 | HG | 5m | 8,977 | 10,090 | +1,113 | +12.4% | 1,395 | 1,460 | +65 | 919 | 899 |
| 42 | HG | 2m | 31,825 | 29,000 | -2,825 | -8.9% | 2,038 | 2,088 | +50 | 4507 | 4507 |
| 43 | RTY | 4h | 35,045 | 34,577 | -468 | -1.3% | 6,757 | 7,342 | +586 | 283 | 283 |
| 44 | RTY | 2h | 18,664 | 18,716 | +52 | +0.3% | 1,727 | 1,905 | +178 | 204 | 204 |
| 45 | RTY | 1h | 17,260 | 17,260 | +0 | +0.0% | 2,928 | 2,928 | +0 | 220 | 220 |
| 46 | RTY | 15m | 10,697 | 8,594 | **-2,103** | **-19.7%** | 1,351 | 3,451 | +2,100 | 135 | 135 |
| 47 | RTY | 5m | 21,120 | 19,487 | -1,633 | -7.7% | 2,145 | 2,448 | +303 | 1312 | 1312 |
| 48 | RTY | 2m | 3,649 | 3,713 | +64 | +1.7% | 831 | 831 | +0 | 214 | 214 |
| 49 | YM | 4h | 32,939 | 31,608 | -1,332 | -4.0% | 17,108 | 17,108 | +0 | 153 | 153 |
| 50 | YM | 2h | 21,954 | 21,618 | -335 | -1.5% | 2,924 | 2,924 | +0 | 32 | 32 |
| 51 | YM | 1h | 45,878 | 46,419 | +541 | +1.2% | 6,846 | 6,846 | +0 | 230 | 230 |
| 52 | YM | 15m | 16,407 | 17,891 | +1,484 | +9.0% | 1,509 | 1,509 | +0 | 186 | 186 |
| 53 | YM | 5m | 31,862 | 34,560 | +2,698 | +8.5% | 5,160 | 5,154 | -5 | 496 | 412 |
| 54 | YM | 2m | 28,716 | 29,127 | +411 | +1.4% | 2,383 | 2,383 | +0 | 963 | 963 |

_Bold marks a move of 15% or more. Raw run log: `optimize/reports/gap_fills/champion_gap_compare.log`._
