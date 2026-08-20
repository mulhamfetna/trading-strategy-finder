# FU-7 (#159) — power-scaled news-leg geometry: pre-registration

**Filed 2026-08-20 BEFORE any run. The second consumer of the proven power layer. The frozen
ride uses ONE bracket for every event (S 0.10% / TP 0.40%); the FU-14 layer predicts each
event's move size the night before (ρ≈0.5). Mechanism: if the expected move is 2× normal, a
bracket sized for a normal move stops too tight and caps too early — scale the bracket WITH
the predicted power at constant R:R. ⚠️ This studies a CHANGE to the confirmed spec: it
ships only via the full gate; FU-7 itself deploys nothing.**

## Fixed design

- **Legs and series** (the deployed book): NQ {CPI, NFP, FOMC} · RTY {CPI, NFP, FOMC} ·
  ES {CPI} · YM {CPI}; full era ≥2016 (RTY from its 2019 data floor), qty=1, stressed costs.
- **The scaler** (mechanism-first, ONE mapping, within-series): r(e) = pred_exp(e) /
  causal median of that SERIES × INSTRUMENT's prior pred_exp values, clipped to [0.5, 2.0];
  events without a scored prediction (<8 priors) ride the frozen bracket (r=1). Within-series
  by design: M2's V2 nuance (NFP out-predicts CPI on power while CPI pays) makes an
  across-series scaler a premium-misallocation trap — r captures each series' power REGIME,
  not the series league table.
- **The scaled arm**: S(e) = 0.10% × r(e), TP(e) = 0.40% × r(e) — constant 1:4 R:R; lead,
  exit +900s, tie⇒STOP, worse-of/better-of fills all unchanged.
- **Implementation**: the deployed `run_bracket` with STOP_PCT/TP_PCT patched per event and
  restored; the FROZEN arm runs with untouched constants and must reproduce the committed
  replay evidence TO THE CENT on every overlapping event (the leakage-proof and parity gate
  in one); 1s bars loaded once per leg, all arms in-process.
- **Falsifier**: 20 seeded within-series permutations of r among each series' scored events
  — if scaling by SHUFFLED power does as well, the geometry gain is bracket-width bias, not
  forecast information.
- **Decision statistic**: pooled (4 legs) net-stressed Δ (scaled − frozen); event-bootstrap
  (10,000) 90% CI; era halves (each leg's span median — the FU-3 lesson: halves defined on
  the DATA's actual span, never the calendar's).

## Pre-registered verdict rule

- **ADOPT-CANDIDATE** iff pooled Δnet > 0 with CI90 > 0 AND the placebo's median Δ ≤ half
  the real Δ AND both era halves ≥ 0. Even then: nothing ships — it arms the full spec-change
  gate (three-stage, per-leg re-verification, owner word).
- **CLOSED-NEGATIVE** iff CI90 < 0 — the frozen geometry stands and the idea dies.
- **CLOSED-NULL** otherwise, with the mandatory MDE.

## Expectations recorded now (honesty anchors)

M3's tail-driven shape (median loses, +4R pays) cuts both ways: a wider bracket on
high-power days holds through noise to the big move, but also doubles the stop cost when
the day chops. The Retail anti-premium is NOT in scope (no Retail leg is deployed). The
scaler touches only scored events (≈85% of ridden events); the rest anchor the frozen
baseline inside the scaled arm.

## Blind spots (declared)

1. r's clip bounds [0.5, 2.0] are a design choice, not searched — one mapping, no grid.
2. pred_exp is the expanding (regime-lagging) primary; a t24 variant exists and is NOT run
   here (declared follow-up, not smuggled in).
3. The four legs share CPI moments (semi-independent, as always declared).
4. Worked-entry interaction (VWAP over 300s) is not re-modeled — qty=1 single-shot replay,
   the study grade every prior geometry claim used.
