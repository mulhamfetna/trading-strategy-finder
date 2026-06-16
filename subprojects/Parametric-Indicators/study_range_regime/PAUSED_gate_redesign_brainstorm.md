---
name: paused_gate_redesign_brainstorm
description: "PAUSED gate-redesign brainstorm — the pause diagnosis (vol gate is NOT the cause) + the open redesign-direction questions to resume AFTER the entry-pause-visibility side task."
metadata:
  type: project
  workstream: gate-redesign
  status: RESOLVED (2026-06-16) — counterfactual study → ACCEPT the pause (see REPORT_counterfactual_pause.md)
  date: 2026-06-16
---

# PAUSED — gate-redesign brainstorm (resume after the side task)

We were brainstorming a "gate redesign" (issue 1: shrink the champion's ~11.5-day no-entry pause). We ran the
pause **diagnosis first** (`optimize/diagnose_pause.py`) and it **flipped the premise**. Parking the open
questions here to resume after the entry-pause-visibility side task.

## Diagnosis result (champion, 4h, gate_pct=87, K=1) — KEY
**All 2119 bars:** no box signal **60.9%** · vol-gated 8.3% · vetoed 8.1% · confirm<K 17.4% · would-enter 5.4%
(only 114 entry opportunities all period).
**Longest pause (~20-day opportunity gap, Apr 14 → May 12, 119 bars):**
- **no box signal 70.6%** (84) · **confirm<K 21.8%** (26) · vol-gated **4.2%** (5) · vetoed 3.4% (4).

⇒ **The volatility gate is NOT the bottleneck (~4%).** The pause is **box-signal sparsity (~71%)** +
**confirmation blocking (~22%, K=1 ⇒ zero confirmers fired)**. A *vol-gate* redesign would barely move it.

## RESOLVED (2026-06-16) — counterfactual study says ACCEPT the pause
The evidence-first investigation is done — see `REPORT_counterfactual_pause.md` (`optimize/counterfactual_pause.py`).
Each gate-/veto-blocked box signal was simulated as an isolated trade with the champion's exact exit:
- **vol gate** blocked 206 trades netting **−$28,040** · **veto** blocked 359 netting **−$73,117** → both are
  **correctly filtering** (they avoid ~$101k of losers; relaxing them destroys P/L).
- **confirm<K = 0** under the engine-faithful pairing (the old diagnose_pause 22% was an off-by-one artifact);
  confirmation-blocking is 100% veto-driven.
- **box-silence (71%)**: silent windows are roughly **symmetric** (median MAE 88 ≥ MFE 75 pts; TP 120) → no
  free directional edge to harvest.

**Verdict: ACCEPT the pause.** It is the strategy correctly NOT trading, not a defect. The only remaining
lever (a new box-entry trigger for silent windows) is unsupported by the displacement data and would be a
speculative research bet, gated on finding a *directional* predictor — not a fix. Lever questions below are
therefore closed unless a directional silent-window signal is found.

## OPEN QUESTIONS (CLOSED by the counterfactual study above — kept for history)
**Q (redesign lever):** given the diagnosis, where should the redesign focus?
1. **Box entry triggers** (biggest lever, ~71%) — broaden what creates an entry candidate (the SMC box
   generator). Most impact, highest risk (core logic).
2. **Confirmation layer** (~22%, lower risk) — rework K-confirmers / veto so the few box signals aren't
   blocked (K=0 option, "confirm OR", softer veto). Smaller, safer.
3. **Diagnose deeper first** — characterize WHEN the box goes silent (regime/time-of-day/after-loss) and what
   the confirm-blocked signals would have returned (good trades missed vs noise correctly filtered).
4. **Accept the pause / stop** — champion numbers are excellent; don't risk the edge.

**Clarifications I offered (pick up later):** what the "box signal" generator is and why it's silent ~71%;
what "confirm<K" means at K=1; whether levers can combine (e.g. 2+3); whether the user has a different lever
in mind; the risk/scope of touching the box vs the confirmation layer.

**My lean (for when we resume):** the visibility side task (below) will itself surface *where* the pauses come
from in the dashboard + per-signal files — which is the data we'd want before committing to lever 1 vs 2. So
resuming with that visibility in hand is ideal. Likely answer: **2 (confirmation rework) + a focused 3**
before touching the box (1).
