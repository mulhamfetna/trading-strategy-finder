---
name: phase-G-combination-tournament
description: Workstream G — combination tournament crossing {normal, static-flip, CUSUM-dynamic-flip} × {no lever, S=HAR SL/TP, G=vol gate, S+G} on the verified single-contract clone. Validates plumbing vs EXP-G baseline. Key findings - the vol GATE is the robust risk-reducer; CUSUM dynamic-flip tops P/L (+$54.9k) but CORRECTS notes/32 (the flip-symmetry assumption is false; max per-trade deviation 368 pts). n=1 caveat stands.
type: explainer
---

# Workstream G — combination tournament (+ a correction to notes/32)

> Crosses two independent decision axes on the **verified single-contract clone**
> (`engine_clone/`, never the main engine, never the 1-1-2 ladder): **entry mode** ×
> **volatility lever**. Feeds the Workstream-A HAR-RV forecast (SL/TP sizing + gate) and the
> notes/32 CUSUM flip detector. Script: `scripts/44_wsg_combination_tournament.py`.

---

## 1. The 12-combo leaderboard (single contract, 2025+2026, $)

| combo | total P/L | 2025 | 2026 | vs base | n | win% | maxDD |
|---|---:|---:|---:|---:|---:|---:|---:|
| **cusum_flip + none** | **+54,910** | +41,740 | +13,170 | +509% | 772 | 67 | 25,500 |
| cusum_flip + G | +30,130 | +22,780 | +7,350 | +325% | 464 | 67 | **15,610** |
| normal + S+G | +21,396 | +31,223 | −9,826 | +259% | 482 | 67 | 27,360 |
| cusum_flip + S+G | +19,976 | +31,223 | −11,247 | +249% | 482 | 67 | 30,908 |
| normal + G | +3,685 | +22,780 | −19,095 | +127% | 464 | 65 | 26,650 |
| normal + S | −10,778 | +53,740 | −64,518 | +20% | 754 | 65 | 68,649 |
| **normal + none (BASELINE)** | **−13,420** | +41,740 | −55,160 | 0% | 772 | 64 | 57,160 |
| flipped + G | −40,000 | −51,000 | +11,000 | −198% | 443 | 64 | 58,000 |
| flipped + none | −75,000 | −88,000 | +13,000 | −459% | 750 | 63 | 101,000 |
| flipped + S/S+G | −57k … −85k | (loses) | | | | | |

**Plumbing validated:** `normal+none` = −$13,420 (2025 +41,740 / 2026 −55,160), and
`normal+G`/`+S`/`+S+G` reproduce EXP-G's `outputs/backtest_matrix.csv` exactly. So the new
rows (flip × lever) are trustworthy mechanics.

---

## 2. Two headline findings

### (a) The volatility GATE is the robust, defensible edge
Skipping the top-20%-volatility bars (the HAR-RV gate `G`) is what consistently helps:
- It cuts the **2026 bleed** (normal 2026: −55,160 → −19,095) and roughly **halves drawdown**
  (57,160 → 26,650; and cusum+G hits the lowest DD of all, **15,610**).
- It turns the strategy positive (`normal+G` +3,685; `normal+S+G` +21,396) **without any flip**.
This matches EXP-G's conclusion: *trust the risk-reduction from volatility, not a P/L oracle.*
The adaptive SL/TP sizing (`S`) **alone hurts** (−10,778); it only helps paired with the gate.

### (b) CUSUM dynamic-flip tops P/L — but it CORRECTS notes/32
`cusum_flip+none` = **+$54,910** (holds all of 2025's +41,740, flips 2026 to +13,170). That's
the best raw P/L. **However**, this is *lower* than notes/32's reported **+$74,460**, and the
reason matters:

> **notes/32 assumed flipped P/L ≡ −normal P/L per trade (engine symmetry). That assumption is
> FALSE in this engine.** Measured here, the max per-trade deviation between `flipped` and
> `−normal` is **367.8 pts** — large. The asymmetric SL/TP (soft 80 / hard 100 / TP 50) means a
> flipped short is *not* the mirror of a normal long. So flipping 2026 yields **+13,170 actual**
> (this tournament, real flipped trades), not the +55,160 a clean sign-flip would imply.

This is an important honesty correction: the **+$74k figure was an artifact of the symmetry
shortcut**; the rigorous, engine-true number is **+$54,910**, and even that is illustrative (§3).

---

## 3. The unavoidable caveat (unchanged): n = 1
There is still exactly **one regime change** in the data. Every flip row — CUSUM included — is
fitted to that single event. The +$54,910 is *in-sample on the only sample*: real arithmetic,
not validated generalisation. **What to trust:** the *mechanism* (a vol gate that cuts tail risk
+ a principled change-point flip), and the **risk reduction** (drawdown 57k → 16–27k). **What not
to trust:** the specific flip dollar figure until more regime changes (→ Workstream F, more
instruments) are observed.

## 4. Best picks (honest)
- **Most defensible:** `normal + G` or `normal + S+G` — positive, no flip dependency, ~half the
  drawdown. The vol gate is the real, mechanism-backed edge.
- **Highest P/L (illustrative):** `cusum_flip + none` (+$54.9k) — but rests on the n=1 flip.
- **Best risk-adjusted:** `cusum_flip + G` (+$30.1k at the lowest drawdown, 15.6k).

## 5. Status & next
- **WS-G tournament: DONE** (12 combos, plumbing validated, notes/32 corrected).
- **Pending in WS-G:** per-combo **dashboard clones** (the dashboard factory — clone the
  standalone HTML per top combo; main untouched), per the original request. Next sub-step.
- Also flags **Workstream D** value: a better/validated flip detector matters, but is capped by
  n=1 until more instruments (F).
- A one-line correction pointer should be added to `notes/32` (its +$74k assumed symmetry).

## 6. One-paragraph summary (baby)
We tried every sensible combination of "which direction to trade" (normal / always-flip / smart
CUSUM-flip) and "how to use the volatility forecast" (nothing / resize stops / skip the wildest
bars / both), all at one contract on the trusted cloned engine. The dependable winner is the
**volatility gate** — sitting out the most volatile bars cuts the 2026 losses and halves the
drawdown, turning the strategy positive with no flipping required. The smart flip gives the
biggest headline profit (+$54.9k), but importantly that's **less than an earlier note claimed
(+$74k)** because that note assumed flipping just negates each trade's result — which we measured
to be false in this engine (stops aren't symmetric). And every flip number still rests on the
single regime change we've ever seen, so treat the dollars as illustrative and trust the
risk-reduction and the mechanism instead. Next: build a separate dashboard for each top
combination (never touching the main one).
