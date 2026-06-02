#!/usr/bin/env bash
# One-time (idempotent) remote environment setup + verification.
#  - ensures scratch dirs exist
#  - verifies the reusable venv + torch-ROCm GPU (forced gfx1031 override)
#  - installs any extra deps we need (darts, etc.) into the venv on request
#
#   ./setup_remote.sh            # verify only
#   ./setup_remote.sh --deps     # also pip-install darts + friends
source "$(dirname "$0")/lib.sh"

log "ensuring scratch dirs"
srv "mkdir -p '$REMOTE_DATA' '$REMOTE_CODE' '$REMOTE_RUNS' '$REMOTE_LOGS'"

log "verifying torch-ROCm GPU (forced gfx1031)"
srv "export $GPU_ENV; '$REMOTE_VENV/bin/python' - <<'PY'
import torch
print('torch', torch.__version__, '| hip', getattr(torch.version,'hip',None))
ok = torch.cuda.is_available()
print('cuda.is_available:', ok)
print('device:', torch.cuda.get_device_name(0) if ok else 'NONE')
assert ok, 'GPU not visible — aborting (forced-GPU mode)'
PY"

if [ "${1:-}" = "--deps" ]; then
  log "installing extra deps (darts, statsforecast, pandas) into the venv"
  srv "export $GPU_ENV; '$REMOTE_VENV/bin/pip' install --upgrade pip >/dev/null; \
       '$REMOTE_VENV/bin/pip' install 'darts' 'statsforecast' 'pandas' 'pyarrow' 2>&1 | tail -5"
  srv "'$REMOTE_VENV/bin/pip' list 2>/dev/null | grep -iE 'darts|statsforecast|pandas|torch' "
fi
log "remote ready."
