# Second-round confirmation of the sizing winner — QUALIFIED (not a clean green)

**2026-07-18, server.** Before deploying, ran stronger tests than the per-year splits. **Result: the signal
is real but the magnitude is NOT statistically confirmed on the n=1 book. Downgrade "GREEN" → "QUALIFIED".**

## What was tested
The a-priori regime size-ramp (0.5→1.5 by vol-rank), fixed — nothing tuned on the test data.

## 1. Block-bootstrap of the EQUAL-RISK dollar uplift (3000×, 20-trade blocks)
| | value |
|---|--:|
| point uplift (at max-DD = flat $27,508) | +$10,356 |
| bootstrap median | +$11,699 |
| **90% CI** | **[−$21,075, +$60,937]** ← includes 0 |
| P(uplift > 0) | **70%** |

The dollar uplift is **not significant** — the confidence interval includes zero. With ~539 trades over one
year, the sampling noise is larger than the effect.

## 2. Purged 5-fold cross-validation (time-contiguous, a-priori ramp)
| fold | period | flat → ramp |
|---|---|---|
| 1 | 2024-01 … 06 | 0.24 → 0.26 (+0.02) |
| 2 | 2024-06 … 11 | 0.26 → 0.35 (+0.09) |
| 3 | 2024-11 … 2025-05 | 1.29 → 1.74 (+0.44) |
| 4 | 2025-05 … 10 | 5.28 → 6.67 (+1.39) |
| 5 | 2025-10 … 2026-05 | 9.95 → 9.89 (−0.05) |

Helps in **4/5** held-out folds — consistently *directional*, but the magnitude swings widely.

## Honest synthesis (reconciling with Exp2b)
- **The regime-sizing SIGNAL is real** — the *ordering* matters (beats 96% of random regime→size maps), it
  helps 4/5 purged folds and all 3 calendar years, and the mechanism is sound (size WITH vol on a vol-seeking
  strategy; inverse-vol *hurts*).
- **The MAGNITUDE is not confirmed** — the equal-risk +$10.4k has a bootstrap CI spanning −$21k to +$61k. On
  one year of trades we cannot claim a reliable dollar figure.
- The Exp2b metrics (random control, OOS-2026, scale-robustness) test whether the regime *carries information*
  (yes); this bootstrap tests whether the *dollar benefit is reliably positive* (not at n=1). Both are correct;
  together they say **"a genuine but modest, not-yet-significant effect."**

## Consequence for deployment
**Do NOT ship it as "the confirmed latest winner"** or change deployed defaults on this evidence. Reasonable to
deploy **behind a flag as an EXPERIMENTAL candidate** (direction is sound, mechanism validated, doesn't degrade
the book) — but the headline claim must be "candidate," not "proven +$10.4k." A **longer / bear-inclusive book
(2010–23 box levels)** is what would move it from qualified to confirmed.

Script: `second_test.py`.
