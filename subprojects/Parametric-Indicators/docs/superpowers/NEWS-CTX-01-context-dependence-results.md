# NEWS-CTX-01 — Does the SAME announcement behave differently in different contexts? — Results

**Date:** 2026-07-23
**Branch:** `research-news-context`
**Spec:** `docs/superpowers/specs/2026-07-23-news-context-dependence-design.md`
**Status:** COMPLETE
**Verdict:** ❌ **NOT ESTABLISHED — the one candidate is a temporal FLUKE by our own pre-registered rule**

---

## 0. The answer in one paragraph

We asked whether the same macro announcement pushes NQ one way in one market state and the other way in
another — because if so, our headline "news is priced in" null could be two opposite effects cancelling out.
**One of twelve tests survived both dumb controls, and it was the theory-backed one.** But it then **failed the
temporal-stability gate**: the effect is **+0.236 in the second half of the data and −0.112 in the first**, so
it reverses. By the decision rule we fixed *before* looking, that is a **fluke, not a finding**. Nothing gets
built.

**The pooled null is confirmed, not overturned** — but read §4 before filing this away, because the way it
failed is unusually informative.

---

## 1. What was tested

Every previous directional news test in this project was **pooled** or split by event type. A pooled average is
exactly what two equal-and-opposite conditional effects produce, so "priced in on average" was never evidence
against "priced in differently in different states".

Three **pre-registered, causal** context splits — no others, because a wide sweep re-enters the
multiple-comparisons trap `Exp 43` already caught us in:

| Split | Buckets | Rationale |
|---|---|---|
| **C1 — policy-response regime** (PRIMARY) | `POS` vs `NEG`: sign of the Spearman correlation over the **previous 40 releases** | Theory-backed. *Fearing the Fed* (JFE 2024) says whether good news is good depends on expected Fed responsiveness |
| **C2 — volatility regime** | `CALM` vs `TURBULENT` (existing causal HMM daily labels) | Does news land differently when the tape is loud? |
| **C3 — prior trend** | `UP` vs `DOWN` vs 50-day MA | The classic McQueen–Roley conditioning |

**Data:** the committed 882-release ALFRED ledger, priced on the 16-year 1-minute NQ frame (5,452,534 bars).
865–871 releases priced per horizon.

**Statistic:** Spearman (Pearson reported alongside — mandatory on these fat tails). The decisive quantity is
the **difference between buckets**, not each bucket's own interval.

---

## 2. Sanity check — the pooled null reproduces exactly

| Horizon | Pooled Spearman | n |
|---|--:|--:|
| 5 min | −0.0073 | 870 |
| 15 min | −0.0225 | 871 |
| 30 min | −0.0020 | 870 |
| 60 min | −0.0000 | 865 |

Flat at every horizon, reproducing the known −0.004. Our pipeline is measuring the same thing the original
study did.

---

## 3. Results

### C1 — the primary, theory-backed split

| Horizon | ρ in `POS` regime | ρ in `NEG` regime | Δ | shuffle p | block p | 1st half | 2nd half | Stable? |
|--:|--:|--:|--:|--:|--:|--:|--:|:--:|
| 5 | +0.0608 (n=481) | −0.1023 (n=354) | +0.163 | 0.019 | 0.052 | −0.126 | +0.072 | ❌ |
| 15 | +0.0509 (n=501) | −0.1034 (n=335) | +0.154 | 0.038 | 0.032 | −0.050 | −0.016 | ✅ |
| 30 | +0.0798 (n=517) | −0.1225 (n=318) | +0.202 | 0.006 | 0.005 | −0.148 | +0.109 | ❌ |
| **60** | **+0.1021 (n=491)** | **−0.1290 (n=339)** | **+0.231** | **0.0020** | **0.0020** | **−0.112** | **+0.236** | ❌ |

At first glance this looks like a real finding: the sign is **consistent at every horizon** (positive
correlation in the `POS` regime, negative in the `NEG` regime), the gap **grows monotonically with horizon**
(0.163 → 0.154 → 0.202 → 0.231), and at 60 minutes it clears the Bonferroni bar (α = 0.00417) against **both**
controls.

**Then the temporal gate kills it.** At h=60 the effect is **+0.236 in the second half and −0.112 in the
first** — it does not merely weaken, it **reverses**. The same reversal appears at h=5 and h=30. The full-sample
result is driven **entirely by the recent half**.

### C2 and C3 — nothing

| Split | Best shuffle p | Verdict |
|---|--:|---|
| C2 volatility regime | 0.090 | No effect at any horizon |
| C3 prior trend | 0.103 | No effect; signs flip across horizons — the classic noise signature |

---

## 4. The part that deserves honesty

**A hypothesis about regime change is awkward to test with a stationarity test.**

