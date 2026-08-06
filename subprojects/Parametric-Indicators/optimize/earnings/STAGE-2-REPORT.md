---
name: ws-earn-stage-2-report
description: "WS-EARN Stage 2 (#111) — effective sample size, power analysis and the multiple-testing budget. Verdict: GO WITH LIMITS. The volatility effect is unambiguous; a directional edge is NOT detectable at 2.4 years, and the sample supports 2-6 approaches, not 2,000."
type: report
date: 2026-08-06
issue: 111
workstream: earnings
verdict: GO WITH LIMITS
---

# WS-EARN Stage 2 — can we detect an edge at all?

Run **before** Stage 3, deliberately. #103 established that the indicator search ran 4,000–47,100 trials
against a sample supporting ~5 independent ones, and 1 of 8 pre-registered criteria passed as a result.
That programme did its power analysis after years of searching. This one does it first.

Reproduce: `python3 optimize/earnings/stage2_power.py`

---

## The verdict in four lines

1. **The volatility effect is real and large** — announcement minutes move **4.98×** a matched
   non-announcement minute. That is not in doubt.
2. **A directional edge is NOT detectable** at this sample size. A rule would need to call direction
   correctly **~71% of the time** to register — implausible for a liquid, fully-scheduled event.
3. **The sample supports 2–6 independent approaches**, not 2,000. Searching harder makes this worse.
4. **The fix is sample size, not cleverness.** At 16 years the bar falls to **~59% accuracy**, which is
   an ordinary edge rather than a fantasy.

**GO WITH LIMITS** — see §7.

---

## 1. S2-C1 — effective sample size ✅ PASS

Two independent methods, agreeing exactly.

| horizon | raw events | **effective n** | lost to overlap |
|---|---:|---:|---:|
| 1 min | 116 | **113** | 3 |
| 5 min | 116 | **104** | 12 |
| 15 min | 116 | **94** | 22 |
| 30 min | 116 | **85** | 31 |
| 60 min | 116 | **83** | 33 |
| overnight (distinct days) | 116 | **83** | 33 |

**Effective n is a property of the horizon, not of the event list.** Two companies reporting 30 minutes
apart are two observations for a 5-minute window and one observation for a 60-minute window. Quoting a
single "n = 116" would overstate the sample for every window we actually care about.

Gap-collapse at 60 min = **83**. Distinct announcement days = **83**. Two different constructions,
identical answer. ✅

---

## 2. S2-C2 — what the moves look like

NQ index points, 116 events:

| window | mean signed | SD | mean absolute | worst | best |
|---|---:|---:|---:|---:|---:|
| 1 min | +2.86 | 26.21 | **16.95** | −84.5 | +128.5 |
| 5 min | +2.47 | 40.28 | **26.78** | −153.8 | +155.8 |
| 15 min | +2.97 | 62.15 | **42.22** | −247.8 | +185.8 |
| 30 min | +13.03 | 65.64 | **46.20** | −149.5 | +223.8 |
| 60 min | +19.02 | 93.49 | **68.20** | −203.5 | +350.0 |

At $20/point, the average 5-minute move is **$536 per contract**, with a worst case of −$3,076 and a
best of +$3,116. The tail is enormous — consistent with this project's standing finding that a fat
per-trade tail defeats most edges.

---

## 3. S2-C2/C3 — minimum detectable effect ✅ computed

MDE = smallest average per-event edge distinguishable from zero at 80% power, α = 0.05 two-sided.

| window | n_eff | SD (pts) | **MDE (pts)** | **MDE ($/contract)** |
|---|---:|---:|---:|---:|
| 1 min | 113 | 26.21 | **6.91** | **$138** |
| 5 min | 104 | 40.28 | **11.07** | **$221** |
| 15 min | 94 | 62.15 | **17.96** | **$359** |
| 30 min | 85 | 65.64 | **19.95** | **$399** |
| 60 min | 83 | 93.49 | **28.75** | **$575** |

### ⚠️ Cost is not the binding constraint — and framing it that way would have misled

