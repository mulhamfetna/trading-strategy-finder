# PLAN — FA-v2: news × trading DECISIONS, narrowed to NQ + GC

**The fundamental-analysis workstream, re-opened 2026-07-14 with a narrowed scope and an expanded goal.
Per the user's new rules: study news only against NQ (Nasdaq) and GC (gold); drop the other 7 markets;
move from "does news predict the return" (answered: no) to "how should news drive a trading DECISION" —
closing, entering, or ASSISTING an open position — and lean harder on the CONTENT of the news, not just
its timing.**

Date: 2026-07-14 · Branch `fundamental-analysis` (pinned worktree). Supersedes the multi-market scope of
reports 05/robustness for FUTURE development. The closed findings (reports 00–06) still stand as history.

---

## 1 — THE NEW SCOPE (rules)

1. **Markets: NQ and GC only.** Gold reacts to US macro differently from Nasdaq (safe-haven / inflation
   hedge vs risk-on), so it is worth its own study — but the other 7 markets are **dropped from future
   development.** (Their closed results remain on the record.)
2. **From prediction → DECISION.** The question is no longer "does the surprise predict the move" (answered
   NO at full power). It is: *given a news event, what is the best action on our book* — close an open
   position, enter a new one, or **assist** (scale in) an open losing one.
3. **Content, not just timing.** Test whether a *specific announcement* produces a *repeatable price
   pattern* we can save and turn into a rule.

---

## 2 — WHAT IS ALREADY ANSWERED (do not re-run blindly)

| Sub-question | Status |
|---|---|
| Surprise **direction** → NQ return (pooled) | ❌ DEAD at n=870 / 99% power (−0.004) |
| Surprise **magnitude** → NQ move size (pooled) | ❌ DEAD (−0.018); the "survivor" was 2025 luck |
| Surprise → **shape / persistence** (pooled) | ❌ DEAD (p=0.880 / 48.2%) |
| The 08:30 **volatility spike** itself | ✅ REAL and large (8.3× on NQ) — vol is real, *direction* is not |
| General (non-news) post-stop **martingale** | ✅ FAIR — no edge to adding on loss, in general |

**The load-bearing implication:** what's dead is *predicting direction/size from the surprise, pooled on
NQ.* What is **NOT** ruled out and is genuinely new: **GC specifically**, **per-event-type conditional
patterns**, and every **news-conditional trade-management decision** (close/enter/assist) — because those
are different questions than "predict the pooled return."

---

## 3 — THE NEW EXPERIMENTS (each gated by the standing discipline)

### Group A — CONTENT → repeatable pattern → rule

- **A1. Does GC react to US macro at all, and how?** Foundational measurement (GC analog of NQ's 8.3×
  spike): the volatility/return response of GC at 08:30 releases, direction and size. *Power-irrelevant
  (a measurement).* **Data: GC 1-min 2025-2026 (wsg-i).**
- **A2. Per-event-type conditional patterns.** For a *specific* announcement (NFP / CPI / PPI / retail /
  PCE / FOMC), does the subsequent path show a repeatable, saveable shape on NQ and GC — beyond the
  shuffled-surprise null? *This is the "content → pattern → rule" idea, done per event type rather than
  pooled.* ⚠️ Powered on NQ (17y); **underpowered on GC** (2025-2026 only) → GC results pre-registered/frozen.

### Group B — News-triggered DECISIONS on an open position

- **B1. Close-on-news.** Does flattening an open position before/at a release beat holding through it?
  (Distinct from the veto: this acts on the *open book*, not entries.) NQ + GC champions.
- **B2. Enter-on-news.** Does entering at a release have an edge as a *decision* (not a prediction)?
  Re-tested NQ+GC-specific with the dumb control.
- **B3. ⚠️ ASSIST (scale-in after a loss) — the flagship new, and the riskiest.** The user's hypothesis:
  *after a certain loss near a news event, price skyrockets, so add a second contract and wait for both to
  recover.* **This is a martingale (adding to losers) — the classic account-killer.** We test it, we do
  not assume it. The pre-declared test:
    - Conditional on holding a losing position of size L during/after a news release, is the subsequent
      recovery **better than (a) chance and (b) a matched NON-news loss of the same size (the dumb
      control)?**
    - If news-losses recover no better than non-news losses → the "assist" is just a martingale with a fat
      tail (which #7 is quantifying) → **REJECT, do not build.**
    - Only if a genuine **news-conditional recovery edge** survives the dumb control + noise check + power
      → design the assist rule (trigger loss, add size, hold horizon) and stress-test the tail risk.

---

## 4 — HARD CONSTRAINTS & CAVEATS (declared up front)

1. **GC has only 2025-2026 data** (the 17-year frame is NQ-only). Every GC finding starts **underpowered,
   in the fluke window** — the silver trap. GC results are **frozen/pre-registered** unless we acquire long
   GC history (a data request, analogous to the 17-year NQ acquisition).
2. **The assist/scale-in idea multiplies exposure to the very fat tail #7 is characterizing.** A martingale
   converts "win small often" into "lose huge rarely." It must clear a *high* bar (a real news-conditional
   recovery edge, not just the general fair martingale) before it is anything but a research finding.
3. **Discipline applies to all of it:** power on every negative, dumb-control + noise-check on every
   positive, pre-registered criteria, no hand-typed numbers, research-first on genuinely new territory.

---

## 5 — SEQUENCE

1. **Research-first** (per the HARD rule) on the genuinely new decision layer: gold's reaction to US macro,
   news-based position *management* (close/scale-in), and the evidence on averaging-down/martingale near
   events. → a real-vs-folklore report.
2. **A1** (GC reacts?) — foundational, runnable now.
3. Then A2 / B1 / B2 / **B3** in priority order, NQ + GC, with the discipline.
4. Data request if a powered GC study is warranted (long GC history).

**Open decision for the user:** do we want to acquire **long GC history** (like the 17-year NQ) so GC news
studies are powered rather than frozen? Cheap to ask FRED/data vendors; it's the same bottleneck that
silver hit.
