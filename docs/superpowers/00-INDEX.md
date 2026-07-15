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
| **▸** | [**`PROGRESS-2026-07-14.md`**](PROGRESS-2026-07-14.md) | 🆕 **Team-leader standup** — what closed today, in one page | 4 min | |
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
