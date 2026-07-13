#!/usr/bin/env bash
# run_dashboard.sh — LOCAL dashboard launcher.
#
# ┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
# │  ⚠️  THE LOCAL DASHBOARD IS FROZEN. IT IS NOT THE LIVE ONE. DO NOT TRUST ITS NUMBERS.            │
# │                                                                                                  │
# │  The live, maintained dashboard runs on the AMD SERVER as a supervised shared service:           │
# │       private / VPN :  http://192.168.50.62:8200/                                                 │
# │       public        :  http://78.89.209.212:8200/                                                 │
# │       manage it     :  ssh amd-trading '~/Mulham/wsg-i/dash.sh {status|refresh}'                  │
# │                                                                                                  │
# │  WHY THIS ONE IS FROZEN:                                                                          │
# │   • It runs on a 12-core / 14 GB laptop. Selecting a 2-minute or 5-minute timeframe has already   │
# │     OOM-frozen that machine once. Heavy timeframes are SERVER-ONLY.                               │
# │   • It is not refreshed when champions change, so it can silently serve an OLD champion set —     │
# │     the most dangerous failure mode we have, because the numbers still look plausible.            │
# │                                                                                                  │
# │  If you really need it (light timeframes only, and you accept the numbers may be stale):          │
# │       LOCAL_DASHBOARD_OK=1 ./run_dashboard.sh                                                     │
# └──────────────────────────────────────────────────────────────────────────────────────────────────┘
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

# ── FROZEN BANNER ───────────────────────────────────────────────────────────────────────────────────
# This is a FLAG, not a gate: it starts normally, but says loudly what it is. `stop`/`status` stay quiet.
case "${1:-start}" in
  stop|status) ;;
  *)
    cat <<'FROZEN'

  ╔════════════════════════════════════════════════════════════════════════════════════╗
  ║  ⚠️  LOCAL DASHBOARD — FROZEN COPY (not the live one)                               ║
  ╚════════════════════════════════════════════════════════════════════════════════════╝

   • Its champion set is NOT auto-synced with the server, so it can serve an OLD champion
     and still look completely plausible. Re-sync before trusting a number.
   • Heavy timeframes (2m / 5m) have OOM-frozen this 14 GB box before — prefer the server
     for those.

   LIVE (always current):  http://192.168.50.62:8200/   ·   http://78.89.209.212:8200/
                           ssh amd-trading '~/Mulham/wsg-i/dash.sh status'

   Starting the local copy anyway...

FROZEN
    ;;
esac

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
