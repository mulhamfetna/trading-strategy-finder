# Study — Does Predicting `exp(return)` Fix the "Near-Zero Values" Problem?

> **Hypothesis tested:** log-returns are tiny numbers near zero (~0.005). Maybe that near-zero-ness
> hurts the model. If we instead predict `exp(log-return) = exp(ln(c_t/c_{t-1})) = c_t/c_{t-1}`
> (the **gross ratio**, a number near 1.0), would close-price prediction improve?
>
> **Verdict: No.** It is mathematically the same prediction problem and empirically gives the
> identical RMSE. The "near-zero" framing is a red herring — the obstacle is signal-to-noise,
> which does not change when you rescale the target. Evidence below.

---

## 1. What `exp(return)` actually is

$$
exp(return) = exp( ln(c_t / c_{t-1}) ) = c_t / c_{t-1}  =  the gross ratio G_t
$$

So predicting `exp(return)` *is* predicting the gross price ratio — a number centered at **1.000160** instead of the log-return's **0.000144**. Same data, shifted by ~1. To get the close back: `ĉ_t = c_{t-1} × Ĝ_t`.

The hypothesis is reasonable on its face: "near-zero targets with tiny variance might confuse a model; targets near 1.0 might train better." Let's test it rigorously.

---

## 2. Why theory says it CANNOT help

`exp()` is a **strictly increasing, invertible (monotone) transformation**. Three consequences:

1. **Information is preserved exactly.** Knowing `G_t` ⟺ knowing `r_t = ln(G_t)`. Nothing is gained or lost — it's the same number relabeled.
2. **Correlation is (near-)invariant.** Linear predictability — autocorrelation, the thing every forecaster exploits — is invariant under affine rescaling and approximately invariant under `exp` for small values. So the predictable structure is unchanged.
3. **Signal-to-noise is scale-free.** "Near zero" vs "near 1" is just a shift; the *ratio* of predictable-signal to unpredictable-noise is identical. Rescaling the y-axis doesn't make a cloud of points less of a cloud.

For models that standardize inputs (Prophet, ARIMA, and our Darts setup all do), the absolute scale of the target is divided out *before fitting anyway* — so near-0 vs near-1 is literally invisible to them.

---

## 3. Empirical proof #1 — autocorrelation is identical

Measured on all 2,119 NQ 4h bars:

| lag | log-return `r` | gross ratio `e^r` | simple `e^r−1` |
|---:|---:|---:|---:|
| 1 | 0.0680 | 0.0686 | 0.0686 |
| 2 | 0.0224 | 0.0225 | 0.0225 |
| 3 | −0.0202 | −0.0208 | −0.0208 |
| 5 | −0.0537 | −0.0543 | −0.0543 |
| 10 | 0.0440 | 0.0438 | 0.0438 |

The differences are in the 3rd–4th decimal (from `exp`'s mild nonlinearity over the data range) — **predictability is identical.** Whatever a model could extract from the gross ratio, it could extract equally from the log-return, and vice versa.

---

## 4. Empirical proof #2 — head-to-head RMSE on the close

Walk-forward on 2026 (trailing-100 mean predictor on each target, reconstructed to price, scored against actual close):

| Target predicted | Reconstructed-price RMSE ($) | vs naive |
|---|---:|---:|
| **naive** (price = previous close) | **133.59** | — |
| **log-return** `r`, then `ĉ = c_prev·exp(r̂)` | 133.84 | −0.19% |
| **gross ratio** `e^r`, then `ĉ = c_prev·Ĝ` | **133.84** | −0.19% |

**The gross-ratio RMSE (133.84) equals the log-return RMSE (133.84) to the penny.** Both land just behind naive. Predicting `exp(return)` changed *nothing*. This is the empirical confirmation of the theory in §2.

---

## 5. The one real (but negligible) difference — Jensen's inequality

There IS a genuine mathematical subtlety, worth noting for rigor:

When you forecast a **log-return** `r̂` and exponentiate to get a price, the result is slightly **biased** because `E[exp(r)] ≠ exp(E[r])` (Jensen's inequality). The unbiased reconstruction needs a small correction:

$$
ĉ_t = c_{t-1} × exp( r̂ + σ²/2 )      ← the +σ²/2 is the bias correction
$$

Predicting the **gross ratio directly** sidesteps this — you never take the exp of a forecast, so no bias creeps in. So there's a *theoretical* tidiness argument for the ratio. But the magnitude:

$$
σ²/2 = (0.005655)² / 2 = 1.6 × 10⁻⁵ = 0.0016% of price
on a $25,000 price → $0.40
$$

**$0.40 on a $133 RMSE** — about 0.3% of the error, swamped by noise. It is not the difference between success and failure; it's a rounding error. (If you ever did need maximum precision, the cleaner fix is to add the `+σ²/2` term to the log-return reconstruction, not to switch targets.)

---

## 6. Why the "near-zero" intuition feels right but isn't

The intuition comes from a real phenomenon in **neural network training**: targets with tiny magnitude and tiny variance *can* cause vanishing-gradient / precision issues **if fed in raw**. But:

1. **We standardize.** Every model here z-scores or min-max-scales the target before fitting, which maps near-zero log-returns to unit variance anyway. The raw scale never reaches the optimizer.
2. **The classical models (ARIMA/Prophet) are scale-equivariant** — they fit the same model whether you feed `r` or `1000·r`; the coefficients just rescale.
3. **The problem was never numerical.** The models didn't fail because the numbers were small — they failed because the *autocorrelation* (the learnable signal) is ~0.07. Making the numbers bigger (×1000, or +1 via `exp`) leaves that 0.07 exactly where it was.

Analogy: if you're trying to hear a faint radio station through static, **turning up the volume amplifies the static just as much as the signal.** Rescaling the target is turning up the volume. The signal-to-noise ratio — the thing that matters — is unchanged.

---

## 7. What WOULD actually change the result

Not a transform of the same target, but a *different target* with more inherent signal:

- **Predict the range / volatility** (`high−low`), which has autocorrelation 0.56 instead of 0.07 — see `17_ohlc_will_it_help.md`. This is the real lever.
- **Predict direction as a classification** and optimize hit-rate, not RMSE.
- **Add new information** (order-flow, VIX, macro) the price series doesn't already contain.

These change the *signal*, not just the *units*. That's the difference between a productive pivot and a relabeling.

---

## 8. One-paragraph summary

Predicting `exp(return)` means predicting the gross price ratio `c_t/c_{t-1}` (near 1.0) instead of the log-return (near 0). Because `exp` is a monotone invertible map, the two carry identical information, have identical autocorrelation (0.068 vs 0.069), and — proven empirically — produce the identical reconstructed-price RMSE (133.84 = 133.84), both just behind naive. The "near-zero values" concern is a red herring: every model standardizes the target before fitting, so the absolute scale is invisible, and the real obstacle (signal-to-noise of ~0.07 autocorrelation) is scale-invariant — amplifying the target amplifies the noise equally. The only genuine difference is a Jensen's-inequality bias of ~\$0.40 on a \$133 error, negligible and better fixed with a `+σ²/2` term than a target switch. To actually improve, change *what* you predict (range/volatility, ACF 0.56), not the *units* of the same unpredictable thing.
