# FA-v2 · 02 — RESEARCH: news DECISIONS — real, contested, and DANGEROUS

**The deep-research pass on the new decision layer (gold's reaction, news-based position management, the
scale-in/"assist" idea, and event→rule methodology). 104 agents, sources adversarially verified. The
verdict is sharply asymmetric — one idea has a real mechanism, one is unproven, and one (the "assist") is
condemned by convergent, uncontested mathematics. This report is what gates B1/B2/B3.**

Date: 2026-07-15 · Branch `fundamental-analysis` · Method: `deep-research` workflow.

---

## ⚡ THE 60-SECOND VERSION — the asymmetric verdict

| Idea (from the new rules) | Verdict | Why |
|---|---|---|
| **Close/trim an open position into a release** (B1) | 🟡 **Real mechanism, contested net-of-cost** | Volatility is forecastable and *decoupled* from returns, so trimming into a vol burst doesn't sacrifice proportional expected return. But volatility-timing profits fail out-of-sample / net of costs in the literature — **must validate on our ledgers.** The most promising of the three. |
| **Enter on the release** (B2) | 🔴 **No documented edge for NQ/GC** | The real directional post-announcement drift is **fixed-income only** (Treasuries, via bond-fund flows); the famous pre-FOMC equity drift **weakened after 2011** and was never shown for gold. Importing either to NQ/GC is a misapplication. |
| **ASSIST — scale in after a loss, wait for recovery** (B3) | ⛔ **CONDEMNED by the math. Route to ruin.** | *There is NO credible evidence that price reliably recovers after a news loss.* Averaging down a book without a genuine positive edge is a documented path to near-certain ruin — and fat tails make it worse, not better. **See the dedicated section — this is the safety-critical finding.** |
| **Gold as a distinct news instrument** | 🟡 **Different channel, same non-predictability** | Gold reacts via the real-rate/dollar/surprise channel (vs NQ's risk channel), but on the release *direction* it is a volatility burst, not a directional signal — like NQ. Academic gold-news evidence is thin; **our own GC study is genuinely needed.** |

---

## ⛔ THE ASSIST IDEA (scale-in after a loss) — READ THIS CAREFULLY

**Your hypothesis:** *"after a certain loss near news, price will skyrocket, so add a second contract and
wait for both to recover."* I researched the honest case for and against. **The case against is
overwhelming and mathematically convergent; the case for does not survive.**

| The mathematics | Source |
|---|---|
| In a **negative-edge** game, repeated small-stake betting makes **ruin near-certain (98%)**, wealth → ~5% of original. Slow accumulation is the **worst** approach. | Whelan 2025 (UCD / CEPR) |
| **Fat tails make it worse, not better:** at constant expected value, more payoff asymmetry *raises* ruin probability (13% → 34% → 64%); and for fat-tailed processes **ruin comes from a single extreme jump**, not a survivable series of small losses (the "single big jump" theorem). | Whelan 2025; Taleb; Foss-Korshunov-Zachary |
| **"Profitable on average" does NOT save a single account.** Any rule with a fixed per-event ruin chance goes to **ruin-probability-one** under repetition. Ensemble ("on average across gamblers") ≠ time (your one account): *"after ruin on day 28, there is no day 29."* | Taleb (ergodicity) |

> **🍼 In plain words** — averaging down into a loser *feels* safe because most of the time price does
> come back and you close both contracts green. But you are trading many small wins for a rare,
> catastrophic loss — and with leveraged futures around news (exactly the fat-tailed regime), that one
> adverse jump into a **doubled** position is the account-killer. "It recovers on average" is precisely
> the trap: on average across a thousand traders, sure — but *you* are one path, and the path that hits
> the barrier is gone. This is the same fat tail that #7 is measuring and that already made every one of
> our edges statistically invisible; the assist idea **multiplies** exposure to it.

**The ONLY thing that could rescue the assist idea:** a *genuine, positive, news-conditional recovery
edge* — i.e. that after a loss **specifically following a news event**, the recovery is better than a
matched non-news loss, by enough to overcome costs and the tail. Our own (non-news) stop-loss study
already found post-loss price is a **fair** game (no edge). **So B3's test is narrow and pre-declared:**
does the *news condition* create a recovery edge our general martingale study didn't see? **If not — and
the prior is heavily against — the assist idea is rejected and must not be built.** We test it honestly;
we do not assume it, and we do not ship it on a "feels right" basis.

---

## 🟡 THE ONE WITH A REAL MECHANISM — close/trim into a release (B1)

**Volatility-managed positioning has a sound basis** (Moreira & Muir, *J. Finance* 2017): volatility is
highly forecastable at short horizons, and **variance forecasts are only weakly related to future
returns** — so *cutting exposure into a scheduled release does not sacrifice proportional expected
return.* You give up variance you can predict, not return you can't.

**But:** the out-of-sample, net-of-cost profitability of volatility timing is **contested** — it beat the
benchmark in only 53/103 portfolios (Cederburg 2020) and fails net of transaction costs (Barroso &
Detzel); and the evidence is *monthly equity factors, not intraday news bursts.* So the **mechanism is
real, the profit is not guaranteed** — this is exactly the kind of thing to test on our own NQ/GC champion
ledgers (does flattening before a release, and optionally re-entering after the burst, beat holding
through, net of costs?).

---

## 🟡 GOLD AS A NEWS INSTRUMENT

Fed decisions have a significant short-term impact on gold, but through the **surprise / real-rate / dollar
channel** — *not* predictable from the rate-move direction. On direction it is a **volatility burst**, like
NQ. It differs from Nasdaq in *channel*, not in *tradeable predictability*. **Caveat:** the gold-specific
evidence is the **weakest** of the four questions (a non-peer-reviewed preprint + mainstream consensus) —
**our own 2025–2026 GC study is genuinely needed here**, and A1 already started it (GC reacts 7.2×, weights
NFP over CPI).

---

## 📏 EVENT → RULE: the discipline (this governs A2)

Turning "the announcement said X → price did Y → save it as a rule" into something trustworthy has verified
traps, all of which A2 must respect:

| Rule | Evidence |
|---|---|
| **Use SHORT windows around the release**, not long-horizon drift | Short-horizon event studies are well-specified; long-horizon ones have low power and are often misspecified (Kothari & Warner) |
| **The vol burst is a false-positive trap** — use variance-robust tests | When event variance rises, standard tests reject the null too often; a variance increase is *indistinguishable* from a real abnormal return (Kothari & Warner; use the BMP variance-robust test) |
| **You need 20–50+ events, not a handful** | ~5–10 events break the normality significance tests assume; required sample scales *linearly* with the instrument's noise |
| **Detectability is non-stationary** | The *same* 1% effect was detected 74% of the time in one era, 51% in another; power collapsed 98% → 22% purely because background volatility rose — a pattern's presence/absence across 2025–26 vs older data may be **noise regime, not truth** |
| **Testing many rule variants manufactures luck** | Across 7,846 rule parameterizations, the *best* had a **~12% chance of no real out-of-sample edge** — correct for data-snooping (White's Reality Check / Deflated Sharpe), especially given our optimizer's large search |

> **The through-line, again:** our own per-event-type samples are **10–18 occurrences** on 2025–2026
> (A1). That is **below** the ~20–50 the literature says you need before a per-announcement pattern is even
> normally-distributed, let alone trustworthy. **Per-announcement rules on GC 2025–2026 are underpowered by
> construction** — the silver bottleneck, quantified. Powered per-event work needs the 17-year NQ frame
> (and long GC history we don't have).

---

## 🎯 WHAT THIS MEANS FOR THE PLAN

| Test | Research verdict | Action |
|---|---|---|
| **B1 close/trim into a release** | Real mechanism, profit contested | ✅ **Worth testing** on our ledgers (net of costs) — the most promising |
| **B2 enter on the release** | No edge for NQ/GC (drift is bond-only / dead post-2011) | ⏸️ **Deprioritize** — re-test only NQ+GC-specific with heavy skepticism |
| **B3 assist / scale-in after loss** | ⛔ Condemned unless a real recovery edge exists | 🔬 **Test the narrow question** (news-conditional recovery vs matched non-news loss) with a pre-declared kill; **default = reject; never build without a proven positive edge** |
| **A2 content → pattern → rule** | Doable but trap-laden; underpowered per-event on 2025–2026 | 🟡 **Short windows + variance-robust tests + 20–50 event minimum + data-snooping correction**; powered on NQ 17y only |

**Recommended order:** **B1 first** (the one real mechanism, testable on ledgers we have), then **B3** (the
narrow recovery-edge test — because you want it answered, and answering it honestly protects the account),
then **A2** on NQ 17y (vol-pattern, not directional). Deprioritize B2.

**Open data decision (unchanged, now reinforced):** powered GC news work — and powered per-announcement
rules — need **long GC history.** Without it, GC findings stay frozen/pre-registered, exactly like silver.

---

## Appendix — source quality

Strong/primary: Moreira & Muir (J. Finance), Lucca & Moench (NY Fed / J. Finance), Brooks-Katz-Lustig
(NBER), Kothari & Warner (canonical event-study methodology), Sullivan-Timmermann-White (J. Finance),
Whelan 2025 + Taleb (canonical ruin/ergodicity math). Weak: the gold-specific ResearchGate preprint
(modest claims, mainstream-consistent, full stats unretrievable). **Refuted/excluded:** pre-FOMC drift
being exclusive to FOMC-equities; the aggressive inverse-vol-scaling alpha figure.
