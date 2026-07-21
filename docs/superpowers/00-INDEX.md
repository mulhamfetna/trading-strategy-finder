# 00 — INDEX · Session Reports, 2026-07-11 → 07-14

**Start here.** Nine documents, two workstreams, 65+ experiments. This page tells you what to read,
in what order, and what decisions are waiting on you.

Branch: `fundamental-analysis` · Author: Claude (Opus 4.8) · Reviewer: Mulham Fetna

---

## 🔄 UPDATE — 2026-07-14: THE QUESTION IS SETTLED

**On 07-13 I retracted the news verdict for having only 12% statistical power, and said the bottleneck
was our price history. You supplied 17 years of it. I re-ran everything.**

| | |
|---|---|
| **Sample** | 52–117 releases → **871 releases** (2010–2026, 5.45M 1-min bars) |
| **Power** | 12–18% → **99.4%** |
| **The answer** | **Unchanged — and now EARNED.** Scheduled US macro is **priced in.** |
| **The one survivor (magnitude)** | ❌ **DEAD.** +0.187 at n=117 → **−0.018 at n=871.** It was **2025 being the luckiest of 17 years.** |
| **Cost** | **$0** |

**→ Read [`06-VERDICT-at-full-power.md`](06-VERDICT-at-full-power.md).** It supersedes the "⭐ PROMISING"
and "we cannot tell" rows below, both of which are now **obsolete**.

✅ **And the one thread that could have cut the other way has been chased down and CLOSED.** 1-second data
confirms the stop-out really is a two-second head-fake — **94% of our stop-outs are swept, median 1 second
beyond the stop.** The resolution complaint was **correct**. **And the stop-loss verdict STANDS anyway:**
the best tradeable delay rule earns **+$80/trade against a ±$1,600 swing (p = 0.452)**, and two-thirds of
even *that* is just "the stop is too tight." **Seeing the sweep more clearly does not make it profitable
to sit through.** See report 06, Part 9.

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **What we set out to do** | Add **fundamental analysis** (news) to the trading system, and build a **dynamic stop-loss** |
| **What we shipped to production** | **NOTHING.** Both features are built, tested, and **OFF by default.** Golden 6/6 byte-identical. **Zero risk to the live system.** |
| **What we spent on data** | **$0** |
| **The big mistake** | I closed the news workstream declaring *"news is priced in"* — **on a study with 12% statistical power.** That verdict was **RETRACTED** on 07-13… |
| **…and then re-earned** | **On 07-14, at 871 releases and 99% power, the same verdict came back — properly this time.** See **06**. |
| **The one thing that "survived"** | **Bigger surprise ⇒ bigger move.** ❌ **It did not survive.** **−0.018 at full power.** It was a lucky year. |
| **The thing that is genuinely dead** | The **dynamic stop-loss** — ⚠️ **but see Task #11.** It was measured on 1-min bars and may be a **resolution artifact**. |
| **What we needed** | **More price history.** ✅ **Got it. It settled the question.** |

---

## 📋 THE DOCUMENTS