Round-trip cost (precedent: `optimize/fundamentals/gc_costs.py`):

| scenario | cost | in NQ points |
|---|---:|---:|
| optimistic — commission only | $4.50 | 0.23 |
| **realistic — commission + 1 tick** | **$9.50** | **0.47** |
| stressed — commission + 2 ticks | $14.50 | 0.72 |

Every MDE is 15–60× the realistic cost. It is tempting to call that good news — *"any edge we could
detect would clear costs"* — and an earlier draft of this analysis did exactly that. **It is the wrong
comparison.** The question is not whether a detectable edge would be profitable; it is whether an edge
that large could plausibly exist.

A rule only earns a *fraction* of the move it trades. Expressed that way:

| window | MDE | mean absolute move | **share needed** | **implied directional accuracy** |
|---|---:|---:|---:|---:|
| 1 min | 6.91 | 16.95 | 40.7% | **70.4%** |
| 5 min | 11.07 | 26.78 | 41.3% | **70.7%** |
| 15 min | 17.96 | 42.22 | 42.5% | **71.3%** |
| 30 min | 19.95 | 46.20 | 43.2% | **71.6%** |
| 60 min | 28.75 | 68.20 | 42.2% | **71.1%** |

> **To be detectable at this sample size, a rule must call direction correctly about 71% of the time.**
> Strikingly constant across every horizon. For a liquid, heavily-traded, fully-scheduled event that is
> an extremely high bar.

---

## 4. S2-C4 — the multiple-testing budget ✅ computed

Using Bailey, Borwein, López de Prado & Zhu (2014) Prop. 1 — the formula #103 verified 3-for-3 against
the authors' own worked examples. A search of N independent approaches finds, **from pure noise alone**,
a best result of about `E[max_N]`. A real finding must beat *that*, not merely beat zero.

| N approaches | best-of-N from noise alone (t) |
|---:|---:|
| 5 | 1.19 |
| 10 | 1.57 |
| 50 | 2.28 |
| 100 | 2.53 |
| 500 | 3.05 |
| **2,000** | **3.45** |
| 10,000 | 3.86 |

At the 5-minute window (n_eff = 104, mean move 26.8 pts, SD 40.3 pts):

| directional accuracy | share of move | edge (pts) | \|t\| | **approaches affordable** |
|---:|---:|---:|---:|---:|
| 55% | 10% | 2.68 | 0.68 | **2** |
| 60% | 20% | 5.36 | 1.36 | **6** |
| 65% | 30% | 8.03 | 2.03 | 27 |
| 70% | 40% | 10.71 | 2.71 | 169 |
| 75% | 50% | 13.39 | 3.39 | 1,619 |
| 80% | 60% | 16.07 | 4.07 | 23,816 |

> ⛔ **"Try 2,000 approaches" is only justified if the edge is already ~75% accurate.** If it were that
> good we would not need 2,000 attempts to find it. At a realistic 55–60% the sample supports
> **2 to 6 independent approaches.**

This is the #103 trap in a new costume, and the number is now on the record *before* the search rather
than after.

---

## 5. Dumb control ✅ — and it separates the two questions cleanly

Identical measurement on random **non-announcement** days, matched for time-of-day (same clock minutes,
so a 16:05 event is compared against ordinary 16:05 bars, not against mid-session activity).

### (a) Size — is the announcement minute unusual?

| window | real mean absolute | control | **ratio** |
|---|---:|---:|---:|
| 1 min | 16.95 | 3.41 | **4.98×** |
| 5 min | 26.78 | 8.40 | **3.19×** |
| 15 min | 42.22 | 17.47 | 2.42× |
| 30 min | 46.20 | 26.25 | 1.76× |
| 60 min | 68.20 | 55.83 | **1.22×** |

**Unambiguous, and it decays fast.** Five times normal in the first minute, essentially gone by an hour.
Whatever is tradeable here lives in the first **1–15 minutes**, not the first hour. That is a concrete
design constraint for Stage 4.

### (b) Direction — or is it just a rising market?

NQ rose over 2024–2026, so *any* window measured long shows positive drift. Without this check the
market's own trend gets reported as a discovery.

