# FA-v2 · 00 — THE COMPLETE WORKSTREAM REPORT (news → decisions, NQ + GC)

**The re-opened news workstream, start to finish. New rules from the user (2026-07-15): study news only
against NQ + GC, drop the other 7 markets, and move from PREDICTION (answered: priced in) to DECISION —
close / enter / assist an open position — plus content → repeatable pattern → rule. This document is the
detailed record of what we tested and what came back. Every experiment: NQ+GC, full discipline, $0,
production untouched.**

Date: 2026-07-15 · Branch `fundamental-analysis` (pinned worktree). Detail:
[`FAV2-01-FINDINGS`](FAV2-01-FINDINGS.md) (A1/B1/B3/A2) · [`FAV2-02-RESEARCH`](FAV2-02-RESEARCH-decisions-real-vs-dangerous.md)
(decision research) · [`plans/2026-07-14-fa-v2-nq-gc-decisions.md`](plans/2026-07-14-fa-v2-nq-gc-decisions.md) (plan).

---

## PART 0 — THE GREAT PICTURE

> **🍼 In one paragraph** — We re-asked the news question with sharper tools: forget predicting direction
> (we proved that's dead), and instead ask what to *do* around a release, on Nasdaq and gold. The answer
> is consistent and clean: **news is a VOLATILITY event, not a direction or a recovery.** Gold reacts
> strongly (differently than Nasdaq — it cares about jobs, Nasdaq cares about inflation), but neither
> gives a tradeable direction. Closing a position before news is sound in theory but pointless in practice
> (we're almost never holding across a release). And the flagship "assist" idea — adding a contract after
> a loss because it'll "skyrocket" — is **false and dangerous**: 17 years show the recovery gets *less*
> likely the bigger the loss, not more, and doubling down just multiplies the catastrophic tail. The one
> real, saveable pattern is the **volatility shape of each announcement** — useful for sizing and stops,
> not for betting a direction.

| The new idea | Verdict | Evidence |
|---|---|---|
| **Gold as a distinct news instrument** | ✅ **Real, different** | Reacts 7.2× (NQ 8.6×); weights **NFP (jobs)** where NQ weights **CPI (inflation)** |
| **Close/trim before a release** (B1) | 🟡 **Sound but negligible** | Mechanism holds, but champions are open across a release only **~1%** of the time |
| **Enter on the release** (B2) | 🔴 **No edge** | Directional drift is bond-market-only; pre-FOMC equity drift died post-2011 |
| **ASSIST — scale in after a loss** (B3) | ⛔ **REJECTED — false & dangerous** | No recovery edge (p≈0.7); recovery *falls* with loss size (61%→45%→22%); tail −$3k to −$9k at 2× size |
| **Content → pattern → rule** (A2) | ✅ **Volatility yes, ❌ direction no** | Repeatable per-event spike-decay (NFP 13.6×, CPI 12.3×); direction a coin flip at full power |

---

## PART 1 — THE EXPERIMENTS

### A1 — Does gold react to US macro? ✅ YES, and differently

GC spikes **7.2×** a normal minute at the 08:30 release (NQ 8.6×, same window), identical spike-decay
shape. **The instrument-specific weighting is the discovery:** NQ reacts most to **CPI** (inflation → Fed
→ equities), gold reacts most to **NFP** (jobs → real rates / dollar → gold) — economically sensible, and
proof the two are different bets (the reason gold was added). A 2025–2026 directional tilt (+6.9 bp,
p=0.02 on NQ) was **flagged as fluke-window bull-drift, not a signal** — it doesn't touch the 17-year
direction null.

### B1 — Close before a release? 🟡 Mechanism real, coverage negligible

The research's one mechanism-backed idea (trimming a vol burst gives up variance, not return — Moreira &
Muir). Tested cost-neutrally on the NQ ledgers: on trades that *do* ride through a release, holding through
earns ~nothing (give-up p=0.22/0.66) while carrying ~$900 sd — so closing *would* be a free de-risk. **But
champions are open across an 08:30 release only ~1%** of the time (4h 0.3%, 1h 1.1%, 15m 1.0%). Short holds
mean there's almost nothing to de-risk. **Sound, not worth building.**

### B3 — The "assist" (scale-in after a loss) ⛔ REJECTED

The flagship, and the riskiest. The added contract is a fresh position at the loss point, so its
expectancy *is* the whole question. On 17 years, at L = 20/40/80 points:
- **No edge:** added-contract E[return] after a news loss is indistinguishable from zero (p=0.39/0.71/0.76)
  and never beats a matched non-news loss.
- **The belief is backwards:** the recovery ("skyrocket") rate *falls* as the loss deepens — **61% → 45%
  → 22%.** Deeper losses recover *less*.
- **The tail is the account-killer:** single-contract worst cases −$3,300 to −$9,040, taken at double size.

**This is the averaging-down-into-ruin the research (Whelan/Taleb) and our own stop-loss martingale finding
both condemn. Do not build it.** The honest, safety-critical answer is no.

### A2 — Content → pattern → rule ✅ volatility / ❌ direction

Per event type, 17-year NQ (144–194 each, Bonferroni-corrected):
- **Volatility pattern REAL + saveable:** consistent spike-decay, sized by event — NFP 13.6×, CPI 12.3×
  (loudest), the rest ~4×, all fading to ~1.5× by +30 min. A genuine rule about **how big / how long.**
- **Directional pattern absent:** every event a coin flip at +30 min (% up 44–57%, none clears the bar).
  *"The announcement said X so price went up/down"* is not supported by 17 years.

---

## PART 2 — DISCOVERIES

1. **Gold is a real, distinct news instrument** — strong reaction, different channel (jobs vs inflation).
2. **News barely intersects our trading** — ~1% of trades are open across a release (short holds). The
   whole "manage the book across news" premise has almost nothing to act on.
3. **The "skyrocket after a loss" belief is empirically backwards** — recovery probability *decreases*
   with loss size. This is the single most important finding for the user's risk: it kills a dangerous idea
   with 17 years of evidence, not opinion.
4. **The saveable content pattern is a volatility pattern** — each announcement has a repeatable magnitude
   and decay; the direction is a coin flip. Consistent with everything: **news is risk, not direction.**
5. **The through-line, again:** the fat per-trade tail (the −$3k to −$9k worst cases here; the ±$1,600
   swing everywhere) is what makes direction unexploitable and averaging-down lethal. → **#7.**

---

## PART 3 — WHAT WENT WELL / WHAT WENT WRONG

**Well:** research-first correctly predicted every outcome (assist dangerous, gold different-channel,
close-on-news contested); the dumb control + 17-year power turned the assist from a "feels right" idea into
a decisively rejected one; the volatility pattern is a real, reusable deliverable.

**Wrong / caught:** A1's per-event ranking (CPI loudest) was a 2025–2026 artifact — on 17 years NFP edges
CPI; the short window over-weighted one sample. Flagged, corrected on the powered frame. The initial B1
script used a trade field (`bars_1m`) that only exists with `track_excursions=True` — fixed to use
`exit_time` directly.

---

## PART 4 — VERDICT & WHAT'S NEXT

| Question | Answer |
|---|---|
| Is gold worth studying as a news instrument? | ✅ Yes — real, different. But **directional GC is frozen** (2025–2026 only). |
| Should we manage the book across news (close/enter)? | ❌ Close: negligible coverage. Enter: no edge. |
| Should we build the "assist" (scale-in after loss)? | ⛔ **No — rejected on 17 years; false and dangerous.** |
| Is there a saveable content→pattern rule? | ✅ A **volatility** rule (sizing/stops/straddle/sit-out), ❌ not directional. |

**The one positive deliverable — the event-conditional volatility pattern — feeds two live workstreams:**
- **#7 (own distribution):** the tail is event-conditional (NFP/CPI produce the biggest shocks) → fit the
  distribution conditioning on event/volatility state (the McNeil–Frey machinery).
- **#5 S3 (session-aware sizing):** event-and-session-conditional stop width.

**Open / deferred:** B2 (deprioritized); **GC directional & per-event work frozen** pending long GC history
(the open data decision, same bottleneck as silver); **task #16** (assess user-supplied data sources).

**→ Next: #7 · D1** — fit the champion's per-trade P&L distribution. The fat tail that killed the assist
and every other edge is exactly what #7 exists to characterize; the A2 volatility pattern is one of its
conditioning axes.
