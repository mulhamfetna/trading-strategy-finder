#!/usr/bin/env bash
# optuna-dashboard launcher (live Pareto / optimization history / param importance for every study).
# Reads the SAME Postgres the optimizer writes to. Bound to DASH_BIND_IP (localhost/VPN, never public).
# Run by wsh-optuna-dashboard.service so it survives reboots. Reads optimize/dashboard/dashboard.env.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HERE/dashboard.env"
[ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE (copy dashboard.env.example)"; exit 1; }
set -a; source "$ENV_FILE"; set +a
: "${REMOTE_VENV:?set REMOTE_VENV in dashboard.env}"
: "${WSH_STORAGE_URL:?WSH_STORAGE_URL unset (dashboard.env should source pg.env)}"
exec "$REMOTE_VENV/bin/optuna-dashboard" "$WSH_STORAGE_URL" \
  --host "${DASH_BIND_IP:-127.0.0.1}" --port "${DASH_OPTUNA_PORT:-8082}"
