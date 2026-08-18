---
name: issue-103-prior-art-statistical-limit
description: "#103 part 2 — the decisive prior art. Bailey/Borwein/López de Prado/Zhu's Minimum Backtest Length, verified against the authors' own worked examples, then applied: our 1.38 years of history supports ~5 independent trials. We run 4,000–47,100."
type: research
date: 2026-08-03
issue: 103
---

# #103 part 2 — the limit is not the optimiser. It is the data.

The literature answers Q1 and Q3 more sharply than any search experiment could, and it answers them in
a direction the whole programme has not been accounting for.

**Every formula below was verified by reproducing the authors' own published worked examples before it
was applied to our numbers.** The verification is shown.

---

## 1. Minimum Backtest Length (MinBTL)

**Bailey, Borwein, López de Prado & Zhu (2014),** *"Pseudo-Mathematics and Financial Charlatanism: The
Effects of Backtest Overfitting on Out-of-Sample Performance"*, **Notices of the AMS 61(5), 458–471.**
DOI [10.1090/noti1105](http://dx.doi.org/10.1090/noti1105) ·
[PDF](https://www.ams.org/notices/201405/rnoti-p458.pdf) ·
[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659)

**Proposition 1, Eq. (4)** — expected maximum Sharpe from `N` independent trials whose *true* Sharpe is
zero:

```
E[max_N]  ≈  (1 − γ)·Z⁻¹[1 − 1/N]  +  γ·Z⁻¹[1 − (1/N)·e⁻¹]
```

`γ` = Euler–Mascheroni ≈ 0.5772; `Z⁻¹` = standard-Normal quantile. Upper bound: `√(2·ln N)`.

**Theorem 2, Eq. (6)** — the minimum years of history needed so that trying `N` configurations does
*not* hand you an in-sample Sharpe of `E[max_N]` that is really zero out of sample:

```
MinBTL  ≈  [ (1−γ)Z⁻¹(1−1/N) + γZ⁻¹(1−e⁻¹/N) ]²  /  ( E[max_N] )²      <   2·ln(N) / E[max_N]²
```

### Verification against the authors' published examples

| the paper says | recomputed here |
|---|---|
| *"if only five years of data are available, no more than forty-five independent model configurations should be tried"* | N=45 → **5.00 years** ✅ |
| *"after trying only seven independent strategy configurations, the expected maximum SR IS is 1 for a two-year long backtest"* | N=7 → **1.92 years** ✅ |
| *"if the researcher tries only N = 10 … she is expected to find a strategy with a Sharpe ratio IS of 1.57"* | N=10 → **E[max] = 1.57** ✅ |

Three for three. The implementation is correct.

---

## 2. Applied to this project

**We have 1.38 years of NQ 4h history (2025-01-01 → 2026-05-19, 2,119 decision bars).**

| what we run | N | MinBTL required | we have |
|---|---:|---:|---:|
| MAP-Elites default | 400 | **8.9 years** | 1.38 |
| MAP-Elites run | 4,000 | **13.2 years** | 1.38 |
| full NSGA-III study | 47,100 | **17.8 years** | 1.38 |
| all 7-of-165 structures | 5.8 × 10¹¹ | **49.5 years** | 1.38 |

### Inverted — the number that matters

> **With 1.38 years of data, the maximum number of independent trials that keeps an in-sample Sharpe of
> 1 meaningful is ≈ 5.**
>
> **We run 4,000 to 47,100.**

That is **824× to 9,699× over the limit**, if the trials were independent.

---

## 3. The honest caveat, and why it does not rescue us

`N` in MinBTL is the number of **independent** trials. The authors state this explicitly and recommend
PCA-style dimension reduction to obtain an effective `N` when trials are correlated. Our evaluations are
*not* independent — they share structure, and MAP-Elites mutations are drawn from a ~30-genome archive
(#101), which correlates them heavily.

So the true ratio is smaller than 824×. **But to be inside the limit, 4,000 correlated evaluations
would have to collapse to fewer than 5 effectively independent trials — a 99.88% reduction.** For a
47,100-trial study, 99.99%.

That is not a rescue. It is a measurable quantity, and measuring it is the obvious next step
(§6 below).

---

## 4. The corroborating instruments, and what they would cost us

### Deflated Sharpe Ratio — Bailey & López de Prado (2014)

*The Journal of Portfolio Management* 40(5), 94–107 ·
[PDF](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf) ·
[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)

```
SR₀ = √V[{SR̂ₙ}] · ( (1−γ)Z⁻¹(1−1/N) + γZ⁻¹(1−e⁻¹/N) )

DSR = Z[ (SR̂ − SR₀)·√(T−1) / √(1 − γ₃·SR̂ + ((γ₄−1)/4)·SR̂²) ]
```

Inputs: number of independent trials `N`, variance of trial Sharpes `V[{SR̂ₙ}]`, sample length `T`,
skew `γ₃`, kurtosis `γ₄`. Their worked example: a strategy reporting annualised Sharpe **2.5** over
**5 years** of daily data **fails** at 95% confidence once `N = 100` trials are disclosed — and would
have passed at `N = 46`.

**Directly relevant to us:** our returns are known to be fat-tailed (memory: per-trade tail ±$1,600),
which the DSR penalises through `γ₃`, `γ₄`. And our `T` is small.

### Probability of Backtest Overfitting (PBO) / CSCV

Bailey, Borwein, López de Prado & Zhu, *Journal of Computational Finance* 20(4), 39–69 ·
[PDF](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) ·
[SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253)

PBO = the probability that the configuration selected best in-sample lands **below the median
out-of-sample**. Estimated by combinatorially symmetric cross-validation: split the `T × N` performance
matrix into `S` blocks, form all `C(S, S/2)` train/test splits, and measure how often the in-sample
winner underperforms. Customary rejection threshold: **PBO > 0.05**.

**This is computable from data we already have** — Optuna stores the per-trial performance matrix.

### Multiple-testing haircut — Harvey & Liu (2015); Harvey, Liu & Zhu (2016)

*JPM* 42(1), 13–28 ·
[PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF) —
`p^M = 1 − (1 − p^S)^N`. Their example: 200 tests cut a 0.75 Sharpe to **0.32, a ~60% haircut**.

*Review of Financial Studies* 29(1), 5–68 ·
[PDF](https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF) —
**"A new factor needs to clear a much higher hurdle, with a t-statistic greater than 3.0"**, and *"most
claimed research findings in financial economics are likely false."* Their own framework: t ≈ 3.9 for
FWER 5%, 3.0 for FDR 1%.

---

## 5. What this does to #103's questions

| question | answer from the literature |
|---|---|
| **Q1** — is search in this space efficient/possible? | The *search* is not the binding constraint. **The data supports ~5 independent trials; we run thousands.** Coverage (10⁻³² from part 1) is a red herring next to this. |
| **Q3** — have we hit a dead end? | **Yes, but not the one we were looking for.** It is not that the algorithm cannot search 10^36.9 — it is that 1.38 years of history cannot *validate* a selection from it. |
| **Q4** — is there a better algorithm? | A better optimiser **makes this worse, not better**: it finds a higher in-sample maximum from the same `N`, and `E[max_N]` is exactly what MinBTL says is spurious. |

> **Q4's uncomfortable corollary: every search improvement we have shipped increases the in-sample
> maximum found from a fixed budget. Under MinBTL, that is the definition of the quantity that is
> spurious at this sample size.** Which is a coherent explanation of the #88/#101 record — 1 pass in 8,
> and the one pass evaporating when conditions changed (part 3).

This does **not** say the work was wasted or that the deployed book is invalid — the deployed champions
were selected under this same regime and are separately OOS-checked (#87 flags the same shortage from
the other side). It says the *marginal* return on making the search better is negative-to-zero until
the sample supports it.

---

## 6. What follows — measurements, not opinions

Three of these are computable from data already on disk:

1. **Estimate the effective number of independent trials** in a real study — PCA on the trial
   performance matrix, as the authors prescribe. This converts "824× over" into a measured number.
2. **Compute PBO via CSCV** on an existing Optuna study. Threshold already standard at 0.05.
3. **Compute the Deflated Sharpe Ratio** for the deployed champions, using our real `N`, `V[{SR̂ₙ}]`,
   `T`, skew and kurtosis.
4. **Re-examine the trial budget policy.** `TRIALS_PER_DIM = 100` scales trials *up* with dimensions —
   under MinBTL, raising `N` at fixed `T` strictly raises the overfitting floor. The
   dimension-proportional budget and the statistical budget point in opposite directions.

Each becomes a child issue.

---

## 7. Sources

- Bailey, Borwein, López de Prado & Zhu (2014). *Pseudo-Mathematics and Financial Charlatanism.* Notices of the AMS 61(5), 458–471. https://www.ams.org/notices/201405/rnoti-p458.pdf
- Bailey & López de Prado (2014). *The Deflated Sharpe Ratio.* JPM 40(5), 94–107. https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf
- Bailey, Borwein, López de Prado & Zhu (2017). *The Probability of Backtest Overfitting.* J. Computational Finance 20(4), 39–69. https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf
- Harvey & Liu (2015). *Backtesting.* JPM 42(1), 13–28. https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF
- Harvey, Liu & Zhu (2016). *… and the Cross-Section of Expected Returns.* RFS 29(1), 5–68. https://people.duke.edu/~charvey/Research/Published_Papers/P118_and_the_cross.PDF
- Bailey & López de Prado (2012). *The Sharpe Ratio Efficient Frontier.* J. Risk 15(2), 3–44 — MinTRL, the N=1 analogue.
