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
do_stop() { pkill -f "$MATCH" 2>/dev/null && echo "■ stopped dashboard on :$PORT" || echo "· nothing running on :$PORT"; }

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
if pgrep -f "$MATCH" >/dev/null 2>&1; then
  echo "· clearing a stale/wedged server on :$PORT"; pkill -9 -f "$MATCH" 2>/dev/null; sleep 1
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
