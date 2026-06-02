#!/usr/bin/env bash
# Show run status + GPU/host load. With a run_id, reports whether its PID is alive.
#   ./status.sh [run_id]
source "$(dirname "$0")/lib.sh"

run="${1:-}"
log "host load / GPU:"
srv 'echo "uptime:$(uptime | sed "s/.*average://")"; echo "mem: $(free -g | awk "/Mem:/{print \$7\"GiB free / \"\$2\"GiB\"}")";
     HSA_OVERRIDE_GFX_VERSION=10.3.0 rocm-smi --showuse --showmemuse 2>/dev/null | grep -E "GPU\[0\]|use" | head -6 || true'
echo
if [ -n "$run" ]; then
  srv "pid=\$(cat '$REMOTE_RUNS/$run/.pid' 2>/dev/null); \
       if [ -n \"\$pid\" ] && kill -0 \$pid 2>/dev/null; then echo 'RUN $run: ALIVE (pid '\$pid')'; \
       else echo 'RUN $run: not running'; fi; \
       echo '--- last 8 log lines ---'; tail -n 8 '$REMOTE_LOGS/$run.log' 2>/dev/null || echo '(no log)'; \
       echo '--- outputs ---'; ls -la '$REMOTE_RUNS/$run' 2>/dev/null || true"
else
  log "all runs:"; srv "ls -1 '$REMOTE_RUNS' 2>/dev/null || echo '(none)'"
fi
