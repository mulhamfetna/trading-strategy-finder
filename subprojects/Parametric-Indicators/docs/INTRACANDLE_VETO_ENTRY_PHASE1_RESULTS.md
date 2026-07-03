# Intra-Candle Vetoed Entry — Phase 1 results (champion study)

**Date:** 2026-07-03 · **Anchor:** NQ 4h champion (214 trades, $142,203, DD ~$9,589). Reproduce:
`python3 -m research.intracandle.run_sweep`. Feature: arm a vetoed (vol-passed) box signal, enter mid-candle at
the first 1-min bar where the full gate (`¬veto ∧ ≥K confirms`) re-opens, while flat for the candle.

## Result — the feature adds many entries, but BELOW breakeven → it costs P/L

| N (max-wait bars) | total trades | net + | new (rescued) | win% of new | ≥57.5% breakeven? | median hold | total P/L | ΔP/L vs champ | max DD |
|--:|--:|--:|--:|--:|:--:|--:|--:|--:|--:|
| **30** | 322 | +108 | 129 | 50.4% | ❌ | 388m | $73,198 | **−$69,005** | $34,553 |
| **60** | 348 | +134 | 160 | 54.4% | ❌ | 402m | $85,398 | **−$56,805** | $27,109 |
| **120** | 369 | +155 | 191 | 54.4% | ❌ | 386m | $62,119 | **−$80,084** | $31,389 |
| **240** | 384 | +170 | 214 | 57.0% | ❌ | 386m | $87,363 | **−$54,840** | $34,434 |

## Reading

- **Entries: goal met, mechanically.** The feature roughly **doubles** entry count (214 → up to 384; +170 at
  N=240) — it clearly rescues the dropped flow.
- **Quality: below the bar.** The rescued entries win only **50–57%**, **all below the 57.5% breakeven** implied by
  the pinned 0.74 payoff. Longer waits help slightly (50.4% → 57.0% as N 30 → 240) but never clear it.
- **P/L: worse, materially.** Total P/L falls **$55k–$80k** and **max drawdown ~3×** ($9.6k → $27–34k). Two causes:
  (1) the new entries are sub-breakeven, and (2) not purely additive — a rescued mid-candle trade occupies the one
  position and **displaces profitable champion trades** downstream.
- **Hold time: not shorter.** Median hold stays ~**6.4h** (~386–402m) — this does **not** move toward
  zero-day-hold; it just adds more multi-hour trades.

## Verdict — NO-GO on the naive "admit-all" version (pre-registered gate not cleared)

Per the design gate (D9: proceed to the optimizer only if added entries clear breakeven at held-or-better payoff),
**this does not clear it.** The veto was doing real work: the signals it drops are genuinely lower-quality, and
re-admitting *all* of them — even gated on the veto re-clearing intra-candle — trades below breakeven. This
matches the pre-registered prior-art evidence (pullback/delayed entry catastrophic on MNQ; delay can destroy edge).

**The one open thread (user's call):** this test admits **all** vol-passed vetoed signals whose gate re-opens. The
win% *rises* with N and reaches **57.0% at N=240 — a hair under breakeven** — so a **selective** admission (let the
optimizer choose *which* vetoed signals / regimes / a higher confirm-K intra-candle, not all) *might* isolate a
profitable subset. That would be a Phase-2 optimizer question, explicitly NOT auto-triggered by this result.

## Status

Built, TDD-tested, golden 6/6 byte-identical (flag off), shipped behind a default-off dashboard toggle. Off the
production path in effect (default off). No optimizer wiring (Phase 2) unless the user opts to pursue the selective
thread.

*Caveat: single champion, in-sample (2025→2026 combined via the golden bundle). A walk-forward / OOS split would be
the honest next check even for the selective thread — the l2v3 / Kalman lesson.*
