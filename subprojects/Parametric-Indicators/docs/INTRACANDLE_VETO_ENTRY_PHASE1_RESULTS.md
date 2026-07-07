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

## Force-close variant (normal entry closes an open rescued trade) — recovers part of the loss

| version (N=240) | trades | total P/L | vs champion |
|---|--:|--:|--:|
| plain (rescued trade blocks normal entries) | 384 | $87,363 | −$54,840 |
| force-close, first cut (buggy ordering) | 409 | $109,456 | −$32,747 |
| **force-close, corrected** (boundary preempts candle; full-gate normal entry) | **423** | **$143,657** | **+$1,454** |

**The corrected force-close is the headline:** ~**2× entries (214 → 423) at slightly ABOVE the champion's P/L**
($143,657 vs $142,203) — **on the fixed champion params, before any re-optimization.** The "stealing the seat"
problem was the whole story: giving the proven trades priority turns the feature from −$55k to +$1.5k. (43
force-closes. In-sample, single champion — DD and OOS still to check; re-optimization is expected to widen it.)

## Verdict — NOT a fair test yet; do NOT call it dead (correction, 2026-07-03)

The above bolts the feature onto the champion's **FIXED** settings — but the champion was optimized **without** this
feature, so this understates it. **The 57.5% breakeven is not fixed: it is a function of the exits** (win≈$2,400 @
120pt TP, loss≈$3,340 @ 167pt SL ⇒ 1/(1+0.72)≈57.5%). **Re-optimizing the exits changes the bar** — e.g. a bigger
target + tighter stop could drop breakeven toward ~40%, at which the already-observed **50–57% win rate becomes
profitable.** Two levers open under re-optimization: (1) **lower the bar** via re-tuned SL/TP; (2) **raise win% of
admitted trades** via searched N / force-close / K / which vetoed signals.

## OOS + drawdown check of the corrected force-close (fixed champion params)

| | champion (off) | force-close (on) |
|---|--:|--:|
| ALL: n / P/L / maxDD | 214 / $142,203 / $14,082 | 423 / $143,657 / **$24,902** |
| 2025 (IS): n / P/L / maxDD | 157 / $113,304 / $10,505 | 292 / $109,356 / $22,726 |
| **2026 (OOS): n / P/L / maxDD** | 57 / $28,899 / $14,082 | **131 / $34,301 / $18,511** |

**OOS verdict:** the feature **holds out-of-sample** — 2026 (unseen) shows **2.3× entries and +19% P/L**
($34,301 vs $28,899), the opposite of overfitting (IS 2025 was slightly *lower*). **But drawdown roughly doubles**
(P/L:DD ~10:1 → ~6:1), degrading the ratio L1 is valued for. **Re-optimization's job: keep the 2× entries + P/L
while controlling DD** (DD as an explicit objective). This justifies Phase 2.

**FAIR TEST (Phase 2) — re-optimize L1 with the feature ON, then validate out-of-sample.** Add the feature params
(`intracandle_veto_entry`, `intracandle_max_wait`, `intracandle_force_close`) to the optimizer search space, run a
fresh L1 optimization (server), and compare that new champion to the current $153,321/$142,203 champion. Target the
milestone: **~2× entries at breakeven-or-better**. Only if the *re-optimized* strategy still loses is the feature
dead. Guardrail: in-sample gains must survive **walk-forward / OOS** (the Kalman + l2v3 lesson).

## Status

Built, TDD-tested, golden 6/6 byte-identical (flag off), shipped behind a default-off dashboard toggle. Off the
production path in effect (default off). No optimizer wiring (Phase 2) unless the user opts to pursue the selective
thread.

*Caveat: single champion, in-sample (2025→2026 combined via the golden bundle). A walk-forward / OOS split would be
the honest next check even for the selective thread — the l2v3 / Kalman lesson.*
