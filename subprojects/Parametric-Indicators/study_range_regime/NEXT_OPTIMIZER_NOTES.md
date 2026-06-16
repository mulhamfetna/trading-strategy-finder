# Notes for the NEXT full optimizer run (wsh5) — carry these forward

> # ⚠️ **THE FULL-DATA OPTIMIZER RUNS 4h ONLY (2026-06-15 directive)** ⚠️
> **Every full-data optimizer sweep — this one and all future ones — optimizes ONLY the 4h timeframe and
> CONCENTRATES ALL workers on it. The other timeframes (2h/1h/15m/5m/2m) are HELD (not run) for time-saving
> and study focus.** This is enforced in `optimize/server/remote_wsi.sh` (`TFS=(4h)`, `WORKERS[4h]=30`).
> **This restriction applies ONLY to the production full-data optimizer.** Parity tests, smoke tests, golden
> byte-match, and ALL engine/system development STILL consider ALL timeframes — nothing else is narrowed.
> To resume the full all-TF sweep later: set `TFS=("${TFS_ALL[@]}")` in remote_wsi.sh and restore per-TF WORKERS.



Post-`wsh4` edits that change what a fresh optimizer run should search. The deployed champion (`wsh4`,
4h decision frame / 1-min indicators) is **shared-SL/TP, all-indicators-on**; these notes widen the space.

## 1. Split long/short SL/TP is now searchable (Q3 / E2)
- New optimizer inputs available: `long_sl_soft`, `long_sl_hard`, `long_tp`, `short_sl_soft`, `short_sl_hard`,
  `short_tp` (per-side; hard = soft + delta, same per-TF bounds as the shared path).
- **Enable with:** `optimize.optimizer.run(tf, ..., split_sltp=True, study_prefix="wsh5")`.
- **Default is OFF** (`split_sltp=False`) ⇒ shared SL/TP ⇒ identical to wsh4. The wsh4 champion used
  long==short; turning this on lets buys and sells get their own stops/targets (user's point 5).
- Plumbing is golden- + fast-parity-locked (see `UPDATE_E2_split_threading.md`).

## 2. Use a NEW study prefix
Per standing rule: fresh runs use a NEW prefix (**`wsh5`**), never reuse `wsh4`. Per-TF Postgres DBs on the
AMD server (`wsh-pg`, creds in `$WSI/pg.env`).

## 2b. wsh5 4h split run — ✅ DONE (5028 trials, 2026-06-15)
`wsh5_4h` (split long/short SL/TP, `--ind-1min --split-sltp`, 4h-only) completed at 5028/5000 trials.
**Result (see `REPORT_wsh5_4h_split_champion.md`):** the split champion (median fold P/L $28.2k, worst DD $6.2k,
win 86.5 %, full P/L $89.0k) **did NOT OOS-dominate** the wsh4 shared champion ($33.6k / $13.9k / 71.1 % /
$142.2k). Per the adoption gate the **shared champion stays deployed**; the split champion was **imported as a
new alternative profile** (`presets.py` → `⚖ WS split 4h · long/short SL/TP`, source
`optimize/results/wsh5_4h_split_champion.json`). Confirms Q1: asymmetric SL/TP trades return for lower DD —
not a strict win. **This run did NOT search the new vote indicators below.** Held: `wsh5_{2h,1h,15m,5m,2m}`.

## 2c. NEXT full run (e.g. wsh6) — search the 3 new indicators too
Now that engine + optimizer + dashboard all support `ifvg`/`breaker`/`cisd` (§3) AND split SL/TP (§1), a fresh
4h-only run with a NEW prefix (wsh6) would search the widest space yet. Keep `--split-sltp` if you still want
the per-side option in the search; the registry auto-adds `en_ifvg/en_breaker/en_cisd`.

## 2d. ⭐ OPTIMIZER HARDENING (2026-06-15) — warm-start + dimension-proportional budget + acceptance gate
After the superset paradox (`REPORT_optimizer_superset_paradox_and_system_breakdown.md`: a bigger space returned a
WORSE champion because NSGA-III is a finite stochastic search), the optimizer now defends against it:
- **Warm-start (default ON):** `optimizer.run` enqueues the known champions (wsh4 per-TF + wsh5 split when
  `--split-sltp`) as the FIRST trials ⇒ the front is **provably ≥ the prior champion**. Disable with `--no-warm-start`.
- **Trials ∝ dimensions:** `--auto-trials` sets trials = `search_dims × --trials-per-dim` (default 100; wsh4 ≈105/dim)
  ⇒ adding indicators/split auto-expands the budget. `--plan` is a dry run that prints the plan and exits.
- **Acceptance gate:** `bash optimize/server/remote_wsi.sh run` (no number) auto-sizes the budget, prints the plan
  via `... plan`, and **asks for confirmation** before launching (`WSH_CONFIRM=1` skips it in automation).
- **Launch wsh6 (4h-only, hardened):**
  `WSH_PREFIX=wsh6 WSH_SPLIT=1 bash optimize/server/remote_wsi.sh run`  → review the printed plan → type `y`.
- Algorithm alternatives surveyed in `REPORT_optimizer_algorithm_alternatives.md` (two-stage decomposition +
  CMA-ES/GP-BO + MAP-Elites). All report visuals are **Mermaid** (never ASCII art) per standing instruction.

## 2e. ⭐ ALGORITHM WORKSTREAM (P2→P4) — applying the report's recommendations one-by-one
**LIVE TRACKER:** `WORKSTREAM_optimizer_algorithm_hardening_TRACKER.md` (read first when resuming — has the
P3-proof RESUME PROTOCOL). Implementing `REPORT_optimizer_algorithm_alternatives.md` staged plan.
P0 done (§2d); P1 = wsh6 launch (user's call).
- **P2 — selectable sampler ✅ DONE (2026-06-16).** The Optuna "brain" is now `--sampler {nsga3*|nsga2|tpe|motpe|gp|cmaes}`
  (and `run(..., sampler=)`); default `nsga3` ⇒ byte-identical to prior runs. `make_sampler()` factory guards `cmaes`
  (single-obj/continuous-only ⇒ refused on the 3-obj study; it is the P3 Stage-B engine) and rejects unknown names.
  GP-BO uses Optuna's **native** `GPSampler` (no BoTorch). Verified: nsga3 & gp both reproduce the golden 4h champion
  (full P/L $142,203) exactly ⇒ sampler-agnostic objective. Lock: `optimize/test_sampler_factory.py` (6 checks).
  Verbose doc: `UPDATE_P2_selectable_sampler.md`.
- **P3 — two-stage decomposition** (discrete indicator pick → continuous CMA-ES/GP tuning): NEXT.
- **P4 — MAP-Elites** quality-diversity archive (anti-collapse portfolio): after P3.

## 3. NOW-WIRED vote indicators (available for a SUBSEQUENT run, not in the live wsh5)
- **IFVG, breaker, CISD** are now registered vote-source indicators (`indicators/library.py` keys `ifvg`,
  `breaker`, `cisd`) ⇒ a future optimizer run will include `en_ifvg/en_breaker/en_cisd` in the search space
  automatically (golden 6/6 unaffected; champion preset enumerates its own indicators).
- Still NOT wired: the regime study's trend-follow·pinned·widen-only TP rule, and OB/breaker entry-placement
  policy (immediate/mid/far/wait) — see `PLAN_entry_rules.md` (Q6 steps 2–3, task #218).

## 4. Adoption gate (unchanged)
Only swap the deployed champion if the new (split / wider) search OOS-dominates on return/DD under the
pre-registered walk-forward rule. Fixed champion stays deployed until then.
