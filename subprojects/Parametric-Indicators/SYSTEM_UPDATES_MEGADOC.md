# SYSTEM UPDATES — MEGA RECORD (Parametric-Indicators)

**Date:** 2026-06-12 · branch `dev` (pushed to `origin/dev`) · single consolidated record of **every** system
update in this cycle + the **technologies record**. All numbers are **pre-extracted** from `perf/bench_history.json`,
the per-step `UPDATE_*.md` docs, the equivalence/parity runs, and the server deployment — nothing was re-run to
produce this document. Per-step detail lives in the linked docs (§10).

---

## 0. The three workstreams in this cycle

| # | Workstream | Outcome | Result-safety |
|---|------------|---------|---------------|
| **A** | **Backtester engine speed** (task #210) | single backtest ~3× faster coarse, 3–7× fine | **byte-identical** (golden 6-TF) |
| **B** | **Dashboard UX** | profile change no longer auto-runs; Run button = red/green freshness signal; Reset = restore selected profile | UI-only; no engine change |
| **C** | **Optimizer scaling + Postgres deploy** | SQLite many-writer contention fixed; Postgres live on the server; all studies migrated | env-unset byte-identical; deploy verified |

One-line: **the backtester got much faster without changing a single trade; the dashboard got clearer; and the
optimizer's reliability bottleneck (the wsh4 `database is locked` incident) is structurally fixed on PostgreSQL.**

---

## 1. Full commit map (this cycle, newest→oldest)

```
C  5654600 deploy(optimizer): Phase D — Postgres cutover on the server + pg.env auto-source
C  e43a3e3 feat(optimizer): migrate_to_pg.py — copy studies SQLite→Postgres (idempotent)
C  5800e56 feat(optimizer): Tier 4 — opt-in Parquet (parity-locked) + dataset registry + capacity formula
C  de01a17 feat(optimizer): Tier 3 — observability (live FAIL counts + JSON) + pre-flight contention smoke
C  0637f9a feat(optimizer): Tier 2 — watchdog/respawn + target-based idempotent runs
C  16ccd37 feat(optimizer): Tier 1 — centralize Optuna storage URL (Postgres-ready, env-unset byte-identical)
C  4206fd8 docs(optimizer): explainer — Tier 1 (Postgres + storage URL) + history decision
C  a7f5ad6 docs(optimizer): scaling-tiers action plan + SSH connection-reset incident post-mortem
B  4fcc842 ui(dashboard): profile no auto-run; Run button red/green freshness; Reset→selected profile
A  3343c25 docs(perf): MASTER report — end-to-end backtester optimization map + timing tables
A  2208fd8 docs(perf): pin Axis-B completion (B1-B3b) in STATUS + ROI report
A  7fc9655 perf(engine): numpy 1-min exit walk (Axis B · B3b) — byte-identical, completes Axis B
A  e20c8b8 perf(engine): numpy df_4h row access (Axis B · B3a) — byte-identical
A  6bab4e2 perf(engine): inject precomputed signal into backtest (Axis B · B2) — fine-TF speedup
A  6b89b22 perf(engine): vectorize decision_signals (Axis B · B1) — bit-identical, +equiv test
A  5d1945e perf(indicators): order_blocks numpy-zone rewrite (C′) — 4h 16.5→12.1s, byte-identical
A  08b8c77 perf(indicators): order_blocks sampled-overlap (E) — 4h 25.6→16.5s, byte-identical
A  d4f67c6 docs(perf): pin status + indicator incremental-recurrence research
A  f178ec3 perf(indicators): vectorize cci (A2) — 4×, bit-identical
A  1f1c29f perf(indicators): vectorize bollinger (A1) — 40×, bit-identical
A  e764482 perf(indicators): vectorize obv (D) — 64×, bit-identical
A  f9d6f36 test(perf): Phase 0 safety net — golden baselines + harness  ← rollback anchor
A  9b16a53 docs(perf): deep backtester speed-optimization study (profiled)
```
Revert any step with `git revert <sha>`; pre-optimization anchor is `f9d6f36`.

---

## 2. Workstream A — Backtester engine optimization (task #210)

**Two cost axes** (scale oppositely with timeframe): **Axis A** = 1-minute indicator compute (dominates coarse
TFs); **Axis B** = the per-decision-bar engine loop (dominates fine TFs).

### 2.1 Master timing table — full backtest per TF (recorded benchmarks)
| TF | baseline (pre-all) | post-Axis-A | post-Axis-B (final) | total Δ |
|----|-------------------:|------------:|--------------------:|--------:|
| 4h | 36.2 s | 12.1 s | **11.1 s** | **−69 %** |
| 2h | 17.9 s | 10.7 s | (golden MATCH) | ~−40 % |
| 1h | 36.1 s | 21.2 s | **15.8 s** | **−56 %** |
| 15m | 84.4 s | 43.7 s | **21.9 s** | **−74 %** |
| 5m | 113.4 s | 96.3 s | **35.2 s** | **−69 %** |
| 2m | >600 s | 269.1 s | **89.4 s** | **≥ −85 %** |

### 2.2 Axis A — indicator vectorizations (bit-identical, real 486,969-bar 1-min series)
| Step | Indicator | Before→After | Speedup | Technique |
|------|-----------|-------------|--------:|-----------|
| D | `obv` | 540→8 ms | 64× | `np.cumsum(sign(diff)·vol)` |
| A1 | `bollinger` std | 6,375→159 ms | 40× | `sliding_window_view().std()` |
| A2 | `cci` MAD | 3,567→925 ms | 4× | vectorized mean-abs-deviation |
| E | `order_blocks` sampled | (−9 s on 4h) | — | per-bar signal only at sampled indices (`signal_at`) |
| C′ | `order_blocks` numpy zones | 16.6→5.8 s | 2.8× | live zones Python-list→numpy arrays (`np.any` overlap, mask prune) |

> Numba (`C`) was **blocked** (Python 3.14 has no wheel + PEP 668) → replaced by the dependency-free C′.

### 2.3 Axis B — per-decision engine loop (byte-identical, all 6 golden TFs)
| Step | Change | Effect |
|------|--------|--------|
| B1 | vectorize `decision_signals` (numpy) + equivalence test | signal precompute **100–490×**; 0 mismatches on all 6 real TFs |
| B2 | engine reads precomputed signal (`signals=`) instead of per-bar `_stage1_candle_signal`+box `.loc` | fine TFs −36…−58 % |
| B3a | pre-extract `df_4h` Date/Close → numpy (kill per-bar `df.iloc`/`fast_xs`) | fine TFs further −14…−19 % |
| B3b | `_walk_exit_for_4h` over 1-min numpy arrays (not `iloc[lo:hi].itertuples()`) | completes Axis B |

**Scope note:** the slow `engine.SimpleStrategy` is used only by `strategy.build_payload` (dashboard + standalone
backtester); optimizer sweeps already use the vectorized `optimize/fast_engine.py`. B1's vectorized
`decision_signals` also speeds the optimizer's per-trial signal precompute.

---

## 3. Workstream B — Dashboard UX (`frontend/index.html`, commit `4fcc842`)

1. **No auto-run on profile change** — selecting a profile fills the form but does **not** run the backtester.
2. **Run button = freshness signal** — 🟢 **green** when displayed results match the form; 🔴 **red (pulsing)**
   when the form changed since the last run (set by any edit / profile pick / reset; cleared on a successful run).
3. **Reset = restore the *selected* profile's values** (undo user edits) — no longer jumps to the winner; no auto-run.

UI-only (CSS + `markDirty`/`markClean` + the strategy/reset handlers + boot); the engine and results are untouched.

---

## 4. Workstream C — Optimizer scaling + PostgreSQL deployment

### 4.1 The problem (the wsh4 incident)
One shared SQLite store (`wsh.db`) behind ~30 concurrent Optuna workers → `database is locked` →
`study.optimize` had no `catch=` → **workers died** → 4h/1h under-sampled. Root cause: *one writable file behind
thirty writers* — not the math, data volume, or memory.

### 4.2 The tiers (all parity-locked / env-unset byte-identical; Tiers 0.x pre-this-cycle, 1–4 this cycle)
| Tier | What | Key artifact |
|------|------|--------------|
| 0 | `catch=StorageInternalError` + WAL + 60 s busy_timeout + per-TF DB files | (`93a9244`, `813f9f5`) |
| **1** | centralize the store URL — SQLite↔Postgres = one env var | `optimize/storage.py` |
| **2** | watchdog/respawn + target-based idempotent runs ("reach N", not "add N") | `optimize/trial_count.py` + `run_worker` |
| **3** | observability (live COMPLETE/RUNNING/**FAIL**, JSON) + pre-flight contention smoke | `study_stats.py`, `contention_smoke.py` |
| **4** | opt-in Parquet (byte-identical) + dataset registry + capacity formula | `to_parquet.py`, `dataset_registry.py` |

### 4.3 Phase D — server rollout + Postgres cutover (live, verified; **no sweep launched**)
- push → **server parity** `$7,735/$3,670/n=66` ✅
- **PostgreSQL** `wsh-pg` (`postgres:16`, localhost `127.0.0.1:55432`, persistent volume `wsh_pg`, creds in
  `$WSI/pg.env` chmod 600; `psycopg2-binary` in venv) ✅
- **Migrated ALL 6 studies** SQLite→PG (`copy_study`): 4h 6100 · 2h 5000 · 1h 5553 · 15m 3507 · 5m 5004 · 2m 4256
  (~29k trials) ✅
- **Contention smoke 30×20 on Postgres = 0 lock deaths** — the incident scenario now passes ✅
- **Store auto-selection:** local `WSH_STORAGE_URL` → server `pg.env` → per-TF SQLite (verified live via `stats`).
- Old `wsh.db` (405 MB) kept as read-only backup.

**Future fresh run (user-triggered):** uses a **new prefix** (`wsh5`) on updated data — never append to `wsh4_*`
(old-data trials). Sequence: refresh data → `push` → `smoke 30 20` → `run 5000` → `stats` → `pull`.

---

## 4D. Workstream D — Adaptive / derived SL/TP sizing (newest, this cycle)

### 4D.1 What was built
- **ATR-multiplier SL/TP mode** in the backtester (`sltp_mode='atr'`, additive; `'fixed'` byte-identical to
  golden). Per-decision-bar multiplier scales the base SL/TP; 4h or 1-min ATR source; multiplier chart.
- **UX:** Reset/profile-load no longer leaves stale ATR fields; settings panel is drag-resizable; input boxes
  grow to show full numbers; **value boxes accept inline math** (`+ - * / ( )`, evaluated on blur/Enter/Run,
  sandboxed; invalid → red border) — see `FEATURE_inline_math_inputs.md`.

### 4D.2 The contradiction + investigation (`REVIEW_atr_sizing_contradiction.md`)
Dashboard ATR appeared to **beat** fixed (+21% on 1-min) while the prior study said ATR **shrinks** profit.
Root-caused as a **measurement artifact** across 6 confounds: in-sample window, 3× expansion band, a 14-*minute*
ATR (period-14 on the 1-min frame), and a **look-ahead** normalization ref. Controlling them collapses the 1-min
result onto fixed (172k→144k≈142k).

### 4D.3 Two expert councils (multi-agent)
- `COUNCIL_RULING_atr_sizing.md` — **6–0:** the STUDY is the valid measurement; the dashboard "+21%" is a
  confounded in-sample artifact. Fixed is champion; ATR is a drawdown knob, not a profit engine.
- `COUNCIL_RULING_reoptimization.md` — **6–0:** the deployed fixed champion needs **NO** re-optimization
  (byte-identical; every change gated to the ATR path); adopting volatility sizing **IS** a new search
  dimension requiring a fresh joint `wsh5` walk-forward.

### 4D.4 Fixes applied (R1–R3, ATR-mode only; fixed mode re-verified byte-identical)
- **R1** — normalization ref → **causal expanding mean** (no look-ahead).
- **R2** — `atr_period` default keyed to source (4h→14, 1m→240); unit surfaced in UI.
- **R3** — default clip band → **shrink-only 0.33–1.05**; warning when expansion (>1.05) is selected.

### 4D.6 REMOVED (2026-06-15): the SL/TP sizing mode (ATR multiplier)
With the dynamic/derived avenue closed (4D.2–4D.4 + the fixed-window study), the ATR-multiplier **sizing mode**
was removed from the dashboard UI and `strategy.py` — SL/TP are always FIXED now. Golden byte-match still MATCH
on all 6 TFs (fixed mode provably unchanged). The engine's neutral `sl_tp_mult` hook is KEPT for the archived
research scripts (`optimize/sub/stage2.py`), which the dashboard never triggers. Full change list:
`REMOVAL_sltp_sizing_mode.md`.

### 4D.5 Earlier plan: derived / self-recalibrating SL/TP (`ACTION_PLAN_derived_sltp.md`) — NOT adopted (closed)
Replace stale *absolute* SL/TP with a **ratio to a live driver** (`SL=k·D_t`) so nothing decays — Manual + Auto
modes, Approach A (formula) spine + Approach B (fitted policy) seam, staged: **Stage 0 feasibility** →
engine/UI → joint `wsh5` (4h pilot → all TF) → fitted policy → remove ATR mode. See `META_STAGE_adaptive_sltp.md`.

---

## 5. TECHNOLOGIES RECORD — stack + every adopt/reject decision

### 5.1 Stack in play
| Layer | Tech | Role |
|-------|------|------|
| Language / arrays | **Python 3.12 (server) / 3.14 (dev)**, **numpy 2.3**, **pandas 3.0** | engine, vectorized indicators |
| Backtest engines | `engine.SimpleStrategy` (reference, exact) + `optimize/fast_engine.py` (vectorized, parity-locked) | trades |
| HPO | **Optuna 4.8/4.9** (NSGA-III, multi-objective + constraints) | per-TF parameter search |
| Trial store | **SQLite** (default/local) → **PostgreSQL 16** (server, MVCC) | shared trial store |
| PG driver | **psycopg2-binary 2.9** (server venv) | optuna→Postgres |
| Columnar (opt-in) | **pyarrow 24** (Parquet) | faster/smaller data load (Tier 4.1) |
| Orchestration | bash `remote_wsi.sh` (rsync + SSH key-auth + setsid detached workers) | server runs |
| Container | **Docker 29.5** (`wsh-pg`, localhost-only, persistent volume) | Postgres host |
| Tests | **pytest** (183 local) + golden byte-match + parity suites | correctness gates |

### 5.2 Decisions (what was adopted, what was rejected, and why)
| Question | Verdict | Why |
|----------|---------|-----|
| Speed indicators — vectorize vs **Dask**? | **numpy vectorization** (Dask rejected) | data is 28 MB on a 123 GB box; the stall was the DB, not compute; Dask adds overhead + targets the wrong layer |
| Trial store — SQLite vs **MongoDB** vs **PostgreSQL**? | **PostgreSQL** (Mongo rejected) | Optuna doesn't support Mongo; Postgres is Optuna-native and MVCC removes the write-lock contention |
| JIT the engine loops with **Numba**? | **Rejected/blocked** | no Numba wheel for Python 3.14 + PEP 668; replaced by dependency-free numpy rewrites (C′, Axis B) |
| Data format — CSV vs **Parquet**? | **CSV default; Parquet opt-in** | Parquet faster/smaller but data-load is sub-second now; opt-in keeps the byte-identical baselines safe |
| Per-decision signal — per-bar vs **vectorized**? | **Vectorized** (`decision_signals`) | param-independent; 100–490× faster; proven bit-identical |
| Trial history on PG — **migrate** vs fresh? | **Migrated all** (`copy_study`) | preserve the full ~29k-trial record; fresh runs use a new prefix |
| Contention fix — bigger hammer vs targeted? | **Targeted store change + resilience** | "one file behind thirty writers" → fix the store (PG) + watchdog + observability, not a rewrite |

### 5.3 Deferred / not needed (recorded for honesty)
- **Dask / Ray / multi-node** — only past one machine or a >RAM dataset.
- **Numba** — until a controlled env (venv/Py with a wheel).
- **MongoDB** — only for genuinely document-shaped metadata, if it ever arises.
- **A3 (stochastic/mfi/keltner) + market_structure vectorization** — low ROI; re-validation tax (see ROI report).

---

## 6. Verification & safety posture (applies across A + C)
- **Golden baselines** — 6-TF frozen summary + trades-SHA + per-indicator vote-SHA; `perf/check_golden.py` byte-compares. **Every Axis-A/B step proven MATCH.**
- **Equivalence tests** — optimized fn == frozen `_reference` on random + adversarial inputs (Axis A; B1 signal).
- **Parity suites** — `test_parity.py` (`$7,735/$3,670/n=66`), `test_fast_parity.py`, `test_indicator_parity.py`.
- **183 pytest** locally (was 148 pre-cycle: +18 Axis-B signal, +7 storage, +3 trial_count, +3 observability, +4 data-layer, +2 migrate).
- **Server-side bash** — `bash -n` on the driver AND on the extracted generated `launch.sh`.
- **Env-unset byte-identical** — Tiers 1–4 change nothing with `WSH_STORAGE_URL` / `WSH_USE_PARQUET` unset.
- **Rollback** — one commit per step (`git revert <sha>`); Postgres reverts by `rm pg.env` (→ sqlite) + `docker rm -f wsh-pg`; engine anchor `f9d6f36`.

---

## 7. Live infrastructure state (as deployed)
- **Dashboard**: `server.py` restarted on the optimized engine (local, port 8000).
- **AMD server** (`78.89.209.212:33362`, user `dev`): hardened code in `$WSI/Parametric-Indicators`; Postgres
  container `wsh-pg` up (localhost `:55432`, volume `wsh_pg`, creds in `$WSI/pg.env`); all `wsh4_*` studies in PG;
  `wsh.db` retained as backup. `remote_wsi.sh` auto-selects the store via `pg.env`.

---

## 8. Pending / next (user-triggered)
- **Derived/adaptive SL/TP (Workstream D)** — approved action plan; **Stage 0 feasibility in progress**.
  Stage 2 is the `wsh5` joint walk-forward. See `ACTION_PLAN_derived_sltp.md` / `META_STAGE_adaptive_sltp.md`.
- **Fresh optimizer run on updated data** — new `wsh5` prefix on Postgres (sequence in §4.3). Not started by design.
- **Optional Axis-A leftovers** (A3, `market_structure`) — held (low ROI). **Tier 5** (multi-node) — deferred.
- **Optimizer search-space enhancement (candidate):** add each indicator's **mode** (confirm/veto/both) to the
  Optuna search (`_suggest_indicators`) — today mode is fixed to the schema default; everything else about the
  confirmation layer (enable, own params, K) is already searched. Widens the space → mind trial-count/overfit
  limits. See `DIAGRAM_optimizer_io.md §4d`.

---

## 9. Document index (where the detail lives)
- **Backtester (A):** `perf/MASTER_REPORT_backtester_optimization.md`, `perf/STATUS_optimization.md`,
  `perf/REPORT_optimization_roi_and_decision.md`, `perf/INVESTIGATION_axisB_per_decision_loop.md`,
  `perf/ACTION_PLAN_axisB.md`, `perf/UPDATE_step_{D,A1,A2,E,Cprime,B1,B2,B3a,B3b}_*.md`,
  `optimize/REPORT_backtester_speed_optimization.md`, `optimize/RESEARCH_indicator_recurrence_relations.md`.
- **Optimizer scaling (C):** `optimize/server/REPORT_system_scaling_study.md`,
  `optimize/server/INCIDENT_wsh4_sqlite_contention.md`, `optimize/server/MIGRATION_per_tf_db.md`,
  `optimize/server/EXPLAINER_tier1_postgres_and_history.md`, `optimize/server/ACTION_PLAN_scaling_tiers.md`,
  `optimize/server/UPDATE_tier{1,2,3,4}_*.md`, `optimize/server/UPDATE_phaseD_deploy_postgres.md`,
  `optimize/server/INCIDENT_ssh_connection_reset.md`.
- **Adaptive/derived SL/TP (D):** `META_STAGE_adaptive_sltp.md` (current-stage map), `ACTION_PLAN_derived_sltp.md`,
  `REVIEW_atr_sizing_contradiction.md`, `COUNCIL_RULING_atr_sizing.md`, `COUNCIL_RULING_reoptimization.md`,
  `optimize/sub/STUDY_sub_optimizer_*.md`, `optimize/sub/STUDY_relative_feasibility.md` (Stage 0),
  `DECISION_derived_sltp_options.md` (+ `_BABY`), `RESEARCH_fixed_vs_dynamic_sltp.md` (verified internal+external
  evidence; + `_BABY`).
- **Optimizer I/O map:** `DIAGRAM_optimizer_io.md` (neural-net-style diagram — search-space inputs, the per-bar
  decision wheel incl. the confirm/veto layer, the 3-objective+constraint scoring, NSGA-III → champion;
  confirms indicator OWN params ARE searched and the confirmation layer IS wired in; only indicator *mode* is not).
- **Market structure + split SL/TP (E, 2026-06-15):** `study_range_regime/REPORT_STREAM_2026-06-15.md` (the
  stream report), `study_range_regime/DEFINITION_BOOK.md` (ICT concept definitions: LL/HL/HH/LH, FVG/IFVG, order
  block, breaker, CISD, golf=engulfing — user-def vs standard vs project-impl), `study_range_regime/range_registry.py`
  (per-M/Q/Y high/low + new/repeat band machine; trend = relative HH/LL per `REPORT_Q5_trend_rule.md`),
  `study_range_regime/structure_tables.py` (LL/HL/HH/LH swing tables + IFVG/breaker/CISD events),
  `study_range_regime/regime_charts.py` (ribbon/structure/band charts). **Engine:** 4 new causal detectors in
  `indicators/smc.py` (`swing_labels`, `ifvg`, `breaker_blocks`, `cisd`); **split long/short SL/TP threaded**
  through `fast_engine`/`core`/`optimizer` (`split_sltp` flag) / `build_payload` — defaults = shared champion ⇒
  golden 6/6 + fast-parity (T4) preserved (`study_range_regime/UPDATE_E2_split_threading.md`,
  `NEXT_OPTIMIZER_NOTES.md`). **Dashboard (E3, `study_range_regime/UPDATE_E3_dashboard_split_sltp.md`):** the
  backtester dashboard now exposes split SL/TP via an "SL/TP mode" dropdown (shared | split long/short) atop the
  value-box container + 6 per-side boxes in `frontend/index.html` (split mode hides the shared boxes; shared mode ⇒
  all `null` ⇒ byte-identical to a normal run; blank per-side box ⇒ falls back to shared),
  with split bounds added to `server.py` `/api/config`. The 3 new vote indicators (`ifvg`/`breaker`/`cisd`) were
  already three-way synced via the schema-driven indicator panel. Engine⇄optimizer⇄dashboard now share one input
  set (verified: golden 6/6, split-OFF≡plain, split-ON diverges). Q1 split sweep (`split_sltp_sweep.py`,
  `REPORT_Q1_split_sltp.md`): no asymmetric edge — symmetric champion wins; wsh5 free search pinned. Entry-rule
  plan: `PLAN_entry_rules.md`.
- **Optimizer superset paradox + FULL system breakdown (2026-06-15):**
  `study_range_regime/REPORT_optimizer_superset_paradox_and_system_breakdown.md` — answers "how can a LARGER
  search space (wsh5 split SL/TP) return a WORSE champion than wsh4?". Proven empirically on the live studies:
  wsh4's champion is a point inside wsh5's space scoring the SAME $33,592 (re-evaluated), but wsh5's best-ever
  sample over all 5028 trials was only $28,228 — NSGA-III is a finite-budget *stochastic* search, +6 dims
  enlarged the volume with fewer trials (5028<5483), and only 0.2 % of trials stayed near-symmetric. Includes a
  block-by-block system breakdown (data→HAR-RV→box→indicators→engine→metrics→walk-forward→NSGA-III→champion→
  dashboard) with inputs/inner-layers/outputs + file:line, the two champions' exact values, and the warm-start
  fix (enqueue the known champion ⇒ guaranteed equal-or-better next run).
- **Optimizer hardening — warm-start + dimension-proportional budget + acceptance gate (2026-06-15):**
  `optimize/optimizer.py` now warm-starts known champions as the first trials (`warm_start_seeds` →
  `study.enqueue_trial`, default ON) so the returned front is provably ≥ the prior champion (verified: the seed
  reproduces $142,203 full P/L); `search_dims`/`recommended_trials` + CLI `--auto-trials`/`--trials-per-dim`/`--plan`
  scale trials ∝ dimensions; `optimize/server/remote_wsi.sh` `run` reports the plan and requires acceptance
  (`WSH_CONFIRM=1` to skip), with a new `plan` subcommand. Algorithm-alternatives research (two-stage decomposition,
  CMA-ES/GP-BO, MAP-Elites): `study_range_regime/REPORT_optimizer_algorithm_alternatives.md`. **All report visuals
  are Mermaid (never ASCII art)** per standing instruction.
- **Optimizer ALGORITHM workstream P2→P4 (2026-06-16, IN-PROGRESS):** applying the algorithm-alternatives report
  one-by-one. **LIVE tracker:** `study_range_regime/WORKSTREAM_optimizer_algorithm_hardening_TRACKER.md` (read first
  when resuming; has the P3-proof RESUME PROTOCOL).
  - **P2 — selectable sampler ✅:** `optimize/optimizer.py` `make_sampler()` + `--sampler {nsga3*|nsga2|tpe|motpe|gp|cmaes}`;
    default `nsga3` ⇒ byte-identical; GP uses native `GPSampler` (no BoTorch); `cmaes` guarded to single-obj.
    Lock `optimize/test_sampler_factory.py` (6/6). Doc `study_range_regime/UPDATE_P2_selectable_sampler.md`.
  - **P3 — two-stage decomposition 🟡 (code+doc done, full 4h proof running):** `optimize/two_stage.py` —
    Stage A (discrete indicator-set pick, NSGA-III) → Stage B (continuous knob tuning per subset, `--stage-b
    {cmaes|gp}`); warm-start guarantees ≥ wsh4. New dep `cmaes==0.13.0`. Doc
    `study_range_regime/UPDATE_P3_two_stage_decomposition.md`.
  - **P4 — MAP-Elites quality-diversity archive ✅:** `optimize/map_elites.py` — keeps the best solution PER
    NICHE (worst-DD × #indicators), so it cannot collapse into one basin and yields a PORTFOLIO (safe /
    high-return / few-indicator). Champion-seeded ⇒ archive provably ≥ wsh4. 4h proof: 16 niches filled,
    portfolio confirmed (best-return median $36k @ higher DD; safest $5.4k-DD; simplest 5-ind). Lock
    `optimize/test_map_elites.py` (5/5). Doc `study_range_regime/UPDATE_P4_map_elites_archive.md`.
    **Algorithm-hardening workstream COMPLETE (P0/P2/P3/P4); P1=wsh6 launch is the user's operational call.**
- **Optimizer Control & Visualization Dashboard (2026-06-16, BUILT local; deploy-time steps remain):**
  `optimize/dashboard/` — hybrid: **optuna-dashboard** (prebuilt, reads `wsh-pg`) for live Pareto/trials +
  a **FastAPI control plane** (`app.py`: config/plan/run/stop/resume/status/SSE-log/bundle) + a **Telegram
  bot** (`bot.py`: notify+control, chat-id allowlist), all sharing one **`control.py`** seam that wraps
  `remote_wsi.sh` + reads Postgres. VPN-served (bind private IP only; full-tunnel `kw-full.ovpn`). Pause=stop;
  data-pull = server-built `.tar.gz` (full pg_dump | lite) download. Spec/Plan/Tracker/UPDATE docs under
  `optimize/dashboard/`. **26 tests green (control 10 + app 9 + bot 7); golden 6/6 unchanged.** Remaining:
  deploy on the AMD server (confirm VPN bind IP) + server smoke + (later) docker-compose.
- **STAGE REPORT (2026-06-16) — optimizer hardening + dashboard:** `STAGE_REPORT_optimizer_hardening_and_dashboard.md`
  consolidates this whole stage (algorithm P2→P4 + the dashboard) with evidence, status board, and the held
  next actions (#3 two-stage launch wiring → #2 deploy). First committed at `25942eb`.
- **Strategy refinement — S0 no-entry metric + β indicator ablation (2026-06-16):** `optimize/no_entry.py`
  (warmup-vs-decision-attributed no-entry-streak; additive `backtest_metrics` keys, golden 6/6 unchanged) +
  `optimize/ablate_indicators.py` (exhaustive 256-subset ablation of the wsh4 1-min 4h champion, parallel,
  full-period). **Findings** (`study_range_regime/UPDATE_S0_beta_no_entry_and_ablation.md` +
  `REPORT_indicator_ablation_wsi1m_4h.md`): the worst pause is **11.5d, decision-sourced** (0/256 subsets get
  <3d ⇒ needs α); and keeping just **cci+order_block+structure_trend** (drop 5) gives **+5.5% P/L
  ($149,989) at half the data footprint (346→138)** — caveat: full-period only, re-check on folds/OOS before
  deploying. Tests: `test_no_entry_metric.py` (4) + `test_ablate.py` (4). α (#227) held + now well-motivated.
- **Backtester dashboard — warmup/footprint cards + responsive metric row (2026-06-16):** new
  `POST /api/warmup` (single source of truth = `library.warmup_bars()`) drives two LIVE cards in the main
  metric row beside "longest no-entry streak" — **warmup period** + **longest indicator candles requirement**
  (champion → 346 candles / SMA trend) — recomputing on any indicator change/preset import. `.cards` switched
  to `repeat(auto-fit, minmax(150px,1fr))` so the metric row wraps into rows instead of overflowing. Golden
  6/6 untouched. Doc `study_range_regime/UPDATE_dashboard_warmup_boxes_and_responsive_cards.md`.
- **This file** is the top-level index over all of them.
