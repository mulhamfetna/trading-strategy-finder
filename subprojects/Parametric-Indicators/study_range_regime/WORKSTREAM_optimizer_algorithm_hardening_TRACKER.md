---
name: workstream_optimizer_algorithm_hardening_tracker
description: "LIVE progress tracker for the optimizer-algorithm-hardening workstream (apply REPORT_optimizer_algorithm_alternatives.md P0→P4 one-by-one). Has past/current/next actions + a precise RESUME PROTOCOL for when the P3 background proof signals back. Read this first when resuming."
metadata:
  type: project
  workstream: optimizer-algorithm-hardening
  status: IN-PROGRESS
  date: 2026-06-16
---

# 🧭 WORKSTREAM TRACKER — Optimizer algorithm hardening (P0 → P4)

> **READ THIS FIRST WHEN RESUMING.** This is the single source of truth for where the workstream stands,
> what is running in the background, and exactly what to do when the P3 proof signals back. It exists so a
> context switch (a NEW big task is being scoped in parallel) does not mix up this in-flight workstream.

**Goal:** apply every recommendation in `REPORT_optimizer_algorithm_alternatives.md` **one-by-one**, each
with: baby explanation → implement → stress-test/validate → verbose standalone doc → next. User process,
verbatim: *"do it one by one … explain … implement … stress test it and validation … document it verbosely
in its own document … proceed to the next."* After P4 the user assigns a **separate big optimizer task**
(being scoped now — see `WORKSTREAM_<new>_TRACKER.md` once created).

---

## 📊 STATUS BOARD

| Stage | What | Status | Artifacts |
|---|---|---|---|
| **P0** | warm-start + ∝-budget + acceptance gate | ✅ DONE (prior session) | `optimizer.py`, `remote_wsi.sh`, `project_optimizer_warmstart_budget` memory |
| **P1** | wsh6 launch (NSGA-III + warm-start + auto-trials, new indicators) | ⏸ USER'S CALL (operational, not code) | launch cmd in `NEXT_OPTIMIZER_NOTES.md` §2d |
| **P2** | selectable sampler (`--sampler`) | ✅ DONE & validated | `optimizer.py` `make_sampler()`, `test_sampler_factory.py` (6/6), `UPDATE_P2_selectable_sampler.md` |
| **P3** | two-stage decomposition | ✅ DONE & validated (golden 6/6, test 4/4, proof: both engines = wsh4 to the dollar, guarantee held) | `two_stage.py`, `test_two_stage.py`, `UPDATE_P3_two_stage_decomposition.md` |
| **P4** | MAP-Elites quality-diversity archive | ✅ DONE & validated (test 5/5; 4h proof: 16 niches, portfolio, champion-floor met) | `map_elites.py`, `test_map_elites.py`, `UPDATE_P4_map_elites_archive.md` |

> **🎉 WORKSTREAM COMPLETE (P0✅ P2✅ P3✅ P4✅).** P1 (wsh6 launch) is the user's operational call. The
> dashboard workstream (`optimize/dashboard/`) now exposes P2 (sampler) + P3 (engine) and can surface P4 archives.
> **Committed `25942eb` (2026-06-16).** Full stage report: `../STAGE_REPORT_optimizer_hardening_and_dashboard.md`.

Task IDs: **#221 P2 (completed)**, **#222 P3 (in_progress)**, **#223 P4 (pending)**. (#220 P0 docs completed.)

---

## ⏳ CURRENT / IN-FLIGHT — the P3 full proof

