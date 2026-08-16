---
name: ws-news2-final-report
description: "WS-NEWS2 closeout: the complete record of round two of the news study — what was asked, what was built, every experiment and its result, the twelve corrections made along the way, and the single conclusion four independent attacks now support."
type: report
date: 2026-08-15
issues: [109, 111, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123]
---

# WS-NEWS2 — final report

**Four independent attacks. Four real, replicated effects. Not one of them tradeable.**

That is a finding about the problem, not a failure of the method — and it is worth far more than
another inconclusive maybe.

---

# PART 0 — WHAT WAS ASKED, AND WHAT CAME BACK

## The brief

> *"We will study all the news — each news alone, not combined — on all instruments. A news release may
> affect the oil a lot but not that much on nasdaq, so we trade oil. Using previous, forecast and actual
> to extract POWER and DIRECTION."*

In three phases: **before** the release, **after** the release, and **at** the release.

## The answer

| phase | question | answer |
|---|---|---|
| **1** | can we position **before** a release using what is known in advance? | ⛔ **No.** A tradeable edge is **excluded at 95%** on 8 instruments |
| **2** | does the **surprise** carry power and direction? | ⭐ **Yes, enormously** — ρ up to −0.63 — ⛔ **and it is not tradeable** |
| **3** | can we execute **at** the release? | ⏳ open, and Phase 2 leaves it **no viable target** |

## ⭐⭐⭐ The one-sentence result

> **The surprise explains the release-minute jump extremely well and explains essentially nothing
> afterwards. What we can measure, we cannot reach; what we can reach, is not there.**

---

# PART 1 — THE NUMBERS

| | |
|---|---|
| calendar acquired | **39,221** US events, 2013 → 2026, with actual + forecast + previous |
| usable after the DST constraint | **2016 →** |
| instruments | **8** (of 9 — YM's aggregation is empty) |
| price history verified | **~5M bars each**, 100.0000% agreement with the engine's own frames |
| pairs in the decidable matrix | **643** |
| pairs with adequate power | **612** |
| **pairs reaching the tradeable threshold** | **0** |
| statistically significant effects found | **24** (23 jump-inclusive + 1 post-jump) |
| ledger claims, all re-derived on demand | **18/18** |
| historical defects the harness rejects | **5/5** |

---

# PART 2 — WHAT WAS BUILT

## 2.1 The data (#114, #121)

Seven consensus sources failed on access or on dates. **TradingView's public calendar** was the eighth
and it worked — 39,221 US events with all three numbers and real UTC timestamps.

⚠️ **And it is DST-broken before 2016**: 87 series are an hour late in summer (2014: 90% of series
inconsistent). Discovered because I had verified the timestamps **on one series** — Nonfarm Payrolls,
which happens to be the one that is clean.

The owner then supplied long price history for the six missing instruments. **All eight frames passed a
purpose-built acceptance gate**: 100.0000% identical closes on the overlap with the engine's own data,
volume-profile ρ = 1.000.

## 2.2 The verification system (#118)

Built **before** the data was used, because the project's expensive failures were never bad analysis —
they were plausible data accepted without a check that could have failed.

> **A check was run, it passed, and the check was not capable of failing.**

So three verifications that must fail for **different** reasons:

| | catches | ⚠️ blind to |
|---|---|---|
| **V1** re-derivation, different code path | implementation bugs | **bad input** |
| **V2** independent source | bad input | **a shared convention error** |
| **V3** falsification | **an instrument that cannot fail** | needs imagination |

Plus two structural gates that fail before any measurement: **every claim must declare its blind spot**,
and **every claim must have a V3**. And a ledger in which **no number is publishable unless a script
re-derives it from the committed file it came from**.

⭐ **The harness is tested by being made to fail** — five real historical defects replayed as originally
published, all five rejected.

## 2.3 Provenance (#119, #120)

| field | verdict | evidence |
|---|---|---|
| `actual` | ✅ **FIRST PRINT** | 4 series, 503 releases: 100%/100%/99% match to the first print, **0%** to the revised value. March 2020 payrolls were revised −701k → **−1,398k**; TradingView carries −701k |
| `previous` | ✅ **POINT-IN-TIME** | 99%/98%/99% match to the value that stood that morning, **0%** to today's. ⭐ **A back-fill cannot produce this** — it needs a per-series vintage archive |
| `forecast` | ⚠️ **not verifiable** | **no consensus archive exists.** No evidence of contamination: a planted copy is caught at 100% while the real rate is 0.8% |

---

# PART 3 — EVERY EXPERIMENT

## Phase 1 (#115, #122) — before the release

| test | scope | result |
|---|---|---|
| **H1-A** survival | 8 instruments | ⚠️ **NOT universal.** NG survives only **70.1%** of a 5-min wait at a 0.40% stop |
| **H1-A** danger signature | 8 instruments | ⚠️ **equity indices + gold only.** CL, NG, SI sit at or **below** 1.0 |
| **H1-B/C** direction | 16 runs | ⛔ **14 NEGATIVE, 1 VOID, 1 rejected by controls, 0 positive** |

⭐ **A tradeable edge was excluded at 95% in 16 of 16 runs** — highest accuracy upper bound **58.3%**
against a **71%** break-even.

⭐⭐ **The null counts because of the planted-effect probe**: a synthetic effect was planted and the
pipeline had to find it. Study resolution ≈ 0.195; smallest detected 0.15. **The absence is an absence,
not a failure to look.**

## Phase 2 (#116) — the surprise

| stage | result |
|---|---|
| **S0** validity | ✅ reproduces gold's known inverse response (ρ = −0.273 vs round 1's −0.193), **Pearson blind in both** |
| **S1** features | ✅ prefix invariance **0/303**; a planted full-sample z-score caught **207/207** |
| **S2** power | ✅ **612 powered**, 31 VOID (≈ the ~30 expected by chance) |
| **S3** release reaction | ⭐ **23 survivors**, ρ to **−0.63**, p to **1.9e-10**, controls null |
| **S4** capturable window | ⭐ **1 survivor** of 612 |

