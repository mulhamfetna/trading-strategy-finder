#!/usr/bin/env bash
# Control-plane-ONLY launcher (the FastAPI app that serves the SPA + drives the owned optimizer runs).
# Deliberately does NOT start optuna-dashboard or the Telegram bot (run_dashboard.sh does that, and would
# clash on :8081). This is what the systemd unit (wsh-control-plane.service) execs, so the control plane
# survives reboots + auto-restarts. Reads optimize/dashboard/dashboard.env (gitignored) for bind IP + env.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HERE/dashboard.env"
[ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE (copy dashboard.env.example)"; exit 1; }
set -a; source "$ENV_FILE"; set +a
: "${REMOTE_VENV:?set REMOTE_VENV in dashboard.env}"
cd "$HERE/../.."                                    # Parametric-Indicators root (import base + child cwd)
exec "$REMOTE_VENV/bin/uvicorn" optimize.dashboard.app:app \
  --host "${DASH_BIND_IP:-127.0.0.1}" --port "${DASH_CONTROL_PORT:-8350}"
