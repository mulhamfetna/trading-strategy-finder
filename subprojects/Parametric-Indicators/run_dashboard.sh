#!/usr/bin/env bash
# run_dashboard.sh — one-click launch of the unified L1 · L2 · Combined dashboard.
#
#   ./run_dashboard.sh            start (if not already running) + open it in your browser
#   ./run_dashboard.sh stop       stop the dashboard server
#   ./run_dashboard.sh restart    stop then start fresh (picks up code changes)
#   ./run_dashboard.sh status     just report whether it's up
#   PORT=8300 ./run_dashboard.sh  use a different port (default 8200)
#   PYTHON=./.venv/bin/python ./run_dashboard.sh   use a specific interpreter
#
# The server runs detached (setsid → its own session) so it survives this script AND the terminal closing.
# If it says "already running" but you changed code or it's stale, use:  ./run_dashboard.sh restart

# absolute dir of this script = the Parametric-Indicators project (portable: works under bash and zsh)
HERE="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]:-$0}")")" && pwd)"
cd "$HERE" || { echo "cannot cd to $HERE"; exit 1; }

PORT="${PORT:-8200}"
PY="${PYTHON:-python3}"
URL="http://localhost:${PORT}/"
LOG="/tmp/wsi_dashboard_${PORT}.log"
MATCH="server.py --port ${PORT}"

is_up()  { curl -s -m2 "http://localhost:${PORT}/api/health" >/dev/null 2>&1; }
do_open() {
  if   command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" >/dev/null 2>&1 &
  elif command -v open     >/dev/null 2>&1; then open "$URL"     >/dev/null 2>&1 &
  else echo "   open this in your browser → $URL"; fi
}
# Kill ANY running dashboard backend, not just one whose cmdline contains "--port $PORT". A stale server
# started a different way (python3 server.py, a different port, the IDE, a prior session) would otherwise
# survive `restart` and keep serving OLD code — the #1 cause of "I restarted but the results didn't change".
BROAD='[s]erver\.py'                              # bracket trick: never matches this script's own cmdline
do_stop() {
  if pgrep -f "$BROAD" >/dev/null 2>&1; then
    pkill -9 -f "$BROAD" 2>/dev/null; sleep 1; echo "■ stopped all server.py backends"
  else echo "· no server.py backend running"; fi
}

case "${1:-start}" in
  stop)    do_stop; exit 0 ;;
  status)  is_up && echo "✓ up   → $URL" || echo "· down (:$PORT)"; exit 0 ;;
  restart) do_stop; sleep 1 ;;
  start|"") ;;
  *) echo "usage: $0 [start|stop|restart|status]"; exit 2 ;;
esac

if is_up; then
  echo "✓ dashboard already running → $URL"
  do_open
  exit 0
fi

# Reached here ⇒ NOT healthy. Clear any wedged/stale server.py still bound to this port (a frozen run can
# leave one that fails health checks but holds the port → a fresh start would hit 'Address already in use').
if pgrep -f "$BROAD" >/dev/null 2>&1; then
  echo "· clearing a stale/wedged server.py before start"; pkill -9 -f "$BROAD" 2>/dev/null; sleep 1
fi

echo "▶ starting dashboard on :$PORT  (log: $LOG)"
# setsid → its own session, so it survives this script, the terminal closing, AND a parent process-group kill
setsid "$PY" server.py --port "$PORT" < /dev/null > "$LOG" 2>&1 &
for i in {1..60}; do
  if is_up; then echo "✓ ready → $URL"; do_open; exit 0; fi
  sleep 1
done
echo "⚠ server did not become healthy within 60s — last log lines:"
tail -n 8 "$LOG"
exit 1