### ⭐⭐⭐ The decisive measurement of the whole programme

Re-measuring S3's 23 survivors with the release-minute jump removed:

| | jump-inclusive ρ | **post-jump ρ** | p |
|---|---|---|---|
| NQ Inflation Rate MoM | −0.586 | −0.146 | 0.149 |
| RTY Core Inflation YoY | −0.631 | −0.071 | 0.576 |
| GC Non Farm Payrolls | −0.530 | −0.050 | 0.620 |
| **CL API Crude Oil** | −0.512 | **−0.247** | **0.000** |

**22 of 23 collapse to noise.** Seven had point-estimate accuracy above 71% — **none had a lower bound
that reached it.**

## #123 — the one survivor, chased down

| | |
|---|---|
| provenance | ⛔ **cannot be verified** — a private trade-association report, no public archive, nothing in FRED/ALFRED |
| mechanism, premise | ⭐ API forecasts EIA at **ρ = +0.742, p = 3.7e-51** — so the repricing story is **possible** |
| mechanism, discriminator | ⚠️ right direction (−0.284 → −0.149) but **Fisher z p = 0.237** — the design could only resolve an outright reversal |
| tradeable | ⛔ **57.4%** [51.2, 63.4] vs 71% |

---

# PART 4 — ⭐ THE TWELVE CORRECTIONS

Every one caught before it reached a conclusion. Listed because the point of the verification system is
that this list exists at all.

| # | what I published or built | what was true |
|---|---|---|
| 1 | *"daylight saving is correctly encoded"* | **87 pre-2016 series are an hour late** — verified on 1 series of 649 |
| 2 | *"1.31–2.92× more dangerous"* | **appears in no result file** |
| 3 | *"`Inflation Rate Mom` is TradingView's casing, verified"* | **no such title exists** |
| 4 | *"the matrix is 927 pairs"* | **I counted the event side and never checked the price side** |
| 5 | *"EIA → CL, ~510 releases"* | the CL frame reached **79**. And EIA → NQ reached 545 |
| 6 | *"EVIDENCE OF CONTAMINATION"* (the revision test) | **the test was confounded** — both hypotheses predict the same sign |
| 7 | the acceptance gate | **rejected 5 of 7 good files** |
| 8 | the Phase 1 probe | **voided an instrument on a single coin flip** |
| 9 | *"4.27×"*, then *"4.37×"* | **17 events against one** — CI [2.23, 125] |
| 10 | H1-C's anchor | measured the **post-jump residue**, overturning Phase 1's only positive |
| 11 | the S2 probe | **four** fixes — grid ceiling, threshold, hypothesis, metric |
| 12 | the pre-registration file | **had never been committed** |

## ⭐ The rules these produced

> 1. **A check that passes on a sample must state the sample and the population.**
> 2. **State the anchor to the bar AND the side of the bar.** Open-versus-close was the difference
>    between a 5.5σ effect and noise.
> 3. **When a gate rejects most of its subjects, read it as evidence about the gate first.** Five for
>    five here.
> 4. **A metric moving in the right direction is not evidence the cause has been found.**
> 5. **Design the falsifier so the innocent and claimed explanations predict DIFFERENT signs.**
> 6. **A join has two sides, and an `n` quoted from one of them is not an `n`.**
> 7. **Compute the detectable effect size BEFORE a split-sample test.**
> 8. **Before labelling something "unverified", establish whether it is verifiable.**