| # | Document | What it is | Time | 🇸🇦 |
|---|---|---|---|---|
| **00** | **`00-INDEX.md`** | ← you are here | 5 min | |
| **★** | [**`PROGRESS-DISCUSSION-2026-07-18.md`**](PROGRESS-DISCUSSION-2026-07-18.md) | 🆕 **REVIEW & DECIDE** — scorecard, discoveries, what the discipline prevented, decisions for you | 8 min | |
| **★** | [**`MASTER-STATUS-2026-07-14.md`**](MASTER-STATUS-2026-07-14.md) | 🆕 **READ AFTER THIS** — all workstreams, every discovery, every open thread, one page in | 10 min | |
| **▸** | [**`PROGRESS-2026-07-14.md`**](PROGRESS-2026-07-14.md) | 🆕 **Team-leader standup** — what closed today, in one page | 4 min | |
| **▸** | [**`ENGINEERING-NOTE-what-blocks-an-entry.md`**](ENGINEERING-NOTE-what-blocks-an-entry.md) | 🆕 **Engine discovery (#4)** — the ONE thing that blocks a trade, and the `veto_mask` trap | 6 min | |
| **▸** | [**`SESSION-00-WORKSTREAM-REPORT.md`**](SESSION-00-WORKSTREAM-REPORT.md) | 🆕 **#5 COMPLETE** — the whole session-windows workstream in one detailed report (research→S1→S3→verdict) | 15 min | |
| **▸** | [**`SESSION-01-RESEARCH-real-vs-folklore.md`**](SESSION-01-RESEARCH-real-vs-folklore.md) | 🆕 **#5 kickoff** — deep-research on session windows: what's REAL vs FOLKLORE, + the on-data test list | 12 min | |
| **▸** | [**`SESSION-02-S1-our-session-shape.md`**](SESSION-02-S1-our-session-shape.md) | 🆕 **#5 · S1** — our own session shape measured (17y NQ): U-shape confirmed (1.94×), overlap is a non-event, tz triple-confirmed | 8 min | |
| **▸** | [**`SESSION-03-S3-does-our-edge-have-a-shape.md`**](SESSION-03-S3-does-our-edge-have-a-shape.md) | 🆕 **#5 · S3** — our RISK inherits the session shape (stop-out 56%→16%), our EDGE does not. No entry filter; sizing yes. #5 answered | 8 min | |
| **▸** | [**`SESSION-04-asia-cell-oos-verdict.md`**](SESSION-04-asia-cell-oos-verdict.md) | ✅ **#5 · Asia cell OOS — FLUKE** — the frozen 22:00/Asia edge tested cross-instrument: 0 of 3 independent equity indices replicate (ES/YM/RTY all *below* average at 22:00). Dead; #5 fully closed. | 7 min | |
| **▸** | [**`DIST-00-WORKSTREAM-REPORT.md`**](DIST-00-WORKSTREAM-REPORT.md) | ⚠️ **#7 RE-EARNED 07-20** — corrected after BUG-01: P&L bounded **[−151.4,+125.6]**, **3.89% gap through the stop**, raw returns fat (α≈3), vol-scaled stop rejected (reinforced) → keep the fixed stop | 12 min | |
| **▸** | [**`DIST-01-RESEARCH-tail-fitting-recipe.md`**](DIST-01-RESEARCH-tail-fitting-recipe.md) | 🆕 **#7 kickoff** — deep-research on fitting the fat tail: the EVT/GARCH recipe, the pitfalls, + the on-data plan | 12 min | |
| **▸** | [**`DIST-02-D1-per-trade-pnl-is-truncated.md`**](DIST-02-D1-per-trade-pnl-is-truncated.md) | ⚠️ **#7 · D1 — HEADLINE WAS CIRCULAR** (BUG-01). Corrected: bounds **[−151.4,+125.6]**, 3.89% gap through, tail **$3,029**; truncation now proven by EVT ξ<0 | 7 min | |
| **▸** | [**`DIST-03-D2-raw-return-tail-index.md`**](DIST-03-D2-raw-return-tail-index.md) | 🆕 **#7 · D2** — raw-return tail index α≈3 (genuinely fat); HEAVIER overnight than RTH | 7 min | |
| **▸** | [**`DIST-04-D3-conditional-tail.md`**](DIST-04-D3-conditional-tail.md) | 🆕 **#7 · D3** — conditional tail: the 40-pt stop's safety is regime-dependent → vol-scaled stop (proposed) | 8 min | |
| **▸** | [**`DIST-05-D4-vol-scaled-stop-rejected.md`**](DIST-05-D4-vol-scaled-stop-rejected.md) | ✅ **#7 · D4 REINFORCED** — fixed stop-out rate is regime-**FLAT** (55.1/56.2/56.5%) while a σ-stop would **SWING** (69.0/56.2/46.3%). Keep the fixed stop | 7 min | |
| **▸** | [**`SIZE-00-WORKSTREAM-REPORT.md`**](SIZE-00-WORKSTREAM-REPORT.md) | ⚠️ **SIZING RE-EARNED 07-20** — recommendation SURVIVES (~0.6–1.2%, quarter-half Kelly, edge-champs, hard cap) but CI floor **0.0%**, tail **$3,029 not $1,600**, 5m f\*=0.0%; **Z3 vol-target REJECTED** | 12 min | |
| **▸** | [**`SIZE-01-RESEARCH-fractional-kelly.md`**](SIZE-01-RESEARCH-fractional-kelly.md) | 🆕 **Sizing kickoff** — deep-research on fractional Kelly / risk-of-ruin under fat tails; the recipe | 9 min | |
| **▸** | [**`SIZE-02-Z1-kelly-on-our-ledger.md`**](SIZE-02-Z1-kelly-on-our-ledger.md) | ⚠️ **Sizing · Z1 RECOMPUTED** — full Kelly still 2.5% but CI **[0.0%, 5.3%]** (cannot exclude zero edge); pooled win **49.1%**; 5m f\*=0.0% | 6 min | |
| **▸** | [**`SIZE-03-Z2-ruin-and-gap-haircut.md`**](SIZE-03-Z2-ruin-and-gap-haircut.md) | 🆕 **Sizing · Z2** — drawdown binds not ruin → risk ~0.6–1.2% (quarter-half Kelly), edge-champs only, hard cap | 7 min | |
| **▸** | [**`SIZE-04-Z3-vol-targeting.md`**](SIZE-04-Z3-vol-targeting.md) | ❌ **Sizing · Z3 REJECTED** — on the real ledger the halves **FLIP** (−0.79/+0.27), corr(pnl,σ)=+0.020 ⇒ fluke artifact. GC OOS test moot | 6 min | |
| **▸** | [**`SIZE-05-Z4-pnldd-objective.md`**](SIZE-05-Z4-pnldd-objective.md) | 🔄 **Sizing · Z4 REVERSED** — the 'flat' reading was the bug; it really **DECLINES** as f rises, optimum ~0.3%. Fraction CLOSED at ~quarter-half Kelly | 6 min | |
| **▸** | [**`plans/2026-07-14-fa-v2-nq-gc-decisions.md`**](plans/2026-07-14-fa-v2-nq-gc-decisions.md) | 🆕 **FA-v2 PLAN** — news re-opened, NQ+GC only, prediction→decision (close/enter/assist) | 8 min | |
| **▸** | [**`FAV2-00-WORKSTREAM-REPORT.md`**](FAV2-00-WORKSTREAM-REPORT.md) | 🆕 **FA-v2 COMPLETE** — news→decisions on NQ+GC, one report: gold, close, enter, **assist rejected**, content=vol-not-direction | 12 min | |
| **▸** | [**`GC-01-REPLICATION-verdict.md`**](GC-01-REPLICATION-verdict.md) | 🆕 **GC REPLICATION** — the verdict **replicates on gold** (n=866/99% power) ⇒ not an NQ quirk. ⭐ Gold moves **INVERSE** to macro surprises (rank −0.193, 15/16 yrs) — Pearson was blind. Residual at +1s real (+\$49.90, t=3.40) but killed by slippage. **Two method lessons + a self-correction.** | 15 min | |
| **🚨** | [**`BUG-01-sizing-studies-ran-the-wrong-strategy.md`**](BUG-01-sizing-studies-ran-the-wrong-strategy.md) | **THE BUG THAT INVALIDATED TWO WORKSTREAMS** — 11 studies read champion stops under keys that do not exist, so `dict.get` silently backtested 30/40/60 instead of 128.6/151.4/125.6. Three layers deep. All re-run: sizing SURVIVES (~0.6-1.2%) but tail is **$3,029 not $1,600**; D1 was CIRCULAR, now real; **Z3 vol-targeting REJECTED**. | 15 min | |
| **🔧** | [**`GAP-01-how-the-engine-fills-a-gapped-stop.md`**](GAP-01-how-the-engine-fills-a-gapped-stop.md) | **GAP FILLS** — gapped stop now fills at the bar OPEN, not the line. Parity 11/11, golden recaptured. | 12 min | |
| **📊** | [**`GAP-02-champion-before-after.md`**](GAP-02-champion-before-after.md) | **54-champion before/after** — P&L neutral (−0.2%), drawdown +9.8% (NG +148%). Old model understated RISK. | 10 min | |
| **▸** | [**`TESTS-01-suite-triage.md`**](TESTS-01-suite-triage.md) | **Suite triage (#19)** — a red suite has zero signal. Fixed a real environment-dependent `perf` import bug (namespace package shadowed by a system library) that made two studies unrunnable; the 3 L2 anchors are **stale, not a regression**. | 8 min | |
| **▸** | [**`FAV2-01-FINDINGS.md`**](FAV2-01-FINDINGS.md) | 🆕 **FA-v2 detail** — A1 (gold reacts) · B1 (close negligible) · B3 (assist rejected) · A2 (vol pattern) | 10 min | |
| **▸** | [**`FAV2-02-RESEARCH-decisions-real-vs-dangerous.md`**](FAV2-02-RESEARCH-decisions-real-vs-dangerous.md) | 🆕 **FA-v2 research** — close-on-news real, enter-on-news no edge, **ASSIST = route to ruin** | 10 min | |
| **▸** | [**`RESOURCES-to-investigate.md`**](RESOURCES-to-investigate.md) | 🆕 external data/signal sources to assess (task #16) | 3 min | |
| **01** | [`01-RETRACTION-verdict-withdrawn.md`](01-RETRACTION-verdict-withdrawn.md) | **🚨 READ FIRST.** I was wrong, here is exactly how | **17 min** | |
| **02** | [`02-EXPERIMENT-LOG-all-65-trials.md`](02-EXPERIMENT-LOG-all-65-trials.md) | **The complete record.** All 65 trials, every number | 39 min | [AR](02-EXPERIMENT-LOG-all-65-trials_AR.md) |
| **03** | [`03-SEMINAR-fundamental-analysis.md`](03-SEMINAR-fundamental-analysis.md) | **Teaching doc.** Every step, plain language + technical | 39 min | [AR](03-SEMINAR-fundamental-analysis_AR.md) |
| **04** | [`04-REPORT-dynamic-stop-loss.md`](04-REPORT-dynamic-stop-loss.md) | The stop-loss investigation, candle → theorem | 39 min | [AR](04-REPORT-dynamic-stop-loss_AR.md) |
| **05** | [`05-REPORT-robustness-9-markets.md`](05-REPORT-robustness-9-markets.md) | Re-testing every result across 9 markets | 20 min | |
| **06** | [**`06-VERDICT-at-full-power.md`**](06-VERDICT-at-full-power.md) | 🆕 **THE ANSWER.** 17 years, 871 releases, 99% power | **22 min** | |
| **07** | [`specs/2026-07-11-fundamental-analysis-design.md`](specs/2026-07-11-fundamental-analysis-design.md) | The original design + the correction block | 27 min | |
| **08** | [`plans/2026-07-11-fa-milestone1-veto-window.md`](plans/2026-07-11-fa-milestone1-veto-window.md) | The implementation plan (executed) | 42 min | |

---

## 🎯 READING PATHS — pick one

### Path A — "I have 20 minutes and I need to make decisions"
**Read `01` only.** It contains the retraction, what still stands, what doesn't, and why. Then come back
to the **DECISIONS** section below.

### Path B — "I have an hour and I want the whole picture"
**`01` (17 min) → `02` Part 0 master table (5 min) → `02` Parts 8, 9, 15 (20 min).**
That gives you: the mistake, every experiment at a glance, the power analysis, the one surviving signal,
and the lesson.

### Path C — "I want to understand the method well enough to check it"
**`03` (the seminar) → `01` (the retraction) → `02` (the full log).**
The seminar teaches the method. The retraction shows where the method failed. The log proves it.

### Path D — "Just the stop-loss question"
**`04` alone.** Self-contained.

---

## 📊 STATUS BOARD — what is true, what is not

### ✅ CONFIRMED — measurements. These stand regardless of sample size.

| Finding | Value | Doc |
|---|---|---|
| The release calendar **validates itself** | **8.32×** volatility spike, landing **exactly** on the print | 02 · 03 |
| The market goes **QUIET before** a release | **0.78×** at −2 min — no pre-release ramp | 02 · 03 |
| **The 08:30 lockup does NOT leak** | 07:45–08:28 = **0.81–0.89×** vs ordinary days | 02 |
| We are **already flat for 77%** of releases | Median hold **1.4 hours** | 02 · 03 |
| **4h bars cannot see an 08:30 release** | 4h bars land 02/06/10/14/18/22 — **88% of events invisible** | 02 · 03 |
| Our 9 markets are **~3.2 effective markets** | NQ/ES/RTY/YM are **0.95 correlated** | 05 |
| Payrolls get **massively revised** | **−801k to −1,032k jobs** after first print | 02 |
| Post-stop price is a **fair random walk** | Recovery = gambler's ruin, deviation **+0.34 pp** | 04 |
| **We give back winners** | **$145,640.** 42% of losers were once **+20 pts up** | 04 |

### ❄️ FROZEN — pre-registered, awaiting data (nothing else is open)

| Finding | Status | Doc |
|---|---|---|
| **Silver** | ✅ **D3 RESOLVED — frozen forward test.** Passed a pre-registered gold-controlled + 4/4-quarter-stability test, so **not dropped** — but the raw headline **died under the 17-year surprise ruler** (−0.360→−0.173, ns) and what survives is a suppressor-prone partial at 12% power **inside the fluke window**, so **not confirmed.** Protocol frozen: silver only, h=5, new data past 2026-07-02. **Build nothing.** | **06 Part 12** · 05 |

### ❌ DEAD — tested, failed, on adequate evidence

| Idea | Why | Doc |
|---|---|---|
| **Trade the direction** | **−0.004** at n=870, sign-hit **49.3%**. ~**99% power.** The −0.43 "hawkish-Fed" story was **noise** | **06** |
| **Trade the magnitude** ~~⭐~~ | ❌ **THE SURVIVOR DIED.** **+0.187** (n=117) → **−0.018** (n=871). It was **2025 being the luckiest of 17 years** | **06** |
| **Trade the persistence** | **48.2%** — a coin flip | **06** |
| **Trade the shape** | **p = 0.880** — the surprise does not pick the path shape | **06** |
| **The news veto** (stand aside) | We're **already flat for 77%** of releases. And **fake calendars help just as much** | 02 · 03 |
| **Trade the reaction** | 0/30 significant. The **"$72,170 edge"** is ordinary NQ mean-reversion — **the fakes reproduce it** | 02 · 03 |
| **The dynamic stop-loss** | Post-stop is a **martingale**. Doob + Osler + Kaminski-Lo + Liaudinskas — **and now CONFIRMED at 1-SECOND resolution.** 94% of stop-outs ARE two-second sweeps (the resolution complaint was right!) — and the best tradeable rule is still **+$80/trade vs a ±$1,600 swing, p=0.452.** Seeing the sweep does not make it profitable to sit through | 04 · **06** |

### ♻️ RETRACTED on 07-13 → **RE-INSTATED on 07-14**

**The retraction was correct. And then the data arrived and the verdict came back — properly earned.**

| Claim | Retracted because | **Now** |
|---|---|---|
| **"Scheduled US macro is priced in"** | 12% power. Needed 647 events; had 52 | ✅ **RE-CONFIRMED.** **871 events, 99% power** |
| "The surprise signal is dead" | 28 out-of-sample events | ✅ **RE-CONFIRMED** at n=870 |
| "Nothing survives Bonferroni" | Guaranteed by sample size, not the market | ✅ **RE-CONFIRMED** — and now it *means* something |
| "Don't buy vendor consensus data" | Rested on the retracted verdict | ✅ **RE-INSTATED.** See 06 Part 10 |

> **Same sentences. Completely different standing.** On 07-13 they were guesses in lab coats and were
> correctly withdrawn. On 07-14 they are measurements. **A correct conclusion reached by an invalid
> method is not knowledge — it is luck.**

---

## 🚨 THE ONE THING TO UNDERSTAND

> **A NULL TEST tells you whether an effect you FOUND is real.**
> **A POWER ANALYSIS tells you whether you could have FOUND it at all.**
>
> **I built an elaborate machine for the first — it caught three real mirages.**
> **I never once ran the second.**
>
> **And because the machine kept firing, it FELT like it was working. The more false positives it
> killed, the more confident I became in the false negatives it was producing.**

**Result:** a whole workstream conclusion had to be publicly withdrawn across four documents and memory.

---

## ✋ DECISIONS WAITING ON YOU

| # | Decision | Context | Status |
|---|---|---|---|
| **D1** | **Get more price history?** | We needed ~650 releases; we had 117. | ✅ **DONE — and it settled the question.** 17 years, 871 releases, **$0**. |
| **D2** | **Pursue the magnitude signal?** | Bigger surprise ⇒ bigger move. | ❌ **DEAD.** **−0.018 at n=871.** It was **2025 being the luckiest of 17 years.** No action. |
| **D3** | **Test silver?** | p=0.007 **despite** 12% power, and it **strengthened** out-of-sample. But it is 1 cell of 36 — being the best of 36 is what luck produces. | ✅ **RESOLVED — Part 12.** Pre-registered & tested. **Not dropped, not confirmed → frozen forward test.** No build. |
| **D4** | **Buy vendor consensus data?** | Our "expected" is a *statistical* guess, not the market's. | ❌ **NO.** Consensus would have to carry **100%** of the edge alone. Bar is now very high — see 06 Part 10. |
| **D5** | **What's next on the queue?** | 4 tasks remain (see below) | ⚠️ **Task #11.** It is the only live thread that could **overturn a shipped verdict**. |

---

## 📌 OPEN TASK QUEUE

| # | Task | Why it matters |
|---|---|---|
| **4** | **Rename the `veto_mask` trap + document the real blocking logic** | The parameter **named `veto_mask` does not veto.** It nearly made me build a feature that silently did nothing. **Cheap, safe, zero behaviour change.** **Start here.** |
| **5** | **Trading-session windows** (Asia / London / NY, overlaps, gaps) | The 09:30 NY open contaminated our news study — session structure **matters and is currently invisible** to the system |
| **7** | **Fit our own probability distribution** | Returns are certainly not Gaussian. Correct tail probabilities directly inform **stop placement and sizing**. **Now better motivated than ever:** the per-trade spread on a stop-out is **80 points** — that fat tail is exactly what defeats every edge we've measured |
| ~~**D3**~~ | ~~Silver: pre-register a test, or drop it~~ | ✅ **DONE — Part 12.** Frozen forward test. Re-run `study_silver.py` once ~6-12 mo of new silver data exist. |

**✅ Closed since the last index:** **#11** (*1-second stop-loss re-test* — **the verdict HELD**; sweeps
are 94% real but worth **+$80/trade against a ±$1,600 swing, p=0.452**), **#6** (*is 1-min too coarse for
news?* — **YES, provably**), **#10** (*fold in 2024* — **superseded**: we got 17 years, not 1),
**#12/#13/#14** (ALFRED retry + cache; the per-year table; the inverted power labels).

---

## 🔒 PRODUCTION SAFETY — nothing is at risk

| Gate | Status |
|---|---|
| **Golden 6/6** (all timeframes byte-identical with features OFF) | ✅ **MATCH** |
| **Engine ↔ fast-engine parity** | ✅ **11/11, zero mismatches** |
| Unit tests (news veto · excursions · calendar · window) | ✅ **7/7 · 9/9 · 7/7 · 12/12** |
| Features shipped to production | **NONE.** All default OFF |
| Money spent on data | **$0** |

**Both new engine features (`news_veto`, `track_excursions`) are inert by default. Every champion's
numbers are unchanged to the cent.**

---

## 🗂️ WHERE THE CODE LIVES

`subprojects/Parametric-Indicators/optimize/fundamentals/`

| Script | Runs |
|---|---|
| `power_analysis.py` | **The retraction** — the 12% figure |
| `study_lockup.py` | The 08:30 leak test |
| `nulltest.py` · `run_nulltest.py` | The fake-calendar null test (**caught 3 mirages**) |
| `study_pattern.py` | Magnitude · shape · persistence |
| `study_magnitude_oos.py` · `study_magnitude_regime.py` | The gates on the surviving signal |
| `extended_data.py` | 2024 + 2025 + 2026 (**study-only** — the engine is untouched) |
| `study_excursions.py` · `study_stop_counterfactual.py` | The stop-loss investigation |
| `robustness.py` · `robustness2.py` | The 9-market re-test |
| `alfred.py` · `fetch_calendar.py` · `release_calendar.py` · `window.py` | The data spine |

---

## 📖 GLOSSARY (for anyone joining cold)

| Term | Plain meaning |
|---|---|
| **Statistical power** | If the effect is really there, what's the chance my test spots it? **Ours was 12%.** |
| **Null test** | Run the same rule on **fake** data. If the fake works too, you found nothing. |
| **Out-of-sample** | Test on data the model never saw. The only honest test. |
| **Martingale** | A fair game. **No exit rule can change its expected value** (Doob's theorem). |
| **Gambler's ruin** | The odds a coin-flip walk hits +A before −B. **Our stop data matched it exactly.** |
| **MFE / MAE** | The best / worst a trade ever got while open. Previously unmeasurable. |
| **Golden 6/6** | Our fingerprint test: change the engine, and all six timeframes must produce **byte-identical** results. |
| **Point-in-time** | The number **as printed that morning** — not today's revised version. Payrolls get revised by ~1M jobs. |
