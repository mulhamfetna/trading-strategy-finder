# FA-v2 · FINDINGS — news × NQ + GC (running log)

**The on-data findings of the re-opened, narrowed news workstream (NQ + GC only; prediction → decision).
Plan: [`plans/2026-07-14-fa-v2-nq-gc-decisions.md`](plans/2026-07-14-fa-v2-nq-gc-decisions.md). This file
grows as A1 → A2 → B1/B2/B3 complete.**

Branch `fundamental-analysis` · $0 · production untouched. Raw output under `results/`.

---

## A1 — DOES GOLD REACT TO US MACRO? (foundational measurement) ✅

**Question:** before any GC news study, does gold even respond to scheduled US macro releases, how
strongly vs NQ, and is there a directional tilt? Both measured on the same 2025–2026 window (wsg-i) for a
fair head-to-head. Raw: [`results/news_reaction_nq_gc.txt`](results/news_reaction_nq_gc.txt).

### Result: YES — gold reacts strongly, ~84% as much as Nasdaq

| Offset from 08:30 | NQ | GC |
|---|---|---|
| −1 min (08:29) | 1.36× | 1.03× |
| **0 min (08:30)** | **8.57×** | **7.22×** |
| +1 min (08:31) | 2.95× | 2.85× |
| +3 min (08:33) | 2.58× | 2.27× |

