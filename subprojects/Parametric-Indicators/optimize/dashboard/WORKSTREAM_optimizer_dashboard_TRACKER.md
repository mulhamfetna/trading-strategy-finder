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
| **Implementation (P-A…P-E, local)** | ✅ BUILT & tested (26 tests green; golden 6/6) | `control.py`/`app.py`/`bot.py`/`static/index.html`/`run_dashboard.sh`; doc `UPDATE_optimizer_dashboard.md` |
| **Deploy (P-A.3 + server smoke) + P-F compose** | ⬜ deploy-time (needs AMD server over SSH) | see UPDATE doc §4 |

Task: **#224 DASH** (pending). Decisions locked: hybrid · VPN-served · stop-as-pause · full Telegram bot ·
containerize-later · FastAPI · bundle both-modes. Access = full-tunnel VPN (verified, §3.0 of spec).

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
