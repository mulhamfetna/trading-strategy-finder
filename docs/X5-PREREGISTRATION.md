# X-5 (#172 ledger) — monitor × compound power: pre-registration

**Filed 2026-08-20 BEFORE any run. Order rationale (recorded): X-5 before X-4 — it consumes
X-3's freshly shipped composition on COMMITTED data only, while X-4 needs a dashboard
deployment window with the browser ship gate. X-5 is PROTECTIVE ANALYSIS: whatever it
finds, NO monitor trigger changes (any trigger change would need its own full gate — the
D2 monitor is a deployed protection layer).**

## The question

The news regime monitor stands the layer down when the rolling 24-CPI net-stressed mean
turns negative. Does that rolling health co-move with the COMPOUND power regime (macro
P_hist + adjacent top-12 earnings power — X-3's additive composition)? If yes: the
monitor's episodes have a knowable-in-advance context field (information). If no: the
monitor's risk is orthogonal to forecastable violence — also worth knowing.

## Fixed design

- **The monitor series** (its own definition, from frozen data): NQ CPI events ≥2016 from
  the frozen FU-9 dataset (`ride_net_stressed_usd`), rolling-24 mean (the D2 window),
  evaluated at each event with ≥24 priors.
- **The compound-power series** (X-3's law-#1 composition, historical): per CPI event, its
  own `pred_exp` + the MAX top-12 earnings `pred` within ±24h (0 added when none) — from
  the frozen FU-9 + E-P1 files.
- **Statistic**: Spearman(rolling health, compound power) over the evaluable events;
  event-bootstrap 90% CI (10,000); **noise check**: 200 within-year shuffles of the
  compound series (preserving its annual regime) — |ρ| must beat the shuffled 95th
  percentile for any INFORMATIVE verdict.
- **Era halves** (true-span median): sign consistency required for INFORMATIVE.

## Pre-registered verdict rule

- **INFORMATIVE** iff the CI90 excludes 0 AND |ρ| > shuffle-p95 AND both era halves share
  the sign. Consequence: a context field may be ADDED to the monitor's report output
  (information only, its own small parity gate) — the trigger never changes.
- **CLOSED-ORTHOGONAL** otherwise, with MDE — the monitor's risk is not forecastable
  violence; equally recorded, no follow-up.
- No directional prediction is registered (either sign could be mechanistic: high compound
  power → bigger wins for a vol-seeking ride, OR → sweep-chop losses) — so the CI is
  two-sided and the verdict is about EXISTENCE, not direction. Declared to avoid the FU-5
  post-hoc-flip trap in reverse.

## Blind spots (declared)

1. n ≈ 92 evaluable events (116 CPI − 24 warmup) — the MDE will be honest and wide.
2. Rolling means are autocorrelated — the event bootstrap understates CI width somewhat
   (declared; a block bootstrap variant is a follow-up if the verdict is INFORMATIVE).
3. The monitor's deployed implementation runs on the replay evidence (2024→); this study
   uses the same definition over the longer frozen history — a definition match, not a
   byte match (declared).
