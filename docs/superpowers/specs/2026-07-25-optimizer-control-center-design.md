# Design: Optimizer Control Center (v2 dashboard)

**Date:** 2026-07-25
**Issue:** #22 (epic) · **Branch/worktree:** TBD at implementation (own worktree)
**Status:** Approved design → writing-plans
**Extends:** the deployed v1 optimizer-dashboard (`optimize/dashboard/`).

---

## 0. Goal
A GUI to **fully drive and report the optimizer**, replacing terminal use — configure every run
parameter, launch/stop/resume, watch live progress + Pareto + scatter, and browse a champion
leaderboard with full drill-down reports. Server-hosted, VPN-reachable (same access model as v1).

## 1. What already exists (reuse, don't rebuild)
`optimize/dashboard/` (deployed on AMD `192.168.50.62`): a **FastAPI control plane** (`app.py`+`control.py`,
:8350) exposing `/api/{config,plan,run,resume,stop,status,progress(SSE),bundle}`; it drives the optimizer
via `remote_wsi.sh` (`run`/`stop`/`stats --json`/`pull`), maps a `cfg` dict → optimizer env/args, and
builds a downloadable data bundle. Viz is delegated to **optuna-dashboard** (:8082, reads `wsh-pg`).
A **Telegram bot** (`bot.py`) notifies+controls. Access = full-tunnel VPN, private-IP bind only
(spec §3.0 of `SPEC_optimizer_dashboard.md`).

**v2 reuses:** the control plane process, `control.py` functions, `remote_wsi.sh`, optuna-dashboard, the
bundle download, the VPN access model, the Telegram bot.
**v2 adds:** a rich **Vue SPA** frontend (replaces the basic static page), indicator/family + reference +
K-cap selection, live custom charts, a **champion leaderboard + report** panel, a **run queue/matrix**,
**one-click adopt-gate**, **saved presets + provenance**, **compare + Pareto drill-down**, and baseline
**health / budget-guard / notifications**.

## 2. Approved decisions (2026-07-25)
| # | Decision | Choice |
|---|---|---|
| A1 | Frontend | **New Vue+Vite SPA** served by the FastAPI control plane (matches `trading/frontend` stack) |
| A2 | Live figures | **Both** — custom in-panel Pareto + scatter (+history/param-importance); **"Open optuna-dashboard ↗"** for deep dives |
| A3 | Champion source | **Champion JSON** (`best_champions_full[_<inst>].json`) + a **deployed flag registry**; "read more" **regenerates** the full bundle report on demand |
| A4 | Rollout | **Phased MVP-first** — P1 settings+control+progress/ETA · P2 live figures · P3 leaderboard+reports |
| A5 | Extra features | **All four** (run queue/matrix, one-click adopt-gate, saved presets+provenance, compare+drill-down) + baked-in health/budget/notifications |
| A6 | Access | **Unchanged** — VPN-only, private-IP bind (inherit v1 §3.0) |

## 3. Architecture
```
Vue SPA (served by FastAPI)  ──HTTP/SSE──►  FastAPI control plane (:8350, control.py)
       │                                          │
       │  "Open optuna-dashboard ↗"               ├─ remote_wsi.sh → optimizer workers + watchdog
       ▼                                          ├─ wsh-pg (optuna studies: trials, Pareto)
  optuna-dashboard (:8082) ◄── reads ── wsh-pg    ├─ best_champions_full[_<inst>].json (+ deployed registry)
                                                  └─ report regen (backtest_metrics + bundle format)
```
Three panels in the SPA: **Control**, **Settings**, **Reporting**. All read/write the control plane over
JSON; live data over SSE (`/api/progress`, new `/api/live/*`).

## 4. Panels

### 4.1 Control panel
- **Start / Stop / Resume** (existing `/api/{run,stop,resume}`; stop = lossless pause per v1 D3).
- **Progress bar**: trials done / target, per queued study; source = optuna study `len(trials)` vs target
  (new `/api/live/progress` aggregating `stats --json` + study counts).
- **Live ETA**: `remaining / trailing_trial_rate` (rate = Δtrials/Δt over the last polls), recomputed each
  poll; also feasible-Pareto count and elapsed.
- **Live log tail** (existing SSE) with a filter (all / errors / pruned / feasible).
- **Health strip** (baked-in): server CPU/mem, worker count, DB size, active study count.

