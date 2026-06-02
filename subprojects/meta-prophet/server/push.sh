#!/usr/bin/env bash
# Push data and/or code to the server scratch. Local is the source of truth.
#   ./push.sh data   <local_csv_or_dir>      -> REMOTE_DATA/
#   ./push.sh code    <local_dir_or_file>    -> REMOTE_CODE/
#   ./push.sh path    <local_src> <remote_dst_abs>
source "$(dirname "$0")/lib.sh"

sub="${1:-}"; src="${2:-}"
[ -z "$sub" ] && die "usage: push.sh {data|code|path} <src> [remote_dst]"
[ -e "$src" ] || die "local source not found: $src"
srv "mkdir -p '$REMOTE_DATA' '$REMOTE_CODE' '$REMOTE_RUNS' '$REMOTE_LOGS'"

case "$sub" in
  data) log "push data: $src -> $REMOTE_DATA/"; push "$src" "$REMOTE_DATA/" ;;
  code) log "push code: $src -> $REMOTE_CODE/"; push "$src" "$REMOTE_CODE/" ;;
  path) dst="${3:-}"; [ -z "$dst" ] && die "path mode needs <remote_dst_abs>"
        log "push: $src -> $dst"; push "$src" "$dst" ;;
  *) die "unknown subcommand: $sub" ;;
esac
log "done."
