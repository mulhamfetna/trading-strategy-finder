# Regime-edge program — experiments log

**Branch `research-regime-edge` (off dev). Opened 2026-07-18.** The 3 post-vol-model directions, cycled
one-by-one via the reporting system. Context: vol-gating is dead (3 methods); these are the directions with a
real mechanism. See [PLAN.md](../PLAN.md).

| # | Experiment | Result | Doc |
|---|-----------|--------|-----|
| 1 | **NQ concentration** (non-vol signal, QQQ/QQEW) | **Suggestive, not established** — clean monotonic gradient (earns best in mega-cap regimes), genuinely *different* from vol, but fails the random-label control on the n=1 book. Best non-vol lead. | [EXP1_CONCENTRATION.md](EXP1_CONCENTRATION.md) |
| 2 | **Sizing not veto** | **PROMISING (first positive)** — regime ramp (upsize turbulent) 5.52→5.90, beats 95% of random, helps all 3 yrs; classic inverse-vol sizing HURTS (4.06). Tempered: borderline/n=1/DD rises. | [EXP2_SIZING.md](EXP2_SIZING.md) |
| 3 | **Gate a vol-hurt layer** | _in progress_ | EXP3 (tbd) |

## Discoveries banked
1. **Concentration is non-redundant with volatility** (cleaner gradient than realized-vol) — the one signal
   here that isn't already-dead; worth a cleaner test (bootstrap high-vs-low difference) + a longer book.
2. Free ETF history is sourceable via **Yahoo Finance** (stooq is JS-anti-bot-walled now) — unblocks the
   no-API data constraint for ETF-derived signals.
