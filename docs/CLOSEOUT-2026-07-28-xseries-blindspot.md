# Closeout — The Cross-Series Blind Spot (2026-07-28)

**Issue:** #74 · **Branch:** `feat/74-xseries-blindspot` · **Spun off:** #75 (a wiring bug, deliberately
not fixed here) · **Follows:** #62 · **Status:** ✅ **CLOSED**

---

## 1. What was wrong

`bench_worstcase.py` built its context from **one** instrument. The four cross-series indicators read
`ctx.ref_close`, found `None`, returned all-zero votes immediately, and were reported at **0.00 s**.

That is a pass meaning **"never ran"**, not "cheap" — and it survived the whole of #62, whose headline
claim was "0 of 165 indicators over the 2 s budget". Measured properly, with an ES reference attached:

| indicator | before | after | speed-up |
|---|---:|---:|---:|
| `cointegration` | 8.26 s | 0.57 s | 14× |
| `rolling_corr` | 7.53 s | 0.53 s | 14× |
| `pca_factor` | 5.82 s | 0.35 s | 17× |
| `rolling_beta` | 5.76 s | 0.37 s | 16× |
| **together** | **27.4 s** | **1.9 s** | **14×** |
| **over the 2 s budget** | **4 of 4** | **0 of 4** | |

So #62's real number was *four over budget, 27.4 s unaccounted for*. And because
`core._cached_votes` deliberately never caches cross-series votes (the cache key does not encode the
reference), that 27.4 s would have been paid on **every single trial**.

---

## 2. The bigger thing this uncovered — #75

Measuring "does it emit anything?" before "how long did it take?" surfaced a **correctness** bug:

```
ctx_1m WITHOUT ref -> ref_close is None
ctx_1m WITH ref    -> finite ref bars: 50000 of 50000
pca_factor WITHOUT ref: non-zero = 0
pca_factor WITH ref   : non-zero = 99900
```

`runner.indicator_source_1min` builds `market_context(df1)` with **no `ref_df` argument, at every call
site in the repo**. So on the production `--ind-1min` path all four cross-series indicators are inert
regardless of `--reference`, while on the decision-TF path three of four are alive (522 / 802 / 765
non-zero votes). The optimizer only excludes them from the search when `ref_df is None`, so with a
reference configured they enter the search space and can never contribute.

**Filed as #75 and deliberately NOT fixed here.** Wiring the reference through turns four inert
indicators live, which changes optimizer results and could move champions. That is a behaviour change
and needs an explicit decision — not a drive-by commit inside a performance PR. #74 stays
result-neutral (golden 6/6). #75 also should not land until #74 has, or it lands 27.4 s of per-trial
cost at the same time.

---

## 3. Parity — and the three ways `pca_factor` fought back