---

# PART 5 — ⭐⭐ THE THROUGH-LINE

| workstream | what was found | why it did not pay |
|---|---|---|
| **WS-EARN** (#109–113) | earnings move NQ **4.98×** | **magnitude, not direction** — and we cannot express magnitude with 1 contract and no options |
| **round 1 / S0** | gold responds to macro surprises at **5.5σ** | **62–63%** accuracy against a 71% break-even |
| **Phase 2 / S3** | surprises explain the release jump at **ρ −0.63** | **over before the input is knowable** |
| **#123** | a real post-release drift on crude | **57.4%**, unverifiable, unexplained |

> ⭐⭐⭐ **Every effect is either the wrong KIND of quantity — magnitude when we can only trade direction
> — or it arrives on the wrong SIDE of the moment we could act.**

**Two structural obstacles, found four separate ways.** Neither is a measurement problem, and neither
is fixed by more data or a better model.

## ⚠️ And one of them is fixable — but not by research

The **magnitude** obstacle is architectural: `pnl = pnl_points × pv`. **There is no quantity term in the
engine.** Every "the move is 4.98× normal" result in this programme is unusable *because we cannot size
a position*, not because the effect is absent.

> **That is an owner decision about the engine, not a research question — and it is the single change
> that would make the largest body of confirmed findings in this project actionable.**

---

# PART 6 — WHAT WENT WELL, WHAT WENT WRONG

## What went well

1. ⭐⭐⭐ **Every negative carries a planted-effect probe.** No null in this workstream is
   indistinguishable from a broken pipeline.
2. ⭐⭐ **The decision number was measured, not inferred.** Directional accuracy with an interval turned
   "no effect detected" into "a tradeable edge is excluded at 95%" — and stopped seven point estimates
   above 71% from reading as a trading system.
3. ⭐ **The verification system caught its own author twelve times**, including two published figures
   and a defect already shipped in Phase 1.
4. **The economics came out right without being imposed** — inflation negative on all equity indices and
   gold, jobless claims positive.
5. **The unverifiable finding was attacked from a falsifiable direction** rather than abandoned or
   over-claimed.

## What went wrong

1. ⚠️ **Twelve corrections is a lot.** The system caught them, but a slower first pass would have
   produced fewer.
2. ⚠️ **Five separate gates rejected healthy data on first contact.** The pattern is consistent enough
   to be a personal failure mode, not bad luck.
3. ⚠️ **`forecast` is unverifiable and always will be.** Every surprise-based result in this workstream
   inherits that caveat, permanently.
4. ⚠️ **Test C in #123 was underpowered by design**, and I did not compute that before running it.

---

# PART 7 — RECOMMENDATIONS

| # | recommendation | why |
|---|---|---|
| **1** | ⛔ **Do not run Phase 3 (#117) on the CL/API target** | it would optimise the *reach* toward something that does not pay **even if reached perfectly** |
| **2** | ⭐⭐ **Decide on the sizing layer** | it is the one change that would make WS-EARN's 4.98× and this programme's ρ = −0.63 usable at all. **Owner's call, not research** |
| **3** | ⚠️ **Fix YM's aggregation** | its 1-second source is fine (14.5M rows) but every aggregated frame is 0 bytes |
| **4** | **Close the news programme** | four independent attacks, one consistent answer. Further variants of the same question have low expected value |
| **5** | ⭐ **Keep the verification harness** | it is workstream-independent, it caught twelve defects here, and it is the most reusable thing this round produced |

---

# PART 8 — WHAT IS LEFT OPEN, EXPLICITLY

Nothing here is forgotten; it is declined or deferred with a reason.

| item | status |
|---|---|
| **#117 Phase 3** | open, **no viable target**; recommendation is not to proceed |
| **`forecast` verification** | ⛔ impossible — no archive exists |
| **API/EIA provenance** | ⛔ impossible — private report |
| **the sizing layer** | ⏳ **owner's decision** |
| **YM aggregation** | ⏳ a data-engineering fix, not research |
| **the exploratory grid** (4 features × 7 outcomes) | computed, **not inferred from** — would need its own correction |
| **threshold effects** | untested — a monotone correlation cannot see them |
| **C4 earnings check** (#110) | ⏳ still with the owner |
| **INTC 7-minute filing lag** (#110) | ⏳ measured, not corrected |

> **The most useful thing this workstream produced is not a strategy. It is the knowledge that the news
> edge is not there — established four independent ways, with every null backed by a probe proving the
> pipeline could have found it.**
