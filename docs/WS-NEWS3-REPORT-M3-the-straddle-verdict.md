# WS-NEWS3 M3 — the straddle, finally tested: not confirmed, dominated by its own long leg — which IS confirmed

**Date:** 2026-08-16 · **Issue:** #117 (M3), parent #124 · pre-registered on #117 before any code ran
**Verification:** V1 PASS (1s reproduces P1's 1m cell: +$80.80 vs +$84.24, n=574 exact) · V2 PASS
3/3 (first 60s carry 0.91–1.01 of the +900s move) · V3 PASS on NQ/RTY, **FAIL on CL → CL VOID as
registered** · ledger **27/27** (`P3-STRADDLE-NOT-CONFIRMED`, `P3-LONG-RELEASE-TRADE-CONFIRMED`,
`P3-WHIPSAW-MEASURED`) · selftest 5/5 · evidence committed (dcb3eea)

---

## Part 0 — What was tested (the experiment the WS-NEWS2 closeout skipped)

The owner's proposal, verbatim in #117 since the workstream began: at the release moment, enter
**long AND short** with a **small stop** and a **big take-profit**, so the violent move pays one leg
whichever way it goes. Design (all fixed in the pre-registration): 1-second bars; entry at the
close of the bar at release−300s; stop fills at the worse of line/open (GAP-01); TP is a resting
limit (better of line/open); **a 1-second bar breaching both stop and TP counts as STOPPED**
(pessimistic); open legs exit at release+900s; grid S ∈ {0.05, 0.10, 0.20}% × TP ∈ {0.20, 0.40,
∞}% × {straddle, long-only}; costs per **leg** $2.50 + {1,2,4} ticks — the straddle pays two legs
(NQ stressed: $45/event). Targets from M2's power table: {CPI, NFP, FOMC} on NQ (329 events) and
RTY (239); EIA on CL (549) as the no-premium control instrument.

## Part 1 — Gates first

- **V1 — two frames, one trade:** the long-only arm (S=0.20%, no TP) run on P1's full five-series
  NQ set from the **1-second** file reproduces the **1-minute** pipeline: **+$80.80 vs +$84.24**
  (n=574 exactly; the $3.44 is finer stop-fill resolution, in the expected direction).
- **V2 — the release-second physics:** the first 60 seconds carry **0.97** (NQ), **1.01** (RTY),
  0.91 (CL) of the whole 15-minute |move| on average — round 1's "$132 of $137 inside the minute"
  reproduced at 1-second resolution. A timezone or alignment defect could not have survived this.
- **V3 — the structure must not pay where there is no release:** NQ control straddle −$31.44
  (p=0.99) ✅, RTY −$3.63 ✅. **CL +$19.12 gross, p=0.002 — FAIL ⇒ CL's arm is VOID as registered.**
  Whatever the straddle harvests on CL exists at ordinary matched minutes too, so nothing there is
  attributable to the release — and net of the $85 stressed two-leg cost even that gross is deeply
  negative. Dead either way; recorded as VOID, not as a null.
- ⚠️ One units defect caught before publication: the first run printed "median time-to-TP 239s"
  that was really 239 **bars** — 1-second files carry bars only for seconds with trades (NQ has
  ~203 of the 300 pre-release seconds; RTY ~116). Exits are now timestamped in real seconds
  relative to the release; the rerun's numbers are the record.

## Part 2 — ⭐ The pre-registered PRIMARY: the straddle is NOT confirmed

> **STRADDLE S=0.10%, TP=0.40%, NQ {CPI+NFP+FOMC}, net of stressed costs: +$50.33/event,
> t = +1.35, one-sided p = 0.0897 (n=327). NOT significant at the registered α=0.05.**

Two honesty notes, both mandatory:
1. **This is not an exclusion.** The cell's MDE is ≈ $104/event and the CI spans [−23, +124]; a
   modest positive straddle cannot be ruled out at this sample size (power rule respected — no
   negative is claimed).
2. **What IS decisive is domination: the straddle is beaten by its own long leg in 18 of 18
   (instrument × S × TP) cells.** The short leg pays the premium (M1) and the second leg doubles
   costs. There is no configuration in which adding the short leg helped. The structure fails not
   because the moment lacks money, but because half the structure is pointed the wrong way.

## Part 3 — ⭐⭐ The trade that IS confirmed, under the strictest bar this programme has

The pre-registered secondary criterion — Bonferroni α = 0.05/54 across every cell examined, AND
sign-consistency on both chronological halves — is met by the **LONG arm** on both instruments:

| cell (enter release−300s) | gross $/event [95% CI] | net stressed | t | halves |
|---|---|---|---|---|
| **NQ long S=0.10% TP=0.40%** | **+155.56 [+81.83, +229.30]** | **+133.06** | **4.13** | +51 / +259 ✅ |
| NQ long S=0.20% TP=0.40% | +163.08 [+75.57, +250.59] | +140.58 | 3.65 | +68 / +257 ✅ |
| NQ long S=0.10% no TP | +184.28 [+78.22, +290.33] | +161.78 | 3.41 | +67 / +301 ✅ |
| **RTY long S=0.10% TP=0.40%** | **+57.98 [+28.02, +87.94]** | +35.48 | **3.79** | +27 / +89 ✅ |
| RTY long S=0.20% no TP | +122.72 [+55.51, +189.94] | +100.22 | 3.58 | +58 / +188 ✅ |

Its falsifiers: the identical cell on matched no-news control windows is **negative** (NQ −$27.91,
RTY −$8.01), and the FOMC subset — the release M1 showed has no premium — shows nothing (−$4.32).
This is not "any window traded this way pays"; it is release-specific and premium-specific.

**Per-series at the NQ winning cell:** CPI **+$331.52 [+187, +476]** (n=116) · NFP +$100.60 (ns) ·
FOMC −$4.32. The engine is once more CPI — third time, third independent method (M1 1-minute ride,
M2 magnitude, M3 1-second structure).

**Anatomy of the winning cell (NQ):** 48.6% stop after the release (−1R ≈ −$47 avg), **22.9% hit
the +4R take-profit**, 15.6% ride to the timed exit, 12.8% die before the release. The convexity is
exactly the owner's "small stop, big take profit" intuition — **executed on one side only.**

**Timing (real seconds, from the fixed rerun):** TP fills at **median 15s after the print** on NQ
(p25 = 1s, p75 = 80s), **3s** on RTY; post-release stops at median 2–3s. The trade is entered five
quiet minutes early and *decided within seconds of the release* — consistent with V2 and with
Christensen–Timmermann–Veliyev's price-discovery-in-seconds (from #112).

## Part 4 — The whipsaw, measured at last (headline it was registered to be)

| stop | NQ both-legs-stopped | RTY |
|---|---|---|
| 0.05% | **65.4%** | **72.7%** |
| 0.10% | 46.2% | 55.9% |
| 0.20% | 20.5% | 31.9% |

The 94%-of-stop-outs-are-1-second-sweeps threat is real and now quantified for this structure:
**at the owner's "small stop", roughly two thirds of straddles lose BOTH legs.** Monotone in stop
width (the falsifier: a rate that ignored the stop would be a pipeline artefact — it doesn't).
A single long leg survives this regime because it only needs the up-side of the whipsaw once; a
two-legged structure pays the sweep twice.

## Part 5 — What it is worth, and what it is not

NQ winning cell, ~52 events/yr: net stressed ≈ **+$6,900/yr per contract** (CPI-only variant:
12 × +$331 ≈ +$4,000 gross on a tenth of the exposure days). RTY adds ≈ +$1,800. Fat-tailed as
ever (median event loses; the CPI tail pays). Standing constraints unchanged: **no quantity term
in the engine** — deployment needs the sizing/multi-leg decision (owner's), and the era
concentration (halves +51/+259) makes a rolling CPI-mean monitoring rule mandatory in any spec.

⚠️ Execution caveat, pinned in the claims' blind spots: fills inside the release second assume
stop/TP orders execute at line-or-open on 1-second bars. The stressed scenario already carries 4
ticks; sweep-second slippage beyond that is invisible to this data and stated, not hidden.

## Part 6 — What went well / what went wrong

**Well:** the pre-registration held its shape under pressure — the owner's structure was tested
exactly as proposed, failed its primary honestly, and the thing that *is* real emerged under a
stricter bar than the primary itself; the V1 frame-bridge (1s ↔ 1m, ±$4 on the same 574 events)
retires a whole class of doubts; CL's VOID shows the falsifier doing its job on the third
instrument rather than rubber-stamping.

**Wrong, kept visible:** the first run published-to-log a timing number in wrong units (bars as
seconds) — caught before any report carried it, fixed in code with the reason; and the primary's
arm choice was knowably suboptimal from M1 (the straddle was registered anyway because it was the
owner's actual proposal — the right call, but worth recording that the registered primary and the
best-supported hypothesis differed going in).

## Part 7 — Milestones (#124)

M0 ✅ M1 ✅ M2 ✅ **M3 ✅ (this report)** — next **M4: closeout** — the workstream goal is now fully
answered clause by clause; M4 assembles the final report, the deployment-decision packet for the
owner (sizing/multi-leg engine change, monitoring rule, the confirmed spec), and the memory update.
