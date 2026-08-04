---
name: issue-103-prior-art-quality-diversity-scaling
description: "#103 part 5 — the QD literature had already published the #88 diagnosis ('reduced selective pressure', 2016), already found stepping stones to be condition-dependent (validating #101's negative), and offers a resolution-invariant algorithm we are not using."
type: research
date: 2026-08-03
issue: 103
---

# #103 part 5 — quality-diversity at scale

Three findings here matter, and two of them are retrospective judgements on work we already did.

---

## 1. The #88 diagnosis was published in 2016. We rediscovered it in 2026.

**Vassiliades, Chatzilygeroudis & Mouret**, *"Using Centroidal Voronoi Tessellations to Scale Up
MAP-Elites"*, [arXiv:1610.05729](https://arxiv.org/abs/1610.05729); IEEE TEVC 22(4):623–630, 2018.
Verbatim:

> **"The increase in the number of niches results in reduced selective pressure, making the algorithm
> unable to cope with high-dimensional feature spaces even when memory is not a problem."**

> **"there is more selective pressure for performance when randomly selecting a parent from an archive
> of 1000 elites than from an archive of 1 million because the niches are bigger in the former case…
> as these niches get filled with solutions, selective pressure for performance decreases. In
> CVT-MAP-Elites, by having fewer niches (thus, solutions) and keeping the same selection method … we
> effectively increase selective pressure for performance."**

That is **#88**, ten years early: too many niches ⇒ selection stops working ⇒ the fix is *fewer niches*.
Our archive went 171 → 1,494 and we independently arrived at the same conclusion and the same remedy
(1,494 → 81).

> **This does not vindicate our measurement — it vindicates our reasoning.** #88's outcome test passed
> warm and failed cold. The mechanism, however, is a documented and named failure mode of this
> algorithm family, and the published fix is exactly the one we applied.

Note also: *"MAP-Elites has only been employed in settings with low-dimensional feature spaces (2 to 6
dimensions)."* Ours is 2-D. **Our behaviour space is not the problem** — the *resolution* was.

---

## 2. Our evaluations-per-niche is 1–3 orders of magnitude below every published setting

**No source states a rule of thumb.** But published configurations can be divided out:

