---
name: ws-h-results-report
description: WS-H results + overfit diagnostics — per-timeframe (1m…4h) NSGA-II Pareto search (8400 trials) for the single-contract box strategy, scored by walk-forward folds. Debunks the fine-TF (1m/2m) flip-scalper "winners" as overfit + cost-blind; identifies 2h (all folds positive) as the only robust candidate. Honest caveats throughout.
type: report
status: complete
created: 2026-06-03
---

# WS-H — Multi-Timeframe Parameter Search: Results & Overfit Diagnostics

## 0. Engine identity & version pin
This report is produced by, and pins, the engine:

> **`WSH-HAR_RV-Drowdown_Breaker-Cooldown_Couner-Vectorized_NASGII`**

Decoding the full name (each token is a real component of the system):

| Token | Component | Where |
|---|---|---|
| **WSH** | multi-timeframe decision-candle search (1m…4h); exits always resolve on 1-min | `optimize/` |
| **HAR_RV** | HAR-RV realized-volatility gate (trade only when forecast vol is calm) | `volatility.py` |
| **Drowdown_Breaker** | global high-water-mark drawdown circuit-breaker (cooldown-and-probe) | `optimize/core.py` |
| **Cooldown_Couner** | realized-trade-gap cooldown counter / per-TF cap (D1) | `optimize/cooldown.py` |
| **Vectorized** | numpy `fast_engine` (~200×), trade-for-trade parity-locked to the verified engine | `optimize/fast_engine.py` |
| **NASGII** | NSGA-II multi-objective Pareto search (median P/L vs worst-fold maxDD) | `optimize/optimizer.py` |

**Pinned at:** branch `wsh-engine`, tag `WSH-HAR_RV-Drowdown_Breaker-Cooldown_Couner-Vectorized_NASGII`
(HEAD = WS-H complete). Parity locks: `test_parity.py`, `test_fast_parity.py`.