| window | real mean signed | \|t\| | control mean signed | real − control |
|---|---:|---:|---:|---:|
| 1 min | +2.86 | 1.16 | −0.25 | +3.11 |
| 5 min | +2.47 | 0.63 | −0.74 | +3.22 |
| 15 min | +2.97 | 0.46 | −3.19 | +6.16 |
| 30 min | +13.03 | 1.83 | −2.96 | +15.99 |
| 60 min | +19.02 | 1.85 | −6.90 | +25.92 |

**No window reaches significance** (|t| < 1.98 everywhere; t computed against n_effective, not the raw
count). The directional drift is positive and consistently above control, but **not distinguishable from
zero at this sample size** — which is exactly what §3 predicted.

⚠️ None of these is a result. This stage measures *detectability*; it does not test a hypothesis.

---

## 6. ⭐ What would actually fix this

MDE shrinks as `1/√n`. **No amount of modelling skill changes that — only more events do.**

A 16-year NQ frame (2010→2026, plus a 1-second archive) already exists on the server via
`optimize/fundamentals/extended_data.py`. 12 companies × 4 quarters × 16 years ≈ 768 events.

| history | events | n_eff | share of move needed | **accuracy needed** | |
|---|---:|---:|---:|---:|---|
| **now (2.4 years)** | 116 | 104 | 41.3% | **70.7%** | ❌ implausible |
| 6 years | 288 | 206 | 29.4% | 64.7% | marginal |
| 10 years | 480 | 343 | 22.8% | **61.4%** | ✅ plausible |
| **16 years (server)** | **768** | **550** | **18.0%** | **59.0%** | ✅ plausible |

> **This is the whole finding.** At 2.4 years a rule needs ~71% directional accuracy to register —
> implausible. At 16 years it needs ~59% — an ordinary edge.
>
> **The sample, not the method, is the binding constraint.**

This mirrors #103 exactly, where #87 (more history) turned out to outrank every optimiser improvement.
Same conclusion, reached independently, on a completely different question. That is the kind of
agreement worth taking seriously.

---

## 7. S2-C5 — recommendation: **GO WITH LIMITS**

**Do not** run a large approach search on 2.4 years of data. It would reproduce #103 precisely: a
confident in-sample winner that evaporates, and months spent earning it.

**Do, in this order:**

1. **Extend the history to the 16-year server frame before Stage 4.** This is the single highest-value
   action available and it is cheap — the data exists and is already validated as 100.000% identical to
   our engine's file on the overlap. It moves the required accuracy from implausible to ordinary.
2. **Correct Intel's ~7-minute filing lag** (#110, criterion C5) and measure the offset for the other
   companies. At present INTC contributes a near-quiet 1.32× minute where the real event sits at 3.22×,
   which biases every effect-size estimate **downward**.
3. **Stage 3 prior-art pass** — free, and it may supply the theoretically-motivated hypothesis that a
   2-to-6-approach budget demands. With a budget this small, choosing *what* to test matters far more
   than how many things you test.
4. **Only then Stage 4**, with the approach count fixed in writing beforehand.

**If the history is not extended**, the honest budget is **2–6 pre-registered approaches** targeting the
1–15 minute window, and the likely outcome is "cannot tell" rather than a finding. That is a legitimate
result — but it should be chosen deliberately, not discovered afterwards.

---

## 8. Caveats

- ⚠️ **C4 (human verification of the timestamps) has not returned.** Counting and variance are
  insensitive to ±1-minute error, so this stage stands — but per-company numbers are provisional.
- ⚠️ **INTC's timestamps are ~7 minutes late**, biasing effect sizes downward.
- ⚠️ **Pre-market announcements are out of scope** after the universe narrowing — WMT and ASML were the
  only pre-open reporters. Not answered; not asked.
- ⚠️ The projection in §6 assumes the independent-window yield (83/116) and the move distribution hold
  over 16 years. Both are plausible and neither is verified.
- ⚠️ **Volatility is not direction.** A 4.98× spike says the market will move, not which way.
