# NSGA-II prep — deep analysis of `sub-projects-preprint.md`

**Date:** 2026-05-26
**Source preprint:** `/mnt/data/projects/trading/sub-projects-preprint.md`
**Status:** analysis only — no code changes yet

---

## 1. What the preprint says, in plain English

The preprint is a plan written in five logical beats:

1. **Context** — the backtest platform exists. It is split into a backend ("the mathematical engine that takes parameters and returns the status of a trade") and a frontend dashboard. The backend already produces full trade logs and stats summaries.
2. **Far goal** — feed *all* dashboard parameters as a vector **x** into NSGA-II and search for the **x** that maximises winrate or total profit.
3. **Near goal** — limit the search to two parameters: `sl` and `tp`. Objective: maximise **total profit** (one Y, not Pareto).
4. **Hard gate before NSGA-II resumes** — first extract the **truth table of the backtest platform**: every possible trade probability and its output. Write it to an MD file.
5. **Cross-check** — diff that truth table against Stage 1's truth table (`subprojects/signals/truth_table.md`).
   - If the backtest is a *simplified version* of Stage 1's logic → green-light NSGA-II.
   - If there's a *logical contradiction* → freeze NSGA-II, fix the backtest, because **Stage 1 is the verified ground truth** (team leader signed off on it).

The preprint is therefore a verification protocol, not a feature request. NSGA-II tasks #98–#110 stay paused until the gate passes.

---

## 2. Where this lands vs. memory

Two relevant memories:

- **`project_nsga2.md`** — "22-task plan at `docs/superpowers/plans/`, paused, ready to resume." Tasks #98–#110 in the task list are the paused tail.
- **`project_unified_box_v4.md`** — `NQ_full_data.csv` replaces the older preprocessed files; hour ≥ 18 mapping rule; no `window_days`.

Neither memory needs to change. The preprint adds a **new phase 0** ("truth-table reconciliation") in front of the existing plan; once it clears, the existing plan resumes.

---

## 3. What "the truth table of the backtest platform" actually is

The preprint uses the phrase loosely. To extract it usefully we have to decide which of three things the user means. They are not the same — picking the wrong one will produce a comparison that looks coherent but is meaningless.

| Reading | What gets enumerated | Compares cleanly to Stage 1? |
|---|---|---|
| **A. Entry-direction truth table** | Per-4h-boundary inputs → `long` / `short` / `hold` | **Yes — directly.** Stage 1 emits the same three labels. |
| **B. Per-trade outcome truth table** | (entry direction × big-candle override × ladder progression × exit reason × 4h-end mode × direction-flip mode) → final `exit_reason` ∈ {TAKE PROFIT, STOP LOSS (SOFT), STOP LOSS (HARD), DIRECTION_FLIP, OPEN} | **No.** Stage 1 has no concept of trades, ladders, or exits. Comparison would be apples to oranges. |
| **C. Per-candle signal truth table** | (just-closed 4h candle properties × active box geometry × prior-bar state) → `long` / `short` / `hold` for THIS candle | **Yes**, and this is what the backtest's `BoxLookup.get_signal()` actually returns. Stage 1's truth table is the per-candle equivalent. |

**Reading A** is what `docs/strategy/references/truth_table.md` already documents. **Reading C** is what `src/strategy/box_lookup.py` actually implements. They are NOT the same — see §5.

The right choice depends on what "verified" means for Stage 1. Stage 1's truth table is at the **per-candle** level (a stateless one-shot rule per candle-vs-box-pair). So the comparison must be against the backtest's per-candle signal rule, not the per-trade outcome. That points to **Reading A / C** as the comparison target. **Reading B** is interesting in its own right but is out of scope for the cross-check.

> **Question for the user — Q1, Q2 in the wizard MD.**

---

## 4. What Stage 1 actually says (recap)

`subprojects/signals/truth_table.md` is a 10-row stateless decision matrix per (candle, active level pair):

```
inputs:  touched = (L ≤ BU) AND (H ≥ BL)
         color   = green | red | doji
         C vs BU, C vs BL

output:  long   iff  touched AND green AND C > BU
         short  iff  touched AND red   AND C < BL
         hold   otherwise
```

Properties:

- **Stateless.** No memory of prior bars. Each candle is judged in isolation.
- **Per level pair, not per candle.** A candle with K active level pairs produces K rows. The "candle signal" used by Stage 2 is the OR collapse: any long row → `long`, any short → `short`, else `hold`.
- **Touched is inclusive overlap** (`L ≤ BU` AND `H ≥ BL`). Not "close inside the box".
- **No box selection.** It just runs the rule on every active row for the candle.
- **No big-candle override.** No ladder, no exit, no direction flip.

This is what the team leader signed off on.

---

## 5. What the backtest *actually* implements (not what the doc says)

The MASTER strategy doc claims the backtest uses a `miss` / `bounce` / `traverse` model. The code does not. Inspecting `src/strategy/box_lookup.py:240-323`, the actual model is a per-(level-pair) **state machine**:

