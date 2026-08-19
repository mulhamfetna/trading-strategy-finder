# Achievement Summary — the project till this point (v5.4.3, 2026-08-19)

**High-level, plain language. The detailed trail: `PROGRESS-RECORD.md` (state) ·
`NEWS-MASTER-EXPERIMENT-RECORD.md` (eras 0–9) · `WS-FUSION-FULL-RECORD.md` (F-0..F-5) ·
the claims ledger (43/43 on both machines).**

## What the project HAS today (the assets)

1. **The box strategy** — 55 verified champions across 9 futures markets, ≈ $840k/yr at the
   deployed caps (2026 OOS), engine golden-locked. Its entry gate runs on the system's one
   deployed forecast: the HAR-RV volatility engine.
2. **The news layer (v5.4.2)** — four legs, one bet: the CPI announcement premium ridden on
   NQ + RTY (with NFP/FOMC in the confirmed pooled set) + ES + YM. $67,767 net stressed for
   2024→2026 at one contract per leg; scaled tiers approved by pre-registered rule
   (NQ/RTY/ES ≤20 worked entry, YM ≤5); ≈ $1.167M/window at max tiers (model-grade).
   Guarded by a sticky regime monitor; paper-only until a live gateway.
3. **The power-forecast layer (v5.4.3, new)** — every scheduled macro release's move SIZE,
   predicted the night before (Spearman ≈ 0.5–0.6 across five instruments). Information only.
4. **A verification culture that provably works** — pre-registration before every run,
   V1/V2/V3 + a machine-checked claims ledger, positive controls (one caught a live bug),
   golden gates, two-implementation parity on every shipped number.
5. **A follow-up system that cannot drop ideas** — the RQ/FU ledgers + intake rule, labels,
   milestones, the pinned progress record, the project board, releases with bundles.

## What the project KNOWS (laws bought with evidence, not opinions)

- **Size is forecastable; direction is not.** Proven independently three times (meta-prophet's
  11-model battery; 643 surprise pairs; the fundamentals era) — and the two size engines
  (tape HAR-RV, calendar M2) are both now deployed layers.
- **POWER ≠ PREMIUM.** Violence is everywhere in the calendar; payment exists in exactly one
  place — equity-index futures at the CPI print (NQ > ES > YM > RTY, by index beta).
- **Retail Sales is the calendar's one confirmed anti-premium** (gross-negative on 7 instruments).
- **The box book is drawn INTO news windows** (entries up to 8.4×, stop-outs 2–6×, half
  seasonality half release-specific) — the counterfactual money question is armed for FU-2.
- **Vol-gating doesn't help a vol-seeking book; vol-mapped sizing doesn't generalize either**
  (the Exp2 ramp reversed on the first independent book — killed by its own pre-registered rule).

## What was killed, and why that is an achievement

TimesFM gate · Chronos-2 gate · regime HMM · direction forecasting (twice) · 656 of 661 grid
cells · the Exp2 sizing ramp's deployment. Every kill is a pre-registered verdict with
committed evidence — the system's edge is partly THAT it cannot talk itself into maybes.

## The scoreboard (releases)

v5.2.0 box milestone → v5.3.0 news layer (NQ/RTY) → v5.4.0 ES CPI → v5.4.1 YM CPI (execution
gate) → v5.4.2 scaled tiers → **v5.4.3 power-forecast layer + the FU-13 honest kill**.

## What is next (the live queue, in order)

The **FU-11 fused size engine** (design saved: upgrade the live HAR-RV gate with the calendar
terms it cannot see) → FU-9 event-state dataset → FU-2 news-veto replay (armed) → FU-3/FU-7 →
FU-5/6 → then the WS-EARN return. Every item has an issue; nothing exists without a number.