`rolling_corr`, `rolling_beta` and `spread_zscore` are **bit-identical** on the real 486,969-bar frame
at every `n` tested (5, 8, 20, 50, 300), because their reductions go through `pw_sum` (#62).

`pca_factor` cannot be: its reference builds the covariance with a BLAS `@` product and calls LAPACK
`np.linalg.eigh` **per bar**. The closed-form 2×2 eigen-solve that replaces it disagreed in three
distinct ways, each found only by measuring, and each fixed:

| # | Failure | How it showed up | Guard |
|---|---|---|---|
| 1 | The eigenvector from `(cab, λ − caa)` **cancels catastrophically** near degeneracy | drift **0.156** and **3 flipped stances** at n=5 | rewritten as `θ = ½·atan2(2·cab, caa − cbb)`, well-conditioned everywhere |
| 2 | The score sits **on the sign boundary** — LAPACK snaps a near-diagonal covariance to an exact axis vector (score exactly 0.0) while a closed form leaves ~1e-18 | **12 flipped stances** at n=5 | recompute with the reference when `abs(score) < 1e-9` |
| 3 | The two eigenvalues nearly **coincide**, so the principal direction is undefined and the eigenvector error is ~1e-16/gap | drift **1.33** at n=3, on scores nowhere near zero | recompute when `gap ≤ 1e-6 · trace` |
| 4 | The primary **loading** is near zero, so `sign(pc1[0])` — which the indicator multiplies through — is decided by noise | a **well-conditioned** matrix (gap/trace = 0.14) came out exactly negated | recompute when `abs(u0) < 1e-8` |

Failure 4 is the instructive one: it bites on a matrix that is *not* ill-conditioned and a score that is
*not* near zero. No amount of "the answer looks fine" reasoning finds it — only a diff against the
reference on real data.

**The result is correct by construction, not by observation.** A bar trips a guard, or it is further
from its decision boundary than the drift (5.7e-14) can reach. Disagreement is impossible, not merely
unobserved. The fallback fires on **0.4%** of bars, so it costs nothing.

### Verified

| gate | result |
|---|---|
| real frame, n ∈ {5, 8, 20, 50, 300} | `rolling_corr`/`rolling_beta`/`spread_zscore` **bit-identical**; `pca_factor` **0 stance flips** |
| stress: 40 seeds × 7 window sizes, tick-quantised prices + flat stretches (280 configs) | **0 sign flips**, worst \|Δ\| 3.6e-15, fallback 0.44% of bars |
| worst-case scan **with** `--reference ES` | **0 of 165 over budget** — and this time the claim covers all 165 |
| full suite | *(§6)* |
| golden gate | *(§6)* |

---

## 4. The harness lied to me once

The parity phase reused the **cost scan's 20,000-bar context** while its own log said *"on the real
1-minute frame"*. It reported `pca_factor` drift 3e-14 and **0 flips** — reassuring, and wrong. Rebuilt
on the full 486,969 bars, the same code showed drift **0.156** and **12 flipped stances**.

The numbers were never false; the **population** was. It now rebuilds the context explicitly and prints
the bar count next to the verdict:

```
parity frame = 486,969 bars (cost scan used 20,000 — not reused here)
```

→ playbook rule **C17**: never let a cost subset leak into a correctness gate.

---

## 5. The scan can no longer hide this

`bench_worstcase.py` now:

1. takes **`--reference <token>`** and attaches the reference instrument's 1-minute frame;
2. distinguishes two things it used to conflate —
   * **void**: a cross-series indicator on a reference-free context *could not run*; its timing is not a
     measurement;
   * **quiet**: it *did* compute (the time is real) but voted nowhere — normal for a rarely-triggering
     veto, and `proj_bands` is one. Not a coverage problem;
3. **exits non-zero** when anything was void, because a budget claim that silently excludes indicators
   is worse than no claim. Verified: without `--reference` it now exits **1** and names all four.

The playbook's END-of-round command carries `--reference ES` and says why.

---

## 6. Verification results

All on the AMD server, real 486,969-bar NQ 1-minute frame with an ES reference.

| gate | result | log |
|---|---|---|
| cross-series cost, with a reference | **0/4 over budget · 27.4 s → 1.9 s** | `issue74_probe_after.log` |
| cross-series parity, full frame | 3/4 **bit-identical**; `pca_factor` **0 stance flips** | `issue74_probe_after.log` |
| worst-case scan `--reference ES` | **exit 0 — 0/165 over budget**, worst `rsi_connors` 1.53 s | `issue74_worstcase_withref.log` |
| worst-case scan **without** `--reference` | **exit 1**, names the 4 unmeasured — the guard is live | — |
| full test suite | **992 passed · 1 skipped · 0 FAILED** (963 → 992: +29 new gates) | `issue74_full_pytest.log` |
| golden gate | **6/6 ✅ byte-identical** — 4h $151,655/277 · 2h $101,518/173 · 1h $110,038/353 · 15m $82,156/654 · 5m $20,092/314 · 2m $31,898/276 | `issue74_golden.log` |

Golden staying 6/6 is expected and is *not* evidence that the accelerators are correct: no champion
enables a cross-series indicator, and #75 means they emit nothing on the 1-minute path anyway. The
evidence that they are correct is §3 — the real-frame diff and the stress sweep.

---

## 7. What changed

| file | change |
|---|---|
| `indicators/calc/xseries.py` | all four accelerated; verbatim `*_reference` oracles + numba-absent fallbacks; reductions via `pw_sum`/`pw_mean`/`pw_var`; `pca_factor` gets the closed-form eigen-solve plus the three-guard exact fallback; `_window_has_nan` replaces a per-bar `.any()` scan with an O(1) prefix count |
| `optimize/perf/probe_xseries.py` | **new** — the four-question harness (wiring · control · cost · parity) that produced every number here |
| `optimize/perf/bench_worstcase.py` | `--reference`; void-vs-quiet distinction; **exits non-zero on an incomplete measurement** |
| `optimize/perf/test_budget_accel_parity.py` | +7 tests: bit-identity for three, stance-identity for `pca_factor` on tick-quantised data, an end-to-end gate that asserts the vote is non-trivial before comparing, an inert-without-reference contract test, and a test that the fallback band is **live and still clear of the drift** |
| `docs/EXPANSION_ROUND_PLAYBOOK.md` | blind-spot section rewritten (closed); rules **C17**, **C18**; END-checklist command now passes `--reference ES` |

---

## 8. One paragraph

A scan that reported **0.00 s** was hiding **27.4 s** — four indicators that had never once been
measured, in a round whose headline was "0 of 165 over budget". They are now measured, accelerated 14×,
and inside the budget, and the scan **fails** rather than quietly excluding anything. Getting there
turned up a correctness bug worth more than the performance work (#75: the production 1-minute path
drops the reference entirely, so all four are inert), and `pca_factor` needed four separate fixes
because a closed-form eigen-solve disagrees with LAPACK in three independent ways — one of them on a
perfectly well-conditioned matrix. The through-line for both rounds: **ask what the code returned, not
just how long it took.**
