# 00 — INDEX · Session Reports, 2026-07-11 → 07-13

**Start here.** Eight documents, two workstreams, 65 experiments. This page tells you what to read,
in what order, and what decisions are waiting on you.

Branch: `fundamental-analysis` · Author: Claude (Opus 4.8) · Reviewer: Mulham Fetna

---

## ⚡ THE 60-SECOND VERSION

| | |
|---|---|
| **What we set out to do** | Add **fundamental analysis** (news) to the trading system, and build a **dynamic stop-loss** |
| **What we shipped to production** | **NOTHING.** Both features are built, tested, and **OFF by default.** Golden 6/6 byte-identical. **Zero risk to the live system.** |
| **What we spent on data** | **$0** |
| **The big mistake** | I closed the news workstream declaring *"news is priced in"* — **on a study with 12% statistical power.** That verdict is **RETRACTED**. |
| **The one thing that survived** | **Bigger surprise ⇒ bigger move.** A *volatility* signal, not a directional one. Significant, positive in all 3 years, **not yet proven**. |
| **The thing that is genuinely dead** | The **dynamic stop-loss**. Killed by our own data, a theorem, and the two most rigorous papers in the field — all agreeing. |
| **What we need** | **More price history.** That is the entire bottleneck. |

---

## 📋 THE DOCUMENTS

| # | Document | What it is | Time | 🇸🇦 |
|---|---|---|---|---|
| **00** | **`00-INDEX.md`** | ← you are here | 5 min | |
| **01** | [`01-RETRACTION-verdict-withdrawn.md`](01-RETRACTION-verdict-withdrawn.md) | **🚨 READ FIRST.** I was wrong, here is exactly how | **17 min** | |
| **02** | [`02-EXPERIMENT-LOG-all-65-trials.md`](02-EXPERIMENT-LOG-all-65-trials.md) | **The complete record.** All 65 trials, every number | 39 min | [AR](02-EXPERIMENT-LOG-all-65-trials_AR.md) |
| **03** | [`03-SEMINAR-fundamental-analysis.md`](03-SEMINAR-fundamental-analysis.md) | **Teaching doc.** Every step, plain language + technical | 39 min | [AR](03-SEMINAR-fundamental-analysis_AR.md) |
| **04** | [`04-REPORT-dynamic-stop-loss.md`](04-REPORT-dynamic-stop-loss.md) | The stop-loss investigation, candle → theorem | 39 min | [AR](04-REPORT-dynamic-stop-loss_AR.md) |
| **05** | [`05-REPORT-robustness-9-markets.md`](05-REPORT-robustness-9-markets.md) | Re-testing every result across 9 markets | 20 min | |
| **06** | [`specs/2026-07-11-fundamental-analysis-design.md`](specs/2026-07-11-fundamental-analysis-design.md) | The original design + the correction block | 27 min | |
| **07** | [`plans/2026-07-11-fa-milestone1-veto-window.md`](plans/2026-07-11-fa-milestone1-veto-window.md) | The implementation plan (executed) | 42 min | |

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

### ⭐ PROMISING — not proven, worth pursuing

| Finding | Evidence | Doc |
|---|---|---|
| **Bigger surprise ⇒ bigger move** | **+0.187 (p=0.044)** · **+0.206 (p=0.027)** at n=117. **Positive in ALL 3 years. Never flips sign.** | 02 · 01 |
| **Silver** | p = **0.007** — the strongest of 36 cells — and it **STRENGTHENED out-of-sample** (−0.140 → −0.500) | 05 |

### ❌ DEAD — tested, failed, on adequate evidence

| Idea | Why | Doc |
|---|---|---|
| **The news veto** (stand aside) | We're **already flat for 77%** of releases. And **fake calendars help just as much** | 02 · 03 |
| **Trade the reaction** | 0/30 significant. The **"$72,170 edge"** is ordinary NQ mean-reversion — **the fakes reproduce it** | 02 · 03 |
| **Trade the direction** | Real in 2025 (−0.43), **gone in 2026. Sign FLIPPED.** A Fed regime, not an edge | 02 · 03 |
| **The dynamic stop-loss** | Post-stop is a **martingale**. Doob's theorem + Osler + Kaminski-Lo + Liaudinskas — **all agree** | 04 |

### ⚠️ RETRACTED — I claimed this and was wrong

| Claim | Why it fell |
|---|---|
| **"Scheduled US macro is priced in"** | **12% statistical power.** We needed 647 events; we had 52 |
| "The surprise signal is dead" | 28 out-of-sample events |
| "Nothing survives Bonferroni" | Guaranteed by sample size, **not** by the market |
| "Don't buy vendor consensus data" | **SUSPENDED** — rested on the retracted verdict |

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

| # | Decision | Context | My recommendation |
|---|---|---|---|
| **D1** | **Buy more price history?** | We need **~650 releases** for a real answer; we have **117**. And we only need **±60-min windows** — about **78,000 bars**, one-sixth the size of a single file we already own. **Small, cheap, and it settles the question.** | ✅ **YES.** This is the whole bottleneck. |
| **D2** | **Pursue the magnitude signal?** | Bigger surprise ⇒ bigger move. Positive all 3 years, never flips. If it holds, it's a **risk/sizing** signal — *"big surprise ⇒ widen stops, size differently"* — **not** a directional bet. | ⭐ **Yes, but gated on D1.** |
| **D3** | **Test silver?** | p=0.007 **despite** 12% power, and it **strengthened** out-of-sample. But it is 1 cell of 36 — being the best of 36 is what luck produces. | ⚠️ **Pre-register or drop.** Do not fish. |
| **D4** | **Buy vendor consensus data?** | Our "expected" is a *statistical* guess, not the market's. A bad yardstick attenuates a real signal. | ⏸️ **NOT YET.** Settle D1 first — it's free. |
| **D5** | **What's next on the queue?** | 4 tasks remain (see below) | Start with **#4** — cheap, safe, removes a live trap |

---

## 📌 OPEN TASK QUEUE

| # | Task | Why it matters |
|---|---|---|
| **4** | **Rename the `veto_mask` trap + document the real blocking logic** | The parameter **named `veto_mask` does not veto.** It nearly made me build a feature that silently did nothing. **Cheap, safe, zero behaviour change.** |
| **5** | **Trading-session windows** (Asia / London / NY, overlaps, gaps) | The 09:30 NY open contaminated our news study — session structure **matters and is currently invisible** to the system |
| **6** | **Is 1-minute data too coarse for news?** | The 08:30 bar went **down 46 pts AND up 141 pts in the same minute.** An OHLC candle **cannot tell you the order.** This may be *why* the reaction study found nothing |
| **7** | **Fit our own probability distribution** | Returns are certainly not Gaussian. Correct tail probabilities directly inform **stop placement and sizing** |

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