## 1. What was run
For every decision timeframe TF ∈ {1m, 2m, 5m, 15m, 1h, 2h, 4h} we searched the single-contract box
strategy (box signal + HAR-RV volatility gate + global-HWM drawdown breaker) with **Optuna NSGA-II**,
two objectives — **maximise median-fold P/L**, **minimise worst-fold maxDD** — scored by **5-fold
walk-forward** (fold 0 = causal gate-reference/warmup; folds 1–4 scored). **1200 trials per TF =
8400 total**. Only the **entry/decision candle** varied; exits always resolved on **1-minute**
(absolute point distances). Per-TF search bounds: cooldown cap from the realized-trade-gap rule
(D1), SL/TP from each TF's excursion distribution (D2). Engine = the vectorized `fast_engine`
(trade-for-trade identical to the verified engine; ~200× faster — that's what made this feasible).

Artifacts: `optimize/results/<tf>_pareto.csv` (full fronts), `<tf>_pareto.png` (profit-vs-DD),
`leaderboard.csv`. Studies persisted in `optimize/studies/wsh.db` (git-ignored).

> **All P/L figures are median-fold; all maxDD figures are worst-fold** — a *harsher* drawdown than
> the full-period number, and per-fold P/L is ~⅓–¼ of a full-period run (folds are ~3-month slices).

## 2. Leaderboard — best point with worst-fold maxDD ≤ $5,000, per TF
Re-verified by re-running each TF's capped winner through the walk-forward scorer:

| TF | median P/L | worstDD | per-fold P/L (1→4) | params (slS/slH·TP·gate·ddlim·cd·flip) | verdict |
|---|---:|---:|---|---|---|
| 4h | $4,830 | $4,745 | +8.2k +10.5k +1.4k **−1.2k** | 108/134·36·35·2460·2·N | ok, weak tail |
| **2h** | **$12,082** | $4,605 | +14.8k +15.0k +9.4k **+4.1k** | 37/54·41·75·400·2·N | **robust — all folds +** |
| 1h | $9,453 | $4,470 | +7.8k +11.1k +12.7k **+0.2k** | 15/66·89·46·3840·4·N | ok, thin tail |
| 15m | $6,348 | $4,523 | +10.8k +10.7k +2.0k **−4.9k** | 25/40·44·33·4877·7·N | shaky tail |
| 5m | $7,435 | $4,826 | +8.8k +7.1k +7.8k **−3.1k** | 19/43·37·37·4638·9·N | shaky tail |
| 2m | $24,731 | $4,318 | +10.8k +20.9k +28.5k +39.1k | 7/7·11·99·3892·31·**Y** | **OVERFIT — do not trust** |
| 1m | $39,190 | $4,040 | +24.8k +19.8k +53.6k +54.8k | 5/6·10·99·3281·0·**Y** | **OVERFIT — do not trust** |

(Param values are rounded from the CSV; exact floats live in the study DB.)

## 3. The fine-TF (1m/2m) results are overfit artifacts, not edges
They share an unmistakable signature and fail three independent sanity checks:

1. **Degenerate parameters.** `flip=True` + **5–7-point stops** + **gate ≈ 99th pct (i.e. gate
   effectively OFF)**. That's not a strategy — it's a hyperactive contrarian scalper fitting
   1-minute noise.
2. **Trade count is absurd.** 1,200–2,600 trades **per fold** (vs ~15–95 for the sane TFs). The 1m
   "winner" takes ~8,300 trades over the data.
3. **Cost-blind — the killer.** The backtest models **zero commission and zero slippage**. On NQ a
   realistic round-turn (commission + ~1 tick spread/slippage) is on the order of **$5–$15**. At
   ~1,500 trades/fold that is **$7.5k–$22k of costs per fold** — which **erases the entire reported
   profit** and then some. The 5-point stop is itself smaller than a typical bid/ask bounce, so the
   fills are not realistically achievable. P/L also *grows* fold-over-fold (recency-fit), the
   opposite of a stable edge.

**Conclusion:** 1m and 2m are excluded as winners. They are kept in the results only as a
documented overfit example. (The `OVERFIT?` auto-flag in `leaderboard.csv` marks
flip+tiny-stop+gate-off rows.)

## 4. The believable result: 2h
**2h is the only timeframe whose capped winner is positive in all four folds** (+14.8k, +15.0k,
+9.4k, +4.1k; median $12,082, worst-fold DD $4,605), with **sane mechanics**: normal direction,
37/54-pt stops (~$1,080 hard-stop loss cap), a real 75th-percentile volatility gate, light breaker.
It is the same *family* as the 4h winner (calm-bar gate + tight stops + favourable R:R) but trades
~2× more often, which lifts P/L while keeping worst-fold DD under $5k. **This is the candidate worth
forward-testing.** 1h is a reasonable second (all folds positive but a very thin +$176 fourth fold).

The coarse/mid TFs degrade toward the tail: **fold 4 (the most recent slice) is the weakest for
almost every TF** (4h, 15m, 5m go negative there). That temporal pattern is a mild **regime-decay**
warning — the edge was stronger earlier in the sample.

## 5. Honest caveats (read before trusting any number)
- **Still in-sample on one instrument** (NQ, ~2025–2026). Walk-forward reduces but does not
  eliminate overfit; it is **not** true out-of-sample (no unseen instrument/era).
- **No transaction costs modelled.** Fine for 4h/2h (tens of trades); **fatal** for fine TFs.
  Any forward use must add realistic commission + slippage — this alone disqualifies 1m/2m.
- **Worst-fold maxDD ≤ $5k is a soft selection, not a guarantee** — and as `notes/49` showed, the
  breaker delays but cannot hard-cap drawdown.
- **Gate threshold** is frozen causally per fold (expanding window); other freezing choices would
  shift results.
- These are **hypotheses**, not forward promises.

## 6. Recommendations / next steps
1. **Forward-test 2h** (normal, 37/54·TP41·gate75·breaker400/2) with **realistic costs added** to the
   engine; compare against the incumbent 4h winner.
2. **Add a transaction-cost model** (commission + slippage per round-turn) to `fast_engine` and
   **re-run the search** — this will collapse the fine-TF mirage and give honest fine-TF fronts.
3. **True OOS**: when other instruments/years arrive (WS-F), re-score the 2h/1h candidates frozen.
4. Optionally tighten the fine-TF search (forbid `flip` + floor the stops well above 1 tick) so the
   optimiser can't chase the noise corner.

## 7. Reproduce
```
# per-TF search (vectorized engine; ~minutes/TF locally)
python3 subprojects/wsg-strategy/optimize/optimizer.py <tf> --trials 1200 --folds 5 --min-trades 3
# outputs (Pareto CSV/PNG + leaderboard)
python3 subprojects/wsg-strategy/optimize/report.py 4h 2h 1h 15m 5m 2m 1m
# live progress:  watch -n 5 python3 subprojects/wsg-strategy/optimize/progress.py
```
Parity locks: `test_parity.py` (TF=4h == +$7,735/$3,670/66) and `test_fast_parity.py`
(vectorized == verified engine, trade-for-trade).
