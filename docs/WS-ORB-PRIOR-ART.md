# WS-ORB (#183) — prior art on opening-range breakout, verified

**Date:** 2026-08-23 · **Method:** deep-research harness (99 agents, fan-out search → fetch → 3-vote adversarial
verification per claim → synthesis). 17 claims survived verification; 9 are reported below, the refuted ones
are listed so nobody re-cites them. Raw journal: session workflow `wf_61c9fbd9-a70`.

## 1. What is actually established

| # | finding | confidence | source |
|---|---|---|---|
| 1 | **Canonical rule set (Zarattini & Aziz 2023, QQQ):** opening range = first 5-min bar after the 09:30 cash open; enter at the open of the second bar in the first bar's direction (no trade on a doji); stop at the first bar's opposite extreme (= 1R); target 10R or flat at the close; 1% of capital risked; 4× leverage cap; commission $0.0005/share; **no slippage modelled**. | high (3-0, 3-0) | SSRN 4416622; open replication github.com/giovannibrusco/zarattini-2023-orb-qqq |
| 2 | Reported QQQ 2016-01 → 2023-02: +675% net of commission (buy-and-hold +169%), α 33%/yr (p=0.0025), β≈0, Sharpe 1.12, 1,795 trades, **24% win rate, +0.13R/trade**. TQQQ variant +1,484%, α 47%, Sharpe 1.18. Single in-sample window, no OOS, authors have a commercial day-trading-education interest. | high (3-0, 2-1) | SSRN 4416622 |
| 3 | Their own stop/target sweep found the in-sample optimum at a **5%-of-14-day-ATR stop with no target** (+9,350% on TQQQ) — and flagged it as unrealistic (stop inside the slippage). | high | SSRN 4416622; concretumgroup.com |
| 4 | **Zarattini, Barbon & Aziz 2024 (7,000 US stocks):** stocks-in-play filter (relative volume ≥ 100%, top-20), stop = 10% of 14-day ATR, EoD exit; compared 5/15/30/60-min ranges — **5 min best, "reason unclear"**. Filtered +1,637%, Sharpe 2.81, MDD 12%; unfiltered +29%, Sharpe 0.48. Equities only. | high (3-0 ×3) | SSRN 4729284; QuantConnect replication |
| 5 | **Cost sensitivity (open replication of #2):** reproduces within noise (1,775 vs 1,795 trades); **gross edge ≈ 7 ¢/share; net P/L crosses zero at ≈ 2.2 ¢/share entry slippage** (QQQ spread ≈ 1 ¢). At 2 ¢ entry + 4 ¢ stop slippage: Sharpe 0.23. | medium | giovannibrusco replication README |
| 6 | **Regime concentration:** in the replication 76% of filtered P/L (38% unfiltered) comes from **2022 alone**; filtered variant loses in 2017, 2020, early 2023; bootstrap Sharpe CI [0.05, 1.41] overlaps buy-and-hold. | medium | same |
| 7 | **Only direct index-futures test (Mesfin 2026, MNQ, 09:30–09:55 range, 947 days 2021-12 → 2025-08, 2-pt round-trip friction):** fails the paper's validation gate (N≥30, net>0, T≥2, year stability) in all 5 variants; best: long, hold 15 bars, +2.82 pts/trade, T=1.50; shorts net negative; **2024 +7.04 masks 2022 −1.42** — "one strong year masking the rest" was the study's commonest failure mode. arXiv preprint, no code. | medium (2-1, 3-0) | arxiv.org/pdf/2605.04004 |
| 8 | **Only peer-reviewed futures ORB (Holmberg, Lönnbark & Lundström 2013, crude oil 1983–2011, daily OHLC):** the "range" is **not a time window** but a volatility-scaled threshold around the open (ψ = (1±ρ)·P_open, ρ = μ̂ + σ̂·q_α), flat at the close, no stop/target, zero costs; returns significantly > 0, **concentrated in the high-volatility 2001–2011 subperiod**. | high | Finance Research Letters 2013 |
| 9 | Practitioner ES rule (edgeful): 09:30–09:35 range, trade the break in its direction, target 50% of range width, stop at the opposite edge — rules verified, **performance figures refuted** (6-month in-sample, vendor, no costs, extra filters). | low (rules 2-1; stats 0-3) | edgeful.com |

## 2. Refuted — do not cite
- Instrument-specific "best" windows (15 min ES, 30 min NQ/CL) and measured-move targets (crosstrade.io) — 0-3.
- QuantConnect's 1.5×ATR stop / 17% win-rate figures — refuted.
- Vendor ES stats (72% win, 115 trades, $10,825 in 6 months) — refuted as evidence (no costs, in-sample, filters added).
- MNQ preprint side-claims (80.7% stop-out rate on the pullback variant; 0.07–1.50 pts max gross edge across 14 families) — 0-3 / 1-2.
- Circulated TQQQ MDD 28% / QQQ MDD 22% — not in the paper text.

## 3. What this means for our design (carried into the pre-registration)

1. **Nothing verified exists for metals, energy (beyond daily-bar crude 2013), RTY/YM, or the 18:00 Globex open.** Arm B
   (session-open ORB) is unexplored territory; arm A on futures has one negative test (MNQ) and no positive one.
2. **The edge, where reported, lives inside the spread** (7 ¢/share gross on QQQ; 2.82 pts/trade on MNQ with T 1.5).
   Our stressed-cost rule ($10 and $25 per round-trip) is therefore the primary lens, not a footnote, and a
   **per-trade gross edge vs tick size** table is a required output.
3. **Regime/year concentration is the documented failure mode** (2020/2022 on QQQ; 2024 on MNQ). Our 16-year 1-minute
   tape (2010-06 → 2026-08) lets us require **year-by-year stability** and a leave-one-year-out check — pre-registered,
   not post-hoc.
4. **The 5-minute window's dominance is an equities result with an unknown reason.** We sweep {5, 15, 30, 60} min in
   both arms with a Bonferroni-style correction across the grid, and treat "5 min wins" as a hypothesis to test, not a prior.
5. **Low win rate / long right tail** (24% win, 10R target) means power depends on the tail; the 16-year tape is the
   only reason per-instrument verdicts are reachable at all.
6. **The volatility-scaled threshold (Holmberg 2013)** is a natural third rule family and connects to the in-house finding
   that the box strategy is vol-seeking (the ORB edge may be long-volatility exposure in disguise). It enters as a
   pre-registered comparator, not a primary arm.
7. **Open questions the study must answer:** does any ORB variant survive realistic futures friction on each of the 9
   instruments; is the 5-min dominance real on futures / at the Globex open; how much of the edge is explained by a
   vol-forecast gate (FU-14 power forecast already deployed) — i.e. would the existing vol machinery subsume it.
