#!/usr/bin/env bash
# ============================================================================
#  dash.sh — shared control for the WSG "Unified Dashboard — Layer 1" backtester
#  Binds 0.0.0.0:8200 → reachable by anyone with access to this server.
#  Self-restarting (survives logout, auto-restarts on crash). No sudo needed.
#
#  Usage:  ./dash.sh {start | stop | restart | refresh | status | logs}
#    start    – launch the dashboard (no-op if already up)
#    refresh  – restart to pick up code/champion changes (same as restart)
#    status   – show pid, port, URLs and a live health check
#    logs     – tail the server log
# ============================================================================
set -uo pipefail

PORT=8200
BASE=/home/dev/Mulham/wsg-i
APP=$BASE/Parametric-Indicators
LOG=$BASE/logs/dashboard.log
SUP_PID=$BASE/dash_supervisor.pid
PRIVATE_IP=192.168.50.62
PUBLIC_IP=78.89.209.212

_run_server() {                       # one server.py lifetime (foreground)
  source /home/dev/Mulham/.venv/bin/activate
  [ -f "$BASE/pg.env" ] && { set -a; . "$BASE/pg.env"; set +a; }
  export WSH_DATA_BASE="$BASE" WSG_DATA_ROOT="$BASE/data"
  cd "$APP" || exit 1
  exec python3 server.py --port "$PORT"
}

_supervise() {                        # restart-on-crash loop (internal)
  echo "[$(date '+%F %T')] supervisor up (pid $$)" >> "$LOG"
  while true; do
    ( _run_server ) >> "$LOG" 2>&1
    echo "[$(date '+%F %T')] server.py exited ($?) — restarting in 2s" >> "$LOG"
    sleep 2
  done
}

case "${1:-}" in
  __supervise) _supervise ;;          # internal entry point

  start)
    if pgrep -f "server.py --port $PORT" >/dev/null; then
      echo "dashboard already running"; "$0" status; exit 0; fi
    mkdir -p "$BASE/logs"
    setsid bash "$0" __supervise </dev/null >>"$LOG" 2>&1 &
    echo $! > "$SUP_PID"
    sleep 2; "$0" status ;;

  stop)
    if [ -f "$SUP_PID" ]; then
      kill -TERM -- -"$(cat "$SUP_PID")" 2>/dev/null   # kill the whole supervisor group
      rm -f "$SUP_PID"
    fi
    pkill -f "dash.sh __supervise" 2>/dev/null
    pkill -f "server.py --port $PORT" 2>/dev/null
    echo "dashboard stopped" ;;

  restart|refresh)
    "$0" stop; sleep 1; "$0" start ;;

  status)
    if pgrep -f "server.py --port $PORT" >/dev/null; then
      pid=$(pgrep -f "server.py --port $PORT" | head -1)
      echo "● RUNNING   pid=$pid   port=$PORT   (binds 0.0.0.0)"
      echo "    on the server :  http://localhost:$PORT/"
      echo "    private / VPN :  http://$PRIVATE_IP:$PORT/"
      echo "    public       :  http://$PUBLIC_IP:$PORT/"
      code=$(curl -s -o /dev/null -m 5 -w "%{http_code}" "http://localhost:$PORT/" 2>/dev/null)
      echo "    health check :  HTTP ${code:-timeout}"
    else
      echo "○ NOT running  —  start with:  ./dash.sh start"
    fi ;;

  logs) tail -n "${2:-60}" -f "$LOG" ;;

  *) echo "usage: $0 {start|stop|restart|refresh|status|logs}"; exit 1 ;;
esac
