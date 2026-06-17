---
name: update_optimizer_dashboard
description: "Optimizer Control & Visualization Dashboard — BUILT (P-A…P-E local; deploy + P-F remain). Hybrid: optuna-dashboard for live Pareto/trials + a FastAPI control plane + a Telegram bot, all sharing one control.py seam, VPN-served. 26 unit/API/bot tests green; golden 6/6 unchanged."
metadata:
  type: project
  workstream: optimizer-dashboard
  status: BUILT (local) — deploy-time steps remain
  date: 2026-06-16
---

# Optimizer Control & Visualization Dashboard — build report

> Spec: `optimize/dashboard/SPEC_optimizer_dashboard.md` · Plan: `PLAN_optimizer_dashboard.md` ·
> Tracker: `WORKSTREAM_optimizer_dashboard_TRACKER.md`.

## 1. What was built (P-A…P-E)

```mermaid
flowchart TB
    subgraph CLIENT["📱/💻 on VPN"]
        BR["browser"]; TG["Telegram"]
    end
    subgraph SRV["🖥 server (bind = private/VPN IP only)"]
        OD["optuna-dashboard :8081<br/>live Pareto + trials (prebuilt)"]
        APP["app.py (FastAPI) :8350<br/>config/plan/run/stop/resume/status/<br/>progress(SSE)/bundle + static UI"]
        BOT["bot.py (python-telegram-bot)<br/>long-poll · allowlisted"]
        CTL["control.py — single seam"]
        RW["remote_wsi.sh (now reads WSH_SAMPLER)"]
        PG[("wsh-pg Postgres")]
    end
    BR --> OD
    BR --> APP --> CTL
    TG <--> BOT --> CTL
    CTL --> RW --> PG
    OD --> PG
    APP -. links .-> OD
    style OD fill:#13241a,stroke:#00c853,color:#fff
    style APP fill:#1a3a5a,stroke:#2962ff,color:#fff
    style BOT fill:#3a2f10,stroke:#ff9800,color:#fff
    style CTL fill:#2a1a3a,stroke:#9c27b0,color:#fff
```

| Phase | Built | Files | Tests |
|---|---|---|---|
| **P-A** | deps + launcher + env template + gitignore | `requirements.txt`, `run_dashboard.sh`, `dashboard.env.example`, `.gitignore` | deps import OK |
| **P-B** | control seam + `remote_wsi.sh` `--sampler` + FastAPI API | `control.py`, `app.py`, `remote_wsi.sh` | `test_control.py` 10/10 · `test_app.py` 9/9 |
| **P-C** | control web UI (vanilla, cloned theme/math/fetch patterns) | `static/index.html` | live uvicorn serve HTTP 200; TestClient `/` |
| **P-D** | data bundle (full \| lite) build + download | `control.build_bundle`, `app.py` `/api/bundle` | covered in `test_app.py` |
| **P-E** | Telegram bot (notify + control, allowlist) | `bot.py` | `test_bot.py` 7/7 |

**Total: 26 dashboard tests green; golden 6/6 unchanged** (the only engine-adjacent change — `remote_wsi.sh`
`--sampler` — is additive/default-off, verified unset→unchanged).

## 2. Key behaviors (as built)
- **`control.py` is the single seam**: `_run_remote` wraps `remote_wsi.sh`; everything else (config/plan/
  start/stop/resume/status/tail_logs/follow_logs/build_bundle) is pure + mockable. The API and bot are thin.
- **Pause = stop** (`/api/stop` → `remote_wsi.sh stop`); **Resume** relaunches (watchdog continues target−completed).
- **Sampler picker (P2)** flows via `WSH_SAMPLER` → `remote_wsi.sh --sampler` (default unset ⇒ nsga3 unchanged).
- **Engine picker**: `engine=single` → `remote_wsi.sh run` (NSGA-III watchdog path); **`engine=two_stage`
  (P3) → `remote_wsi.sh two-stage <tfs>`** — a separate detached, **non-watchdog** launch (two-stage runs
  finite in-memory studies with no trial-count target, so it is launched once with no respawn; stage-B/
  trials/top-K tunable via `WSH_STAGE_B`/`WSH_STAGE_A_TRIALS`/`WSH_STAGE_B_TRIALS`/`WSH_TOP_K`).
- **Plan preview** gates the Start button (must POST `/api/plan` first → dims → recommended trials).
- **Live log** via SSE (`/api/progress?tf=`); **status cards** poll `/api/status` (`stats --json`).
- **Data bundle**: server builds `.tar.gz` (full = +`pg_dump`; lite = results+logs+Pareto), browser downloads.
- **Telegram**: `/status /stop /resume /pull`, **chat-id allowlist** enforced; `new_champions()` diff drives alerts.
- **VPN-only**: `run_dashboard.sh` binds every service to `DASH_BIND_IP` (private), never `0.0.0.0`.

