# Experiment 1 — NQ concentration as a non-vol regime signal

**2026-07-18, server.** Full reporting structure. **Verdict: SUGGESTIVE, not established** (best non-vol
lead so far; fails the random-label control on the n=1 book).

## PRIOR_ART
Concentration (how much a few mega-caps drive the Nasdaq-100) is *orthogonal* to price volatility, and our
own finding (NQ ~1.3–1.5× ES vol from tech concentration) makes it the on-point non-vol signal. Data sourced
**free**: QQQ (cap-weight) and QQEW (equal-weight) daily from Yahoo Finance (stooq is now JS-anti-bot-walled;
we have no paid API). Proxy = **QQQ/QQEW ratio**; signal = its **causal 60-day z-score** (past-only).

## BASELINE — conditioned P/L (2024–26 fusion book, 518/539 trades labeled)
| concentration (0=broad → 2=mega-cap) | trades | P/L | Return/DD | win |
|---|--:|--:|--:|--:|
| all | 518 | $151,550 | 6.06 | — |
| 0 low / broad | 65 | $18,594 | **1.66** | 48% |
| 1 mid | 93 | $27,250 | 3.87 | 51% |
| 2 high / mega-cap | 360 | $105,706 | **4.29** | 53% |

A **monotonic gradient**: the strategy earns best in mega-cap-concentrated (trending) regimes, worst in broad
(choppier) ones. Per-year the high-conc regime dominates P/L (2024 $19.7k, 2025 $48.3k, 2026 $37.7k) — though
it also holds most trades.

## DUMB CONTROL — vs realized volatility
Realized-vol terciles show **no clean gradient** (4.23 / 2.52 / 2.99). So concentration carries **different,
cleaner** structure than volatility — it is not just vol in disguise. This is the key positive: it's genuinely
non-redundant information.

## ROBUSTNESS — random-label control (the honest test)
Shuffle the concentration labels across the same trades (2000×, sizes preserved) and compare the max−min
Return/DD spread across regimes: **real spread 2.63 vs null median 4.37 → real beats only 20% of shuffles.**
With unequal bucket sizes (65/93/360) and path-dependent drawdown, the observed gradient is **within noise** —
not statistically special on this single book. (n=1 again; and the spread metric is dominated by the small
low-conc bucket.)

## VERDICT: SUGGESTIVE — the best non-vol lead, but not yet an edge
- ✅ Concentration is **different information** from volatility (cleaner monotonic gradient than vol) — the one
  direction here that isn't already-dead.
- ❌ It does **not** clear the random-label control on the 2024–26 book → not a validated edge.
- **If pursued:** (a) a cleaner test — bootstrap the high-vs-low-conc Return/DD *difference* directly (the
  spread metric is too noisy with unequal buckets); (b) a longer book (needs 2010–23 box levels); (c) try
  concentration *level/slope* variants and a broader breadth measure (finviz #106, parked on no-API).

Data/scripts: `conc_experiment.py`; QQQ/QQEW via Yahoo (`~/Mulham/regime-edge/{QQQ,QQEW}.json`).
