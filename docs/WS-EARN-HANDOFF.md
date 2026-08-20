# WS-EARN return — hand-off notes from WS-FUSION (2026-08-20)

**The owner's roadmap ③: after WS-FUSION, return to earnings — "earnings alone → earnings ×
indicators → earnings × news × indicators; same high-volatility nature, something hiding
between the lines." These notes are what the return inherits, so it starts warm.**

## What WS-EARN already established (#109–#113, do not re-derive)

- H1 (an earnings ride premium on index futures) REJECTED 0/8 over 783 events, 16 years,
  1-second bars. Earnings move NQ 4.98× — volatility ≠ direction (the POWER ≠ PREMIUM law,
  earnings edition, found before the law was named).
- ⚠️⚠️ NEVER use EDGAR submissions-JSON timestamps (mixed UTC/Eastern) — use the
  `-index-headers.html` ACCEPTANCE-DATETIME. ⚠️⚠️ Acceptance ≠ announcement (INTC lags
  ~7 min). C4 human check was left PENDING (#110).

## What the fusion era hands over (use, don't rebuild)

1. **The FU-9 schema, verbatim on earnings timestamps** — one row per (event × instrument):
   identity + power context + the frozen-bracket outcome + the 165-stance vector at the
   last closed 1m bar before entry + integrity gates C1–C4 (`fu9_build.py` is the template;
   the C2 repaint falsifier is already proven library-wide).
2. **The bracket primitive**: `release_executor.run_bracket` handles long AND short with
   worse-of/better-of fills and tie⇒STOP (FU-8 exercised the short path; parity-anchored).
3. **The power-model methodology for earnings**: P_hist per TICKER (expanding median of the
   same ticker's prior earnings |move|, shifted, ≥8 priors) — M2's `build_predictions` is
   generic over any grouping key. The night-before size question is the FIRST study: if
   earnings size is forecastable like macro size (ρ≈0.5), the fused-forecast result (FU-11)
   predicts the vol engine is equally blind to earnings dates — measurable immediately.
4. **The claims-ledger pattern**: every study = pre-registration with fixed verdict rule →
   server run → V1/V2/V3 claim → both machines green — the fusion era ran 14 studies in 2
   days this way; the machinery is warm.

## The priors the fusion era proved (bind them a priori)

- The calendar pays; the tape does not predict it — condition earnings studies on EVENT
  identity/power regime, not pre-release tape state (FU-5/6 nulls).
- Instrument/ticker asymmetry is first-class: a single-name result is that name's fact.
- A positive CI needs its placebo; a near-miss is a miss; an anti-premium is not a
  harvestable drift until the mirror trade is actually run (FU-8's both-ways lesson —
  earnings chop may eat both bracket directions exactly like Retail).
- Consumed history confirms nothing: 783 events are read — new claims need either untouched
  slices (other instruments/tickers) or forward elements, declared per study.

## The queue skeleton (to be pre-registered when the owner opens the workstream)

1. **E-P1 — earnings power model**: P_hist per ticker vs realized |move| (the M2 gates:
   primary Spearman + quintiles + shuffle + control minutes).
2. **E-S1 — the event-state dataset for earnings** (FU-9 schema) — built ONCE, gates C1–C4.
3. **E-X1 — earnings × the fused forecast**: does the live vol engine mis-forecast earnings
   bars the way it mis-forecasts CPI bars (FU-11's method, earnings dummy)?
4. Then and only then: conditioning/geometry studies, each with the fusion-era rules bound.