## 3. Deviations from the plan (and why)
- ~~**Two-stage engine NOT routed through `remote_wsi.sh`**~~ — **RESOLVED (2026-06-17, follow-up #3).** Added a
  dedicated `remote_wsi.sh two-stage <tfs>` command: a detached, **non-watchdog** launch of
  `python3 -m optimize.two_stage` per TF (one finite run, no respawn — the watchdog's trial-count target
  doesn't apply to two-stage's in-memory studies). `control.start()` now branches on `engine`: `single` →
  `run`, `two_stage` → `two-stage`. `cmd_stop` kills both. New test
  `test_start_two_stage_routes_to_two_stage_cmd` (27 dashboard tests total); golden 6/6 unchanged (additive).
  Note: two-stage still does NOT surface in optuna-dashboard (in-memory studies) — progress is the per-TF log
  the SSE already tails; the final champion prints at the end of that log.
- **Per-task commits skipped**: per the standing "commit only when asked" rule — all work is uncommitted on `dev`.

## 4. DEPLOYED on the AMD server (2026-06-17) — P-A.3 done

> **Current operational state:** deploy verified, then **all three instances STOPPED** (no idle processes
> left on the box). Relaunch on demand with `bash optimize/dashboard/run_dashboard.sh` (§6). `dashboard.env`
> persists server-side (gitignored) so relaunch needs no reconfiguration.

Live on the AMD box (`192.168.50.62`, VPN-reachable; the public IP forwards only SSH):
- **Deps** installed into `REMOTE_VENV`: `fastapi uvicorn python-telegram-bot optuna-dashboard cmaes`.
- **`dashboard.env`** (gitignored, server-side): `DASH_BIND_IP=192.168.50.62`, `WSH_STORAGE_URL` from `pg.env`,
  `WSH_LOGS_DIR=$WSI/logs`, token from `SERVER_DATA.env`, allowlist = the operator's chat id, **`WSH_LOCAL=1`**.
- **Ports:** control **8350**, optuna **8082** (NOT spec's 8081 — taken by the `searxng` container). Both bind
  the **private IP only**, never `0.0.0.0`.
- **Processes:** `run_dashboard.sh` launches all three `setsid`-detached (survive SSH disconnect). Verified:
  `/api/config`, `/api/status` (real JSON: `wsh4_4h` 5483 complete), `/api/stop` ok; bot replies to
  `/status /stop /resume /pull` (allowlist enforced; `/pull` built a lite bundle).

**Deploy-time fixes (found during the server smoke, all golden-6/6-safe — `remote_wsi.sh` only):**
1. **Local mode (`WSH_LOCAL=1`)**: the control plane runs ON the server, so `remote_wsi.sh` must run commands
   locally instead of SSHing back to itself (the laptop's `server.env` + key aren't on the box). Added a
   `WSH_LOCAL` branch to `srv()` (runs `bash -c` locally) + tolerant `server.env` sourcing (REMOTE_VENV then
   comes from `dashboard.env`).
2. **`stats --json` not forwarded**: `control.status()` parses JSON but the `stats)` dispatch dropped the
   `--json` flag → human table → "no studies". Fixed: `stats) shift; cmd_stats "$@"` + `cmd_stats` forwards `$*`.
3. **`pkill` self-match**: `cmd_stop`'s pattern matched its own `bash -c` argv in local mode and SIGTERM'd
   itself → `/api/stop` "Terminated". Fixed with the `[o]` bracket trick (safe in both local + SSH modes).

## 5. Remaining
- **Server smoke (final leg):** start a *real* tiny run from the UI (NEW prefix per the rule) → watch trials in
  optuna-dashboard → Pause/Resume → download the full bundle + `pg_restore` locally → confirm a champion alert.
  Deferred — starting a run is heavy + needs the operator's go-ahead and a fresh study prefix.
- **Persistence across reboot / P-F:** processes are `setsid`-detached (survive disconnect) but not a service;
  docker-compose or a systemd unit for one-command redeploy is the remaining P-F item (spec D5).

## 6. How to launch (on the server)
```bash
cp optimize/dashboard/dashboard.env.example optimize/dashboard/dashboard.env   # fill bind IP, storage URL, bot token
bash optimize/dashboard/run_dashboard.sh        # optuna-dashboard :8081 + control :8350 + bot
# phone on VPN → http://<DASH_BIND_IP>:8350 (control)  ·  :8081 (live graphs)
```
