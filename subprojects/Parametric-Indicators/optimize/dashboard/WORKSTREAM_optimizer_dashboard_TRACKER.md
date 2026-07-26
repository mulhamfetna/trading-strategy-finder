---
name: workstream_optimizer_dashboard_tracker
description: "LIVE tracker for the optimizer-dashboard workstream (hybrid optuna-dashboard + FastAPI control plane + Telegram bot, VPN-served). Spec + plan DONE; implementation NOT started (held by user). Read first when resuming."
metadata:
  type: project
  workstream: optimizer-dashboard
  status: PLANNED (implementation on hold)
  date: 2026-06-16
---

# 🧭 WORKSTREAM TRACKER — Optimizer Control & Visualization Dashboard

## 🆕 Control Center v2 — P1 (control + settings + progress/ETA) — issues #22 (epic) / #23 (P1)
**Branch `feat/optimizer-control-center` (off dev@247afd7). Design + plan in `docs/superpowers/{specs,plans}/2026-07-25-optimizer-control-center-*`.**

P1 replaces terminal launching with a Vue SPA served by the FastAPI control plane. Status by phase:
- **A (backend)** ✅ schema `family` tag · cfg→CLI wiring (only/exclude/reference/K-cap/instrument/tf/ind-frame/cold) · `/api/live/progress`+ETA · `/api/presets` · `/api/queue` (+`max_trials` budget clamp) · `/api/health`.
- **B (scaffold)** ✅ `web/` Vite+Vue3, 3-column shell, `api.js`+reactive `store.js`, mounted at `/` (StaticFiles) below `/api/*`; `run_dashboard.sh` builds first.
- **C (control)** ✅ start/resume/stop · progress bar + live ETA · health strip · SSE log tail (filterable).
- **D (settings)** ✅ indicator+family picker · instruments×tf matrix · trials three-way + knobs · command preview (`/api/plan` returns the exact `optimizer.py` command) · presets UI · queue + budget guard.
- **E (integration)** ⏳ guardrails (golden 6/6 · parity 4h · VPN-bind) + user-run live acceptance over VPN.

Guardrails: **no scoring-engine change** — additions are dashboard/control/config/queue only. `optimize/dashboard/` unit suite = 49 green. Live acceptance (real launch over VPN + screenshot) is the user's step; click-path in the #23 PR body.
P2 (live figures) + P3 (leaderboard/reports/adopt-gate) are separate plans under epic #22.

---


> **READ FIRST WHEN RESUMING.** Single source of truth for this workstream. Spec + plan are written; the
> user explicitly **held implementation**. Do not write dashboard code until the user says go.

**Goal:** VPN-reachable, server-hosted dashboard to configure/launch/stop/pause the optimizer, watch live
trials + Pareto (optuna-dashboard), pull full data as a download, control/notify over Telegram.

## 📊 STATUS BOARD
| Item | Status | Artifact |
|---|---|---|
| Brainstorm (deep analysis + prebuilt-tool research) | ✅ done | findings in chat; optuna-dashboard chosen for viz |
| **Spec** | ✅ done | `optimize/dashboard/SPEC_optimizer_dashboard.md` |
| **Implementation plan** | ✅ done | `optimize/dashboard/PLAN_optimizer_dashboard.md` |
| **Implementation (P-A…P-E, local)** | ✅ BUILT & tested (27 tests green; golden 6/6) | `control.py`/`app.py`/`bot.py`/`static/index.html`/`run_dashboard.sh`; doc `UPDATE_optimizer_dashboard.md` |
| **#3 Two-stage launch wiring** | ✅ DONE (2026-06-17) | `remote_wsi.sh two-stage <tfs>` (detached, non-watchdog) + `control.start` engine branch + new test; UPDATE §3 resolved |
| **#2 Deploy on AMD server (P-A.3)** | ✅ LIVE (2026-06-17) on `192.168.50.62` — control:8350 optuna:8082 + bot; local-mode `remote_wsi.sh` | UPDATE doc §4 |
| **#2b final smoke (real run) + P-F compose** | ⬜ deferred (needs operator go-ahead + fresh prefix) | UPDATE doc §5 |

Task: **#224 DASH** (in progress). Decisions locked: hybrid · VPN-served · stop-as-pause · full Telegram bot ·
containerize-later · FastAPI · bundle both-modes. Access = full-tunnel VPN (verified, §3.0 of spec).

**Committed `25942eb` (2026-06-16).** Full stage report: `../../STAGE_REPORT_optimizer_hardening_and_dashboard.md`.
**NEXT: #2 — deploy on AMD server (P-A.3 confirm VPN bind IP + server smoke), then P-F compose.** (#3 two-stage
wiring DONE — uncommitted on `dev`, awaiting the user's commit go-ahead.)

## ▶️ WHEN IMPLEMENTATION IS UNHELD — resume protocol
1. Decide execution mode (writing-plans handoff): **subagent-driven** (recommended) or **inline executing-plans**.
2. Execute the plan phase-by-phase: **P-A** (optuna-dashboard live + confirm bind IP) → **P-B** (control.py +
   remote_wsi.sh env + FastAPI) → **P-C** (web UI) → **P-D** (bundle, folded into B7/B9/C3) → **P-E** (bot) →
   **P-F later** (compose).
3. After EACH phase: tests green + `perf/check_golden.py` 6/6 (B1 touches remote_wsi.sh — additive) + verbose
   Mermaid doc + update this tracker.
4. **P-A FIRST ACTION:** on the server, confirm the private bind IP reachable from the phone over VPN
   (LAN `private_ip` vs OpenVPN tun IP); record it here.

## 🔑 KEY FACTS / GOTCHAS
- Optimizer persists to **Postgres `wsh-pg`** (`127.0.0.1:55432`); optuna-dashboard reads it directly.
- Launch/stop via **`remote_wsi.sh`** (`run`/`stop`/`stats --json`/`pull`); detached `setsid` workers + watchdog.
- **Pause = stop** (lossless; watchdog resumes target−completed). No optimizer-engine change.
- **Bind private-only, never `0.0.0.0`/public** — full-tunnel VPN makes private IP reachable only when connected.
- **Secrets:** `SERVER_DATA.env` already holds `telegram_bot_token` + OpenVPN creds — gitignored, NEVER staged.
  Dashboard reads token from env / gitignored `dashboard.env`.
- New deps to install on the server venv: `fastapi uvicorn python-telegram-bot optuna-dashboard` (+`cmaes` from P3).
- Everything UNCOMMITTED on `dev` (standing rule: commit only when asked).

## 🔗 RELATED
Sibling workstream: `study_range_regime/WORKSTREAM_optimizer_algorithm_hardening_TRACKER.md` (P2✅ P3✅ P4 pending).
The dashboard exposes that work: sampler picker (P2) + engine single/two-stage (P3) live in the config panel.