Our temporal gate asks: *is the effect the same in both halves?* But *Fearing the Fed* says the mechanism
**changed around 2022** — good news stopped being good for stocks. An effect that is genuinely absent before
2022 and present after would **necessarily fail a first-half/second-half test**. The gate assumes stationarity;
the hypothesis is explicitly about non-stationarity.

And the pattern does fit that story: the first half is consistently **negative** at all four horizons (−0.126,
−0.050, −0.148, −0.112) while the second half is **positive** at three of four. The second half of an 882-release
ledger spanning 2010–2026 begins around 2018 and therefore contains the entire post-2022 period.

**We are not going to use this to rescue the result.** Two readings fit the same data:

1. A real regime-dependent effect that only became active recently.
2. A fluke in the recent window — which is what *every* near-miss in this project has turned out to be
   (the Asia session cell, `Exp 50`'s direction signal, the surprise signal that evaporated out-of-sample).

Nothing in this test distinguishes them, and the pre-registered rule says a sign flip across halves is a fluke.
**So the verdict is fluke.** Choosing the flattering interpretation after seeing the numbers is exactly the
failure mode the pre-registration exists to prevent.

### Two further reasons for caution

- **The effect sits barely above the detection floor.** Δ = 0.231 against a minimum detectable effect of
  **0.196**. We are resolving something at the very edge of what 882 releases can resolve.
- **C1 is partly self-referential.** Its label comes from the trailing correlation of *the same relationship
  being measured*. We added a **persistence-preserving block permutation** precisely for this — and the effect
  did survive it (p=0.002) — but self-referential conditioning still deserves more suspicion than an
  independent variable would.

---

## 5. Verdict

| Split | Verdict |
|---|---|
| **C1 policy-response regime** | ❌ **FLUKE** — beat both controls, reversed sign across halves |
| **C2 volatility regime** | ❌ **NULL** (underpowered below \|Δρ\| ≈ 0.214) |
| **C3 prior trend** | ❌ **NULL** (underpowered below \|Δρ\| ≈ 0.207) |

**0 of 12 tests beat both controls *and* were temporally stable.**

**The "news is priced in" conclusion stands** — and is now stronger than it was, because it has survived the
most credible remaining challenge to it rather than merely not having been challenged.

**Power caveat, stated plainly:** the worst-case minimum detectable difference was **\|Δρ\| ≈ 0.214**. Effects
smaller than that are *not* excluded by this study. The C2/C3 nulls mean "no large context effect", not "no
context effect".

---

## 6. What would actually settle it

Not more slicing of NQ — that is how you manufacture a false positive from a fixed 882 releases.

**Cross-instrument replication.** If the C1 pattern is a real macro mechanism, it must appear on **ES, RTY and
GC** too, since they all price the same US macro releases. If it appears only on NQ, it is noise. This is
exactly the test that killed the Asia session cell (0 of 3 indices replicated), and it is the cleanest
available discriminator between the two readings in §4.

That is a well-defined next workstream, and this study's harness already does everything needed except point at
another instrument.

---

## 7. What went well / what went wrong

**Went well**
- **The pre-registered decision rule did its job.** It stopped a result that beat two dumb controls, had a
  consistent sign across four horizons, a monotone dose-response in horizon, and a published theory behind it.
  Without the temporal gate fixed in advance, this would very likely have been written up as a discovery.
- **The added block control was the right instinct.** Suspecting C1's self-referential labelling, we built a
  harder null that preserves label persistence. It happened to *confirm* the effect rather than kill it — which
  is what a fair control looks like.
- **The pooled null reproduced exactly**, validating the pipeline against prior work.
- **The prior-art pass paid for itself**: it supplied the primary hypothesis, the mechanism, and — critically —
  the disconfirming evidence (Poitras 2004) that kept expectations honest.

**Went wrong**
- **The stationarity gate is a blunt instrument for a non-stationarity hypothesis** (§4). We used it anyway
  because it was pre-registered, but the right design would have specified the discriminator (cross-instrument
  replication) *in advance* rather than discovering the need afterwards.
- **C1's self-referential construction** is a genuine design weakness. An independent regime proxy — the
  stock-bond comovement *Fearing the Fed* actually uses — would be cleaner, but needs bond futures we do not
  have loaded.
- The first run aborted on a path off-by-one (`parents[1]` vs `parents[2]`); now covered by a regression test.

---

## 8. Reproduce

```bash
# server, from ~/Mulham/news-context/subprojects/Parametric-Indicators
env WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data \
  /home/dev/Mulham/.venv/bin/python3 -m research.news_context.run_study \
  --k 40 --horizons 5,15,30,60 --ma-days 50 --draws 1000 --seed 20260723 --block 20
```

Outputs (pulled to local and committed): `results/news_context/context_dependence.csv`, `run.log`.
Unit tests: `python3 -m pytest tests/test_news_context_*.py` → **18 passed**.
