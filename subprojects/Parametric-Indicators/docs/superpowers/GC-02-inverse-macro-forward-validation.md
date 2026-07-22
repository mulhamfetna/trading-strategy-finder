# GC-02 — Forward-validation of gold's inverse macro reaction

**Date:** 2026-07-22
**Branch / Issue:** `fundamental-analysis` · GitHub Issue #4 (forward-validate GC's inverse-macro reaction)
**Builds on:** [GC-01](./GC-01-REPLICATION-verdict.md) (the discovery + sub-minute tradeability study)
**Verdict:** The inverse reaction **forward-validates as a real, sign-stable statistical phenomenon** (walk-forward, no-peek, t=+4.26, gold-specific) — but it is **NOT tradeable**: 100% of the edge is the release-instant jump you cannot enter in time to catch. The causal +5-minute trade earns **−$2/trade gross, dead at any cost**. This independently confirms and strengthens GC-01's "un-tradeable at cost" conclusion, now with real statistical power.

---

## 1. The question

GC-01 discovered that gold's move right after a scheduled US macro release is **inversely rank-correlated**
with the surprise (Spearman −0.193; negative 15 of 16 years; both halves). `gc_robust.py` validated that
**in-sample** — each year's own correlation. Issue #4 asks the harder question: does it survive a true
**out-of-sample, no-peek forward test** — and does it hold up as something you could actually have *traded*
year by year?

## 2. Method — walk-forward, no peeking

For each release in chronological order, we decide the trade **using only prior releases**: fit the sign of
the surprise→move relationship on the expanding history (Spearman on everything before this release), then
trade the current release in the direction that history implies and bank the realized move. This produces a
genuine out-of-sample track record with **766 trades over 2012–2026** — far more power than GC-01's
2025→2026 split (a handful of events). An **NQ control** runs identically and should stay null.

**The causality trap we hit and fixed (documented so it can't recur):** the first version measured the
+5-minute move from the bar *before* the print (the `paths_for` anchor, `close[t0−1]`). That **includes the
release-instant jump you cannot trade** — you only learn the surprise *at* the release. It gave a
spectacular, false +$131/trade "tradeable" result. GC-01 itself found ~60% of gold's move completes in the
first *second* and ~95% within 30 seconds — i.e. the edge is a sub-second repricing. So v2 uses a **causal
entry**: enter at the **close of the release-minute bar** (the number is public), hold to +5 minutes. We
report both, so the gap between them *is* the un-tradeable jump. (Lesson: measure at the resolution of the
decision — the same SOP that caught the "priced in a minute" resolution artifact.)

## 3. Result

**Gold (walk-forward OOS, 766 trades, sign fitted from the past only):**

| Move measured | mean | t-stat | $/trade | cumulative |
|---|---|---|---|---|
| **FULL** (from pre-print bar — look-ahead) | +1.068 pts | **+4.26** | +$106.80 | +$81,810 |
| **CAUSAL** (enter at release-bar close — tradeable) | **−0.023 pts** | **−0.17** | **−$2.28** | −$1,750 |

The fitted sign was **negative in 95% of trades** — the inverse relationship is real and stable out of
sample. But **the entire edge is the release-instant jump**: once you enter *after* the number is public,
there is nothing left. Net of cost it only gets worse:

| Round-trip cost | causal $/trade | t-stat | verdict |
|---|---|---|---|
| $4 (commission only) | −$6.28 | −0.47 | DEAD |
| $24 (1 tick/side) | −$26.28 | −1.96 | DEAD |
| $44 (2 tick/side) | −$46.28 | −3.44 | DEAD |
| $104 (5 tick/side) | −$106.28 | −7.91 | DEAD |

Per-year causal P&L scatters around zero (2021 −$7,670, 2023 +$4,210, most years ±$1k) — no tradeable edge
in any era.

**NQ control:** fitted sign negative in only 0.5% of trades (no stable relationship at all); causal move
−0.315 pts, t=−0.39 (null). The control behaves — the phenomenon is **gold-specific**, and the walk-forward
correctly finds nothing to trade on the Nasdaq.

## 4. Reading it

- **As science, it validates.** The inverse reaction is not a data-mined fluke or a single era: a no-peek
  forward rule, refit every release, keeps the same (negative) sign 95–100% of the time and shows a strongly
  significant look-ahead correlation (t=+4.26) across 15 unseen years, on gold only. GC-01's discovery is
  robust.
- **As a trade, it is dead.** All of it lives in the sub-second release jump. Entering one minute later (the
  causal test) captures ≈0; even GC-01's more aggressive *one-second* entry earned only ~$50/trade gross and
  died at realistic slippage. Two independent constructions (sub-minute scalp in GC-01; +5-minute hold here)
  now agree: **real, but un-tradeable at cost.**

## 5. What went well / what to watch

- **Went well:** the walk-forward gave the finding real out-of-sample power; the NQ control isolated it to
  gold; and the causal-vs-look-ahead split made the un-tradeability unambiguous — the gap between the two
  rows *is* the money you can't get.
- **Caught in flight:** v1's pre-print anchor was look-ahead and produced a false "tradeable" result.
  Flagging and fixing it before reporting is the point of the discipline, not an embarrassment.
- **Watch:** entry at the release-minute *close* is conservative (a fast desk enters within seconds); the
  honest bracket is "≈$50/trade gross at T+1s (GC-01) down to ≈$0 at T+60s (here), and cost kills both."
  Sub-second execution research would be the only path to revisit this, and GC-01 already showed the swing
  (±$434) swamps the edge there.

## 6. Status

**Issue #4 CLOSED.** Gold's inverse macro reaction is a **confirmed, forward-validated statistical fact but
not a tradeable edge.** No deployment. It remains useful as *context* (a known gold behaviour around macro
releases), not as a signal. Recorded alongside [GC-01](./GC-01-REPLICATION-verdict.md).
