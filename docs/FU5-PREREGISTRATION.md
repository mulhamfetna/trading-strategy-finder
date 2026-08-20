# FU-5 (#157) — the state-gated ride: pre-registration

**Filed 2026-08-20 BEFORE any run. The first B-family conditioning study on the frozen FU-9
substrate. The ride's median event LOSES and the +4R tail pays — if a cheap PRE-RELEASE tape
state separates tail days from chop days, the same premium arrives with less bleed. The
integrity constraints (brainstorm §2) bind: exactly TWO mechanism-first conditions, fixed
here with their predicted directions; cross-instrument confirmation via the other legs; era
halves on the data's true span; nothing ships — a passing condition only ARMS a gated
skip/scale design with its own pre-registration.**

## The two conditions (fixed now — no others will be read)

Both are computed at the last 1m bar CLOSED before the rel−300s entry (the FU-9 stance
convention), from the same extended 1m frames, strictly causal.

- **A — overnight trend agreement**: sign of (stance-bar close − the close 12 hours
  earlier). **Predicted direction: trend-POSITIVE events ride better** (the ride is LONG;
  mechanism: a risk-on tape carries the post-release drift more often than it reverses;
  note honestly AGAINST it: WS-NEWS2 killed pre-release direction for the JUMP — this bets
  on drift continuation, a different quantity, and may well be null).
- **B — pre-release tape vol**: the standard deviation of the last 60 1m log-returns before
  the stance bar, ranked against the causal history of the same measure on that instrument's
  prior events (≥20 priors; else the event is unconditioned). **Predicted direction:
  HIGH-vol (above causal median) events ride better** (the book and the premium are
  vol-seeking; sizing WITH vol beat inverse-vol; the M-era "smart entries" arm hinted state
  matters).

## Fixed design

- **Events/legs**: the deployed book (NQ/RTY {CPI,NFP,FOMC}; ES/YM {CPI}) ≥2016; outcomes =
  the FROZEN committed FU-9 v1 `ride_net_stressed_usd` (no new bracket runs — the substrate
  study as intended).
- **Primary statistic** (per condition, NQ as the primary leg): mean per-event net
  difference (condition-true − condition-false), event-bootstrap 90% CI (10,000).
- **Confirmation lines**: sign agreement on ≥2 of the 3 other legs; both era halves (split
  at the NQ events' median date) same sign as the pooled effect.
- **Multiplicity**: two conditions are two tests — a condition PASSES only with its OWN CI
  clear of zero in the predicted direction AND both confirmation lines; no third condition
  will be evaluated regardless of what the data suggests.
- **Dumb control**: each condition re-tested with the condition labels shuffled (20 seeds)
  — the real |Δ| must exceed the shuffled 95th percentile (the noise check for a positive).

## Pre-registered verdict rule (per condition)

- **ARMED** iff CI90 clear of zero in the PREDICTED direction + ≥2/3 legs sign-agree + both
  era halves agree + the shuffle control passes. (Armed = a gated skip/scale design may be
  pre-registered; nothing changes in any deployed layer.)
- **CLOSED-CONTRARIAN** iff CI90 clear of zero in the OPPOSITE direction (recorded as a
  real finding, but NOT armed — an unpredicted sign is a hypothesis for a fresh study, not
  a result to trade).
- **CLOSED-NULL** otherwise, with the mandatory MDE.

## Blind spots (declared)

1. The dataset's discipline warning applies in full: FU-9 has 330 state columns; this study
   reads exactly TWO engineered features and none of the stance columns — the stance-mining
   question belongs to FU-6's locked-holdout design, not here.
2. The four legs share CPI moments (semi-independent, as always).
3. Condition A's 12-hour window and B's 60-minute window are single choices, not searched.
4. Outcomes are qty=1 single-shot replay grade (the study grade of every geometry/state
   claim so far).
