---
name: known-quirks
description: Honest audit of non-obvious behaviours, dead parameters, silent defaults and design
  choices in the box+indicator backtester/optimiser — both pre-existing and introduced this session.
  Each is verified in code, with severity and a suggested fix.
type: reference
status: audit
workstream: WS-I
---

# Known quirks / hidden behaviours — honest audit

Verified in the source. Grouped by severity. "Pre-existing" = baked into the design before this
session; "NEW" = a choice made this session that wasn't loudly flagged.

---

## 🔴 Worth a decision (can change results / interpretation)

### Q1. `flip=True` confirms the *pre-flip* direction (pre-existing)
The indicator gate (veto / confirm / resolver) is computed against the **unflipped** box direction
(`runner.box_direction_int` → `decision_signals`, no flip), while the engine applies `flip` to the
signal **afterwards** (`engine`: `if flip: signal = opposite`). So with `flip=True`, the indicators
confirm/veto the box's **original** read, but the trade is entered in the **opposite** direction.
- **Who it hits:** the **2h and 1h champions both use `flip=True`** with indicators on.
- **Is it a bug?** Depends on intent. Reading (a) = bug: indicators should vet the *actual* trade
  direction. Reading (b) = feature: indicators vet the box's raw read and `flip` is an independent
  "trade the inverse" wrapper. It is **self-consistent** (optimiser == dashboard both do this), so the
  champion numbers are real *for this behaviour* — but if you meant (a), the flip champions are gated
  on the wrong side. **Needs your call.**

### Q2. `dd_cap` does nothing to the backtest (pre-existing)
`dd_cap` (the "$5,000 max-drawdown") is validated and drawn as a grey dashed line on the drawdown
chart, but it is **not enforced** — the only circuit-breaker is `dd_limit`. So changing `dd_cap`
never changes a single trade. It's a **display-only / informational** kill-switch level.
- **Fix option:** either enforce it (hard-stop the whole run at `dd_cap`) or relabel it clearly as a
  visual goal line.

### Q3. Two indicator parameters are **dead** for trading (pre-existing)
- **Stochastic `d`** (the %D smoothing): the vote uses **%K only** (`k, _ = stochastic(...)`; %D is
  discarded). So `d` changes nothing about entries.
- **Keltner `m`** (the band multiplier): the vote is `sign(close − EMA_mid)`; the band (which `m`
  sets) is discarded. So `m` changes nothing about entries.
- **Consequence:** the optimiser **searches over `d` and `m`** anyway (wasted search dimensions), and
  the champion records list tuned `d`/`m` values that have **no effect**. (See also Q7.)
- **Fix option:** drop `d`/`m` from the search space, or make the vote actually use %D / the bands.

---

## 🟠 Introduced this session (should have been louder)

### Q4. Warm-up formulas are heuristics, not exact (NEW)
The per-indicator warm-up I added is approximate: `adx = 2n−1`, `macd = slow+signal`,
`structure_trend`/`order_block = swing_l`, `stochastic = n+d−1`. The structure/order-block one is a
**crude under-estimate** — a real swing pivot needs ≥2 *confirmed* swings, which is data-dependent and
usually longer than `swing_l`. And `stochastic = n+d−1` **waits on `d`, which the vote never uses**
(Q3) — so stochastic over-waits; it should arguably be just `n`.

### Q5. Disabled indicators now show "neutral" in the event log without being computed (NEW)
For speed I stopped computing **disabled** indicators' votes. The greyed chips in the event log now
always read **"neutral"** for an off indicator, whereas before they showed what that indicator *would*
have voted. No effect on trades (off = off), purely a log-display change.

### Q6. The SMC "generation report" panel is on the decision frame, the SMC *votes* are on 1-minute (NEW)
When 1-minute indicators are on, `fvg`/`order_block`/`structure_trend` **vote** on the 1-minute frame,
but the dashboard's "Phase 1 — SMC structure generation report" counts are still computed on the
**decision-TF** candles. So that panel's numbers describe a different frame than the actual votes.

### Q7. The optimiser's champion `d`/`m` values are noise (NEW consequence of Q3)
Because `d` and `m` don't affect trading, the values the search "tuned" for them are arbitrary — don't
read meaning into `stochastic d=35` or `keltner m=3.5` in the recipes.

---

## 🟡 Minor / by-design, but worth knowing

### Q8. 1-minute indicators cold-start per window/fold (NEW, mild)
In the dashboard a single-year window slices the 1-minute frame to that window, and in the optimiser
each fold slices it — so the 1-minute indicators **warm up from scratch** at the start of each
window/fold. The warm-up is only minutes (not months), so the effect is small, but it exists.

### Q9. Data gaps ⇒ indicators vote neutral (NEW, by-design)
If a decision bar has **no 1-minute candle** inside its window (a market gap), the 1-minute sampler
returns "none" and that indicator votes **neutral** for that bar. Reasonable, but silent.

### Q10. The optimiser's fast path is an *approximation* of the exact engine (pre-existing)
`confirm_mask` models confirmation as an **immediate-fill gate**; it does **not** model the global
retrace/wait fill or the live-carry-across-HOLD-bars resolver (those live only in the exact dashboard
engine). They agree **only when `retrace=0` and `wait=0`** — which the WS-I champions use, so they
matched on re-validation. If you optimise with retrace/wait, the optimiser's number won't equal the
dashboard's.

### Q11. Mixed-frame system (by-design, restating)
With 1-minute indicators on, it's a **mixed-frame** strategy: box trigger + volatility gate + entry
cadence on the **decision TF**, indicators on **1-minute**, exits on **1-minute**. Easy to forget.

### Q12. Operational guesses (NEW)
- `profiles/user_profiles.json:abdulfattah1` is the 4h-champion config I saved as a stand-in; if your
  browser-saved profile differs, that file is a guess.
- The server worker weighting (`[2m]=6 … [4h]=4`) assumes ~uniform per-trial cost across TFs — it's an
  estimate, not measured per-TF.

---

## Suggested fixes (if you want them)
- **Q1:** decide flip semantics; if (a), flip the box direction *before* the indicator gate.
- **Q2:** enforce `dd_cap` as a hard stop, or relabel it.
- **Q3 + Q7:** drop `stochastic.d` and `keltner.m` from the search space (and the recipes), or wire
  %D / the bands into their votes.
- **Q4:** set `stochastic` warm-up to `n`; revisit the structure/order-block warm-up.
- **Q6:** compute the generation report on the 1-minute frame when indicators are 1-minute.

None of these block the server sweep; they're transparency items. Tell me which to fix.
