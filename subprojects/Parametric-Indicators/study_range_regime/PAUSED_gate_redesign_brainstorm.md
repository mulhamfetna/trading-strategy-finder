---
name: paused_gate_redesign_brainstorm
description: "PAUSED gate-redesign brainstorm — the pause diagnosis (vol gate is NOT the cause) + the open redesign-direction questions to resume AFTER the entry-pause-visibility side task."
metadata:
  type: project
  workstream: gate-redesign
  status: PAUSED — resume after the visibility side task
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

## OPEN QUESTIONS to resume (answer after the side task)
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