```
state per (row_date, label):
  prev_side ∈ {above, below}   (last OUTSIDE classification observed)
  inside_seen ∈ {True, False}  (has price been inside the box since prev_side was set?)

per bar:
  side = classify(close, upper, lower)
         = 'inside' | 'above' | 'below'

transitions:
  side == 'inside'                 → inside_seen := True; emit 'hold'
  prev_side is None                → prev_side := side;   emit 'hold'   (first observation)
  side == prev_side                → no state change;      emit 'hold'
  side opposite prev_side AND
    inside_seen is True            → emit 'short' if prev_side == 'above'
                                     emit 'long'  if prev_side == 'below'
                                     prev_side := side; inside_seen := False
  side opposite prev_side AND
    inside_seen is False           → prev_side := side;   emit 'hold'   (gap-skip)
```

So the backtest's **directional fire** requires three things across *multiple* bars:

1. A previously-recorded outside side.
2. An `inside` close at some point afterwards (the box was actually entered).
3. A close on the opposite outside side.

It is fundamentally **stateful**. Stage 1 is **stateless**. This is the central architectural difference. The preprint's question — "contradiction or simplification?" — almost certainly hinges on this.

Additional backtest-only logic that has no Stage 1 analogue:

- **Big-candle override** (`|close − open| ≥ 400` → reverse direction, full position).
- **Box selection** — nearest unburned box on the correct side; weekly priority on ties.
- **Conflict resolution** — `big_candle_resolution ∈ {big_candle_wins, box_wins, skip}`.
- **Ladder, anchor mode, exits, direction-flip** — not part of any per-candle truth table.

---

## 6. Is it contradiction or simplification?

A preview of what the formal cross-check will show, so the user can sanity-check the framing before we lock the comparison:

| Scenario | Stage 1 says | Backtest says | Verdict |
|---|---|---|---|
| 4h green candle, `H < BL` (price didn't reach the box at all) | `hold` (touched=false) | `hold` for THIS bar; but a `prev_side` may still be set and used later | **Same on this bar.** Backtest may fire later when price returns. Not contradiction — wider scope. |
| 4h green candle inside the box (`O,C` both between BL and BU), close at BU+ε | `long` (touched, green, C>BU) | `hold` — close is *just* above BU, classified `above`. If this is the first observation: no fire. If `prev_side == below` AND `inside_seen`: `long`. | **Possibly contradictory.** Stage 1 fires unconditionally; backtest requires history. |
| Green candle that closes below BL (price collapsed through the level) | `hold` (color/direction mismatch, row 10) | Could fire `short` if `prev_side == above` and `inside_seen`. | **Different.** Stage 1 returns hold; backtest can fire short. |
| Sequence: bar 1 above box → bar 2 inside → bar 3 below box | Each row independent: hold, hold, hold (each is "touched but neither edge broken cleanly" unless final close is decisive) | Bar 3 fires `short` | **Backtest fires; Stage 1 doesn't.** This is the canonical traversal that the backtest is designed to catch. |

**Tentative verdict:** the backtest is *not* a simplified Stage 1 — it is a **different, stateful** ruleset that happens to share the same output vocabulary (`long`/`short`/`hold`). Whether that counts as "contradiction" or "complementary" depends on whether Stage 1's per-candle rule is intended to be a **per-candle equivalent** of what the backtest is doing, or a **separate signal layer**.

Stage 2's output (reverse-signal windows) is also stateless across windows: it just takes the Stage 1 candle-level signal stream and pairs them. So Stage 1 + Stage 2 is a parallel signal pipeline, not a backtest. They may not need to agree per-candle at all.

> **Question for the user — Q3, Q4, Q5 in the wizard MD.**

---

## 7. Proposed phase 0 plan (gating NSGA-II)

If the user confirms Reading A/C as the truth-table scope, the work is six steps:

1. **P0-1.** Write the backtest per-candle truth table as code-grounded MD. Derive it directly from `box_lookup.py` (the state-machine version above), not from the strategy doc (which is out of sync with the code).
2. **P0-2.** Write an explicit row-by-row cross-check vs. Stage 1's table. Each row = one observable scenario; columns = Stage 1 result, backtest result, verdict.
3. **P0-3.** Classify each disagreement as one of:
   - *Identical* — both say the same thing.
   - *Simplification* — Stage 1 is the strict subset (backtest's superset is fine).
   - *Contradiction* — disagreement that cannot be explained by Stage 1 being a simpler view.
4. **P0-4.** Decision:
   - Zero contradictions → resume NSGA-II from task #98.
   - One or more contradictions → freeze NSGA-II, open a strategy-revision task using Stage 1 as the source of truth.
5. **P0-5.** (If contradictions exist) draft the backtest patches and re-run blueprint regression locks.
6. **P0-6.** Update `docs/strategy/MASTER.md` to match whatever wins.

This map sits **in front of** the existing 22-task NSGA-II plan; the existing plan is unchanged.

---

## 8. Out of scope

- Anything past the truth-table reconciliation (the actual NSGA-II algorithm tweaks).
- Stage 1 / Stage 2 code changes — those are verified per the preprint.
- Graphics pipeline (`docs/graphics/`, candles, boxes) — locked.
- Per-trade outcome enumeration (Reading B in §3) — interesting, but not what the preprint asks for.

---

## 9. Open questions

See `wizard.md` in this directory. The five questions there gate every downstream task.