A real two-stage run is executing **detached in the background** (chosen by user: "let the full run
finish ~30–60 min"). It is NOT tracked by a harness task (nohup-detached), so completion is watched by a
Monitor instead.

- **Process:** `python3 -m optimize._p3_proof` (4h, `ind_1min=True`, warm-started; ONE shared Stage A →
  both Stage-B engines cmaes+gp; Stage A 14 trials, Stage B 10/subset, top-k 2).
- **Writes:** `/tmp/p3_proof.json` (final results) · **Log:** `/tmp/p3_proof.log`.
- **Monitor task watching it:** `bhu8x2uqo` (60-min timeout) → fires `JSON READY` + dumps the json, or
  `PROCESS GONE` if it dies. If the monitor times out before completion, re-arm a fresh Monitor on the
  same `until [ -f /tmp/p3_proof.json ]` condition.
- **Already proven (the core claim):** Stage A Trial 0 (enqueued champion pattern) scored
  `[33586.5, −13927, 71.1]` = the wsh4 champion **to the dollar** ⇒ the guarantee (final ≥ champion) holds
  and the frozen-knob evaluation is correct.

### 🔁 RESUME PROTOCOL — do EXACTLY this when the proof signals back
1. **Read** `/tmp/p3_proof.json` (per-engine champion + `beats_or_matches_wsh4` verdict).
2. **Fill** the `<!--P3_PROOF_RESULTS-->` marker in `UPDATE_P3_two_stage_decomposition.md` §4 with a
   per-engine results table (cmaes vs gp: median P/L, worst DD, win, full P/L, full DD, #ind, ≥wsh4?).
   State plainly whether decomposition beat wsh4 or merely matched it (matching is the *expected* floor —
   the guarantee — not a failure).
3. **Golden check (belt-and-suspenders):** `python3 perf/check_golden.py` — must still be 6/6. (P2/P3 did
   NOT touch the engine — only optimizer orchestration + a new module — so this should be untouched.)
4. **Lock a regression test:** `optimize/test_two_stage.py` (mechanism: Stage A reproduces champion;
   shortlist always contains champion pattern; both engines return a point or None cleanly; `run()` rejects
   a bad `--stage-b`). Run it.
5. **Add the new dependency:** `cmaes==0.13.0` is now required for the cmaes Stage-B engine (installed
   locally via `pip install --break-system-packages cmaes`). Add `cmaes` to `requirements.txt` and note in
   `NEXT_OPTIMIZER_NOTES.md` that the server venv needs it before running `two_stage.py` with `--stage-b cmaes`.
6. **Mark task #222 completed.** Update this tracker's status board (P3 → ✅) and `NEXT_OPTIMIZER_NOTES.md` §2e.
7. **Proceed to P4** (below) — but only after the NEW big task's scoping has reached a natural pause, or
   per the user's direction at that moment.

---

## ➡️ NEXT — P4 (MAP-Elites quality-diversity archive)

Not started. When picked up:
- **Baby explanation first** (per user process): MAP-Elites keeps an *archive of the best solution per
  niche* (e.g. bins of worst-fold DD × #indicators) — it is *rewarded for diversity* so it cannot collapse
  into one basin (the direct structural answer to "won't fall in the trap again"), and yields a **portfolio**
  of champions (low-DD, high-return, few-indicator, …) instead of one point.
- Implement as `optimize/map_elites.py` (likely Optuna-independent or a thin QD loop), warm-started.
- Validate (full proof on 4h as with P3, user-confirmed style), verbose doc
  `UPDATE_P4_map_elites_archive.md` (Mermaid only), regression test, mark #223 done.
- Then the workstream is complete and the big optimizer task takes over fully.

---

## ✅ PAST — completed actions (chronological, with evidence)
1. **P2 implement** — `make_sampler()` + `SAMPLER_CHOICES` + `run(sampler=)` + `--sampler` CLI + plan header.
   Default `nsga3` ⇒ byte-identical. GP-BO uses native `GPSampler` (no BoTorch). cmaes guarded (single-obj).
2. **P2 validate** — `test_sampler_factory.py` 6/6; CLI `--plan`/argparse checks; 5 brains smoke end-to-end;
   **nsga3 & gp both reproduce golden 4h $142,203 to the dollar** ⇒ sampler-agnostic objective.
3. **P2 doc** — `UPDATE_P2_selectable_sampler.md` (3 Mermaid, fences balanced).
4. **Task cleanup** — deleted 13 BROKEN tasks (#98–#110): the abandoned Vue/Pinia/Chart.js/SSE optimizer-UI
   workstream. Verified against code: frontend is vanilla standalone HTML, no `.vue/.ts`, no `/api/optimize`.
5. **P3 implement** — `optimize/two_stage.py`: `_Ctx` (load once + frozen champion), `run_stage_a` (discrete
   NSGA-III, champion pattern force-included), `run_stage_b` (cmaes scalarized | gp multi-obj, champion knobs
   seeded), `run()` orchestrator, `main()` CLI. Installed `cmaes==0.13.0`.
6. **P3 mechanism smoke** — both engines run end-to-end (decision-TF; "no feasible" expected = 1-min champion
   infeasible on decision-TF, same as P2 caveat).
7. **P3 doc** — `UPDATE_P3_two_stage_decomposition.md` (2 Mermaid; results placeholder pending the proof).
8. **P3 full proof LAUNCHED** (background, see CURRENT above).

---

## 🔑 KEY FACTS TO NOT LOSE
- **wsh4 champion (deployed, baseline):** median fold P/L **$33,587** / full P/L **$142,203** / DD 10% (9.9%)
  / win 71.1% / **8 indicators** / shared SL/TP. `$142,203` is the **golden 4h full-period P/L**.
- **Search dims:** 56 shared / 62 split (current 18-indicator registry). Trap = density (dims↑, budget flat).
- **Guarantee mechanism (P3):** champion pattern force-included in Stage-A shortlist + champion continuous
  knobs enqueued as Stage-B seed ⇒ result provably ≥ wsh4.
- **New dep:** `cmaes==0.13.0` (Optuna lazy-imports it for `CmaEsSampler`). Native `GPSampler` needs nothing.
- **Standing rules:** commit/push ONLY when asked; NEVER stage repo-root secrets or pre-existing modified
  tracked files; fresh full runs use a NEW prefix (wsh6 next); 4h-only restriction applies ONLY to the
  production full-data optimizer (all dev/parity/smoke/golden still use ALL timeframes); golden byte-match
  after any ENGINE change; all report visuals are **Mermaid, never ASCII**.
- **Everything in this workstream is UNCOMMITTED on `dev`.**

---

## 🆕 PARALLEL: NEW BIG TASK (being scoped now)
The user is assigning a separate, large optimizer task that starts with **deep analysis + deep system
analysis → discuss every aspect → action plan → workstream**. That is its OWN track; it does NOT replace
this one. When it produces a plan, create `WORKSTREAM_<name>_TRACKER.md` for it and cross-link here. This
P0→P4 workstream resumes via the RESUME PROTOCOL above whenever the P3 signal lands.