### 4.2 Settings panel — every run parameter, each as **auto / manual / custom** where applicable
- **Indicators:** searchable 165-key list with **family group checkboxes** (the `lib_<school>` families:
  ma, oscillators, trend, volatility, volume, levels, bill-williams, quant, dsp, cross-series). Select
  individuals and/or whole families → `--only-indicators` / `--exclude-indicators`. Requires `schema()` to
  emit a **`family`** tag per indicator (small addition).
  - **K-cap** (`--max-enabled`) and **cross-series reference** (`--reference`, #17) selectors.
- **Instruments** (multi-select) × **Timeframes** (multi-select) → the run **matrix**.
- **Trials mode:** auto (∝ dims) · one count for all · per-(instrument,tf) counts.
- **Start mode:** cold · **warm-start from a champion** (chosen from the leaderboard).
- **Indicator frame:** 1-minute vs decision-TF (`ind_1min`). **Sampler/engine** (single/two-stage),
  **split-SL/TP**, **dd-cap** — all exposed.
- **Config → command preview:** renders the exact `remote_wsi.sh`/optimizer CLI a config maps to
  (transparency + copyable) — reuses `/api/plan`.
- **Budget guard** (baked-in): optional max-trials / max-wallclock auto-stop.
- **Saved presets + provenance:** name/save a config; every launched run stores its exact config+command
  (reproducibility), surfaced later on the champion.

### 4.3 Reporting panel
- **Live sub-panel:** custom **Pareto** (obj0 median-PnL vs obj1 −worst-DD, updates as trials land),
  **scatter** (colored feasible/infeasible via the DD≤25%·PnL constraint), trial-history + param-importance;
  data from a new `/api/live/study` (reads `wsh-pg`). **"Open optuna-dashboard ↗"** deep-dive link.
  **Pareto drill-down:** click a point → its config + **[backtest ↗]** into the main dashboard (:8200).
- **Final-report sub-panel:** **champion leaderboard** from `best_champions_full[_<inst>].json` — sortable
  columns (instrument, tf, full_pnl, full_dd, median_pnl, win, #indicators, deployed?). Row → **summary
  card**; **"read more"** → **regenerates the full champion-bundle report** (the format submitted since the
  bundles) via `backtest_metrics` + the report builder. **Deployed** badge from a small
  `champions_deployed.json` registry. **Compare:** select 2+ → side-by-side metrics + overlaid equity curves.
- **One-click adopt-gate:** on the top champion, launch the mandatory gate (baseline / dumb / noise / OOS +
  power, per #14) and show the verdict here.

## 5. Data sources & new control-plane endpoints
- Reuse: `/api/{config,plan,run,resume,stop,status,progress,bundle}`.
- New: `/api/live/progress` (aggregate trials/target/rate/ETA), `/api/live/study` (Pareto+scatter+history
  arrays from `wsh-pg`), `/api/champions` (leaderboard rows), `/api/champions/{id}/report` (regen full
  report), `/api/champions/{id}/deploy` (toggle deployed flag), `/api/presets` (CRUD), `/api/queue`
  (batch matrix launch + status), `/api/adopt_gate` (launch gate on a champion).
- `schema()` gains a `family` per indicator.

## 6. Rollout (phased — each = a sub-issue → PR)
- **P1 — Control + Settings + Progress/ETA** (replaces terminal launching): Vue SPA scaffold, control
  panel (start/stop/resume, progress bar, live ETA, health), full settings panel (indicators+families,
  instruments×tf matrix, trials modes, warm/cold, 1min, sampler, reference, K-cap, command preview,
  presets), run queue/matrix, budget guard, notifications.
- **P2 — Live figures:** custom Pareto + scatter + history/param-importance, SSE-updated; optuna deep-dive
  link; Pareto drill-down → backtest.
- **P3 — Champion leaderboard + reports:** leaderboard, deployed registry, report regen, compare, one-click
  adopt-gate.

## 7. Non-goals (v2)
- No public-internet exposure (VPN only; inherit v1). No new auth beyond VPN + Telegram allowlist.
- No optimizer-engine change (golden byte-identical). Pause stays stop-as-pause.
- No [method]/[data] indicator work (separate epics).
- Not consumer-polished — developer-mode UI is fine (per v1).

## 8. Success criteria
1. A full optimization run (choose indicators/families + instruments×tf + trials + warm/cold + reference)
   can be configured, launched, watched (progress+ETA+Pareto+scatter), and stopped — **entirely from the UI**,
   no terminal.
2. Champion leaderboard lists all champions from the JSONs with deployed badges; "read more" regenerates the
   full bundle report; compare + Pareto drill-down work.
3. Run queue launches an instruments×timeframes matrix in one action.
4. One-click adopt-gate runs the #14 controls on a champion and reports the verdict.
5. Golden 6/6 + full indicator parity unaffected; VPN-only bind preserved.
