---
name: phase-C1-results
description: Workstream C1 result — testing the "more data fixes the transformer" hypothesis by training NBEATS/LSTM/Transformer on 467k one-minute bars to predict next-minute price-return. Verdict - more data did NOT help; all three at best tie naive. Confirms next-bar price is unpredictable at 1-min too.
type: explainer
---

# Workstream C1 — does feeding the transformer 1-minute data finally beat naive?

> **The hypothesis (yours):** the transformer only lost the 4h tournament because ~1,500
> candles is too little; give it the **~487,000 one-minute bars** and it should learn to
> predict price.
> **The test:** train NBEATS, LSTM, and a Transformer on 1-min log-returns (467k train /
> 20k held-out test, on the GPU server) and compare price reconstruction to the naive guess.
> **The verdict: NO.** More data did not help. Best case = *tie* naive; worst case = far
> worse. Next-minute price is as unpredictable as next-4h price.

---

## 1. Results (GPU, 467,968 train bars, 20,000-bar held-out test, 10 epochs)

| Model | RMSE (model) | RMSE (naive) | lift vs naive | hit-rate | train time |
|---|---:|---:|---:|---:|---:|
| **naive** ("next price = last price") | — | **9.297** | 0.00% | — | — |
| LSTM | 9.2973 | 9.297 | **−0.005%** | 48.3% | 222 s |
| Transformer | 9.2970 | 9.297 | **−0.001%** | 50.3% | 575 s |
| NBEATS | 58.703 | 9.297 | **−531%** | 48.1% | 36 s |

Pulled to `server_runs/c1/c1_{lstm,transformer,nbeats}/result.json`.

## 2. What the numbers mean (plainly)

- **Nothing beat naive.** LSTM and the Transformer landed within **0.005%** of naive — i.e.
  they *converged to the naive answer itself*: they learned that the best 1-minute prediction
  is "price won't change," which is exactly what naive already says for free. They didn't add
  skill; they rediscovered the trivial answer.
- **NBEATS got 6× worse** (RMSE 58.7 vs 9.3): with no real signal, its extra flexibility just
  injects noise — the same "hallucination on a near-random series" we saw with TFT at 4h.
- **Hit-rate ≈ 50%** for all three (transformer 50.3% = a coin flip). No directional edge.

## 3. Why "more data" did not rescue it (the key insight)

More data only helps if there is a pattern to learn. We measured the 1-minute return
autocorrelation directly: **ACF(1) ≈ −0.006** — statistically indistinguishable from white
noise. There is no next-minute direction pattern, so **487k bars of "no pattern" is still no
pattern.** Worse, at 1-minute the **naive error floor is tiny** (RMSE ≈ 9.3 pts vs ≈ 134 at
4h) because price barely moves in 60 seconds — so "no change" is *nearly perfect* and beating
it is **harder**, not easier. Adding data made naive a tougher opponent, not the models smarter.

> Analogy: giving a student a million coin-flip records doesn't help them predict the next
> flip. The transformer, given more data, didn't learn to predict price — it learned to stop
> guessing (output ≈ "no change"), which is just naive in a costume.

## 4. So was the GPU/server effort wasted? No.

This is the value of the experiment: we **converted an assumption into a measured fact** on
real data + real GPU. We can now say with evidence — not hand-waving — that **deep learning on
high-frequency data does not predict next-bar price**, across NBEATS, LSTM, and Transformer,
at both 4h and 1-min. That closes the "but maybe with more data…" door for good.

It also proved the **server pipeline at scale**: a 467k-bar train + 20k-bar walk of 1-step
forecasts ran in 0.5–10 min/model on the GPU, logs streamed, results synced back. The same
machinery now points at the target that *is* predictable.

## 5. Where the 1-min data actually pays off (next: C2)

The same 1-minute data we just used has a **strong volatility signal**: |return| ACF ≈ 0.38,
range ACF ≈ 0.73 (vs −0.006 for direction). So the high-data deep models should be aimed at
**realized-volatility / range** (Workstream C2), where there is genuinely something to learn —
and benchmarked against the GARCH family (Workstream A). That is the productive use of this
compute, exactly as the volatility pivot (Phase F) predicted.

## 6. Status
- **C1 (price-return on 1-min): DONE.** NBEATS/LSTM/Transformer all fail to beat naive →
  hypothesis disproven. Updates the model-status audit (`notes/30`, `33`): the DL-on-price
  question is now settled at *both* timeframes.
- **C2 (volatility on 1-min): NEXT** — the real bet (await go-ahead).

## 7. One-paragraph summary (baby)
We tested whether giving the transformer a *lot* more data (467,000 one-minute bars instead of
~1,500 four-hour bars) would finally let it predict price. It did not. The LSTM and transformer
just re-learned the dumb "price won't change" answer (tying naive to within 0.005%), and NBEATS
did six times worse. The reason: one-minute price moves are essentially coin flips (we measured
near-zero autocorrelation), and over one minute the dumb guess is *almost perfect*, so there's
nothing to beat. The win from this run is certainty: deep learning does **not** predict next-bar
price, now proven on real GPU + real high-frequency data. The same data, however, is rich in
**volatility** signal — so that's where these models go next (Workstream C2).
