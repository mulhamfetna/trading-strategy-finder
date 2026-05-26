# Wizard — NSGA-II truth-table prep

Answer **inline** below each question (between the `>>>` and `<<<` markers, or wherever feels natural — I'll re-read the file when you say "ok done"). Skip anything you want to defer with `?` and I'll re-ask later.

---

## Q1. Truth-table scope — what should we enumerate?

The preprint says "truth table of the backtest platform — all possible probabilities for a trade and the outputs for each." Three plausible readings; pick one (or describe a hybrid):

- **A. Entry-direction only** — inputs at each 4h boundary → `long` / `short` / `hold`. This is what's *documentable* in a small matrix. Compares cleanly to Stage 1's table.
- **B. Per-trade outcome** — full combinatorial enumeration of trade outcomes: (entry × big-candle override × ladder fills × exit reason × 4h-end mode × direction-flip mode) → final `exit_reason`. Big table, no Stage 1 analogue.
- **C. Per-candle signal** — what `BoxLookup.get_signal()` actually returns per bar, including the state-machine memory across bars. Stateful equivalent to Stage 1's stateless rule.

>>>
(your answer here)
<<<

---

## Q2. Source of truth for the backtest table — code or docs?

`docs/strategy/MASTER.md` describes a `miss / bounce / traverse` model, but `src/strategy/box_lookup.py` actually implements a state machine over `above / inside / below`. They are **not** the same rule. Which one should the new truth-table MD reflect?

- **A. Derive from code** (the state machine in `box_lookup.py:240-323`) — guaranteed accurate to runtime behaviour.
- **B. Derive from docs** (`miss / bounce / traverse`) — easier to reason about, but may not match runtime.
- **C. Derive from code, and flag the doc as out-of-sync** (recommended).

>>>
(your answer here)
<<<

---

## Q3. If we find a contradiction, what defines "contradiction"?

The preprint says: contradiction → fix the backtest because Stage 1 is verified. But the backtest's stateful traversal model fires on sequences (e.g., above → inside → below) that Stage 1's stateless single-candle model can't fire on. So technically those are not contradictions, they're just different scopes.

Pick the definition you want me to use:

- **A. Per-row strict** — for any single candle where Stage 1 fires X and backtest fires Y ≠ X, count it as a contradiction.
- **B. Superset rule** — backtest is allowed to fire on multi-bar patterns Stage 1 can't see. Contradiction only when both say something definitive on the *same* candle and they disagree.
- **C. Coverage rule** — Stage 1 must be derivable from backtest by ignoring history. If you can't recover Stage 1 by stripping the state machine, it's a contradiction.

>>>
(your answer here)
<<<

---

## Q4. Stage 1 + Stage 2 vs. the backtest — same job or different jobs?

Are Stage 1/2 meant to **replace** the backtest's entry-direction logic eventually, or do they exist for a **different purpose** (analysis dataset, candidate-signal stream, regression oracle)?

This matters: if they're going to merge, contradictions must be resolved before NSGA-II. If they're parallel, contradictions may be acceptable and NSGA-II can proceed against the current backtest.

>>>
(your answer here)
<<<

---

## Q5. NSGA-II search space — confirm

Independent of the truth-table work, please confirm the NSGA-II search will be:

- **Vars (x):** `sl_soft_points`, `sl_hard_points` (or `sl_soft + delta`), `tp_target_points`. Anything else?
- **Objective (y):** **total profit** (single objective, maximise). The current implementation in `src/optimization/objective.py` returns `(median_pf, max_dd)` — Pareto two-objective. Should I change it to single-objective total profit?
- **Per-direction (long vs short) separate searches, with an option to tie them** — confirm.

>>>
(your answer here)
<<<

---

## Q6. Visual viewer preference

I built a side-by-side HTML viewer of the two truth tables at `viewer/index.html`. Tell me what to add/remove:

- [ ] Add a third column showing the *firing sequence* the backtest needs (e.g., `above → inside → below` for a short).
- [ ] Add a "play" button that animates a sample candle stream through both models so you can see them diverge.
- [ ] Add a CSV upload to test against real `signals_full.csv` rows.
- [ ] Strip it down — just the static comparison table is enough.

>>>
(your selections / notes here)
<<<

---

## How to view the HTML viewer (terminal-launched Claude Code can't open browsers for you)

```
cd /mnt/data/projects/trading/docs/superpowers/specs/2026-05-26-nsga2-truth-table-prep/viewer
python3 -m http.server 8765
# then in your browser:  http://localhost:8765/
```

If port 8765 is busy, pick another. Stop the server with Ctrl-C in that terminal.
