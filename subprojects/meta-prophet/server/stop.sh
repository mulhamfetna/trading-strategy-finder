#!/usr/bin/env bash
# Stop a running training job (graceful TERM, then KILL after 10s).
#   ./stop.sh <run_id>
source "$(dirname "$0")/lib.sh"
run="${1:-}"; [ -z "$run" ] && die "usage: stop.sh <run_id>"
srv "pid=\$(cat '$REMOTE_RUNS/$run/.pid' 2>/dev/null); \
     if [ -z \"\$pid\" ]; then echo 'no pid file for $run'; exit 0; fi; \
     if kill -0 \$pid 2>/dev/null; then kill -TERM \$pid && echo 'sent TERM to '\$pid; \
       for i in \$(seq 1 10); do kill -0 \$pid 2>/dev/null || break; sleep 1; done; \
       kill -0 \$pid 2>/dev/null && { kill -KILL \$pid; echo 'KILLED '\$pid; } || echo 'stopped cleanly'; \
     else echo '$run not running'; fi"
