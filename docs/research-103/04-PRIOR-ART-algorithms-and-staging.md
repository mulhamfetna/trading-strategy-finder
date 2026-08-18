---
name: issue-103-prior-art-algorithms-and-staging
description: "#103 part 4 — what other fields learned. Staged optimisation has NO convergence guarantee for objectives like ours (Powell/Tseng); NAS measured the exact proxy-ranking failure our Stage A has, and it worsens as the space grows; and 'the harder you search, the worse it gets' is a named, quantified result in feature selection."
type: research
date: 2026-08-03
issue: 103
---

# #103 part 4 — the same problem, solved (and failed) elsewhere

Sources were gathered mechanically; every number I rely on below was either quoted verbatim from the
primary text or re-verified by me directly. Items I could not verify are marked **[unverified]** and are
not used to support any conclusion.

---

## 1. Q5, answered mathematically: staging has no guarantee for an objective like ours

The user asked for a mathematical answer rather than a judgement. It exists, and it is negative.

**Tseng (2001)**, *"Convergence of a Block Coordinate Descent Method for Nondifferentiable
Minimization"*, JOTA 109(3):475–494 ·
[PDF](https://www.mit.edu/~dimitrib/PTseng/papers/archive/bcr_jota.pdf), verbatim:

> **"If f is not (pseudo)convex, then an example of Powell (Ref. 28) shows that the method may cycle
> without approaching any stationary point of f."**

> **"If f is not differentiable, the coordinate descent method may get stuck at a nonstationary point
> even when f is convex … However, an exception occurs when the nondifferentiable part of f is
> separable."**

Tseng's assumed structure is `f = f₀(x₁…x_N) + Σₖ fₖ(xₖ)` — **only the smooth part may couple the
blocks.**

**Powell (1973)**, *Mathematical Programming* 4(1):193–201 — the counterexample, written out in
Wright's survey ([arXiv:1502.04759](https://arxiv.org/abs/1502.04759)):

```
f(x₁,x₂,x₃) = −(x₁x₂ + x₂x₃ + x₁x₃) + Σᵢ (|xᵢ| − 1)²₊
```

> *"coordinate descent with exact minimization, started near … one of the other vertices of the cube
> cycles around the neighborhoods of six points that are close to the six non-optimal vertices."*

And the detail that matters most for us — Tseng, on the sharpness of his own theorem:

> **"the Powell 3-variable example is convex in each variable."**

> **A function can be convex in every individual variable and staged optimisation still fails to reach
> a stationary point.**

### Does our objective satisfy any of the sufficient conditions?

| condition for convergence | our objective |
|---|---|
| convex / pseudoconvex | **No** — backtest P&L over indicator subsets is not convex in anything |
| differentiable | **No** — P&L is a step function of parameters; changing a lookback by 1 either flips a trade or does not |
| non-smooth part **separable** across blocks | **No** — indicators are combined through a `k`-of-`n` vote gate, so they interact by construction |
| unique minimiser along each coordinate | **No** — plateaus everywhere (many parameter values produce identical trades) |

**Not one holds.** There is no theorem that says our two-stage decomposition converges to anything.

Wright's survey states the general position:

> *"we cannot expect a general convergence result for nonconvex functions, of the type that are
> available for full-gradient descent."*

**This does not prove two-stage fails here.** It removes any theoretical basis for assuming it works,
which is what the user asked to establish. Whether it fails *in our case* is the empirical question in
**#104** — and part 2 of this section says what to expect.

---

## 2. The exact same proxy problem, measured: neural architecture search

Our Stage A ranks structures by `h(S) = f(S, θ₀)` — a cheap proxy — and hopes the ranking matches
`g(S) = max_θ f(S,θ)`. NAS does exactly this with weight sharing: rank architectures by their
performance inside one shared supernet instead of training each one.

**Yu, Sciuto, Jaggi, Musat & Salzmann, ICLR 2020**, *"Evaluating the Search Phase of Neural Architecture
Search"* · [arXiv:1902.08142](https://arxiv.org/abs/1902.08142). **Verified directly by me:**

| space | Kendall τ, proxy ranking vs true ranking |
|---|---:|
| RNN space | **−0.004** — *"entirely uncorrelated"* |
| CNN / NASBench-101 (423K architectures) | **0.195** |

And the part that should worry us most — τ by search-space size:

| cell size | architectures | τ |
|---|---:|---:|
| 4 nodes | 91 | **0.441** |
| 5 nodes | 2,500 | **0.314** |
| 6 nodes | 64,000 | **0.214** |
| 7 nodes | 423,000 | **0.195** |

> Authors, verbatim: **"the ranking disorder increases with the space complexity."**

**The proxy gets worse as the space grows.** Our library went **18 → 165**.

Corroborated independently — Zhang et al., [arXiv:2001.01431](https://arxiv.org/abs/2001.01431):
proxy-vs-truth τ ≈ **0.46–0.51**, against a truth-vs-truth baseline of **0.80**; and with sharing
removed entirely, **0.803**.

**Consequence for #104:** the NAS result is a *prediction*, not just an analogy. If our Stage A behaves
like every weight-sharing proxy that has been measured, #104 should return a **low** τ — and lower than
it would have been at 18 indicators. #104's pre-registered failure threshold (τ < 0.4) sits right in the
band NAS reports.

---

## 3. The field moved *away* from staging, deliberately

**Thornton, Hutter, Hoos & Leyton-Brown, KDD 2013**, *Auto-WEKA* ·
[arXiv:1208.3719](https://arxiv.org/abs/1208.3719). Abstract, verbatim:

> **"We consider the problem of simultaneously selecting a learning algorithm and setting its
> hyperparameters, going beyond previous work that addresses these issues in isolation."**

That is the CASH problem — *Combined* Algorithm Selection and Hyperparameter optimisation — and it is
structurally identical to ours: choose which components, and tune them. **The field's considered answer
was to stop separating them.** They also state why it is hard, in terms that describe our space exactly:

> *"the combined space … is very challenging to search: the response function is noisy and the space is
> high dimensional, involves both categorical and continuous choices, and contains hierarchical
> dependencies."*

**This is evidence for branch A over branch B** — but note it is evidence about *which decomposition*,
not about whether either can beat the statistical limit in part 2.

---

## 4. Is there a better algorithm? (Q4) — what exists, and at what scale

| method | space it was demonstrated on | surrogate |
|---|---|---|
| GP-based BO | *"approximately 10 dimensions and 10,000 datapoints"* — the folk limit, quoted in [arXiv:2512.00170](https://arxiv.org/abs/2512.00170) | Gaussian process |
| CoCaBO (ICML 2020) | max tested **22 continuous + 5 categorical** | GP + multi-armed bandit |
| Casmopolitan (ICML 2021) | **50 binary + 3 continuous**; **100 binary + 100 continuous** | GP + trust regions |
| SMAC (LION 2011) | **76 parameters** (CPLEX), mostly categorical | **random forest** |
| TPE (ICML 2013) | **238 hyperparameters** | tree-structured Parzen |
| Auto-WEKA (KDD 2013) | **786 hyperparameters** | random forest via SMAC |
| **ours** | **165 binary + 295 continuous ≈ 460 dimensions** | NSGA-III / MAP-Elites |

**Two honest readings:**

1. Our dimensionality is **not unprecedented** — Auto-WEKA searched 786. So "we exceeded what any
   algorithm can do" is **too strong**. The tools that operate at this scale are **random-forest
   surrogate methods (SMAC) and TPE**, both of which are *joint*, not staged.
2. But every one of those systems had **far more data per query than we do.** Auto-WEKA's failure mode
   is stated by its own authors: *"Auto-WEKA still shows larger improvements in cross-validation
   performance than on test data."* Which is our problem, in their words.

Casmopolitan's authors also give a specific reason CoCaBO-style bandit approaches will not scale for us:

> *"MAB requires pulling each arm at least once, and hence it is difficult to scale COCABO to
> high-dimensional problems, where the total number of possible arm combinations explode
> exponentially."*

---

## 5. "The harder you search, the worse it gets" — named, quantified, replicated

This is the literature's version of our own 1-in-8 record (part 3).

**Reunanen (2003)**, *"Overfitting in Making Comparisons Between Variable Selection Methods"*, JMLR
3:1371–1382 · [PDF](https://www.jmlr.org/papers/volume3/reunanen03a/reunanen03a.pdf). Comparing an
intensive search (SFFS) against a greedy one (SFS) on the Sonar dataset, verbatim:

> *"SFFS has attained at least as high a score as SFS in all the 60 cases … and the performance is
> actually **higher in 50** of these cases. Conversely … with respect to previously unseen test data,
> the subsets found with SFFS are better in **only 18** cases … which means that those found with SFS
> are actually better in **32** cases."*

> *"the mean difference in the **LOOCV-estimated** classification rates is **3.56 percentage points in
> favor of SFFS**, whereas the difference in the **actual test set** classification rates is **0.44
> percentage points on average — in favor of SFS!**"*

**The better search won in-sample and lost out-of-sample.** The paper's own framing: the gap between
those two columns *is* "the amount of overfitting due to an intensive search."

**Kohavi & John (1997)**, *Wrappers for feature subset selection*, Artificial Intelligence 97:273–324 ·
[PDF](https://ai.stanford.edu/~ronnyk/wrappersPrint.pdf), verbatim:

> *"**Because there are so many feature subsets, it is likely that one of them leads to a hypothesis
> that has high predictive accuracy for the holdout sets.**"*

**Schneider, Bischl & Feurer (AutoML 2025)**, *"Overtuning in Hyperparameter Optimization"* ·
[arXiv:2506.19540](https://arxiv.org/abs/2506.19540), verbatim:

> *"In approximately **10% of cases**, overtuning leads to the selection of a seemingly optimal HPC with
> **worse generalization error than the default or first configuration tried**."* — and it is worst
> *"particularly in the small-data regime."*

Also: **Loughrey & Cunningham (2004)**, titled *"Overfitting in Wrapper-Based Feature Subset Selection:
The Harder You Try the Worse it Gets"* — **[unverified: PDF unreachable; cited for its title only]**.

---

## 6. The bound that we comfortably PASS — and why it matters

It would be easy to conclude "the library is too big, shrink it". **The sparse-recovery literature says
otherwise.**

**Wainwright (2009)**, *IEEE Trans. Inf. Theory* 55(5):2183–2202 ·
[arXiv:math/0605740](https://arxiv.org/abs/math/0605740). Theorem 1, uniform Gaussian ensemble — a
**sharp threshold**: recovery succeeds iff

```
n  >  2·s·log(p − s) + s + 1
```

`n` = observations, `p` = candidate features, `s` = true sparsity. Computed for us (`p = 165`,
`n = 2,119` decision bars):

| s (indicators) | observations needed | we have | margin |
|---:|---:|---:|---:|
| 3 | 35 | 2,119 | **61×** |
| **7** | **79** | **2,119** | **27×** |
| 10 | 112 | 2,119 | 19× |
| 25 | 273 | 2,119 | 8× |

> **Identifying which 7 of 165 indicators matter is *not* the binding constraint. We have 27× the
> observations that bound requires.**

**Caveats, stated plainly:** this is for a *linear* model with Gaussian design and i.i.d. observations.
Ours is non-linear, our bars are autocorrelated, and the information-theoretic version carries a
`1/M²(β*)` factor — the smaller the true effect, the more data needed, and our effects are small. So the
27× margin is optimistic. But the **order of magnitude** is the point: the subset-identification bound
is in the tens-to-hundreds of observations, while the multiple-testing bound (part 2) is in the
**tens of years**.

**Those two bounds differ by roughly three orders of magnitude, and only one of them is violated.**

---

## 7. The independent third line: adaptive data analysis

**Dwork, Feldman, Hardt, Pitassi, Reingold & Roth**, *Science* 349(6248):636–638, 2015 ·
[arXiv:1411.2664](https://arxiv.org/abs/1411.2664), verbatim:

> *"in stark contrast to the non-adaptive case in which **n = O(log m / τ²)** samples suffice to answer
> **m** queries…"*

> *"The conservative approach of using fresh samples for each adaptively chosen query would lead to a
> sample complexity that **scales linearly with the number of queries m**. We observe that such a bad
> dependence is **inherent** in the standard approach of estimating expectations by the exact empirical
> average… Note that this requires only a **single round of adaptivity**!"*

**Our search is maximally adaptive** — evolutionary methods choose each new candidate *because* of the
results of previous ones. MAP-Elites mutates the archive; NSGA-III breeds from the front.

| our search | queries m | adaptive requirement | we have |
|---|---:|---:|---:|
| MAP-Elites run | 4,000 | ~4,000 observations | **2,119** |
| full study | 47,100 | ~47,100 observations | **2,119** |

**Blum & Hardt (ICML 2015)**, *The Ladder* · [arXiv:1502.04585](https://arxiv.org/abs/1502.04585) —
lower bound: *"no estimator can achieve error smaller than Ω((log k / n)^(1/2))"*, and this holds
**even for non-adaptively chosen candidates**. At `n = 2,119`: irreducible error **0.053** (k=400) to
**0.071** (k=47,100) on [0,1]-normalised scores.

---

## 8. What part 4 establishes

| question | finding |
|---|---|
| **Q5 — is two-stage mathematically sound?** | **No guarantee exists.** Our objective is non-convex, non-differentiable, non-separable and plateau-ridden; not one sufficient condition holds. Powell's counterexample is *convex in each variable* and still fails. |
| **Q5 — what will #104 find?** | NAS measures this exact proxy failure: **τ = −0.004 to 0.195**, and **degrading as the space grows**. #104's failure threshold (τ<0.4) is inside that band. |
| **Q6 — one stage or two?** | The field that faced our exact problem (CASH/Auto-WEKA) moved **deliberately from staged to joint**. Evidence for **branch A**. |
| **Q4 — is there a better algorithm?** | **Yes, and it is not exotic:** random-forest surrogate (SMAC) or TPE handle 238–786 dimensions. *"We exceeded all available algorithms"* is **too strong**. But every such system had far more data per query. |
| **is the library too big?** | **No.** Wainwright's sharp threshold needs ~79 observations to identify 7 of 165; we have 2,119 — **27× margin**. Shrinking the library does not address the binding constraint. |
| **is searching harder the answer?** | **The literature says the opposite, with numbers:** intensive search won in-sample by 3.56 pp and *lost* out-of-sample by 0.44 pp (Reunanen). |

---

## 9. Sources

- Tseng (2001). *Convergence of a Block Coordinate Descent Method for Nondifferentiable Minimization.* JOTA 109(3):475–494. https://www.mit.edu/~dimitrib/PTseng/papers/archive/bcr_jota.pdf
- Powell (1973). *On search directions for minimization algorithms.* Math. Prog. 4(1):193–201.
- Wright (2015). *Coordinate Descent Algorithms.* Math. Prog. 151(1):3–34. https://arxiv.org/abs/1502.04759
- Yu, Sciuto, Jaggi, Musat & Salzmann (ICLR 2020). *Evaluating the Search Phase of NAS.* https://arxiv.org/abs/1902.08142
- Zhang et al. (2020). *Deeper Insights into Weight Sharing in NAS.* https://arxiv.org/abs/2001.01431
- Thornton, Hutter, Hoos & Leyton-Brown (KDD 2013). *Auto-WEKA.* https://arxiv.org/abs/1208.3719
- Hutter, Hoos & Leyton-Brown (LION 2011). *SMAC.* https://www.cs.ubc.ca/~hutter/papers/10-TR-SMAC.pdf
- Bergstra, Yamins & Cox (ICML 2013). *Hyperparameter Optimization in Hundreds of Dimensions.* https://proceedings.mlr.press/v28/bergstra13.html
- Ru et al. (ICML 2020). *CoCaBO.* https://arxiv.org/abs/1906.08878
- Wan et al. (ICML 2021). *Casmopolitan.* https://arxiv.org/abs/2102.07188
- Reunanen (2003). *Overfitting in Making Comparisons Between Variable Selection Methods.* JMLR 3:1371–1382. https://www.jmlr.org/papers/volume3/reunanen03a/reunanen03a.pdf
- Kohavi & John (1997). *Wrappers for feature subset selection.* AI 97:273–324. https://ai.stanford.edu/~ronnyk/wrappersPrint.pdf
- Schneider, Bischl & Feurer (AutoML 2025). *Overtuning in Hyperparameter Optimization.* https://arxiv.org/abs/2506.19540
- Wainwright (2009). *Sharp thresholds for … sparsity recovery (Lasso).* IEEE TIT 55(5). https://arxiv.org/abs/math/0605740
- Dwork et al. (2015). *The reusable holdout.* Science 349(6248):636–638. https://arxiv.org/abs/1411.2664
- Blum & Hardt (ICML 2015). *The Ladder.* https://arxiv.org/abs/1502.04585
- Bergstra & Bengio (2012). *Random Search for Hyper-Parameter Optimization.* JMLR 13:281–305. https://www.jmlr.org/papers/volume13/bergstra12a/bergstra12a.pdf
- Li & Talwalkar (UAI 2019). *Random Search and Reproducibility for NAS.* https://arxiv.org/abs/1902.07638
- Yang, Esperança & Carlucci (ICLR 2020). *NAS evaluation is frustratingly hard.* https://arxiv.org/abs/1912.12522