**GC spikes 7.22× a normal minute at the release** (NQ 8.57× on the same window; GC/NQ = 0.84). The shape
is identical to NQ's: dead quiet before, explosive at the print, decaying over the next few minutes.
**Gold is a legitimate news instrument — this validates studying it.** (This is a measurement; the spike
is real regardless of sample size, exactly like NQ's 8.3× calendar self-validation.)

### The interesting bit — the two markets weight the announcements differently

Which announcement moves each market most (|move| × normal at the release minute):

| Event | NQ | GC |
|---|---|---|
| **CPI** | **18.5×** (NQ's biggest) | 11.3× |
| **Nonfarm payrolls** | 11.0× | **14.3×** (GC's biggest) |
| PPI | 9.9× | 5.6× |
| PCE | 4.1× | 3.7× |
| Retail sales | 3.4× | 3.9× |
| GDP | 2.4× | 3.6× |

> **🍼 In plain words** — **Nasdaq reacts most to inflation (CPI); gold reacts most to jobs (NFP).** That
> fits the economics: equities care about the *inflation → Fed → discount-rate* channel, while gold cares
> about the *jobs → real interest rates / dollar* channel. So the two are **genuinely different news
> instruments**, not the same bet — which is the whole reason the user added gold. This is directly useful
> for the per-event-type work (A2): the event that matters most differs by market.
>
> **⚠️ Caveat:** these per-event numbers are **n = 10–18 each** (2025–2026), so the *exact ordering* is
> suggestive, not settled. The robust reads are: (1) both react strongly; (2) CPI and NFP dominate for
> both; (3) the NQ-favors-CPI / GC-favors-NFP split is real-looking and economically sensible but wants
> more data to confirm.

### The directional tilt — a trap flagged, not chased

| Market | Mean signed return at release | % up | bootstrap p |
|---|---|---|---|
| NQ | +6.89 bp | 60.0% | **0.020** |
| GC | +4.87 bp | 53.8% | 0.110 |

The NQ "+6.89 bp, p=0.020" looks like a directional tilt. **It is almost certainly not a news signal, and
here is why I'm not chasing it:**
- It is **unconditional** (releases tend to be followed by an up-move) — a *different* thing from our
  17-year finding that the *surprise* doesn't predict direction (−0.004). The 17-year null stands.
- It is **2025–2026 only, n=85, in the fluke window** — and 2025–2026 was a **bull market**. "Prices tend
  to be higher a minute after 08:30" over a rising 18 months is mostly just the market's overall drift
  sampled at release minutes, not a news effect.
- GC shows no such tilt (p=0.110), as expected for a non-trending safe-haven over the same window.

**Verdict A1:** ✅ Gold reacts strongly to US macro (7.2×), with a sensible instrument-specific event
weighting (NQ↔CPI, GC↔NFP). The **direction** remains undecided/frozen (the |move| is real; the sign is
fluke-window noise). GC directional work needs **long GC history** — the silver bottleneck.

---

## B1 — CLOSE AN OPEN POSITION BEFORE A RELEASE? (the one with a real mechanism) ✅ tested

**Question (from FAV2-02):** the research says trimming into a news vol-burst gives up variance, not
return (Moreira–Muir) — is it worth it on our ledgers? The clean, **cost-neutral** test: for every
champion trade open across an 08:30 release, compare holding through vs closing at 08:29 (moving the exit,
adding no round-trip). Raw: [`results/close_on_news_nq.txt`](results/close_on_news_nq.txt).

### Result: the mechanism holds, but there is almost nothing to bite on

| NQ champion | Trades open across an 08:30 release | Give-up (P/L 08:29→exit) | p |
|---|---|---|---|
| 4h | **2 of 642 (0.3%)** | too few to test | — |
| 1h | **13 of 1157 (1.1%)** | +$349/trade (sd $981) | 0.217 |
| 15m | **17 of 1685 (1.0%)** | +$98/trade (sd $910) | 0.664 |

> **🍼 In plain words** — the mechanism is real: on the trades that *do* ride through a release, holding
> through earns **~nothing on average** (give-up indistinguishable from zero) while carrying a large
> per-trade swing (~$900 sd). So closing before news *would* be a free variance reduction. **But our
> champions are open across a release only ~1% of the time** — their hold times are short, so they're
> almost never live at 08:30. There is essentially **nothing to de-risk.** This is the same structural
> fact that made the news-veto "already flat for 77% of releases" — quantified for the decision framing.

**Verdict B1:** ✅ mechanism confirmed, ❌ **not worth building** — it touches ~1% of trades, and the
samples (n=2/13/17) are far too small to claim even the modest benefit reliably. Two caveats: the give-up
*point estimates* are slightly **positive** (holding through may even earn a little), and this is NQ only
(GC needs its champion preset, but has the same short-hold structure so the coverage will be just as
thin). **Close-on-news is mechanistically sound and practically negligible for our strategy.**

---

---

## B3 — THE "ASSIST" (scale-in after a loss): ❌ REJECTED, robustly

**The flagship idea, and the riskiest.** Hypothesis: *after a loss near news, price skyrockets, so add a
second contract and wait for both to recover.* The decisive test on 17-year NQ (full power): the added
contract is just a fresh position entered **at the loss point**, so its expected return **is** the whole
question. Does it pay after a **news** loss, and better than a matched **non-news** loss (dumb control)?
Raw: [`results/assist_nq_L40.txt`](results/assist_nq_L40.txt).

### Result: no edge at any loss threshold — and the belief is falsified

| Loss trigger | Added-contract E[return] after a NEWS loss | vs non-news control | "skyrocket" rate |
|---|---|---|---|
| **L = 20 pts** | +$66/trade (p=0.39) | +$112 (p=0.24) | **61%** |
| **L = 40 pts** | +$45/trade (p=0.71) | +$212 (p=0.21) | **45%** |
| **L = 80 pts** | −$54/trade (p=0.76) | +$97 (p=0.75) | **22–33%** |

> **🍼 In plain words — three findings, all fatal to the idea:**
>
> **1. The added contract has no edge.** After a news loss, the second contract's expected return is
> **indistinguishable from zero** at every threshold (p = 0.39 / 0.71 / 0.76), and **never significantly
> better than the same dip away from news** (the news-minus-control p-values are all > 0.2). It is a
> *fair-or-negative bet* — exactly the martingale our stop-loss study already found. The news condition
> does **not** rescue it.
>
> **2. The belief is backwards.** The "skyrocket" rate — the chance the added contract gains L within an
> hour — **falls as the loss deepens: 61% → 45% → 22%.** So the *deeper* the loss, the *less* likely the
> recovery. The premise "after a *certain* loss it will skyrocket" is the opposite of what 17 years show.
> What feels like "it always comes back" is confirmation bias: you remember the recoveries and forget the
> −$4,290 losses.
>
> **3. The tail is the account-killer.** A single added contract's *worst* outcomes run **−$3,300 to
> −$9,040**, with a per-trade sd of ~$1,200–2,200. The assist takes that at **double size**, at the exact
> moment you're already losing. This is the fat tail (#7) and the 1-second sweep, weaponized against you.

**Verdict B3:** ⛔ **REJECTED. Do not build the assist.** There is no positive, control-beating,
news-conditional recovery edge at any loss threshold; the recovery probability *decreases* with loss size;
and averaging down doubles exposure to the fat tail that has defeated every edge in this project. This is
the averaging-down-into-ruin the research (FAV2-02) and the math (Whelan/Taleb) warn of, confirmed on our
own 17 years of data. **The honest, safety-critical answer is no.**

---

## → Next

- **A2** — per-event-type PATH patterns on NQ (17y, powered): the *volatility* pattern is likely
  repeatable (spike + decay from A1); the *directional* pattern is a coin flip (17y). Short windows,
  variance-robust tests, data-snooping correction (FAV2-02).
- **B2** deprioritized (no documented edge for NQ/GC).
