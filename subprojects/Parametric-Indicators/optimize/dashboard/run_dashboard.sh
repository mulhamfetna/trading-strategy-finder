#!/usr/bin/env bash
# Launch the three dashboard processes bound to the private/VPN IP. Run on the server.
# Reads optimize/dashboard/dashboard.env (gitignored). NEVER bind to 0.0.0.0/public — VPN-only by design.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HERE/dashboard.env"
[ -f "$ENV_FILE" ] || { echo "missing $ENV_FILE (copy dashboard.env.example)"; exit 1; }
set -a; source "$ENV_FILE"; set +a
: "${DASH_BIND_IP:?set DASH_BIND_IP in dashboard.env}"
: "${WSH_STORAGE_URL:?set WSH_STORAGE_URL in dashboard.env}"
echo "binding dashboard to $DASH_BIND_IP (control:${DASH_CONTROL_PORT:-8350} optuna:${DASH_OPTUNA_PORT:-8081})"

# 1) optuna-dashboard (live graphs/Pareto) — reads the same Postgres the optimizer writes to
optuna-dashboard "$WSH_STORAGE_URL" --host "$DASH_BIND_IP" --port "${DASH_OPTUNA_PORT:-8081}" \
  > "$HERE/optuna_dashboard.log" 2>&1 &
echo "optuna-dashboard pid $!"

# 2) control plane (FastAPI) — config/run/stop/resume/status/progress/bundle
( cd "$HERE/../.." && uvicorn optimize.dashboard.app:app --host "$DASH_BIND_IP" --port "${DASH_CONTROL_PORT:-8350}" ) \
  > "$HERE/control.log" 2>&1 &
echo "control-plane pid $!"

# 3) Telegram bot (long-poll; no inbound port needed)
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  ( cd "$HERE/../.." && python3 -m optimize.dashboard.bot ) > "$HERE/bot.log" 2>&1 &
  echo "bot pid $!"
else
  echo "TELEGRAM_BOT_TOKEN unset — skipping bot"
fi
wait
