---
name: drawdown-exceeds-trigger-investigation
description: Investigation into why the WS-G winner's realized max drawdown ($3,670) is nearly double the breaker trigger ($2,000), and why "max drawdown" is shown as a positive number. Root cause — the breaker is a cooldown-and-probe, not an equity hard-stop, so consecutive post-unlock losses ratchet the drawdown against a frozen global high-water mark. Companion to notes/46 (breaker bug) + notes/47 (fix). NOT a bug — working as designed.
type: reference
---

# Investigation — why max drawdown ($3,670) ≫ breaker trigger ($2,000)

**Trigger for this investigation:** "How on earth do I get a [positive / this large] max drawdown?
The strategy is drawdown-*capped* with a $2,000 breaker, yet the dashboard reports **$3,670**."

**Verdict (one line):** Not a bug. The breaker is a *cooldown-and-probe* mechanism, not an equity
hard-stop — it can delay a bleed but **cannot cap drawdown at its trigger**, and three consecutive
post-unlock losing "probe" trades ratcheted the drawdown from $2,300 → $3,670 against a global
high-water mark that never recovered. The "$5,000 cap" line is a *reference only*; nothing enforces it.

---

## 1. Two questions, separated

**Q1 — "positive" max drawdown.** Not a defect. Max drawdown is reported as a **positive
magnitude** (the size of the worst peak-to-trough equity drop) on the metric card, while the
underwater chart plots the same quantity as **negative** (−$3,670). Both are standard convention;
the sign is presentational. The substantive question is Q2.

**Q2 — why $3,670 when the breaker trips at $2,000?** This is the real finding (below).

## 2. Evidence (live engine, winner params: SL 30/40 · TP 60 · gate 60th · breaker $2,000/20)
Recomputed directly from the run payload (`POST /api/backtest`), not eyeballed from the log:
- Summary: **P/L +$7,735 · max_dd $3,670 · 66 trades · 11 locks**.
- Max DD occurs at **trade #23, 2025-08-08**.
- The high-water mark that defines it is **$1,380, set 2025-02-24 (trade #10)** and never recovered
  for the remainder of 2025.

## 3. Root cause — the breaker overshoots, then ratchets

The drawdown is measured from the **global** high-water mark (the fix in notes/47 — correct). The
breaker fires *after* a trade exits and then pauses for 20 trades; on unlock it takes exactly **one
trade** ("probe"), entered while equity is still deep underwater. The worst stretch:

| # | date | result | P/L | equity | peak | **DD** | event |
|---|------|--------|----:|-------:|-----:|------:|-------|
| 20 | 2025-06-17 | WIN  | +1,200 | −120  | 1,380 | 1,500 | |
| 21 | 2025-06-18 | loss | −800   | −920  | 1,380 | **2,300** | 🔒 LOCK (halt 20) |
| —  | | *19 LOCKED skips (cooldown)* | | | | | |
| 22 | 2025-07-17 | loss | −620   | −1,540 | 1,380 | **2,920** | UNLOCK→probe→🔒 LOCK |
| —  | | *19 LOCKED skips* | | | | | |
| 23 | 2025-08-08 | loss | −750   | −2,290 | 1,380 | **3,670** | UNLOCK→probe→🔒 LOCK ← **MAX** |
| —  | | *19 LOCKED skips* | | | | | |
| 24 | 2025-09-08 | WIN  | +1,200 | −1,090 | 1,380 | 2,470 | UNLOCK→probe WINS, recovery begins |

**Mechanism, step by step:**
1. **Overshoot on the trip.** The breaker fires *after* the losing trade closes, so the trip already
   overshoots: at #21 the DD jumped 1,500 → **2,300** in one −$800 trade. It can never catch the
   threshold exactly at $2,000.
2. **One probe per unlock.** After 20 skipped candidates it unlocks and takes a single trade, still
   underwater, still measured against the frozen **$1,380** peak.
3. **Consecutive probe losses ratchet the DD.** #22 (−620) and #23 (−750) both lost → DD climbed
   2,300 → 2,920 → **3,670**. Nothing re-armed in between because no trades occurred during cooldown.
4. **Recovery only on a probe win.** #24 finally won (+1,200) and the drawdown began shrinking.

So, in closed form:
```
worst realized DD  ≈  trigger
                    + overshoot of the tripping loss
                    + Σ(consecutive post-unlock probe losses)
                 ≈  2,000 + (~300) + (620 + 750)  ≈  3,670
```

## 4. Why this is structural, not fixable by tuning
A **cooldown-resume** breaker bounds *how often* you trade in a slump, not *how far* equity can
fall. With ~$800 losses and an unlucky run of three probes, ~$3,670 is the natural result. It stayed
under the $5,000 reference line **by luck** — a 4th consecutive probe loss would have pushed it past
~$4,400. Lowering the trigger or lengthening the cooldown does not change the failure mode; it only
shifts where the probes land. (Consistent with notes/46: the breaker delays, it does not cap.)

## 5. What would actually cap drawdown (proposed, not yet built)
The breaker must become a real **equity hard-stop** instead of a trade counter:
- **Lock-until-recovery:** stay locked after a trip until equity climbs back above the peak (or
  peak − buffer), not after N trades. Caps DD at `trigger + one tripping-loss overshoot` (~$2,800
  worst case) — at the cost of sitting out long underwater stretches.
- **Resume-at-reduced-size:** after a trip, resume at smaller size so each probe risks less.
- **Distance-from-peak position scaling.**

A head-to-head backtest of the lock-until-recovery variant vs the current $7,735/$3,670 is a
contained change in the breaker *overlay* (the verified engine stays untouched) — see open follow-up.

## 6. One-paragraph summary (baby)
The safety brake is set to "stop trading once you're down $2,000," but the account still fell
**$3,670**. That is not a glitch and the brake is working exactly as built — it just isn't the kind
of brake that caps the loss. It pauses trading for 20 trades, then takes **one** test trade to see if
things improved; that test trade lost **three times in a row** (June, July, August), and because each
loss is measured against the best the account ever reached (a peak from February it never beat again),
the paper "drawdown" kept growing past the $2,000 line each time. Only in September did a test trade
finally win and the hole start to fill. (And "max drawdown $3,670" is shown as a positive number
because it's the *size* of the drop — that part is normal.) To genuinely cap the loss, the brake has
to stay on until the account recovers, instead of probing every 20 trades.

## 7. Cross-references
- `notes/46` — the original breaker bookkeeping bug (peak reset on unlock) and its fix.
- `notes/47` — edits report for the global-high-water-mark fix + re-tune ($2,000/20).
- `notes/48` — no-silent-fallback hardening of the standalone app.
- Standalone app the figures came from: `subprojects/wsg-strategy/` (`python3 server.py` → :8200).