| study | archive cells | evaluations | evals/cell |
|---|---:|---:|---:|
| MAP-Elites, real soft arm (2015) | 64 | 420 | ~6.6 |
| MAP-Elites, retina (2015) | 262,144 | 20.02M | ~76 |
| MAP-Elites, soft robots (2015) | 16,384 | 1.43M | ~88 |
| CMA-ME (2020) | 250,000 | 2.5M | ~10 |
| CMA-MAE (2023) | 10,000 | 360,000 | ~36 |
| FI-MAP-Elites (2022) | 256 | 524,288 | ~2,048 |
| QD survey, hexapod | ~15,000 filled | 20M | **~1,333** |
| **ours, measured (#101)** | **81** | **4,000** | **achieved 1.46** |

*(Ratios computed by me from each paper's stated budget and cell count; the papers do not state them.)*

> **Every published QD setting runs at 6.6 to 2,048 evaluations per cell. We achieve 1.46.**

And that is *after* #88 cut the archive from 1,494 to 81 cells. Before it, the achieved figure was
**0.08**. The relevant scarcity is not niches — it is evaluations that survive the feasibility gate
(#101).

---

## 3. #101's negative result is consistent with the literature — which never established the positive

I refuted stepping stones in #101 (1/8, peak got worse). The literature turns out **not** to support the
positive claim either.

The one study I found that actually compares *keeping* infeasible solutions against *discarding* them —
**Liapis, Yannakakis & Togelius (2015)**, *Constrained Novelty Search*, Evolutionary Computation
23(1):101–129 · [PDF](https://antoniosliapis.com/papers/constrained_novelty_search.pdf) — reports:

> *"the two-population constrained novelty search methods can create, **under certain conditions**,
> larger and more diverse sets of feasible game levels … **However, the best algorithm is contingent on
> the particularities of the search space and the genetic operators used.**"*

> *"**MCNS** [which kills all infeasible individuals] **unsurprisingly has far more feasible individuals
> than other methods** in all runs where a feasible individual was discovered."*

The famous pro-stepping-stone claim — **Kimbrough et al. (2008)**, FI-2Pop GA, *"the infeasible
population … is free to explore boundary regions, where the optimum is likely to be found"* — is
**diagnostic, not ablative**: it traces population centroids; it does not run with/without.

And **Constrained MAP-Elites** (Khalifa et al., GECCO 2018) and **FI-MAP-Elites** (Sfikas et al., 2022)
both build feasible/infeasible archives and **neither reports an ablation**.

> **There is no clean published ablation of "infeasible archive on vs off" inside a MAP-Elites archive.**
> #101 may in fact be one — a pre-registered, 8-seed, single-process A/B, which returned **negative**.

That reframes #101 from "a fix that failed" to **"a measurement the field had not made"**.

---

## 4. Q4, answered concretely for the QD branch: yes, there is a better algorithm

**Fontaine & Nikolaidis, *CMA-MAE*, GECCO 2023** · [arXiv:2205.10752](https://arxiv.org/abs/2205.10752):

> *"**CMA-ME suffers from three major limitations** highlighted by the QD community: prematurely
> abandoning the objective in favor of exploration, struggling to explore flat objectives, and having
> **poor performance for low-resolution archives**."*

> Footnote 1: *"**archive resolution affects the performance of all current QD algorithms.**"*

> *"**CMA-MAE is the first QD algorithm invariant to archive resolution.**"*

This is directly relevant to us: **#88 was a resolution problem**, we solved it by hand-picking a
resolution, and there exists an algorithm whose whole point is that you do not have to.

Reported gains, from the papers' own tables:

| | claim |
|---|---|
| CMA-ME vs MAP-Elites | *"more than doubles the performance"* — Hearthstone QD-score 63,296 vs 25,936 (**2.44×**) |
| CMA-MAE vs all derivative-free QD baselines | outperformed *"in all benchmark domains"*, two-way ANOVA F(12,320)=1958.34, p<0.001 |
| data efficiency | *"more than 10k generations for MAP-Elites to reach the same QD-Score as … CMA-ME imp after 500 generations"* |

**With the caveats the same papers report**, which matter given our record:

- CMA-ME is **worse than plain MAP-Elites** at 100×100 resolution on two of the CMA-MAE benchmarks
  (36.50 vs 41.64/49.07; 34.54 vs 47.07/52.20).
- CMA-MAE has a *"**performance cliff** … for archive resolutions under 200 × 200"*. **Our archive is
  9 × 9.**
- Multi-Emitter MAP-Elites: *"MAP-Elites is the top performing algorithm … for both the Redundant-arm
  and Hexapod-omni experiments."*
- Differentiable QD's CMA-MEGA scores **5.36** on LSI where plain CMA-ME scores **18.96**.

> **So: better QD algorithms exist and are well-validated — but the one whose selling point matches our
> defect has a documented cliff at a resolution 20× larger than ours.** That is a real finding, not a
> recommendation, and it needs its own test before adoption.

---

## 5. One budget result worth keeping

**Lim, Allard, Grillotti & Cully (TMLR 2022)** · [arXiv:2202.01258](https://arxiv.org/abs/2202.01258):

> *"reducing the number of generations by two orders of magnitude, and thus having significantly
> shorter lineage, **does not impact the performance of QD algorithms**."*
> *"**iterations are not important as long as the number of evaluations remains identical.**"*
> Measured: batch 131,072 × 39 iterations ≡ batch 256 × 19,532 iterations.

Relevant to how we spend a fixed evaluation budget — and it says the *shape* of the budget matters less
than we might assume.

---

## 6. What part 5 establishes

| | finding |
|---|---|
| was #88's reasoning right? | **Yes, and it was published in 2016** — *"increase in the number of niches results in reduced selective pressure"*, with fewer niches as the remedy |
| is our archive shape now sane? | 2-D behaviour space is normal (*"2 to 6 dimensions"*). **But 1.46 evals/cell is 4×–1,400× below every published setting** |
| was #101 wrong to fail? | **No.** The literature never established the positive; the only keep-vs-discard comparison reports *"contingent on the particularities of the search space"*. #101 may be the cleanest ablation on record — and it is negative |
| is there a better QD algorithm? | **Yes — CMA-MAE, explicitly designed to be resolution-invariant.** But it has a documented cliff below 200×200 and our archive is 9×9 |

---

## 7. Sources

- Mouret & Clune (2015). *Illuminating search spaces by mapping elites.* https://arxiv.org/abs/1504.04909
- Vassiliades, Chatzilygeroudis & Mouret (2018). *CVT-MAP-Elites.* IEEE TEVC 22(4). https://arxiv.org/abs/1610.05729
- Chatzilygeroudis, Cully, Vassiliades & Mouret (2021). *Quality-Diversity Optimization: a novel branch of stochastic optimization.* https://arxiv.org/abs/2012.04322
- Fontaine, Togelius, Nikolaidis & Hoover (2020). *CMA-ME.* https://arxiv.org/abs/1912.02400
- Fontaine & Nikolaidis (2023). *CMA-MAE.* https://arxiv.org/abs/2205.10752
- Fontaine & Nikolaidis (2021). *Differentiable Quality Diversity.* https://arxiv.org/abs/2106.03894
- Cully (2021). *Multi-Emitter MAP-Elites.* https://arxiv.org/abs/2007.05352
- Liapis, Yannakakis & Togelius (2015). *Constrained Novelty Search.* Evol. Comp. 23(1). https://antoniosliapis.com/papers/constrained_novelty_search.pdf
- Kimbrough, Koehler, Lu & Wood (2008). *FI-2Pop GA.* EJOR 190(2):310–327.
- Khalifa, Lee, Nealen & Togelius (2018). *Talakat: Constrained MAP-Elites.* https://arxiv.org/abs/1806.04718
- Sfikas, Liapis & Yannakakis (2022). *FI-MAP-Elites.* https://antoniosliapis.com/papers/a_general-purpose_expressive_algorithm_for_room-based_environments.pdf
- Lim, Allard, Grillotti & Cully (2022). *Accelerated Quality-Diversity through Massive Parallelism.* https://arxiv.org/abs/2202.01258
- Tjanaka, Chen, Fontaine & Nikolaidis (ICLR 2026). *Discount Model Search for QD in High-Dimensional Measure Spaces.* https://arxiv.org/abs/2601.01082
