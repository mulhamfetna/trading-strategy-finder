# Regime-edge program — experiments log

**Branch `research-regime-edge` (off dev). Opened 2026-07-18.** The 3 post-vol-model directions, cycled
one-by-one via the reporting system. Context: vol-gating is dead (3 methods); these are the directions with a
real mechanism. See [PLAN.md](../PLAN.md).

| # | Experiment | Result | Doc |
|---|-----------|--------|-----|
| 1 | **NQ concentration** (non-vol signal, QQQ/QQEW) | **Suggestive, not established** — clean monotonic gradient (earns best in mega-cap regimes), genuinely *different* from vol, but fails the random-label control on the n=1 book. Best non-vol lead. | [EXP1_CONCENTRATION.md](EXP1_CONCENTRATION.md) |
| 2 | **Sizing not veto** | **PROMISING (first positive)** — regime ramp (upsize turbulent) 5.52→5.90, beats 95% of random, helps all 3 yrs; classic inverse-vol sizing HURTS (4.06). Tempered: borderline/n=1/DD rises. | [EXP2_SIZING.md](EXP2_SIZING.md) |
| 3 | **Gate a vol-hurt layer** | **INCONCLUSIVE** — naive NQ mean-reversion is a persistent LOSER (−0.90), no edge to protect; proper test needs the real L2 book. | [EXP3_VOLHURT.md](EXP3_VOLHURT.md) |

## Follow-ups (user-requested, 2026-07-18)
| # | Follow-up | Result | Doc |
|---|-----------|--------|-----|
| 1 | **Promote sizing** | ✅ **GREEN** — equal-risk **+$10,356 (+6.8%)** at identical max-DD; scale-robust; OOS-2026 holds; beats **96%** of random. Deployable spec written. | [EXP2b_SIZING_PROMOTED.md](EXP2b_SIZING_PROMOTED.md) |
| 2 | **Concentration cleaner test** | ❌ **NO-GO** — high-vs-low per-trade gap $8 (p=0.97); the Exp1 gradient was a Return/DD artifact; sizing by it hurts. | [EXP1b_CONCENTRATION_CLEAN.md](EXP1b_CONCENTRATION_CLEAN.md) |
| 3 | **Real L2 book** | Both layers **vol-seeking** (veto hurts both; Exp3 untestable — no vol-hurt book). Size-ramp helps **L2** independently, but **hurts L1-standalone** → sizing win is **not uniform per-layer** (caveat on #1). | [EXP3b_L2_BOOK.md](EXP3b_L2_BOOK.md) |

## Program verdict (all 3 cycled)
- **#2 Sizing is the winner** — the only direction that beats its control (95%, all 3 years). Actionable form
  of the core discovery: for a vol-seeking strategy, size **WITH** vol (not veto, not inverse-vol). **Pursue.**
- **#1 Concentration** — suggestive, different info from vol, but fails its control on n=1. Second priority.
- **#3 vol-hurt** — untestable on a toy mean-rev (NQ punishes fading); needs the real L2 book. Deferred.

## Discoveries banked
1. **Size WITH volatility for a vol-seeking strategy** — classic inverse-vol targeting HURTS; regime-scaled
   up-in-vol sizing helps (Exp2). The actionable takeaway of the whole research arc.
2. **Concentration is non-redundant with volatility** (cleaner gradient than realized-vol) — worth a cleaner
   test (bootstrap high-vs-low) + a longer book (Exp1).
3. **NQ punishes mean-reversion / rewards momentum** — a naive fade loses persistently (Exp3), consistent with
   the vol-seeking breakout edge.
4. Free ETF history via **Yahoo Finance** (stooq is JS-anti-bot-walled) — unblocks ETF-derived signals sans API.
