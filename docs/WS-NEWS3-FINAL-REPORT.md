# WS-NEWS3 — FINAL REPORT: the news goal, answered clause by clause — and the first confirmed news trade

**Date:** 2026-08-16 · **Tracking:** #124 (closing with this report) · **Worktree:** `legacy18`
**Milestones:** M0 audit ✅ · M1 ride/drift ✅ (#125) · M2 power model ✅ (#126) · M3 structure ✅ (#117) · **M4 closeout = this report**
**Verification at close:** claims ledger **27/27** (9 WS-NEWS3 claims) · selftest 5/5 · every
evidence file committed · all work completed 2026-08-16, six days ahead of the M4 date.

Stage reports: `WS-NEWS3-GOAL-REEVALUATION-AND-PLAN` · `-REPORT-P1-the-ride-and-the-premium` ·
`-REPORT-M1-FULL-experiment-log` · `-REPORT-M2-the-power-model` · `-REPORT-M2-FULL-experiment-log`
· `-REPORT-M3-the-straddle-verdict` · `-REPORT-M3-FULL-experiment-log`.

---

## Part 1 — Why this workstream existed

WS-NEWS2 closed with "no tradeable edge" — but the audit (M0) found it had answered the
**direction** question and called the whole goal done, while two of the owner's three strategy
classes — the pre-positioned ride and the non-directional straddle — had **never been simulated**,
and #117's no-go argued against a different strategy than the one recorded in its own body.

> ⭐⭐ The meta-rule that created WS-NEWS3, now permanent: **a workstream is closed against its GOAL
> STATEMENT, not against the strongest verdict it happened to produce.**

## Part 2 — The goal, answered clause by clause (the table the workstream owes the owner)

| # | Owner's goal clause | Answer | Where |
|---|---|---|---|
| 1 | *"relation of previous/forecast/actual → the POWER of news"* | ✅ **Strong and usable.** The surprise explains the jump (ρ to −0.63, WS-NEWS2); power is predictable the NIGHT BEFORE from series identity + own history (OOS ρ ≈ 0.5 on all five instruments); in the current regime CPI is #1 on NQ and RTY | M2 |
| 2 | *"…→ the DIRECTION we want to ride"* | ⛔ **Dead, every route, powered.** From consensus (H1-B/C), from the surprise post-release (1/612 → below break-even), from the pre-release price pattern (0.48–0.51, every CI-hi < 0.71). **Direction cannot be predicted — and the confirmed trade does not need it** | WS-NEWS2, M1 |
| 3 | Phase 1: *"enter early and ride… study that we don't hit the stops before the news"* | ✅ Survival: cheap stops die pre-release (NQ 57%, CL 94% at 0.05%/5min — H1-A); the ride itself carries the **announcement premium**, LONG only, confirmed on a pre-registered untouched holdout (RTY +$69.54/event, p=0.0007) | M1 |
| 4 | Phase 2: the three-number relation | ✅ = clause 1 + 2. Bonus closure: **|forecast−previous| adds nothing** (powered) — the consensus numbers are fully dead as pre-release inputs | M2 |
| 5 | Phase 3: *"enter long AND short, small SL, big TP — either way we profit from the craziness"* | ⭐ **Tested exactly as proposed: NOT confirmed** (+$50 net stressed, p=0.09; not excluded, MDE $104) **and dominated by its own long leg in 18/18 configurations.** The convexity intuition is CONFIRMED — one-sided | M3 |
| 6 | Phase 3: *"smart entries fusing prior knowledge with the moment"* | ✅ That is precisely the confirmed spec: M2's filter chooses WHICH releases, M1's premium chooses the SIDE, M3's bracket chooses the SHAPE | M1+M2+M3 |

## Part 3 — ⭐⭐⭐ THE RESULT: the first confirmed, capturable, net-of-costs news trade of the whole programme

> **LONG NQ (or RTY), enter at the close of the 1-second bar 300 s before a {CPI, NFP, FOMC}
> release, stop 0.10% of price, take-profit 0.40%, exit any open position at release + 900 s.**
>
> **NQ: +$155.56/event gross [+81.83, +229.30], t = 4.13 — clears Bonferroni α = 0.05/54 — net
> +$133.06 under STRESSED costs; sign-positive on both chronological halves (+51/+259).
> RTY: +$57.98, t = 3.79, same bar.** Controls negative (−$28/−$8), FOMC-alone null, CPI the
> engine (+$331/event, n=116). ≈ +$6,900/yr/contract NQ + $1,800 RTY at one contract.

What it is: the **macro-announcement premium** (Savor–Wilson), harvested with a convex bracket at
1-second resolution — paid for holding equity risk through the resolution of scheduled macro
uncertainty. What it is not: a prediction. Direction remains unknowable per event (win rate 36.4%,
median event −$136); the 22.9% of events that hit +4R pay for everything; the trade decides at
median **+15 s** (NQ) / **+3 s** (RTY) after the print.

**Why four previous attacks missed it:** WS-EARN, round 1, and WS-NEWS2 all asked *"can we predict
which way?"* — the answer was always no. The premium is the *unconditional* mean nobody measured,
found only when M1 priced the ride itself. Every effect the programme ever found was real; this is
the first one on the tradeable side of both walls (kind: not direction-dependent; timing: entered
before the moment, decided after it).

## Part 4 — The through-line of the four news workstreams, final form

| attack | real effect found | fate |
|---|---|---|
| WS-EARN (#109–113) | earnings → 4.98× vol | magnitude, no direction — unusable without sizing |
| round 1 / GC | 5.5σ reaction, $132/$137 in the minute | reactive entry impossible |
| WS-NEWS2 (#114–123) | surprise → jump ρ −0.63 | input arrives with the move; post-window empty |
| **WS-NEWS3 (#124–126, #117)** | **the premium + the bracket** | **⭐ confirmed net of stressed costs** |

## Part 5 — THE OWNER DECISION PACKET (the two calls only the owner can make)

### Decision 1 — the engine: sizing + a release executor
`pnl = pnl_points × pv` has **no quantity term**, and the engine is candle-based while this trade
lives at 1-second resolution with a bracket (entry-at-time, SL, TP, timed exit). Deploying the
confirmed spec therefore needs: (a) the **sizing/multi-leg layer** (the same change that would
unlock WS-EARN's 4.98× and every magnitude finding), and (b) a small **dedicated release
executor** (schedule-driven: ~52 known timestamps/yr — it does not need the strategy engine at
all). Without Decision 1 the workstream's result remains knowledge, not P&L.

### Decision 2 — the regime monitor (mandatory in any deployment)
The magnitude is era-concentrated (NQ winning cell: 2016–19 +$59 · 2020–21 +$24 · 2022+ +$292;
positive in all three eras, big in one). Proposed alarm, to be pinned before go-live: **rolling
24-event mean of the CPI-day trade < $0 ⇒ stand down** — plus the annual ledger re-run
(`optimize/verify/run.py`) so the claims stay tied to the data.

### The risk numbers the decisions should be made against
- worst measured single loss = **2.1× the nominal stop** (gap-through-stop on a sweep second) —
  budget the −1R leg as −2R;
- fills assume line-or-open on 1-second bars; sweep-second slippage beyond the stressed 4 ticks is
  unmeasurable in our data (blind spot pinned in the claims);
- fat-tailed by construction: most weeks lose small; a handful of CPI seconds pay the year;
- n = 116 CPI events carries the economics.

## Part 6 — What the verification system caught this time (the workstream's other product)

Every one of these was caught **before** publication — the redo-loop the owner ordered killed:

1. The M0 audit itself was wrong once (claimed H1-A never ran) — caught same-day by verify-don't-assume.
2. **Every control the programme ever drew** ("no *tracked* release that day") was contaminated —
   V3 failed 4/4, exposing Jobless Claims/PPI/GDP at 8:30 on "quiet" days; controls now clean
   against the full 39k-event calendar; H1-A's danger ratios were understated, not overstated.
3. The 8:30 minute's residual 1.4–1.6× was split from pipeline artefact by quiet-minute controls
   (0.89–0.94×) instead of loosening the threshold.
4. M2's V2 anchor named the wrong quantity (premium vs power) — failed as registered, became the
   **power ≠ premium** principle.
5. M2's V1 failure exposed the **regime lag** (expanding median 4.16× under CPI) — cured by a
   *declared* trailing-24 variant under identical gates, never a silent swap.
6. One ledger check compared row counts across two different filters — a defect in the CHECK,
   rebuilt to re-derive the statistic; no `expect` touched anywhere, ever.
7. The 1-second timing readout shipped to logs in wrong units (bars ≠ seconds in a trade-sparse
   file; NQ has 203/300 pre-release traded seconds) — fixed before any report carried it.
8. CL's V3 VOIDed an instrument whose structure "paid" at no-news minutes — the falsifier refusing
   to attribute to news what exists without it.

## Part 7 — Rules extracted (already in memory; listed for the record)

Close against the goal statement, not the strongest verdict · power ≠ premium — name the quantity
an anchor ranks · "no release that day" ≠ "no news at that minute" — clean controls against the
full calendar · when a falsifier keeps failing, split the hypothesis, never loosen the threshold ·
a bar offset in a trade-sparse file is not a duration · a verification check must measure the same
quantity as the thing it verifies · pre-register the confirmatory test on data never touched (RTY),
and let the registered primary fail honestly when it fails.

## Part 8 — Open items at close (explicit, so nothing silently drops)

| item | status | owner |
|---|---|---|
| Decision 1 — sizing/multi-leg + release executor | **OPEN — owner call** (gates deployment) | owner |
| Decision 2 — regime-monitor alarm before any go-live | **OPEN — owner call** | owner |
| straddle's not-excluded +$50 (needs ~4× events) | recorded, moot while the long leg dominates | — |
| sweep-second slippage beyond bars | needs tick/live data — impossible with current data | — |
| YM aggregated frames 0 bytes | data-engineering fix, carried from WS-NEWS2 | backlog |
| `forecast` + API/EIA provenance | permanently unverifiable (no archives) — standing caveat | — |
| WS-EARN C4 owner check (#110) | still pending with the owner | owner |

## Part 9 — What went well / what went wrong (workstream-level)

**Well:** the owner's instinct that the goal was not exhausted was **correct** — the audit found
the gap, and the gap contained the programme's first confirmed trade. The cadence (verbose report →
issues → verification → proceed) produced eight catches before publication and zero redo-loops.
Every milestone landed early. The four-workstream arc ends with an answer instead of a residue of
maybes: what can be predicted (power), what cannot (direction), and what pays anyway (the premium,
harvested convexly, long only).

**Wrong, kept visible:** the audit's own first claim was false for an hour; two registered gates
were mis-specified by their author (me) and stayed failed in the record; a units lie reached the
logs. All were caught by the machinery this project built for exactly that purpose — which is the
point of having it.

---

**WS-NEWS3 is CLOSED.** The news programme (four workstreams, 2026) is complete: further work is
deployment engineering and owner decisions, not research. The ledger will say whether that ever
stops being true.
