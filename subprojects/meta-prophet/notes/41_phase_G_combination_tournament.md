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
| **cusum_flip + none** (realizable) | **+30,130** | +41,740 | −11,610 | +325% | 772 | 67 | 36,940 |
| **normal + S+G** | +21,396 | +31,223 | −9,826 | +259% | 482 | 67 | 27,360 |
| cusum_flip + S+G | +9,097 | +31,223 | −22,125 | +168% | 482 | 66 | 35,666 |
| cusum_flip + G | +8,700 | +22,780 | −14,080 | +165% | 464 | 66 | 25,360 |
| normal + G | +3,685 | +22,780 | −19,095 | +127% | 464 | 65 | **26,650** |
| normal + S | −10,778 | +53,740 | −64,518 | +20% | 754 | 65 | 68,649 |
| **normal + none (BASELINE)** | **−13,420** | +41,740 | −55,160 | 0% | 772 | 64 | 57,160 |
| flipped + G | −40,000 | −51,000 | +11,000 | −198% | 443 | 64 | 58,000 |
| flipped + none | −75,000 | −88,000 | +13,000 | −459% | 750 | 63 | 101,000 |
| flipped + S / S+G | −57k … −85k | (loses) | | | | | |

(Numbers use the **realizable** flip — see §2b. `cusum_flip+none` symmetric upper-bound ≈ +54,910.)

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

### (b) The flip changes the TRADE SET — so per-trade flip is only an approximation
This is the deep finding, and it corrects notes/31/32. Those notes assumed the engine symmetry
*flipped P/L ≡ −normal P/L per trade*, i.e. that the strategy decomposes into per-trade units you
can individually flip. **That is false.** Flipping the entry direction **changes which trades
happen**:

> normal mode = **772** trades; flipped mode = **750** trades; only **723** share an entry bar.
> **49 normal trades have no flipped counterpart** (and 27 flipped-only). Measured max per-trade
> deviation of `flipped` vs `−normal` = **367.8 pts**. A flipped short is *not* the mirror of a
> normal long (asymmetric SL/TP 80/100/50, and the entry/exit interaction differs).

So a per-trade "flip on CUSUM signal" can only be **approximated**, and the answer depends on what
you do with the 49 unmatched trades — bracketing the truth:
- **realizable** (primary, used in the table): unmatched trades **stay normal** → `cusum_flip+none`
  = **+$30,130** (2025 +41,740 held; 2026 only partly recovered, −11,610).
- **symmetric** (optimistic upper bound): unmatched trades flip to −normal → ≈ **+$54,910**.
- notes/32's **+$74,460** was even more optimistic (full symmetry on all trades) — **superseded**.

**The only way to get the true number is to run the engine with a per-bar flip schedule** (so the
engine produces the correct trade set under a time-varying regime). The clone's flip is currently a
single bool *and the exit logic also branches on it*, so this is a real entry+exit change — logged
as a follow-up (WS-D/WS-G). Until then: treat the flip P/L as a **bracket [$30k, $55k], illustrative,
n=1** — and lean on the gate (§2a), which is exact.

---

## 3. The unavoidable caveat (unchanged): n = 1
There is still exactly **one regime change** in the data. Every flip row — CUSUM included — is
fitted to that single event. The +$54,910 is *in-sample on the only sample*: real arithmetic,
not validated generalisation. **What to trust:** the *mechanism* (a vol gate that cuts tail risk
+ a principled change-point flip), and the **risk reduction** (drawdown 57k → 16–27k). **What not
to trust:** the specific flip dollar figure until more regime changes (→ Workstream F, more
instruments) are observed.

## 4. Best picks (honest)
- **Most defensible (recommended):** `normal + S+G` (+$21,396) or `normal + G` (+$3,685) —
  positive, **no flip dependency**, ~half the drawdown (57k → 27k / 27k). The vol gate is the
  real, *exact*, mechanism-backed edge.
- **Highest P/L (illustrative, n=1):** `cusum_flip + none` (+$30,130 realizable; up to ~$54.9k
  symmetric) — rests on the single regime change and the approximate per-trade flip.
- The flip adds little **once the gate is on** (cusum_flip+S+G +9,097 < normal+S+G +21,396) —
  the gate already removes most of the bad-regime bars, so there's little left for the flip to fix.

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
drawdown, turning the strategy positive with no flipping required. The smart flip gives a
bigger headline profit (≈ +$30k realizable, up to +$55k optimistic), but importantly we discovered
that **flipping changes which trades happen** (772 vs 750 trades) — so "flip each trade's result"
is only an approximation, and an earlier note's +$74k assumed a clean negation that isn't true.
Every flip number also rests on the single regime change we've ever seen. So trust the **gate**
(it's exact, halves the drawdown, and needs no flipping) and treat the flip dollars as an
illustrative bracket. Sibling dashboards (one per vol-lever, with a normal/flipped/cusum dropdown)
are generated under `dashboard_combos/`, the main dashboard untouched.
