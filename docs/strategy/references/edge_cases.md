---
name: edge_cases
description: Catalogue of every edge case the strategy explicitly handles, with defaults and the dashboard toggles that override them
type: reference
---

# Edge-Case Catalogue

Cross-reference for every edge case that has explicit strategy semantics. Each entry shows: when it triggers, default behaviour, dashboard alternatives, and the [[strategy-master]] section.

---

## E1. First 4h candle of the dataset

- **Trigger:** the engine starts; no prior 4h close exists.
- **Default:** sit and watch. No entry decision. No trade opened.
- **Alternatives:** none — this is invariant.
- **Spec:** [[strategy-master]] §2.3

---

## E2. Big-candle override (`|close − open| ≥ big_candle_threshold`)

- **Trigger:** the just-closed 4h candle has open-to-close move ≥ `big_candle_threshold` (default 400 pts).
- **Default (toggle `on`):** reverse direction (green→short, red→long), enter 4 contracts at base immediately. Bypass the truth table.
- **Alternative (toggle `off`):** apply the normal truth table; no big-candle special case.
- **Spec:** [[strategy-master]] §2.4

---

## E3. Doji 4h candle

- **Trigger:** the just-closed 4h has `open == close` (no colour).
- **Default:** `hold`. No entry.
- **Alternatives:** none.
- **Spec:** [[strategy-master]] §2.1

---

## E4. Nested boxes (price inside two overlapping boxes)

- **Trigger:** at the 4h close, price is inside both a weekly and a monthly box simultaneously, neither burned.
- **Default (`hold`):** wait until both boxes are burned through.
- **Alternative (`weekly_only`):** use the weekly box for the decision, ignore the monthly.
- **Alternative (`monthly_only`):** use the monthly box, ignore the weekly.
- If one is burned and the other isn't, the same toggle decides. If both are burned, the truth table applies normally.
- **Spec:** [[strategy-master]] §2.2

---

## E5. Active box "wrong side / already burned"

- **Trigger:** the nearest level on the correct side has already been burned this session.
- **Default:** skip the burned level, use the **next-nearest unburned** level.
- **Alternatives:** none.
- **Spec:** [[strategy-master]] §2.2

---

## E6. `hold` signal while a trade is already open

- **Trigger:** next 4h close fires `hold` and there's an open position.
- **Default:** `hold` does **not** close the trade. SL / TP / direction-flip remain the only exit mechanisms.
- **Alternatives:** none.
- **Spec:** [[strategy-master]] §4.4

---

## E7. Direction flip while a trade is already open

- **Trigger:** next 4h close fires the opposite direction of the current open trade.
- **Default (`flip`):** close current trade at the 4h boundary with `exit_reason = DIRECTION_FLIP`. Open new trade in new direction.
- **Alternative (`ignore_flip`):** keep existing trade open; only SL/TP can close it.
- **Alternative (`wait_for_zero`):** keep open until price returns to entry, close at zero P/L, then open new trade.
- **Spec:** [[strategy-master]] §4.3

---

## E8. 4h closes with the ladder partially filled

- **Trigger:** 4h boundary; trade has 1 or 2 contracts but the ladder triggers for further legs haven't fired yet, and the direction signal still allows scaling.
- **Default (`continue`):** keep trade open, continue the 1-1-2 ladder into the next 4h with the same `base` and trigger lines.
- **Alternative (`force_close`):** close the trade at the 4h end, re-evaluate direction for a fresh leg 1.
- **Alternative (`wait_for_zero`):** keep open until price returns to `base`, exit at zero P/L.
- **Spec:** [[strategy-master]] §3.3

---

## E9. 4h closes without SL/TP hit

- **Trigger:** 4h boundary; trade is open, no SL or TP has fired.
- **Default (`carry_open`):** keep trade open across the 4h boundary; SL/TP/direction-flip rules continue.
- **Alternative (`force_close`):** close at the 4h boundary regardless of P/L.
- **Alternative (`wait_for_zero`):** keep open until price returns to entry, exit at zero P/L.
- **Spec:** [[strategy-master]] §4.2

---

## E10. SL set tighter than ladder triggers

- **Trigger:** user configures `sl_soft_points` < `ladder_step_1` (default 100), or `sl_soft_points` < `ladder_step_2` (default 150).
- **Default:** **warn but allow**. UI shows yellow soft-SL number-box + inline note explaining which ladder tier is active.
- **Tiers:**
  - `sl_soft < ladder_step_1` → ladder deactivated, single-contract trade only
  - `ladder_step_1 ≤ sl_soft < ladder_step_2` → leg 2 can fire, leg 3 cannot
  - `sl_soft ≥ ladder_step_2` → full ladder
- **Alternatives:** none — the warning is mandatory; the user just chooses to acknowledge it.
- **Spec:** [[strategy-master]] §3.2

---

## E11. Anchor mode = `average` with running average sliding

- **Trigger:** `anchor_mode = average` and a new leg fills.
- **Default:** SL_soft, SL_hard, TP lines all re-anchor to `new_avg ± thresholds`.
- **Alternative (`base`):** lines never move; legs 2/3 don't affect them.
- **Spec:** [[strategy-master]] §5

---

## E12. Big-candle trade exit lines

- **Trigger:** big-candle override fired; 4 contracts entered at base instantly.
- **Default:** SL/TP lines at `base ± thresholds`. Avg entry = base, so `average` mode coincides with `base` mode — no sliding. Same exit reasons available as a standard laddered trade.
- **Alternatives:** none — big-candle trades cannot ladder (already at full 4 contracts).
- **Spec:** [[strategy-master]] §2.4, §5
