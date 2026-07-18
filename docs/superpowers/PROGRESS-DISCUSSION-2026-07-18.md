# PROGRESS REVIEW — for discussion (2026-07-18)

**A single document to review everything done since 2026-07-14 and decide what's next. Six workstreams,
42 commits, 34 reports. Nothing shipped to production (byte-identical throughout); $0 spent. The point of
this page is the scorecard, the discoveries, what the discipline *prevented*, and the decisions that are
now yours.**

Branch `fundamental-analysis` (pinned worktree, isolated from the parallel `dev` agents). Full index:
[`MASTER-STATUS-2026-07-14.md`](MASTER-STATUS-2026-07-14.md).

---

## 1 — THE SCORECARD

| Workstream | Verdict | Deployable? |
|---|---|---|
| **Fundamental analysis** (news) | Scheduled US macro is **priced in** — earned at 882 releases / 99% power. Direction, magnitude, persistence, shape all null. | Nothing to deploy — no edge |
| **News v2 → decisions** (NQ+GC) | Gold reacts (7.2×, weights **NFP** where NQ weights **CPI**); close/enter negligible/no-edge; **assist REJECTED** (belief backwards + ruinous); content→pattern = **volatility, not direction**. | Nothing to deploy; assist actively dangerous |
| **Dynamic stop-loss** (#3/#11) | Fair martingale even at **1-second** resolution (94% of stop-outs are 2-sec sweeps, but chasing them doesn't pay). | **Keep the fixed stop** |
| **Session windows** (#5) | Real in the **tape** (U-shape) and in our **risk** (stop-out 56% RTH vs 16% Asia), **not** a tradeable entry edge. Overlap a non-event for NQ. | Sizing input, not a filter |
| **Own distribution** (#7) | Trade P&L **truncated** by the stop (bimodal, light tails); raw returns **fat** (α≈3); vol-scaled stop **rejected** (gambler's ruin). | **Keep the fixed stop** |
| **Fat-tail sizing** (#17) | Full Kelly 2.5% but CI [0.3%,4.4%]; drawdown binds → **risk ~0.6–1.2% (quarter-half Kelly), edge-champs only, hard cap**. Vol-targeting promising-pending-OOS. | **Recommendation (not shipped)** |

**Housekeeping done:** the `veto_mask` engine trap renamed + documented (#4, golden 6/6 byte-identical);
the ALFRED/cache/watchdog silent-failure bugs fixed; a data-source assessment (#16).

---

## 2 — THE DISCOVERIES THAT MATTER

1. **News is a *volatility* event, not a direction.** 17 years, ~100% power: the surprise predicts neither
   which way nor how far nor the shape. The volatility burst (8× spike, event-specific decay) is real and
   saveable for *sizing/stops*; the direction is a coin flip. Gold is a genuinely different instrument
   (jobs-channel vs Nasdaq's inflation-channel) but equally unpredictable directionally.
2. **The stop is doing exactly its job.** It converts a fat-tailed return process (α≈3, gaps that can blow
   *through* it live) into a bounded, bimodal trade P&L. That's why the fixed stop is right and why both
   the dynamic stop-loss and the "assist" are wrong — they remove or double past the protection.
3. **The edge is real but small and fragile.** Realized win rate ~40% at a 1.5 payoff → a tiny positive
   expectancy (~$27/trade) against a ~$960 per-trade swing, estimated in a single fluke-prone 18-month
   window. Kelly punishes edge-error hardest, so the honest response is small, capped sizing.
4. **"After a loss it skyrockets" is empirically backwards.** On 17 years, the recovery rate *falls* as the
   loss deepens (61%→45%→22%). The feeling is confirmation bias.

---

## 3 — WHAT THE DISCIPLINE PREVENTED (the real value)

Every one of these looked plausible and was killed by a pre-declared test before it could ship:

| Idea | Why it died |
|---|---|
| The 2025 "hawkish-Fed" direction story | −0.43 → −0.004 at full power (2025 luck) |
| The magnitude "survivor" | +0.187 → −0.018 (2025 was the luckiest of 17 years) |
| The dynamic stop-loss | fair martingale even at 1-second |
| The **assist** (scale-in after loss) | no recovery edge; recovery *falls* with loss size; ruinous tail |
| The vol-scaled **stop** | fixed stop/TP already regime-invariant (gambler's ruin) |
| Silver (p=0.007) | died to −0.173 under the better surprise ruler → frozen |
| A session entry filter | edge doesn't inherit the tape's shape robustly |

And **my own mistakes, caught:** a healthy run killed over a misread error count; a results file with
inverted power labels; a cache that never hit; a sweep detector true-by-construction; two verdicts testing
the wrong contrast; a wrong Z4 prediction. All caught, corrected, documented.

---

## 4 — DECISIONS WAITING ON YOU

| # | Decision | Context | My recommendation |
|---|---|---|---|
| **D-A** | **Assemble long GC history from the existing pipeline** *(corrected 2026-07-18)* | The single bottleneck. Frozen: GC news + GC distribution. Blocked: Z3 vol-targeting's OOS test, the silver forward test. **NOT a paid acquisition** — the server already has the Databento source that produced `NQ.csv` and a *generic* assembler (`main_futures_seconds.py`) that turns any market's raw dump into 1-second continuous candles. NQ was chosen for the 2010 download because the news study was NQ-only; GC/all others are 2025-2026 only. | ✅ **Download GC 2010 raw from the same Databento source, drop it on the server, run the assembler.** Barchart is NOT needed. Same recipe extends to SI/CL/etc. |
| **D-B** | **Adopt the sizing recommendation?** | Risk ~quarter-to-half Kelly (0.6–1.2%/trade), edge-champs only, hard cap. Well-supported but rests on a fluke-window edge and modeled (not live) gap fills. | ⏸️ **Paper-adopt as a risk *ceiling*; don't leverage up.** Confirm the edge OOS before real capital moves. |
| **D-C** | **Vol-targeting contracts?** | Promising in-sample (Sharpe 3.2→3.9, both halves) but unexplained (corr≈0), turnover-heavy, in-sample. | ⏸️ **Hold for OOS** — needs D-A (GC) or a longer frame first. |
| **D-D** | **Silver forward test?** | Frozen pre-registered test; needs data past 2026-07-02. | ⏸️ **Re-run `study_silver.py` when new data exists.** No action now. |

---

## 5 — THE HONEST BOTTOM LINE

**The strategy is well-designed, and this session mostly *confirmed* that by trying hard to improve it and
failing honestly.** The fixed stop is right; the direction is unpredictable; news and sessions inform
*risk*, not *entries*; the edge is small and fragile; sizing should be modest and capped. We shipped no new
feature — but we **prevented several dangerous or spurious ones**, and we now understand *why* the current
design works (gambler's-ruin scale-invariance, the stop truncating the fat tail).

**The binding constraint on further progress is data, not analysis.** Almost every remaining thread — GC
direction, GC distribution, vol-targeting OOS, silver — is frozen for one reason: **we only have long
history for NQ.** The 17-year NQ frame is what turned guesses into 99%-power answers.

**Correction (2026-07-18):** getting the same long frame for GC is **not** a paid vendor purchase. The
server already holds the Databento source that produced `NQ.csv` and a *generic* assembler
(`/home/dev/Mulham/data_2010_1s/main_futures_seconds.py`) that builds 1-second continuous candles for any
market. NQ was the only 2010 market assembled because the news study was NQ-focused at download time. The
highest-leverage next step is simply: **pull GC 2010 raw from that same Databento source and run the
assembler** — a download-and-assemble, not a Barchart quote. (Verified: no GC 2010 file exists on the
server or in the local zips; every non-NQ market starts 2025-01-01.)

**What I'd genuinely value your steer on:** (a) whether to pursue the GC data (D-A), (b) whether the sizing
recommendation is directionally what you want before I refine it further, and (c) whether there's a *new*
question worth opening now that the strategic map is mapped — the workstreams answered the questions we
had; the interesting frontier may be one we haven't asked yet.
