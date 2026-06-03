---
name: breaker-bug-investigation
description: Deep investigation — the WS-G drawdown circuit-breaker did NOT cap drawdown (it reset its high-water mark on unlock, so true drawdown ratcheted to $4,845 while the breaker read $1,600). Root cause, the global-HWM fix, the re-tune (kill-switch loses; best feasible 2000/20 → +$7,735/$3,670 but overfit), and the corrected/superseded headline. Engine logic + parameter integration validated CORRECT.
type: explainer
---

# Investigation — the drawdown breaker didn't cap drawdown

> **Trigger:** "the backtest results don't meet the playbook expectations." Systematic-debugging
> investigation (root cause before fixes). **Verdict:** the entry/exit engine and parameter
> wiring are correct; the **drawdown circuit-breaker had a real bug** — it did not actually cap
> drawdown. Fixed (global high-water mark) and re-tuned. The corrected, honest result is **far
> weaker than the previously-reported $24,720**, and the headline is **superseded** (see §6).

---

## 1. What was validated CORRECT (so we know where the bug is NOT)
- **Parameters are integrated faithfully.** The engine runs with exactly `SL 30/40 · TP 60 ·
  gate 60 · breaker`; each trade's lines are exact (`long in=21322.2 → SLsoft 21292.2 (−30) /
  SLhard 21282.2 (−40) / TP 21382.2 (+60)`).
- **Engine logic obeys the playbook:** one position at a time ✓; loss capped at hard SL (worst
  trade exactly **−$800**, none beyond) ✓; every win exactly **+$1,200** (hard TP) ✓; the vol gate
  is applied ✓ (the one apparent gate "violation" was a *display-rounding* artifact — true
  threshold ≥92.3 shown as 92).

## 2. The bug (root cause)
The breaker is supposed to keep max drawdown small. It tracked drawdown from a high-water mark
that it **reset to the current (lower) equity every time it unlocked**. Consequence: in a
sustained losing stretch punctuated by lock/unlock cycles, the **true (global) drawdown ratchets
down** while the breaker's own reading stays small and never re-fires.

**Smoking gun (worst point, 2025-06-04):** true drawdown = **$4,845**, but the breaker's internal
reading at that instant was only **$1,600** — far below the $2,500 trigger, so by its own (broken)
logic it correctly did nothing. The trigger line is $2,500; equity sank **$4,845** below its peak.

**Why the old report looked fine:** the metric reported `maxDD = $4,845` (the true global value),
but the *explanation* — "the breaker caps drawdown near trigger + one loss / guarantees < $5k" —
was false and contradicted the documented peak-reset. **$4,845 < $5k was luck on this one
regime, not an enforced property.**

## 3. The fix
Measure drawdown from the **global high-water mark** (never reset it on unlock). One-line change in
every breaker implementation (`strategy.py`, both `winner_backtest.py`, `scripts/49`):
```diff
- locked = False; peak = eq      # reset peak on resume  (the bug)
+ locked = False                 # keep the GLOBAL high-water mark
```
Now the breaker's reading == the true drawdown, so it fires at the real threshold and the
dashboards' drawdown panel no longer "lies."

## 4. The re-tune (after the fix) — and an uncomfortable truth
With drawdown measured correctly, the candidate stream is fixed (gate+SL/TP, no breaker:
+$29,405 raw, but huge uncapped DD). We swept breaker settings measuring the **true** maxDD:

- **Kill-switch (hard cap, no resume): every variant LOSES money** (−$2.2k … −$4.3k). The worst
  drawdown is mid-2025; halting there forgoes the rest, so a *guaranteed* cap kills the edge.
- **Global-HWM + cooldown resume:** the best feasible (true maxDD < $5k, P/L > 0) is
  **trigger $2,000 / cooldown 20 → +$7,735 P/L, maxDD $3,670, both years +** (the new default).
- **But the feasible surface is CHAOTIC / overfit:** at trigger 2000, cooldown 10 → +$14,900,
  cooldown 12 → −$5,605, cooldown 5/8 → −$5,800. Tiny parameter changes swing P/L by $15–20k.
  **There is no robust island** — every profitable+capped cell is an n=1 spike.

**Honest conclusion:** the strategy's "capped drawdown" headline does **not** survive correction.
Either you truly cap drawdown (kill-switch) and it's unprofitable here, or you keep trading and
the cap is only met at overfit parameter points. The mechanism is sound in spirit (gate + tight
stops + halt-on-bleed), but its profitability-with-a-real-cap is **not demonstrated** on one regime.

## 5. Corrected numbers (default = SL30/40, TP60, gate60, breaker $2,000/20, global HWM)
| | OLD (buggy reset-peak) | CORRECTED |
|---|---:|---:|
| Total P/L | $24,720 | **$7,735** |
| true max drawdown | $4,845 (under-measured by the bug) | **$3,670** (genuinely < $5k) |
| 2025 / 2026 | +15,995 / +8,725 | +2,565 / +5,170 |
| trades / win% / locks | 120 / 48.3% / 5 | 66 / 43.9% / 11 |
| For reference: documented params 2500/30, corrected | — | +$1,540 / $3,340 |

## 6. Status & what is superseded
- **`notes/44` (full report) and `notes/45` (playbook): their headline (+$24,720 / $4,845, "breaker
  caps drawdown") is SUPERSEDED by this note.** Corrected headline: **+$7,735 / true maxDD $3,670,
  and the breaker now genuinely measures/limits drawdown — but the profitable+capped tuning is
  overfit (n=1).** Banners added to 44/45 pointing here.
- Tag `v4.2-wsg-drawdown-capped-winner` was cut from the buggy version; a corrected tag should be
  cut once a config is settled.
- **Recommended next:** (a) out-of-sample validation (Workstream F — instruments) is now even more
  essential, since the in-sample tuning is demonstrably fragile; (b) consider a fundamentally more
  robust risk rule (e.g., volatility-scaled sizing, or a kill-switch accepted as a risk control
  rather than a profit engine); (c) treat the dashboards as exploration tools, not as evidence of
  a validated edge.

## 7. One-paragraph summary (baby)
The strategy's safety feature — a "circuit-breaker" that's supposed to stop trading after a $2,500
loss streak so the account never drops more than ~$5,000 — was **measuring the loss streak wrong**:
every time it resumed, it forgot the previous high point, so the real drawdown quietly grew to
$4,845 while the breaker thought it was only $1,600 and never reacted. We fixed it to always
measure from the all-time high. Once it measures correctly, the old headline collapses: truly
capping the drawdown either loses money (if you hard-stop) or only makes money at fragile,
cherry-picked settings. The corrected, honest result for a sensible setting is **+$7,735 with a
real $3,670 max drawdown** (down from the illusory +$24,720). The engine and the parameters were
fine — only the breaker's bookkeeping (and the claims about it) were wrong. The real lesson:
this needs testing on other data before anyone trusts it.
