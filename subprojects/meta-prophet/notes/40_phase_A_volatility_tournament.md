---
name: phase-A-volatility-tournament
description: Workstream A — GARCH/HAR volatility tournament benchmarked against the C2 deep-learning models on the SAME 1-min range target + 20k test bars (RMSE + QLIKE). Headline HAR-range (a 3-coefficient linear model, 2s CPU) wins both metrics, beating LSTM/NBEATS/Transformer on GPU. GJR>GARCH (leverage). EGARCH unstable.
type: explainer
---

# Workstream A — volatility tournament: HAR beats deep learning

> C2 showed deep learning beats naive/EWMA on 1-min volatility. Workstream A asks the real
> question: do the *proper* volatility models (HAR, GARCH family) beat both the baselines AND
> the GPU deep nets — on the **same** 1-min range target and **same** 20k test bars, judged on
> RMSE **and** QLIKE? **Answer: yes. A 3-coefficient HAR linear model, fit in ~2 seconds on
> CPU, is the best forecaster — better than the transformer on a GPU.**

---

## 1. The combined leaderboard (1-min range, 20,000-bar test, lower = better)

| Rank | Model | RMSE | QLIKE | lift vs naive | compute |
|---|---|---:|---:|---:|---|
| 🥇 1 | **HAR-range** | **0.000222** | **0.535** | **+17.8%** | 2 s CPU |
| 2 | LSTM (C2) | 0.000226 | 0.654 | +16.5% | 222 s GPU |
| 3 | NBEATS (C2) | 0.000231 | 0.709 | +14.7% | 36 s GPU |
| 4 | Transformer (C2) | 0.000233 | 0.767 | +13.9% | 575 s GPU |
| 5 | GJR-GARCH | 0.000240 | 0.565 | +11.2% | ~1 s CPU |
| 6 | GARCH(1,1) | 0.000244 | 0.624 | +9.6% | ~1 s CPU |
| 7 | EWMA(60) | 0.000245 | 0.594 | +9.2% | trivial |
| 8 | naive (persistence) | 0.000270 | 1.330 | 0% | — |
| ✗ | EGARCH | 0.000525 | 2.7e5 | −94% | unstable (see §4) |

(HAR/GARCH/EWMA/naive from `scripts/43_vol_garch_har.py`; DL rows from C2 `notes/39`.)

## 2. The headlines

1. **HAR-range wins outright — on BOTH metrics.** RMSE 0.000222 (beats LSTM's 0.000226) and
   QLIKE 0.535 (crushes LSTM's 0.654). HAR is just an ordinary least-squares regression of next
   range on three numbers — last range, the average of the last 6, and the average of the last
   30. Three coefficients, 2 seconds, CPU. It is the best volatility model we have.
2. **On QLIKE, every classical model beats every deep model.** HAR 0.535 < GJR 0.565 < EWMA
   0.594 < GARCH 0.624 — all below LSTM 0.654 < NBEATS 0.709 < Transformer 0.767. For
   risk-calibrated volatility (the metric that matters for sizing), the simple models dominate.
3. **GJR-GARCH > GARCH** (+11.2% vs +9.6%): adding the leverage/asymmetry term (down-moves spike
   vol more than up-moves) genuinely helps — the one place a fancier GARCH earned its keep.
4. **Deep learning is not worth it here.** The transformer needed a GPU and 575 s to land
   *fourth*, behind a 2-second linear model. This is the classic finance result: for volatility,
   simple structured models (HAR) beat flexible black boxes.

## 3. Why HAR wins (plain reasoning)
Volatility has two robust features: it's **persistent** (today's level predicts tomorrow's) and
**multi-scale** (recent minutes + recent hour + recent day all matter). HAR encodes exactly
that — three averages over short/medium/long windows — and nothing else, so it can't overfit.
The deep nets have to *learn* this structure from scratch and end up approximating it less
cleanly (and over-flexibly, hence worse QLIKE). When the true signal is "a weighted average of
recent volatility," the model that *is* a weighted average of recent volatility wins.

## 4. Honest caveat — EGARCH failed
EGARCH did not converge cleanly on 447k 1-min bars ("inequality constraints incompatible" during
MLE) and its σ→range mapping produced blown-up errors (QLIKE 2.7e5). It is **excluded as
unstable**, not as evidence. Fixing it (rescaling, bounded optimisation, or per-window refit)
is possible but low-priority given HAR already wins. The other GARCH variants (plain, GJR) fit
fine. IGARCH/GARCH-M/FIGARCH/realized-GARCH/HEAVY remain available to add, but the result is
unlikely to change: HAR-RV-type models are the known state of the art for realized volatility,
and that's what we see.

## 5. What this means for the project
- **Use HAR as the production volatility forecaster.** Cheap, robust, best-in-class here.
  Deep learning is not justified for volatility on this data.
- **Feed HAR's forecast into the cloned backtest engine** (Workstream G) for volatility-aware
  SL/TP sizing and as the volatility-regime confirmation for the flip detector (Workstream D).
  A ~+18%-over-naive vol forecast is where the risk-management edge comes from.
- This closes the "which volatility model" question: **HAR**, with GJR-GARCH as a useful
  asymmetry-aware alternative.

## 6. Status
- **Workstream A: DONE** (HAR/GARCH/GJR/EWMA/naive benchmarked; EGARCH flagged unstable).
- Combined with C1/C2, the volatility verdict is complete: **volatility is predictable; HAR is
  the best model; deep learning underperforms it.**
- Next per plan: **Workstream B** (OHLC multi-target) or **D** (flip committee) / **G**
  (combination tournament feeding HAR vol into the cloned engine).

## 7. One-paragraph summary (baby)
We pitted the proper volatility models against the GPU deep nets on the exact same task. The
winner is **HAR** — a tiny three-number linear formula (last range + average of the last 6 +
average of the last 30) that fits in two seconds on a CPU. It beat the LSTM, NBEATS and the
transformer on *both* accuracy (RMSE) and risk-calibration (QLIKE); in fact every classical
model beat every deep one on QLIKE. Adding asymmetry (GJR-GARCH) helped a bit over plain GARCH,
and EGARCH was numerically unstable and dropped. The lesson is the textbook one: for volatility,
the simple structured model that mirrors how volatility actually behaves (persistent, multi-scale)
beats the expensive black box. So HAR becomes our volatility engine, and it's what we'll plug
into the backtest for risk-sizing.
