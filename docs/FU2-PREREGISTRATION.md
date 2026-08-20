# FU-2 (#154) — the news-veto replay: pre-registration

**Filed 2026-08-20 BEFORE any run. FU-1 armed this study: the NQ book concentrates entries
into Tier-1 release windows (up to 8.4×) and gets stopped there 2.1–5.8× more densely, but
its in-window P&L CIs all include zero — an audit cannot answer the counterfactual. This
replay answers it with money: does BLOCKING new box entries inside the windows pay?**

## Fixed design

- **Scope**: NQ, the six champion frames (4h/2h/1h/15m/5m/2m) — FU-1 Phase-1 scope; other
  instruments are a declared Phase 2, not smuggled in.
- **The veto**: block NEW entries whose entry decision bar timestamp falls inside
  **[rel−5m, rel+15m]** of any Tier-1 calendar minute (FU-1's exact window and calendar —
  the veto removes exactly the entries FU-1 counted as in-window). Exits are UNTOUCHED:
  positions opened outside may ride through releases as they always did (close-before-release
  is a parking-lot idea, not this study).
- **Implementation**: the engine's own entry gate (`gate & ~in_window(d_dates)`) through the
  identical `fast_backtest` call FU-1 used — path dependence (1 entry/candle, flip,
  blocked-until) handled by the engine itself, NOT by filtering a trade log. Nothing in the
  engine changes; the veto is a replay-time mask, default OFF, golden numbers untouched.
- **Runs per TF**: ① baseline (must reproduce FU-1's book — a built-in parity gate: total
  P&L and trade count equal to the committed fu1 audit), ② the veto replay, ③ the
  **shifted-calendar control** (+3 days, clock times kept — the seasonality-only veto).
- **Metrics per TF and pooled**: Δtrades, ΔNet P&L (engine $ units, as FU-1), ΔmaxDD
  (peak-to-trough of the day-cumulative book). **Decision statistic**: the pooled daily
  P&L difference series (veto − base across all six TFs), day-block bootstrap (10,000
  resamples), 90% CI on the total Δ.

## Pre-registered verdict rule

- **ADOPT-CANDIDATE** iff pooled ΔNet > 0 with 90% CI > 0 **AND** pooled ΔmaxDD ≤ 0 **AND**
  the real-calendar Δ exceeds the shifted-calendar Δ (the effect must be release-specific,
  not time-of-day seasonality — FU-1's decomposition made this mandatory). Adoption itself
  would then be a SEPARATE ship gate (default-OFF overlay, golden discipline); FU-2 deploys
  nothing.
- **CLOSED-NEGATIVE** iff pooled ΔNet < 0 with 90% CI < 0 — the book's in-window trades PAY
  net (the 8.4× concentration is earning, not bleeding) and the veto idea dies.
- **CLOSED-NULL** otherwise — with the mandatory power analysis (sd of the daily diff,
  minimum detectable Δ) so the null is a measured null, not a shrug.

## Expectations recorded now (honesty anchors)

FU-1 saw in-window entry P&L worse in point estimate on 5/6 frames (1h: −$120/entry vs +$28
outside) with CIs including zero, and stop-outs 2.1–5.8× denser. The DD improvement is the
more likely win than the P&L improvement (removing sweep-dense entries should cut tail
pain). A large positive P&L surprise would CONTRADICT FU-1's point estimates and must be
treated with suspicion, not celebration.

## Blind spots (declared)

1. NQ-only (Phase 1); a veto that pays on NQ must re-confirm per instrument before any
   wider claim.
2. The veto counterfactual assumes the book's other entries are unchanged by our absence
   from the market (qty-1 assumption — fine at study size).
3. Engine $ units are gross of commissions (as the box book and FU-1 report); the veto
   REMOVES trades, so commissions only make any positive Δ better (conservative direction),
   while a negative Δ could be slightly less negative net of saved commissions — noted, not
   modeled.
4. Tier-1 calendar ≥2016 (the programme rule); the same-minute multi-release overlap is
   handled by the window union, as in FU-1.
