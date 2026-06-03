---
name: breaker-fix-edits-report
description: Change report (where/when/why/how) for the drawdown-breaker fix — the one-line global-high-water-mark correction, the re-tuned default ($2,000/20), regenerated dashboards, and doc supersessions. Commit 751bb8d. Companion to the investigation notes/46.
type: reference
---

# Edits Report — drawdown-breaker fix (commit `751bb8d`)

The *why* and full analysis live in `notes/46`. This document is the **change log**: exactly
**when**, **where**, **why**, and **how** each edit was made.

---

## WHEN
- **Commit:** `751bb8d` — "fix(wsg-strategy): drawdown breaker now caps drawdown (global high-water mark)"
- **Date:** 2026-06-03 16:51 (+03:00) · **Author:** Mulham Fetna · **Pushed:** `origin/dev`
- **Scope:** 16 files, +156 / −27 lines.
- Preceded by a systematic-debugging investigation this session (root cause → fix → re-tune → verify).

## WHY (one sentence)
The drawdown circuit-breaker **reset its high-water mark on every unlock**, so in a sustained
decline the *true* drawdown ratcheted to **$4,845** while the breaker's own reading stayed at
**$1,600** and never re-fired — i.e. it did **not** cap drawdown, and the old +$24,720 / $4,845
headline was inflated by that measurement bug. (Full evidence: `notes/46`.)

## HOW (the change, by category)

### 1. The core code fix — measure from the GLOBAL high-water mark
One line, repeated in all four breaker implementations:
```diff
-                locked = False; peak = eq      # reset the peak on resume   (THE BUG)
+                locked = False                 # FIX: keep the GLOBAL high-water mark (no reset)
```
With the peak no longer reset, the breaker's drawdown reading equals the true drawdown, so it
fires at the real threshold. The stale UNLOCK log text ("peak reset to $…") was changed to
"global peak $… kept".

### 2. Re-tuned default (the kill-switch loses money; the profitable+capped surface is overfit)
Breaker default changed **$2,500 / 30 → $2,000 / 20** (best feasible under the corrected
measurement: +$7,735 P/L, true maxDD $3,670). Updated in `config.WINNER`, both `DEFAULTS`,
`scripts/49` constants, and the three dashboards' "reset" buttons.

### 3. Regenerated artifacts
All three dashboards' `data.js` re-exported with the fixed breaker + new default (verified the
standalone and the meta-prophet exporter agree exactly: +$7,735 / $3,670 / 66 trades).

### 4. Documentation
New investigation `notes/46`; SUPERSEDED banners on `notes/44` + `45`; corrected pin (`notes/35`),
memory, and standalone `STRATEGY.md`.

## WHERE (every file)
| File | What changed | ± |
|---|---|---|
| `wsg-strategy/strategy.py` | core fix (no peak reset) + UNLOCK text | 4 |
| `meta-prophet/dashboard_winner/winner_backtest.py` | core fix + DEFAULTS $2,000/20 | 6 |
| `meta-prophet/winner_dashboard/winner_backtest.py` | core fix + DEFAULTS $2,000/20 | 6 |
| `meta-prophet/scripts/49_winning_dashboard_export.py` | core fix + constants $2,000/20 | 6 |
| `wsg-strategy/config.py` | `WINNER` dd_limit 2500→2000, cooldown 30→20 | 5 |
| `wsg-strategy/frontend/index.html` | reset-button default 2500/30→2000/20 | 2 |
| `meta-prophet/dashboard_winner/index.html` | reset-button default | 2 |
| `meta-prophet/winner_dashboard/index.html` | reset-button default | 2 |
| `wsg-strategy/frontend/data.js` | regenerated (corrected run) | 2 |
| `meta-prophet/dashboard_winner/data.js` | regenerated | 2 |
| `meta-prophet/winner_dashboard/data.js` | regenerated | 2 |
| `meta-prophet/notes/46_breaker_bug_investigation.md` | **new** — the investigation | +100 |
| `meta-prophet/notes/44_winning_system_full_report.md` | SUPERSEDED banner | 11 |
| `meta-prophet/notes/45_winning_strategy_playbook.md` | CORRECTED banner | 9 |
| `meta-prophet/notes/35_action_plan_master.md` | pinned winner corrected | 15 |
| `wsg-strategy/docs/STRATEGY.md` | corrected-results banner | 9 |

**Not touched (deliberately):** the verified production engine (`src/strategy/simple_strategy.py`),
the parity-tested clone's entry/exit logic, the main dashboard/backend. Only the breaker *overlay*
(in the strategy/payload layer) and parameters changed — the engine itself was already correct.

## VERIFICATION (after the edits)
- Standalone (`strategy.build_payload`, self-computed vol) and the meta-prophet exporter
  (`scripts/49`) both return **+$7,735 / true maxDD $3,670 / 66 trades / win 43.9% / 2025 +2,565 /
  2026 +5,170 / 11 locks** — identical, so the fix is consistent across both code paths.
- Re-validated unchanged: $800 loss cap, +$1,200 TP wins, one-position-at-a-time, gate applied.

## RESULT
| | before (buggy) | after (fixed) |
|---|---:|---:|
| P/L | $24,720 | **$7,735** |
| true max drawdown | $4,845 (under-measured) | **$3,670** (genuinely < $5k) |
| breaker actually caps DD? | **no** | **yes (now correctly measured)** |

> Caveat carried forward: the corrected profitable+capped tuning is **overfit (n=1)** — out-of-
> sample validation (Workstream F) is the prerequisite before trusting any figure.

## One-paragraph summary (baby)
On 2026-06-03 (commit `751bb8d`) we fixed one line in four files: the safety "circuit-breaker" used
to forget the account's previous high every time it resumed, so it under-counted the real losing
streak and never stopped trading in time — letting the true drawdown reach $4,845 while it thought
it was only $1,600. Now it always measures from the all-time high, so it genuinely limits the
drawdown. We re-tuned its trigger to $2,000 (the old $2,500 setting was part of the illusion),
regenerated the dashboards, and marked the old reports as superseded. Honest new result: **+$7,735
with a real $3,670 max drawdown** instead of the illusory +$24,720. The trading engine itself was
never wrong — only the breaker's bookkeeping was.
