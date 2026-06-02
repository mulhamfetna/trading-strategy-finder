#!/usr/bin/env bash
# Shared helpers for the remote-training toolkit. Source this from every script.
#   source "$(dirname "$0")/lib.sh"
set -euo pipefail

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$_HERE/server.env"

SSH_OPTS=(-p "$SRV_PORT" -i "$SRV_KEY" -o IdentitiesOnly=yes -o BatchMode=yes \
          -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
          -o ServerAliveInterval=30 -o ServerAliveCountMax=4)

# Run a command on the server (key auth, non-interactive).
srv() { ssh "${SSH_OPTS[@]}" "${SRV_USER}@${SRV_HOST}" "$@"; }

# rsync transport string for -e
RSYNC_E="ssh -p $SRV_PORT -i $SRV_KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

# Push local path -> remote path (trailing-slash semantics are the caller's job).
push() { rsync -az --info=stats1,progress2 -e "$RSYNC_E" "$1" "${SRV_USER}@${SRV_HOST}:$2"; }
# Pull remote path -> local path.
pull() { rsync -az --info=stats1,progress2 -e "$RSYNC_E" "${SRV_USER}@${SRV_HOST}:$1" "$2"; }

log() { printf '\033[1;36m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }
